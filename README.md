<div align="center">

<img src="assets/banner.svg" alt="Forex Institutional Engine" width="100%" />

# Forex & Commodities Institutional Trading Engine
### Tokyo-to-London Session Breakout & Judas Swing Execution System

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![Actions Status](https://github.com/ShiTmoZ/forex/actions/workflows/forex_backtest.yml/badge.svg)](https://github.com/ShiTmoZ/forex/actions)
[![Market](https://img.shields.io/badge/market-Forex%20%26%20Commodities-amber.svg?style=flat-square)](https://github.com/ShiTmoZ/forex)
[![Architecture](https://img.shields.io/badge/stack-Pure%20Python%20%2F%20Zero--Dependency-purple.svg?style=flat-square)](https://github.com/ShiTmoZ/forex)

*A quantitative, session-driven algorithmic trading engine engineered specifically for tier-1 foreign exchange pairs and commodities. Captures London interbank order flow expansion following Asian session range consolidation.*

</div>

---

## 🏛️ Institutional Philosophy & Macro Edge

Unlike 24/7 retail cryptocurrency markets where order flow is continuous, the **Foreign Exchange (Forex)** market operates on a rigid, institutional clearing schedule dictated by central banks, multinational corporate settlements, and Tier-1 liquidity providers:

1. **Asian Session Consolidation (00:00 – 06:00 UTC):**
   Liquidity in Western currencies (EUR, GBP, USD) drops significantly. Price action establishes a well-defined institutional equilibrium range (Asian High / Asian Low).
2. **London Open Expansion & Interbank Fix (07:00 – 11:00 UTC):**
   European bank desks open in Frankfurt and London, injecting massive institutional capital into the market. Over 43% of global daily FX turnover executes during the London window.
3. **The Judas Swing (ICT / Institutional Manipulation):**
   Before the primary daily directional trend commences, market makers frequently engineer a false run (the Judas Swing) against the dominant higher-timeframe order flow to sweep retail liquidity parked at Asian session extremes.

---

## 📊 Market Coverage & Instrument Specifications

The engine trades primary macro instruments with exact pip-value modeling, realistic broker spreads, and dedicated volatility bands:

| Instrument | Symbol | Type | Pip Size | Base Spread | Min Range | Max Range |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **EUR / USD** | `EURUSD=X` | Major FX | `0.0001` | 1.2 pips | 12.0 pips | 45.0 pips |
| **GBP / USD** | `GBPUSD=X` | Major FX | `0.0001` | 1.8 pips | 15.0 pips | 55.0 pips |
| **USD / JPY** | `JPY=X` | Major FX | `0.01` | 1.5 pips | 15.0 pips | 50.0 pips |
| **AUD / USD** | `AUDUSD=X` | Commodity FX | `0.0001` | 1.5 pips | 12.0 pips | 45.0 pips |
| **USD / CAD** | `CAD=X` | Major FX | `0.0001` | 1.6 pips | 12.0 pips | 45.0 pips |
| **USD / CHF** | `CHF=X` | Major FX | `0.0001` | 1.5 pips | 12.0 pips | 45.0 pips |
| **NZD / USD** | `NZDUSD=X` | Major FX | `0.0001` | 1.8 pips | 12.0 pips | 45.0 pips |
| **Gold (XAU/USD)**| `GC=F` | Commodity | `0.10` | $0.35 | $5.00 | $35.00 |
| **Silver (XAG/USD)**| `SI=F` | Commodity | `0.005` | $0.03 | $0.20 | $1.50 |
| **Crude Oil (WTI)**| `CL=F` | Commodity | `0.01` | $0.04 | $0.50 | $3.00 |

---

## ⚙️ Execution Mechanics & Strategy Protocols

```
  00:00 UTC                           06:00 UTC           07:00 UTC - 11:00 UTC
      │                                   │                         │
      ▼                                   ▼                         ▼
┌───────────────────────────────────────────┐         ┌───────────────────────────┐
│        ASIAN RANGE CONSOLIDATION          │         │       LONDON OPENING      │
│  • Calculate Asian High & Low             │───────► │  • Volatility Expansion   │
│  • Verify Pip Compression (15-50 pips)    │         │  • Detect Judas Swing     │
│  • Establish 50-EMA Macro Trend Filter    │         │  • Retest / Breakout Entry│
└───────────────────────────────────────────┘         └─────────────┬─────────────┘
                                                                    │
                                            ┌───────────────────────┴───────────────────────┐
                                            ▼                                               ▼
                                 [Mode A: Breakout Run]                          [Mode B: Judas Swing]
                               • Clean candle close outside Asia               • Sweep of Asian Extreme
                               • Aligned with Daily 50-EMA                     • Instant rejection candle
                               • Target: 1:2.0 Risk-Reward                     • Re-entry into Asian range
```

### 1. Mode A: London Displacement Breakout
* **Condition:** Candle closes cleanly outside the Asian High or Asian Low between 07:00 and 11:00 UTC.
* **Filter:** Candlestick body ratio must exceed 55% of the total candle range (preventing wicks).
* **Trend Alignment:** Direction must align with the 50-period EMA macro trend.
* **Stop Loss:** 2.0 pips behind the breakout candle structure.
* **Take Profit:** 1:2.0 Risk-to-Reward ratio with automated Breakeven trigger at +1.0R.

### 2. Mode B: Judas Swing Manipulation (SFP Reversal)
* **Condition:** Price pierces Asian High/Low by 3–15 pips during London open.
* **Confirmation:** Multi-candle Swing Failure Pattern (SFP) where price fails to sustain and closes back inside the Asian range.
* **Entry:** Market limit upon close back inside range.
* **Target:** Opposite Asian range boundary or 50% Equilibrium.

---

## 📈 Quantitative Performance & Multi-Asset Backtest

Automated CI/CD backtesting executes on GitHub Actions across **5,259 trades** over 2 years of 1-hour candles (~17,500 hourly candles per instrument via Yahoo Finance API):

### Asset Class Performance Matrix

| Asset Class | Trades | Wins | Losses | Win Rate | Target RR |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Forex Majors** (`EURUSD`, `GBPUSD`, `JPY`, `AUDUSD`, `NZDUSD`, `CHF`) | **3,914** | **832** | **2,067** | **28.7% - 31.1%** | **1:2.5** |
| **Commodities** (`Gold GC=F`, `Silver SI=F`, `Crude Oil CL=F`) | **1,345** | **297** | **716** | **28.2% - 30.5%** | **1:2.5** |
| **Total Evaluated Trades** | **5,259** | **1,129** | **2,783** | **28.86%** | **1:2.5** |

> **Market Mechanics Note on Equities & Indices:**  
> US Equities (`AAPL`, `NVDA`, `MSFT`) and US Indices (`^GSPC`, `^IXIC`) are physically closed during the Asian session (00:00–07:00 UTC / 8 PM–3 AM EST). Consequently, Tokyo session range formation and London open manipulation apply strictly to **24/5 global FX and Commodities**, which experience continuous interbank liquidity transfers.

---

## 🛡️ Risk Management & Execution Rules

* **Strict Account Risk:** Default 1.0% maximum equity risk per trade.
* **Pessimistic Intra-Bar Fills:** If both Stop Loss and Take Profit fall within the high/low range of the same candle, the backtester always assumes a **Stop Loss hit** first.
* **Spread & Slippage Subtraction:** Every single entry and exit automatically deducts full broker spread and execution friction before reporting net PnL.
* **Breakeven Trailing:** Once a position reaches +1.0R in unrealized profit, the stop loss is automatically advanced to `Entry + Spread` to lock in zero downside.

---

## 🚀 Quickstart & Usage

### Requirements
- Python 3.10+
- Zero external package dependencies (built using Python Standard Library `urllib`, `json`, `math`, `datetime`).

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ShiTmoZ/forex.git
cd forex

# 2. Run historical multi-asset backtest (uses Yahoo Finance v8 API with local JSON caching)
python3 backtest.py

# 3. Run full multi-asset training & backtest suite (2020-2026 / 730d intraday)
python3 train_backtest_all.py

# 4. Launch live session supervisor (paper mode by default)
python3 main.py
```

### Automated GitHub Actions CI/CD
This repository includes an automated GitHub Actions workflow (`.github/workflows/forex_backtest.yml`) that runs the full multi-asset backtest suite on every push and via manual workflow dispatch.

---

## 📜 License
MIT License. Open-source for quantitative traders, algorithmic researchers, and institutional hobbyists.