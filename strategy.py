"""
Institutional Forex Tokyo/London Breakout & Judas Swing Execution Strategy.
Identifies Asian Range consolidation, checks HTF trend bias, and evaluates London Open moves.
"""

from typing import List, Dict, Any, Optional
from config import (
    SYMBOLS_CONFIG,
    ASIAN_SESSION_START_HOUR,
    ASIAN_SESSION_END_HOUR,
    LONDON_SESSION_START_HOUR,
    LONDON_SESSION_END_HOUR
)

def compute_ema(prices: List[float], period: int = 50) -> List[float]:
    """Calculates Exponential Moving Average across a series."""
    if not prices:
        return []
    k = 2.0 / (period + 1)
    ema = [prices[0]]
    for p in prices[1:]:
        ema.append(p * k + ema[-1] * (1.0 - k))
    return ema

class ForexStrategyEngine:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.config = SYMBOLS_CONFIG[symbol]
        self.pip_size = self.config["pip_size"]
        self.spread = self.config["spread_pips"] * self.pip_size
        self.min_range = self.config["min_range_pips"] * self.pip_size
        self.max_range = self.config["max_range_pips"] * self.pip_size
        self.target_rr = self.config["default_risk_reward"]

    def extract_asian_range(self, day_candles: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
        """Computes High, Low, and Pip Size of Asian Session (00:00 - 06:00 UTC)."""
        asia = [c for c in day_candles if ASIAN_SESSION_START_HOUR <= c["hour"] < ASIAN_SESSION_END_HOUR]
        # At least 12 15m candles (3 hours) or 4 1h candles
        if len(asia) < 4:
            return None

        asian_high = max(c["high"] for c in asia)
        asian_low = min(c["low"] for c in asia)
        range_size = asian_high - asian_low

        if range_size < self.min_range or range_size > self.max_range:
            return None

        return {
            "asian_high": asian_high,
            "asian_low": asian_low,
            "range_size": range_size,
            "range_pips": range_size / self.pip_size,
            "equilibrium": (asian_high + asian_low) / 2.0
        }

    def evaluate_london_setup(
        self,
        candle: Dict[str, Any],
        asian_metrics: Dict[str, float],
        htf_ema: float
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates a single London candle for institutional breakout or Judas sweep reversal.
        """
        hour = candle["hour"]
        if not (LONDON_SESSION_START_HOUR <= hour < LONDON_SESSION_END_HOUR):
            return None

        ah = asian_metrics["asian_high"]
        al = asian_metrics["asian_low"]
        close = candle["close"]
        open_p = candle["open"]
        high = candle["high"]
        low = candle["low"]

        candle_range = high - low
        if candle_range <= 0:
            return None

        body = abs(close - open_p)
        body_ratio = body / candle_range

        # HTF Trend Bias
        trend = "BULLISH" if close > htf_ema else "BEARISH"

        # Mode A: London Displacement Breakout (With Trend + Body Confirmation)
        if trend == "BULLISH" and close > ah and body_ratio >= 0.55 and close > open_p:
            entry_price = close + self.spread
            stop_loss = low - (2.0 * self.pip_size)
            risk = entry_price - stop_loss
            if risk < (4.0 * self.pip_size) or risk > (asian_metrics["range_size"] * 0.85):
                return None
            take_profit = entry_price + (self.target_rr * risk)
            return {
                "type": "LONDON_EXPANSION_BREAKOUT",
                "side": "BUY",
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk": risk,
                "rr": self.target_rr,
                "asian_range_pips": asian_metrics["range_pips"],
                "time_utc": candle.get("datetime_iso", "")
            }

        elif trend == "BEARISH" and close < al and body_ratio >= 0.55 and close < open_p:
            entry_price = close - self.spread
            stop_loss = high + (2.0 * self.pip_size)
            risk = stop_loss - entry_price
            if risk < (4.0 * self.pip_size) or risk > (asian_metrics["range_size"] * 0.85):
                return None
            take_profit = entry_price - (self.target_rr * risk)
            return {
                "type": "LONDON_EXPANSION_BREAKOUT",
                "side": "SELL",
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk": risk,
                "rr": self.target_rr,
                "asian_range_pips": asian_metrics["range_pips"],
                "time_utc": candle.get("datetime_iso", "")
            }

        # Mode B: Judas Swing SFP Reversal (Sweep Extreme & Close Back Inside)
        # Bearish Judas: Pierced Asian High but closed back below Asian High
        if high > ah and close < ah and close < open_p:
            sweep_pips = (high - ah) / self.pip_size
            if 2.0 <= sweep_pips <= 25.0:
                entry_price = close - self.spread
                stop_loss = high + (1.5 * self.pip_size)
                risk = stop_loss - entry_price
                if (3.0 * self.pip_size) <= risk <= (asian_metrics["range_size"] * 0.75):
                    take_profit = entry_price - (self.target_rr * risk)
                    return {
                        "type": "JUDAS_SWING_SFP_REVERSAL",
                        "side": "SELL",
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "risk": risk,
                        "rr": self.target_rr,
                        "asian_range_pips": asian_metrics["range_pips"],
                        "time_utc": candle.get("datetime_iso", "")
                    }

        # Bullish Judas: Pierced Asian Low but closed back above Asian Low
        if low < al and close > al and close > open_p:
            sweep_pips = (al - low) / self.pip_size
            if 2.0 <= sweep_pips <= 25.0:
                entry_price = close + self.spread
                stop_loss = low - (1.5 * self.pip_size)
                risk = entry_price - stop_loss
                if (3.0 * self.pip_size) <= risk <= (asian_metrics["range_size"] * 0.75):
                    take_profit = entry_price + (self.target_rr * risk)
                    return {
                        "type": "JUDAS_SWING_SFP_REVERSAL",
                        "side": "BUY",
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "risk": risk,
                        "rr": self.target_rr,
                        "asian_range_pips": asian_metrics["range_pips"],
                        "time_utc": candle.get("datetime_iso", "")
                    }

        return None
