"""
Zero-dependency Forex & Commodity 15-Minute Data Ingestion Engine.
Connects directly to institutional public feeds, filters missing ticks, and caches cleanly.
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

def get_headers() -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

def fetch_historical_candles(symbol: str, range_str: str = "60d", use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Fetches 15-minute OHLCV candles for a given forex/commodity symbol.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    clean_sym = symbol.replace("=", "_").replace("^", "_")
    cache_file = os.path.join(CACHE_DIR, f"{clean_sym}_15m.json")

    # Use cache if fresh (< 2 hours old)
    if use_cache and os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if (time.time() - mtime) < 7200:
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range={range_str}"
    response = requests.get(url, headers=get_headers(), timeout=15)
    
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch data for {symbol}: HTTP {response.status_code}")

    data = response.json()
    result = data.get("chart", {}).get("result", [])
    if not result:
        raise ValueError(f"No chart data returned for {symbol}")

    chart = result[0]
    timestamps = chart.get("timestamp", [])
    quote = chart.get("indicators", {}).get("quote", [{}])[0]

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    clean_candles = []
    for i in range(len(timestamps)):
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if (volumes and i < len(volumes)) else 0.0

        if o is None or h is None or l is None or c is None:
            continue

        ts = int(timestamps[i])
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        clean_candles.append({
            "timestamp": ts,
            "datetime_iso": dt.isoformat(),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": float(v) if v is not None else 0.0,
            "hour": dt.hour,
            "minute": dt.minute,
            "date": dt.strftime("%Y-%m-%d")
        })

    with open(cache_file, "w") as f:
        json.dump(clean_candles, f)

    return clean_candles
