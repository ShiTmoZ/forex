"""
Forex & Commodities Tokyo/London Institutional Engine - Production Live Supervisor Daemon.
Continuously monitors session transitions, detects London Breakouts and Judas SFP Reversals,
manages open trade lifecycles (Breakeven @ +1.0R), and dispatches formal Telegram alerts.
"""

import time
import os
import signal
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from config import (
    SYMBOLS_CONFIG,
    ASIAN_SESSION_START_HOUR,
    ASIAN_SESSION_END_HOUR,
    LONDON_SESSION_START_HOUR,
    LONDON_SESSION_END_HOUR,
    PAPER_TRADING,
    LOG_FILE,
    BREAKEVEN_TRIGGER_R
)
from data_loader import fetch_historical_candles
from strategy import ForexStrategyEngine, compute_ema
from telegram_notifier import ForexTelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ForexEngine")

RUNNING = True

def handle_exit(signum, frame):
    global RUNNING
    logger.info(f"Received exit signal ({signum}). Gracefully terminating supervisor...")
    RUNNING = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def get_current_session(dt_utc: datetime) -> str:
    h = dt_utc.hour
    if ASIAN_SESSION_START_HOUR <= h < ASIAN_SESSION_END_HOUR:
        return "TOKYO (ASIAN RANGE ACCUMULATION)"
    elif LONDON_SESSION_START_HOUR <= h < LONDON_SESSION_END_HOUR:
        return "LONDON (INSTITUTIONAL EXPANSION / SFP)"
    elif 12 <= h < 17:
        return "NEW YORK (US FIX / CONTINUATION)"
    return "OFF-HOURS / PRE-MARKET"

