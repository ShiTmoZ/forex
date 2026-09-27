"""
Comprehensive Multi-Asset Backtester & Trainer (2020-2026)
Assets Covered:
- Forex Majors: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD
- Commodities & Precious Metals: XAUUSD (Gold), XAGUSD (Silver), USOIL
- Major Global Indices: ^GSPC (S&P 500), ^IXIC (Nasdaq Composite), ^DJI (Dow Jones), ^RUT (Russell 2000), ^FTSE, ^GDAXI, ^N225
- Top 50 US Equities (S&P 500 & Nasdaq 100 leaders):
  AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AVGO, COST, PEP,
  ADBE, CSCO, NFLX, AMD, INTC, TXN, AMAT, QCOM, HON, INTC,
  JPM, V, MA, BAC, WMT, PG, JNJ, UNH, HD, LLY,
  ABBV, MRK, KO, PEP, CVX, XOM, MCD, DIS, NKE, CAT,
  BA, GE, IBM, CRM, ORCL, NOW, PANW, UBER, ABNB, PLTR
"""

import os
import sys
import json
import time
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Asset Universe
ASSET_UNIVERSE = {
    "Forex_Majors": [
        "EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X", "CAD=X", "CHF=X", "NZDUSD=X"
    ],
    "Commodities": [
        "GC=F", "SI=F", "CL=F"
    ],
    "Indices": [
        "^GSPC", "^IXIC", "^DJI", "^RUT", "^FTSE", "^GDAXI", "^N225"
    ],
    "Top_50_Equities": [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP",
        "ADBE", "CSCO", "NFLX", "AMD", "INTC", "TXN", "AMAT", "QCOM", "HON", "AMGN",
        "JPM", "V", "MA", "BAC", "WMT", "PG", "JNJ", "UNH", "HD", "LLY",
        "ABBV", "MRK", "KO", "CVX", "XOM", "MCD", "DIS", "NKE", "CAT", "BA",
        "GE", "IBM", "CRM", "ORCL", "NOW", "PANW", "UBER", "ABNB", "PLTR", "SNOW"
    ]
}

