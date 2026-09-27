"""
Forex & Commodities Tokyo-to-London Institutional Trading Engine Configuration.
Defines asset specifications, pip values, broker spreads, session hours, and risk parameters.
"""

from typing import Dict, Any

# Target Forex Pairs & Commodities
SYMBOLS_CONFIG: Dict[str, Dict[str, Any]] = {
    "EURUSD=X": {
        "display_name": "EUR/USD",
        "pip_size": 0.0001,
        "spread_pips": 1.2,
        "min_range_pips": 12.0,
        "max_range_pips": 50.0,
        "default_risk_reward": 2.0,
    },
    "GBPUSD=X": {
        "display_name": "GBP/USD",
        "pip_size": 0.0001,
        "spread_pips": 1.8,
        "min_range_pips": 15.0,
        "max_range_pips": 65.0,
        "default_risk_reward": 2.0,
    },
    "JPY=X": {
        "display_name": "USD/JPY",
        "pip_size": 0.01,
        "spread_pips": 1.5,
        "min_range_pips": 12.0,
        "max_range_pips": 55.0,
        "default_risk_reward": 2.0,
    },
    "AUDUSD=X": {
        "display_name": "AUD/USD",
        "pip_size": 0.0001,
        "spread_pips": 1.5,
        "min_range_pips": 10.0,
        "max_range_pips": 45.0,
        "default_risk_reward": 2.0,
    },
    "GC=F": {
        "display_name": "Gold (XAU/USD)",
        "pip_size": 0.10,
        "spread_pips": 3.5,
        "min_range_pips": 40.0,
        "max_range_pips": 250.0,
        "default_risk_reward": 2.2,
    }
}

# Session Timing in UTC
ASIAN_SESSION_START_HOUR = 0   # 00:00 UTC (Tokyo open)
ASIAN_SESSION_END_HOUR = 6     # 06:00 UTC (Tokyo close / pre-London)

LONDON_SESSION_START_HOUR = 7  # 07:00 UTC (London open / Frankfurt cross)
LONDON_SESSION_END_HOUR = 12   # 12:00 UTC (Pre-NY overlap)

NEW_YORK_SESSION_END_HOUR = 17 # 17:00 UTC (London close / US fix)

# Risk & Order Management
RISK_PER_TRADE_PERCENT = 1.0   # 1% equity risk
MAX_OPEN_POSITIONS = 3
BREAKEVEN_TRIGGER_R = 1.0      # Move SL to BE once trade reaches +1.0R
SLIPPAGE_BUFFER_PIPS = 0.5     # Additional pessimistic fill buffer

# Operational Parameters
PAPER_TRADING = True
LOG_FILE = "forex_engine.log"
DATABASE_PATH = "forex_trades.db"