class ForexSupervisor:
    def __init__(self):
        self.notifier = ForexTelegramNotifier()
        self.processed_signals = set()
        self.open_trades: List[Dict[str, Any]] = []
        self.trade_counter = 0
        self.last_heartbeat_hour = -1
        self.last_session_label = ""

    def run_cycle(self):
        now_utc = datetime.now(timezone.utc)
        current_session = get_current_session(now_utc)

        # Heartbeat / Session Change Notification
        if now_utc.hour != self.last_heartbeat_hour or current_session != self.last_session_label:
            logger.info(f"=== Session Update: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} | Active: {current_session} ===")
            self.last_heartbeat_hour = now_utc.hour
            self.last_session_label = current_session

        for sym, cfg in SYMBOLS_CONFIG.items():
            name = cfg["display_name"]
            pip_size = cfg["pip_size"]
            try:
                # 15m candles
                candles = fetch_historical_candles(sym, range_str="5d", use_cache=False)
                if len(candles) < 30:
                    continue

                last_c = candles[-1]
                closes = [c["close"] for c in candles]
                ema50 = compute_ema(closes, period=50)

                engine = ForexStrategyEngine(sym)
                today_str = now_utc.strftime("%Y-%m-%d")
                day_candles = [c for c in candles if c["date"] == today_str]

                asian_metrics = engine.extract_asian_range(day_candles)
                if not asian_metrics:
                    continue

                # Check if active in London execution window
                if LONDON_SESSION_START_HOUR <= now_utc.hour < LONDON_SESSION_END_HOUR:
                    setup = engine.evaluate_london_setup(last_c, asian_metrics, ema50[-1])
                    if setup:
                        sig_id = f"{sym}_{setup['type']}_{last_c['timestamp']}"
                        if sig_id not in self.processed_signals:
                            self.processed_signals.add(sig_id)
                            self.trade_counter += 1
                            trade_id = self.trade_counter

                            logger.info(
                                f"SIGNAL [{name}] {setup['type']} {setup['side']} @ "
                                f"{setup['entry_price']:.5f} | SL: {setup['stop_loss']:.5f} | TP: {setup['take_profit']:.5f}"
                            )

                            # Dispatch Telegram Alert
                            self.notifier.notify_signal(sym, name, pip_size, setup)

                            # Register Active Position
                            self.open_trades.append({
                                "id": trade_id,
                                "symbol": sym,
                                "display_name": name,
                                "pip_size": pip_size,
                                "side": setup["side"],
                                "entry_price": setup["entry_price"],
                                "stop_loss": setup["stop_loss"],
                                "initial_sl": setup["stop_loss"],
                                "take_profit": setup["take_profit"],
                                "risk": setup["risk"],
                                "breakeven_active": False,
                                "open_time": last_c.get("datetime_iso", "")
                            })

                # Lifecycle Manager for Open Positions
                self._update_open_trades(sym, last_c)

            except Exception as e:
                logger.error(f"Error scanning {name}: {e}")

    def _update_open_trades(self, symbol: str, current_candle: Dict[str, Any]):
        active_list = []
        high = current_candle["high"]
        low = current_candle["low"]

        for trade in self.open_trades:
            if trade["symbol"] != symbol:
                active_list.append(trade)
                continue

            side = trade["side"]
            entry = trade["entry_price"]
            sl = trade["stop_loss"]
            tp = trade["take_profit"]
            risk = trade["risk"]
            pip_size = trade["pip_size"]
            name = trade["display_name"]
            t_id = trade["id"]

            closed = False
            result = ""
            exit_price = 0.0
            pnl_r = 0.0

            if side == "BUY":
                # Check Breakeven (+1.0R)
                if not trade["breakeven_active"] and (high - entry) >= (risk * BREAKEVEN_TRIGGER_R):
                    trade["breakeven_active"] = True
                    trade["stop_loss"] = entry + (1.2 * pip_size)  # Move SL to Entry + Spread
                    logger.info(f"[{name} #{t_id}] Breakeven reached. SL advanced to {trade['stop_loss']:.5f}")
                    self.notifier.notify_breakeven(symbol, name, t_id, entry, pip_size)

                # Check Stop Loss
                if low <= sl:
                    closed = True
                    exit_price = sl
                    result = "BREAKEVEN_EXIT" if trade["breakeven_active"] else "STOP_LOSS"
                    pnl_r = 0.0 if trade["breakeven_active"] else -1.0
                # Check Take Profit
                elif high >= tp:
                    closed = True
                    exit_price = tp
                    result = "TAKE_PROFIT"
                    pnl_r = trade.get("rr", 2.0)

            elif side == "SELL":
                # Check Breakeven (+1.0R)
                if not trade["breakeven_active"] and (entry - low) >= (risk * BREAKEVEN_TRIGGER_R):
                    trade["breakeven_active"] = True
                    trade["stop_loss"] = entry - (1.2 * pip_size)
                    logger.info(f"[{name} #{t_id}] Breakeven reached. SL advanced to {trade['stop_loss']:.5f}")
                    self.notifier.notify_breakeven(symbol, name, t_id, entry, pip_size)

                # Check Stop Loss
                if high >= sl:
                    closed = True
                    exit_price = sl
                    result = "BREAKEVEN_EXIT" if trade["breakeven_active"] else "STOP_LOSS"
                    pnl_r = 0.0 if trade["breakeven_active"] else -1.0
                # Check Take Profit
                elif low <= tp:
                    closed = True
                    exit_price = tp
                    result = "TAKE_PROFIT"
                    pnl_r = trade.get("rr", 2.0)

            if closed:
                logger.info(f"[{name} #{t_id}] Trade closed: {result} @ {exit_price:.5f} ({pnl_r:+.2f}R)")
                self.notifier.notify_trade_closed(symbol, name, t_id, side, result, exit_price, pnl_r, pip_size)
            else:
                active_list.append(trade)

        self.open_trades = active_list

    def start(self):
        logger.info(f"Institutional Forex Engine Supervisor Started (Paper Mode: {PAPER_TRADING}).")
        now_utc = datetime.now(timezone.utc)
        curr_session = get_current_session(now_utc)
        self.notifier.notify_engine_started(len(SYMBOLS_CONFIG), "Paper Execution", curr_session)

        while RUNNING:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Supervisor cycle exception: {e}")
            time.sleep(60)

        logger.info("Forex Engine Supervisor successfully shut down.")

if __name__ == "__main__":
    supervisor = ForexSupervisor()
    supervisor.start()
