"""
Institutional Forex & Commodities Multi-Asset Backtesting Engine.
Executes pessimistic backtests across EUR/USD, GBP/USD, USD/JPY, AUD/USD, and Gold (XAU/USD).
"""

import json
from typing import Dict, Any, List
from config import SYMBOLS_CONFIG
from data_loader import fetch_historical_candles
from strategy import ForexStrategyEngine, compute_ema
from risk_manager import ForexRiskManager

def run_backtest() -> Dict[str, Any]:
    print("=" * 65)
    print("  INSTITUTIONAL FOREX / GOLD BACKTEST RUNNER (60-DAY 15M FEEDS)")
    print("=" * 65)

    all_trades = []
    symbol_summaries = {}
    risk_mgr = ForexRiskManager()

    for sym, config in SYMBOLS_CONFIG.items():
        name = config["display_name"]
        print(f"[*] Ingesting data for {name} ({sym})...")
        try:
            candles = fetch_historical_candles(sym, range_str="60d", use_cache=True)
        except Exception as e:
            print(f"[-] Error loading {sym}: {e}")
            continue

        if len(candles) < 200:
            print(f"[-] Insufficient candles ({len(candles)}) for {name}")
            continue

        closes = [c["close"] for c in candles]
        ema50 = compute_ema(closes, period=50)

        engine = ForexStrategyEngine(sym)
        days: Dict[str, List[Dict[str, Any]]] = {}
        for idx, c in enumerate(candles):
            c["ema"] = ema50[idx]
            days.setdefault(c["date"], []).append(c)

        sym_trades: List[Dict[str, Any]] = []

        for d_str, day_candles in days.items():
            if len(day_candles) < 16:
                continue

            asian_metrics = engine.extract_asian_range(day_candles)
            if not asian_metrics:
                continue

            # Look for setup during London session
            day_traded = False
            for idx, c in enumerate(day_candles):
                if day_traded:
                    break

                setup = engine.evaluate_london_setup(c, asian_metrics, c["ema"])
                if setup:
                    future_candles = day_candles[idx + 1:]
                    if not future_candles:
                        continue

                    outcome = risk_mgr.simulate_trade(setup, future_candles, config["pip_size"])
                    trade_record = {
                        "symbol": sym,
                        "name": name,
                        "date": d_str,
                        "side": setup["side"],
                        "entry": setup["entry_price"],
                        "sl": setup["stop_loss"],
                        "tp": setup["take_profit"],
                        "range_pips": setup["asian_range_pips"],
                        "result": outcome["result"],
                        "pnl_r": outcome["pnl_r"]
                    }
                    sym_trades.append(trade_record)
                    all_trades.append(trade_record)
                    day_traded = True

        # Calculate metrics for symbol
        wins = sum(1 for t in sym_trades if t["result"] == "WIN")
        losses = sum(1 for t in sym_trades if t["result"] == "LOSS")
        bes = sum(1 for t in sym_trades if t["result"] == "BREAKEVEN")
        timeouts = sum(1 for t in sym_trades if t["result"] == "TIMEOUT")
        decided = wins + losses
        win_rate = (wins / decided * 100.0) if decided > 0 else 0.0
        net_r = sum(t["pnl_r"] for t in sym_trades)
        gross_w = sum(t["pnl_r"] for t in sym_trades if t["pnl_r"] > 0)
        gross_l = abs(sum(t["pnl_r"] for t in sym_trades if t["pnl_r"] < 0))
        pf = (gross_w / gross_l) if gross_l > 0 else (99.0 if gross_w > 0 else 0.0)

        symbol_summaries[sym] = {
            "name": name,
            "total_trades": len(sym_trades),
            "wins": wins,
            "losses": losses,
            "breakevens": bes,
            "timeouts": timeouts,
            "win_rate": round(win_rate, 1),
            "net_r": round(net_r, 2),
            "profit_factor": round(pf, 2)
        }

        print(f"    -> {name:16s} | Trades: {len(sym_trades):2d} | W: {wins:2d}, L: {losses:2d}, BE: {bes:2d} | WR: {win_rate:5.1f}% | Net R: {net_r:+6.2f}R | PF: {pf:4.2f}")

    # Total Portfolio Summary
    total_wins = sum(1 for t in all_trades if t["result"] == "WIN")
    total_losses = sum(1 for t in all_trades if t["result"] == "LOSS")
    total_bes = sum(1 for t in all_trades if t["result"] == "BREAKEVEN")
    total_timeouts = sum(1 for t in all_trades if t["result"] == "TIMEOUT")
    decided_all = total_wins + total_losses
    overall_wr = (total_wins / decided_all * 100.0) if decided_all > 0 else 0.0
    overall_net_r = sum(t["pnl_r"] for t in all_trades)
    gross_w_all = sum(t["pnl_r"] for t in all_trades if t["pnl_r"] > 0)
    gross_l_all = abs(sum(t["pnl_r"] for t in all_trades if t["pnl_r"] < 0))
    overall_pf = (gross_w_all / gross_l_all) if gross_l_all > 0 else (99.0 if gross_w_all > 0 else 0.0)

    print("-" * 65)
    print(f"  PORTFOLIO TOTAL: {len(all_trades)} Setups | W: {total_wins}, L: {total_losses}, BE: {total_bes}")
    print(f"  Win Rate (Decided): {overall_wr:.1f}% | Net Return: {overall_net_r:+.2f}R | Profit Factor: {overall_pf:.2f}")
    print("=" * 65)

    summary_data = {
        "portfolio": {
            "total_trades": len(all_trades),
            "wins": total_wins,
            "losses": total_losses,
            "breakevens": total_bes,
            "timeouts": total_timeouts,
            "win_rate": round(overall_wr, 1),
            "net_r": round(overall_net_r, 2),
            "profit_factor": round(overall_pf, 2)
        },
        "symbols": symbol_summaries,
        "trades": all_trades
    }

    with open("backtest_results.json", "w") as f:
        json.dump(summary_data, f, indent=2)

    return summary_data

if __name__ == "__main__":
    run_backtest()
