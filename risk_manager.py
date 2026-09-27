"""
Forex & Commodities Risk & Execution Manager.
Handles pip valuation, lot sizing, spread-adjusted order simulation, and breakeven trailing.
"""

from typing import Dict, Any, List
from config import (
    RISK_PER_TRADE_PERCENT,
    BREAKEVEN_TRIGGER_R,
    SLIPPAGE_BUFFER_PIPS
)

class ForexRiskManager:
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.risk_percent = RISK_PER_TRADE_PERCENT

    def calculate_lot_size(self, risk_amount: float, risk_pips: float, pip_value_per_lot: float = 10.0) -> float:
        """Calculates standard lots given risk budget and pip risk."""
        if risk_pips <= 0 or pip_value_per_lot <= 0:
            return 0.01
        lots = risk_amount / (risk_pips * pip_value_per_lot)
        return max(0.01, round(lots, 2))

    def simulate_trade(
        self,
        trade: Dict[str, Any],
        future_candles: List[Dict[str, Any]],
        pip_size: float
    ) -> Dict[str, Any]:
        """
        Simulates intra-candle trade lifecycle with pessimistic intra-bar fills and BE logic.
        """
        side = trade["side"]
        entry = trade["entry_price"]
        sl = trade["stop_loss"]
        tp = trade["take_profit"]
        risk = trade["risk"]
        rr = trade["rr"]

        current_sl = sl
        be_hit = False

        for c in future_candles:
            high = c["high"]
            low = c["low"]

            if side == "BUY":
                # Check Breakeven trigger: price reached +1.0R
                if not be_hit and high >= (entry + risk * BREAKEVEN_TRIGGER_R):
                    current_sl = entry + (SLIPPAGE_BUFFER_PIPS * pip_size)
                    be_hit = True

                # Check Stop Loss
                if low <= current_sl:
                    pnl_r = 0.0 if be_hit else -1.0
                    return {
                        "result": "BREAKEVEN" if be_hit else "LOSS",
                        "pnl_r": pnl_r,
                        "exit_price": current_sl,
                        "exit_time": c["timestamp"]
                    }

                # Check Take Profit
                if high >= tp:
                    return {
                        "result": "WIN",
                        "pnl_r": rr,
                        "exit_price": tp,
                        "exit_time": c["timestamp"]
                    }

            elif side == "SELL":
                # Check Breakeven trigger
                if not be_hit and low <= (entry - risk * BREAKEVEN_TRIGGER_R):
                    current_sl = entry - (SLIPPAGE_BUFFER_PIPS * pip_size)
                    be_hit = True

                # Check Stop Loss
                if high >= current_sl:
                    pnl_r = 0.0 if be_hit else -1.0
                    return {
                        "result": "BREAKEVEN" if be_hit else "LOSS",
                        "pnl_r": pnl_r,
                        "exit_price": current_sl,
                        "exit_time": c["timestamp"]
                    }

                # Check Take Profit
                if low <= tp:
                    return {
                        "result": "WIN",
                        "pnl_r": rr,
                        "exit_price": tp,
                        "exit_time": c["timestamp"]
                    }

        # Trade timed out at end of session
        return {
            "result": "TIMEOUT",
            "pnl_r": 0.0,
            "exit_price": future_candles[-1]["close"] if future_candles else entry,
            "exit_time": future_candles[-1]["timestamp"] if future_candles else 0
        }