def fetch_historical_series(ticker, period1=1577836800, period2=1774900000, interval="1h"):
    """
    Fetch multi-year historical candles using Yahoo Finance API without any external packages.
    1577836800 corresponds to Jan 1, 2020.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?period1={period1}&period2={period2}&interval={interval}&includePrePost=true"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        result = data.get("chart", {}).get("result")
        if not result:
            return []
        
        timestamps = result[0].get("timestamp", [])
        quote = result[0].get("indicators", {}).get("quote", [{}])[0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])
        
        candles = []
        for i in range(len(timestamps)):
            if None in (timestamps[i], opens[i], highs[i], lows[i], closes[i]):
                continue
            candles.append({
                "timestamp": timestamps[i],
                "open": opens[i],
                "high": highs[i],
                "low": lows[i],
                "close": closes[i],
                "volume": volumes[i] if volumes and i < len(volumes) and volumes[i] is not None else 0
            })
        return candles
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return []

def evaluate_session_strategy(candles, session_start_utc=0, session_end_utc=7, trade_end_utc=16):
    """
    Backtest Asian Range sweep and London Judas swing across historical candles.
    """
    if len(candles) < 20:
        return {"trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "net_r": 0.0}
    
    # Group by day
    days = {}
    for c in candles:
        dt = datetime.fromtimestamp(c["timestamp"], tz=timezone.utc)
        d_str = dt.strftime("%Y-%m-%d")
        if d_str not in days:
            days[d_str] = []
        days[d_str].append(c)
        
    trades = []
    
    for d_str, day_candles in days.items():
        session_candles = []
        trade_candles = []
        
        for c in day_candles:
            dt = datetime.fromtimestamp(c["timestamp"], tz=timezone.utc)
            if session_start_utc <= dt.hour < session_end_utc:
                session_candles.append(c)
            elif session_end_utc <= dt.hour < trade_end_utc:
                trade_candles.append(c)
                
        if len(session_candles) < 3 or not trade_candles:
            continue
            
        s_high = max(c["high"] for c in session_candles)
        s_low = min(c["low"] for c in session_candles)
        range_size = s_high - s_low
        if range_size <= 0:
            continue
            
        # Check sweep and reversal
        for i, tc in enumerate(trade_candles):
            # Bullish sweep of low (SFP / Judas Swing)
            if tc["low"] < s_low and tc["close"] > s_low:
                entry = tc["close"]
                sl = tc["low"] - (range_size * 0.1)
                risk = entry - sl
                if risk <= 0:
                    continue
                tp = entry + (risk * 2.0)
                
                # Intra-day resolution
                outcome = "TIMEOUT"
                net_r = 0.0
                for fc in trade_candles[i+1:]:
                    if fc["low"] <= sl:
                        outcome = "LOSS"
                        net_r = -1.0
                        break
                    elif fc["high"] >= tp:
                        outcome = "WIN"
                        net_r = 2.0
                        break
                trades.append({"outcome": outcome, "net_r": net_r})
                break
                
            # Bearish sweep of high
            elif tc["high"] > s_high and tc["close"] < s_high:
                entry = tc["close"]
                sl = tc["high"] + (range_size * 0.1)
                risk = sl - entry
                if risk <= 0:
                    continue
                tp = entry - (risk * 2.0)
                
                outcome = "TIMEOUT"
                net_r = 0.0
                for fc in trade_candles[i+1:]:
                    if fc["high"] >= sl:
                        outcome = "LOSS"
                        net_r = -1.0
                        break
                    elif fc["low"] <= tp:
                        outcome = "WIN"
                        net_r = 2.0
                        break
                trades.append({"outcome": outcome, "net_r": net_r})
                break

    total = len(trades)
    wins = len([t for t in trades if t["outcome"] == "WIN"])
    losses = len([t for t in trades if t["outcome"] == "LOSS"])
    net_r = sum(t["net_r"] for t in trades)
    wr = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0
    
    return {
        "trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 2),
        "net_r": round(net_r, 2)
    }

def main():
    print("=" * 60)
    print("MULTI-ASSET INSTITUTIONAL BACKTEST RUNNER (2020-2026)")
    print("=" * 60)
    
    summary = {}
    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_net_r = 0.0
    
    for category, tickers in ASSET_UNIVERSE.items():
        print(f"\nProcessing Category: {category} ({len(tickers)} symbols)...")
        cat_trades = 0
        cat_wins = 0
        cat_losses = 0
        cat_net_r = 0.0
        cat_results = {}
        
        for t in tickers:
            candles = fetch_historical_series(t)
            res = evaluate_session_strategy(candles)
            cat_results[t] = res
            cat_trades += res["trades"]
            cat_wins += res["wins"]
            cat_losses += res["losses"]
            cat_net_r += res["net_r"]
            print(f"  [{t:10}] Trades: {res['trades']:3} | Wins: {res['wins']:2} | Losses: {res['losses']:2} | WR: {res['win_rate']:5.1f}% | Net R: {res['net_r']:+6.2f}R")
            time.sleep(0.3)
            
        cat_wr = (cat_wins / (cat_wins + cat_losses) * 100.0) if (cat_wins + cat_losses) > 0 else 0.0
        summary[category] = {
            "trades": cat_trades,
            "wins": cat_wins,
            "losses": cat_losses,
            "win_rate": round(cat_wr, 2),
            "net_r": round(cat_net_r, 2),
            "symbols": cat_results
        }
        total_trades += cat_trades
        total_wins += cat_wins
        total_losses += cat_losses
        total_net_r += cat_net_r
        
    overall_wr = (total_wins / (total_wins + total_losses) * 100.0) if (total_wins + total_losses) > 0 else 0.0
    overall = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_trades": total_trades,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "overall_win_rate": round(overall_wr, 2),
        "total_net_r": round(total_net_r, 2),
        "categories": summary
    }
    
    with open("multi_asset_backtest_report.json", "w") as f:
        json.dump(overall, f, indent=2)
        
    print("\n" + "=" * 60)
    print(f"OVERALL BACKTEST COMPLETE: {total_trades} Trades | WR: {overall_wr:.2f}% | Total Net R: {total_net_r:+.2f}R")
    print("=" * 60)

if __name__ == "__main__":
    main()
