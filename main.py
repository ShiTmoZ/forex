"""
Forex & Commodities Tokyo/London Institutional Engine - Live / Paper Execution Supervisor.
Monitors session transitions (Tokyo -> London -> New York) and executes trades with spread control.
"""

import time
import json
import logging
from datetime import datetime, timezone
from config import (
    SYMBOLS_CONFIG,
    ASIAN_SESSION_START_HOUR,
    ASIAN_SESSION_END_HOUR,
    LONDON_SESSION_START_HOUR,
    LONDON_SESSION_END_HOUR,
    PAPER_TRADING,
    LOG_FILE
)
from data_loader import fetch_historical_candles
from strategy import ForexStrategyEngine, compute_ema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ForexEngine")

def get_current_session(dt_utc: datetime) -> str:
    h = dt_utc.hour
    if ASIAN_SESSION_START_HOUR <= h < ASIAN_SESSION_END_HOUR:
        return "TOKYO (ASIAN RANGE FORMATION)"
    elif LONDON_SESSION_START_HOUR <= h < LONDON_SESSION_END_HOUR:
        return "LONDON (INSTITUTIONAL EXPANSION / SWEEP)"
    elif 12 <= h < 17:
        return "NEW YORK (US FIX / CONTINUATION)"
    return "OFF-HOURS / LOW LIQUIDITY"

def run_supervisor_cycle():
    now_utc = datetime.now(timezone.utc)
    session_label = get_current_session(now_utc)
    logger.info(f"=== Session Heartbeat: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} | Active: {session_label} ===")

    for sym, cfg in SYMBOLS_CONFIG.items():
        name = cfg["display_name"]
        try:
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
                logger.info(f"[{name:15s}] Asian Range forming or pending. Last Close: {last_c['close']:.5f}")
                continue

            logger.info(
                f"[{name:15s}] Asian Range: {asian_metrics['range_pips']:.1f} pips "
                f"(H: {asian_metrics['asian_high']:.5f} | L: {asian_metrics['asian_low']:.5f}) | Price: {last_c['close']:.5f}"
            )

            # Check if active in London window
            if LONDON_SESSION_START_HOUR <= now_utc.hour < LONDON_SESSION_END_HOUR:
                setup = engine.evaluate_london_setup(last_c, asian_metrics, ema50[-1])
                if setup:
                    logger.info(
                        f"🚨 [{name}] SIGNAL DETECTED: {setup['type']} {setup['side']} @ {setup['entry_price']:.5f} "
                        f"| SL: {setup['stop_loss']:.5f} | TP: {setup['take_profit']:.5f}"
                    )
        except Exception as e:
            logger.error(f"[{name}] Scan error: {e}")

if __name__ == "__main__":
    logger.info(f"Starting Institutional Forex Engine (Paper Mode: {PAPER_TRADING})...")
    run_supervisor_cycle()
