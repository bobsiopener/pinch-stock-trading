# 📈 Pinch Stock Trading Platform

> *"Rule of Acquisition #22: A wise man can hear profit in the wind."*

Managed by **Pinch**, Chief of Finance aboard the USS Clawbot. This is the stock and ETF trading platform — the equity counterpart to the [pinch-crypto-trading](https://github.com/bobsiopener/pinch-crypto-trading) platform.

---

## Overview

A disciplined, research-driven stock and ETF trading system. Every strategy is backtested before deployment. Every position has a documented rationale. Every trade is logged. No gut feelings — only data.

**Status:** Phase 1 — Strategy Research

**Starting Capital:** $500,000 (imaginary portfolio)

---

## Strategy Categories

Six strategy families under active research:

| Strategy | Description | Status |
|----------|-------------|--------|
| **Growth / Momentum** | Price momentum, CANSLIM, relative strength | Researching |
| **Value Investing** | P/E, P/B, Magic Formula, Buffett/Graham | Researching |
| **Dividend / Income** | Aristocrats, covered calls, REITs | Researching |
| **Sector Rotation** | Business cycle rotation, relative strength across sectors | Researching |
| **Mean Reversion** | Pairs trading, Bollinger Bands, RSI signals | Researching |
| **Macro / Tactical** | Risk parity, regime detection, yield curve | Researching |

---

## Phase Plan

```
Phase 1: Strategy Research     ← We are here
    ↓
Phase 2: Backtesting           (2010-2026 historical data)
    ↓
Phase 3: Portfolio System      (imaginary portfolio infrastructure)
    ↓
Phase 4: Paper Trading         (4-8 weeks with real prices)
    ↓
Phase 5: Signal Research       (earnings, insider flow, sentiment)
    ↓
Phase 6: Go Live               (real money, real broker)
```

---

## Shared Infrastructure

### Market Database
**Location:** `/mnt/media/market_data/pinch_market.db`

Already built and maintained by the market data collection system:

- **200K+ price records** for 38 stocks and ETFs
- **Daily OHLCV** going back to 2010
- **FRED economic data** (80K+ records): Fed Funds Rate, CPI, GDP, yield curve
- **VIX history** since 1990
- **Options chains** (accumulating daily)
- **CBOE put/call ratios**

### Available Symbols
Stocks: AAPL, AMZN, MSFT, GOOGL, NVDA, AMD, META, TSLA, BRK-B, JPM, BAC, WFC, JNJ, PFE, UNH, XOM, CVX, PLTR, ANET, CSCO, and more

ETFs: SPY, QQQ, IWM, GLD, SLV, USO, TLT, IEF, XLK, XLF, XLV, XLE, XBI, SMH, EEM, FXI, EWJ

---

## Repository Structure

```
pinch-stock-trading/
├── README.md
├── research/
│   └── strategies/          # Strategy research documents (.md files)
├── backtest/
│   ├── strategies/          # Strategy implementations (Python)
│   ├── data/                # Data loader — reads from shared market DB
│   │   └── db_loader.py
│   └── results/             # Backtest results and reports
├── live/
│   ├── portfolio/           # Portfolio manager (imaginary portfolio system)
│   │   ├── portfolio_manager.py
│   │   └── analytics.py
│   ├── signals/             # Signal generators
│   ├── execution/           # Risk management, kill switch
│   └── monitor/             # Market monitoring, alerts
├── docs/
│   └── strategy-plan.md     # Master strategy document
├── logs/
│   └── trades/              # Trade logs (CSV + JSON)
└── state/                   # Runtime state (portfolio DB, snapshots)
```

---

## Imaginary Portfolio System

The **imaginary portfolio** is a paper trading system that tracks positions with real market prices but no real money. It's how we validate strategies before going live.

- **$500,000 starting capital**
- SQLite-backed transaction log
- Daily mark-to-market using market DB prices
- Benchmarked against SPY and QQQ
- Displayed on The Bridge dashboard

CLI usage (once built):
```bash
python3 live/portfolio/portfolio_manager.py buy AAPL 50
python3 live/portfolio/portfolio_manager.py sell AAPL 25
python3 live/portfolio/portfolio_manager.py status
python3 live/portfolio/portfolio_manager.py performance --since-inception
```

---

## Relationship to Crypto Platform

This platform is a **parallel system** to [pinch-crypto-trading](https://github.com/bobsiopener/pinch-crypto-trading):

- Both use the same underlying market database
- Both managed by Pinch (CFO)
- Crypto: 24/7 markets, higher volatility, momentum-focused
- Stocks: Market hours, earnings-driven, broader strategy range
- Cross-asset risk monitored across both portfolios

---

## Issues & Milestones

| Milestone | Issues | Description |
|-----------|--------|-------------|
| Phase 1: Strategy Research | #1–#10 | Research all strategy types |
| Phase 2: Backtesting | #11–#17 | Backtest against 15+ years of data |
| Phase 3: Portfolio System | #18–#22 | Build imaginary portfolio infrastructure |
| Phase 4: Paper Trading | #23–#25 | Run paper trades with live prices |
| Phase 5: Signal Research | #26–#30 | Advanced signals and factor data |
| Phase 6: Go Live | #31–#32 | Real broker, real money |

---

## Setup

```bash
# Clone the repo
git clone https://github.com/bobsiopener/pinch-stock-trading
cd pinch-stock-trading

# Install dependencies
pip install pandas sqlite3 numpy scipy

# Verify database access
python3 backtest/data/db_loader.py
```

---

*Pinch does not give financial advice. Pinch gives profit-maximizing recommendations backed by data. The distinction is important.*
