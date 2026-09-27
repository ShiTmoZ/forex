"""
Forex & Commodities Tokyo-to-London Institutional Engine - Telegram Dispatcher.
Delivers formal, luxury, zero-emoji institutional trading signals with exact instrument precision.
"""

import os
import json
import urllib.request
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ForexTelegram")

class ForexTelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or self._load_token()
        self.chat_id = chat_id or "7441068375"

    def _load_token(self) -> str:
        env_paths = ["/root/.hermes/.env", "/root/.env"]
        for p in env_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("TELEGRAM_BOT_TOKEN="):
                                return line.split("=", 1)[1].strip()
                except Exception:
                    pass
        return ""

    def send_message(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram dispatch skipped: Missing bot_token or chat_id.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Telegram dispatch failed: {e}")
            return False

    @staticmethod
    def _format_price(val: float, pip_size: float) -> str:
        if pip_size >= 0.1:
            return f"{val:,.2f}"
        elif pip_size >= 0.01:
            return f"{val:,.3f}"
        else:
            return f"{val:,.5f}"

    def notify_engine_started(self, active_pairs: int, mode: str, session: str):
        msg = (
            f"*INSTITUTIONAL FOREX ENGINE ACTIVATED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Mode: `{mode}`\n"
            f"Monitored Assets: `{active_pairs} Tier-1 Pairs & Commodities`\n"
            f"Current Session: `{session}`\n"
            f"Strategy: `Tokyo Range Accumulation + London Expansion / SFP`\n"
            f"Risk Control: `1.0% Equity Risk | Breakeven @ +1.0R`\n"
            f"Status: `Online & Listening for Institutional Flow`"
        )
        self.send_message(msg)

    def notify_signal(self, symbol: str, display_name: str, pip_size: float, setup: Dict[str, Any]):
        entry = self._format_price(setup["entry_price"], pip_size)
        sl = self._format_price(setup["stop_loss"], pip_size)
        tp = self._format_price(setup["take_profit"], pip_size)
        risk_pips = setup["risk"] / pip_size

        msg = (
            f"*INSTITUTIONAL SIGNAL DETECTED: {display_name}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Setup Type: `{setup['type']}`\n"
            f"Direction: `{setup['side']}`\n"
            f"Entry Price: `{entry}`\n"
            f"Stop Loss: `{sl}` ({risk_pips:.1f} pips)\n"
            f"Take Profit: `{tp}` (RR 1:{setup['rr']:.1f})\n"
            f"Asian Range: `{setup['asian_range_pips']:.1f} pips`\n"
            f"Execution: `Paper Trading / Verified Strategy`\n"
            f"Timestamp: `{setup.get('time_utc', 'Live UTC')}`"
        )
        self.send_message(msg)

    def notify_breakeven(self, symbol: str, display_name: str, trade_id: int, entry_price: float, pip_size: float):
        entry = self._format_price(entry_price, pip_size)
        msg = (
            f"*BREAKEVEN PROTECTION ACTIVATED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Trade ID: `#{trade_id}` ({display_name})\n"
            f"Threshold: `+1.0R Reached`\n"
            f"Action: `Stop Loss moved to Entry + Spread ({entry})`\n"
            f"Capital Protection: `Risk-Free Trade Guaranteed`"
        )
        self.send_message(msg)

    def notify_trade_closed(self, symbol: str, display_name: str, trade_id: int, side: str,
                            result: str, exit_price: float, pnl_r: float, pip_size: float):
        exit_str = self._format_price(exit_price, pip_size)
        msg = (
            f"*TRADE CONCLUDED: {display_name}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Trade ID: `#{trade_id}` ({side})\n"
            f"Outcome: `{result}`\n"
            f"Exit Price: `{exit_str}`\n"
            f"Realized Return: `{pnl_r:+.2f} R`\n"
            f"Execution: `Institutional Paper Portfolio`"
        )
        self.send_message(msg)
