# Broker Integration Research
**Pinch Stock Trading Project — Issue #31**
*Research Date: March 2026 | Analyst: Pinch (Chief of Finance, USS Clawbot)*

---

> "Rule of Acquisition #75: Home is where the heart is, but the stars are made of latinum." — Choosing the right broker is choosing the right launchpad for profit.

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Broker Profiles](#broker-profiles)
   - [Alpaca Markets](#1-alpaca-markets)
   - [Interactive Brokers (IBKR)](#2-interactive-brokers-ibkr)
   - [TD Ameritrade / Charles Schwab](#3-td-ameritrade--charles-schwab)
   - [Tradier](#4-tradier)
   - [Webull](#5-webull)
3. [Evaluation Scorecard](#evaluation-scorecard)
4. [Weighted Score Summary](#weighted-score-summary)
5. [Recommendation](#recommendation)
6. [Alpaca Paper Trading — Immediate Action Path](#alpaca-paper-trading--immediate-action-path)
7. [Rate Limits Reference](#rate-limits-reference)
8. [Security & Auth Implementation](#security--auth-implementation)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Code Architecture](#code-architecture)

---

## Executive Summary

For our use case — automated stock trading, $500K portfolio, covered calls strategy — the analysis is unambiguous:

**Short-term:** Start with **Alpaca** for paper trading immediately. Free, clean API, instant setup.

**Long-term:** Go live with **Interactive Brokers (IBKR)** for the full portfolio. It's the only broker that supports covered calls + automated trading at scale without paying absurd option premiums per contract. At $500K+ AUM, the $10/month inactivity fee is waived, and the commission savings on covered call volume are substantial.

**Hybrid approach (recommended):** Run both simultaneously. Alpaca for equity-only automated strategies. IBKR for the options overlay (covered calls, protective puts). This is not over-engineering — it's risk compartmentalization.

**Skip immediately:** Webull (no official API), TD Ameritrade (API in transition/limbo post-Schwab).

---

## Broker Profiles

### 1. Alpaca Markets

**Website:** https://alpaca.markets  
**Account Type:** Commission-free stock/ETF brokerage  
**Clearing:** Apex Clearing / SIPC insured  
**Regulatory:** FINRA member, SEC-registered

#### API Overview

| Attribute | Details |
|-----------|---------|
| API Type | REST + WebSocket |
| Auth Method | API key + secret header (`APCA-API-KEY-ID`, `APCA-API-SECRET-KEY`) |
| Base URL (Live) | `https://api.alpaca.markets` |
| Base URL (Paper) | `https://paper-api.alpaca.markets` |
| Data URL | `https://data.alpaca.markets` |
| WebSocket Feed | `wss://stream.alpaca.markets/v2/{iex|sip}` |
| Python SDK | `alpaca-trade-api` (official), `alpaca-py` (newer v2 SDK) |

#### Commissions & Fees

| Fee Type | Amount |
|----------|--------|
| Stock/ETF trades | $0 |
| Fractional shares | $0 |
| Account minimum | $0 |
| Market data (IEX) | Free |
| Market data (SIP) | $0 for unlimited plan subscribers / pro plan required |
| Margin interest | ~11–12%/year (varies) |

#### Order Types Supported

- ✅ Market
- ✅ Limit
- ✅ Stop
- ✅ Stop-limit
- ✅ Trailing stop
- ✅ Bracket (OTO/OCO)
- ✅ One-cancels-other (OCO)
- ❌ Options (not supported — equities only)

#### Paper Trading

Alpaca's paper trading is a first-class, production-equivalent environment. **Same API, same endpoints, different base URL.** Paper trading accounts are free, unlimited, and reset on demand. WebSocket feeds work identically. This is the gold standard for paper trading APIs.

```python
# Switching between paper and live is one variable change
BASE_URL = "https://paper-api.alpaca.markets"  # paper
BASE_URL = "https://api.alpaca.markets"          # live
```

#### Fractional Shares

- Buy/sell as little as $1 of any supported stock
- Critical for $500K portfolio with 20–30 positions — avoids cash drag
- Not all symbols support fractional (major stocks and ETFs do)

#### Market Data

| Tier | Feed | Latency | Cost |
|------|------|---------|------|
| Free | IEX (Investors Exchange) | ~15ms | $0 |
| Unlimited | SIP (consolidated) | Real-time | Subscription required |

IEX is sufficient for automated strategy execution. The data is real-time, not delayed, though it represents only IEX-routed trades (roughly 2-3% of total volume) — adequate for price signals, not for market microstructure analysis.

#### Strengths
- Easiest API to work with in this entire comparison
- Paper trading indistinguishable from live trading (same endpoints)
- WebSocket streaming for live price feeds and order updates
- Fractional shares eliminate allocation rounding errors
- Generous rate limits for retail automation
- Active developer community, good documentation

#### Weaknesses
- No options support whatsoever — covered call overlay impossible
- Newer company (founded 2015) vs. IBKR (founded 1977)
- No futures, forex, or international markets
- IEX data has lower volume representation than SIP feed
- No advanced order routing control

---

### 2. Interactive Brokers (IBKR)

**Website:** https://www.interactivebrokers.com  
**Account Type:** Full-service brokerage  
**Clearing:** Self-clearing, SIPC insured  
**Regulatory:** FINRA, SEC, multiple international regulators  
**Founded:** 1977 — the most battle-tested API in this comparison

#### API Overview

IBKR offers three distinct API paths:

| API | Description | Best For |
|-----|-------------|---------|
| **TWS API** | Native API via Trader Workstation | Desktop automation, full feature access |
| **IB Gateway** | Headless TWS (no GUI) | Server/automated deployment |
| **Client Portal API** | REST API via web session | Simpler REST flows, limited features |
| **IBKR Quant** | FIX protocol | Institutional HFT |

For our automated strategy: **IB Gateway + `ib_insync`** is the correct path.

| Attribute | Details |
|-----------|---------|
| API Type | TCP socket (TWS API), REST (Client Portal) |
| Python SDK | `ib_insync` (async, wraps TWS API) |
| TWS Port (live) | 7496 |
| TWS Port (paper) | 7497 |
| IB Gateway Port (live) | 4001 |
| IB Gateway Port (paper) | 4002 |
| Auth Method | Local socket connection (TWS/Gateway must be running) |

#### Commissions & Fees

| Fee Type | Amount |
|----------|--------|
| Stocks (Fixed) | $0.005/share, $1 min, $1% max |
| Stocks (Tiered) | $0.0035/share with volume discounts |
| ETF trades | Same as stocks |
| Options | $0.65/contract (Fixed), tiered from $0.25+ at volume |
| Inactivity fee | $10/month (waived if $100K+ or active trader) |
| Market data | Free delayed, real-time by exchange subscription (~$4.50–$10/mo for US equities) |
| Account minimum | $0 (but $10K recommended to avoid pattern day trader restrictions easily) |

**At $500K portfolio with covered call volume:** The options commission of $0.65/contract is effectively nothing. If we write 20 covered call contracts/month (200 shares × 10 positions), that's $13/month. Compared to the premium income generated, trivial.

#### Order Types Supported

- ✅ Market, Limit, Stop, Stop-Limit
- ✅ Trailing Stop
- ✅ Bracket (Attach Take-Profit + Stop-Loss)
- ✅ OCO (One-Cancels-Other)
- ✅ VWAP, TWAP (algorithmic execution)
- ✅ Adaptive orders (IBKR's smart routing)
- ✅ **Options orders** — buy/write covered calls, spreads, etc.
- ✅ Futures, Forex, International equities

#### Paper Trading

IBKR paper trading requires a separate account (free). It uses port 7497 instead of 7496. Data is real-time market data. The only difference: execution fills use simulated matching, not live order flow. **Paper and live accounts are completely separate credentials** — you can run both simultaneously with different socket connections.

#### Market Data

IBKR provides the most complete market data available at retail:
- Real-time quotes (subscription required per exchange, ~$4.50–$10/month)
- Historical bar data (going back decades)
- Options chains with Greeks (delta, gamma, theta, vega)
- Level 2 / order book data
- News feeds
- Fundamental data (earnings, financials)

#### ib_insync — Python Usage Pattern

```python
from ib_insync import IB, Stock, Order, Option

ib = IB()
ib.connect('127.0.0.1', 4001, clientId=1)  # IB Gateway

# Place market order
contract = Stock('AAPL', 'SMART', 'USD')
order = Order(action='BUY', totalQuantity=100, orderType='MKT')
trade = ib.placeOrder(contract, order)

# Write covered call
option = Option('AAPL', '20261120', 230, 'C', 'SMART')
write_order = Order(action='SELL', totalQuantity=1, orderType='LMT', lmtPrice=3.50)
ib.placeOrder(option, write_order)

ib.disconnect()
```

#### Strengths
- Only broker on this list with full options support for covered call automation
- Lowest effective commission at scale ($0.0035/share tiered)
- Most complete product set: equities, options, futures, forex, international
- 47 years of operational history — institutional-grade stability
- Market data includes options Greeks (critical for covered call selection)
- Smart order routing for best execution
- IB Gateway runs headless — perfect for server deployment

#### Weaknesses
- **Most complex API** — TWS API is socket-based, requires TWS/Gateway to be running
- `ib_insync` is excellent but is a community library (not official IBKR)
- IB Gateway requires manual login or automated credential management (API token approach)
- $10/month inactivity fee (irrelevant at $500K+ but worth noting)
- Slower to get started than Alpaca — account opening takes 1–3 days
- No fractional shares for stocks (though fractional ETFs supported in some cases)

---

### 3. TD Ameritrade / Charles Schwab

**Status: ⚠️ API IN TRANSITION — NOT RECOMMENDED**

The TD Ameritrade / Schwab merger completed in 2020, with the TDA platform fully migrated to Schwab's infrastructure by 2023–2024. The thinkorswim API (TDA's algorithmic trading API) has had an uncertain status throughout this transition.

**Current situation as of March 2026:**
- TD Ameritrade API (`api.tdameritrade.com`) is effectively sunset
- Schwab Developer Portal (`developer.schwab.com`) exists but has limited automation support
- The thinkorswim platform continues as Schwab's active trading platform
- No official Python SDK with maintained support

#### Why to Skip

| Issue | Detail |
|-------|--------|
| API stability | TDA API officially deprecated; Schwab replacement immature |
| Documentation | Schwab developer docs are sparse compared to Alpaca/IBKR |
| Automation support | Not designed for algo trading at our level |
| Python support | No official SDK; community libraries poorly maintained |
| Options support | Platform exists but API access for options automation is unreliable |

**Verdict: Skip.** The API uncertainty alone disqualifies it for a production automated trading system. May revisit in 12–18 months if Schwab's developer platform matures.

---

### 4. Tradier

**Website:** https://tradier.com  
**Founded:** 2014  
**Account Type:** Self-directed brokerage + API-first platform  
**Regulatory:** FINRA, SIPC

#### API Overview

| Attribute | Details |
|-----------|---------|
| API Type | REST (well-documented) |
| Auth Method | OAuth 2.0 access token + account token |
| Base URL (Live) | `https://api.tradier.com/v1` |
| Base URL (Paper) | `https://sandbox.tradier.com/v1` |
| WebSocket | `wss://ws.tradier.com/v1/markets/events` |
| Python SDK | `tradier` (unofficial but maintained) |

#### Commissions & Fees

| Fee Type | Amount |
|----------|--------|
| Stock/ETF trades | $0 |
| Options | **$0.35/contract** (best in class for options) |
| Account minimum | $0 |
| Market data (delayed) | Free |
| Market data (real-time) | $10/month (Level 1), $25/month (Level 2) |

#### Order Types Supported

- ✅ Market, Limit, Stop, Stop-Limit
- ✅ Trailing Stop
- ✅ OCO (One-Cancels-Other)
- ✅ Options (calls and puts — covered calls, spreads)
- ❌ No futures or forex

#### Paper Trading (Sandbox)

Tradier's sandbox is REST-identical to production. Auth works the same way, data is somewhat simulated (not always live prices in sandbox). Functional for testing order flow and logic.

#### Strengths
- **Cheapest options commissions** at $0.35/contract (vs. IBKR $0.65)
- Clean, well-documented REST API — easier to work with than IBKR
- Options support for covered calls and spreads
- Paper trading sandbox
- Good WebSocket streaming

#### Weaknesses
- **Smaller company** — less institutional backing than IBKR, could be acquired or pivot
- Market data feed requires subscription for real-time
- Less market depth and routing quality vs. IBKR
- No fractional shares
- Python SDK community-maintained, not official
- Less robust historical data access than IBKR

---

### 5. Webull

**Status: ❌ NOT SUITABLE FOR AUTOMATION**

| Issue | Detail |
|-------|--------|
| Official API | Does not exist |
| Unofficial libraries | `webull` Python package (reverse-engineered, frequently breaks) |
| Reliability | Session-based authentication breaks without warning |
| Terms of Service | Automated trading likely violates ToS |
| Stability | Chinese-owned (Fumi Technology); regulatory risk in US |

**Verdict: Hard no.** Using reverse-engineered session tokens for a $500K automated portfolio is how you wake up at 2am to a trading halt and a blocked account. The latinum is not worth the risk.

---

## Evaluation Scorecard

Scores on 1–5 scale.

### API Quality (Weight: 25%)

| Broker | Score | Rationale |
|--------|-------|-----------|
| Alpaca | **5** | Best-in-class REST/WebSocket, official Python SDK, excellent docs |
| IBKR | **3** | Powerful but complex; socket-based; learning curve is real |
| TD/Schwab | **1** | API in transition, unreliable, poor documentation |
| Tradier | **4** | Clean REST API, good documentation, functional WebSocket |
| Webull | **1** | No official API, reverse-engineered only |

### Cost (Weight: 20%)

| Broker | Score | Rationale |
|--------|-------|-----------|
| Alpaca | **5** | Completely free for equities; best cost structure for stock-only |
| IBKR | **4** | Low per-share cost; $10/month fee waived at our AUM; data fees modest |
| TD/Schwab | **3** | Free stocks/ETFs; $0.65/option; but API costs indirectly via transition risk |
| Tradier | **5** | Free stocks; $0.35/contract options — cheapest options on the list |
| Webull | **4** | Free, but the "free" has hidden API risk costs |

### Order Types (Weight: 15%)

| Broker | Score | Rationale |
|--------|-------|-----------|
| Alpaca | **4** | Market, limit, stop, bracket, OCO, trailing; no options |
| IBKR | **5** | Everything: bracket, OCO, VWAP, TWAP, options, futures |
| TD/Schwab | **2** | Basic types supported in transition; unreliable for automation |
| Tradier | **4** | Market, limit, stop, OCO, options; solid set |
| Webull | **1** | Basic types via unofficial API; unreliable |

### Paper Trading (Weight: 15%)

| Broker | Score | Rationale |
|--------|-------|-----------|
| Alpaca | **5** | Gold standard: identical API, same endpoint structure, free, unlimited resets |
| IBKR | **4** | Separate paper account, same features, real data; requires TWS login |
| TD/Schwab | **2** | thinkorswim paper exists but API access is uncertain |
| Tradier | **3** | Sandbox available; data not always live prices in sandbox |
| Webull | **1** | Paper trading exists in app but no reliable API access |

### Options Support (Weight: 10%)

| Broker | Score | Rationale |
|--------|-------|-----------|
| Alpaca | **1** | No options support at all |
| IBKR | **5** | Full options: single-leg, spreads, combos, Greeks via API |
| TD/Schwab | **3** | Options exist but API automation reliability is poor |
| Tradier | **4** | Single-leg and multi-leg options, good API access |
| Webull | **2** | Options in-app only; no automation |

### Data Feed (Weight: 10%)

| Broker | Score | Rationale |
|--------|-------|-----------|
| Alpaca | **3** | Free IEX (real-time, not full SIP); adequate for strategy signals |
| IBKR | **5** | Most complete: Level 1, Level 2, options chains with Greeks, fundamentals |
| TD/Schwab | **2** | Data quality fine but API access uncertain |
| Tradier | **3** | Real-time available with subscription; options chain data included |
| Webull | **1** | Data via unofficial API only; unreliable |

### Stability (Weight: 5%)

| Broker | Score | Rationale |
|--------|-------|-----------|
| Alpaca | **3** | Founded 2015; VC-backed; good track record; not 47 years old |
| IBKR | **5** | Public company (IBKR), 47 years, institutional grade, extremely stable |
| TD/Schwab | **4** | Charles Schwab is massive, established; TDA API itself is unstable |
| Tradier | **2** | Smaller, private company; acquisition/pivot risk |
| Webull | **1** | Chinese ownership adds regulatory/operational risk |

---

## Weighted Score Summary

| Broker | API (25%) | Cost (20%) | Orders (15%) | Paper (15%) | Options (10%) | Data (10%) | Stability (5%) | **Total** |
|--------|-----------|-----------|-------------|------------|--------------|-----------|---------------|-----------|
| **Alpaca** | 5×0.25=1.25 | 5×0.20=1.00 | 4×0.15=0.60 | 5×0.15=0.75 | 1×0.10=0.10 | 3×0.10=0.30 | 3×0.05=0.15 | **4.15** |
| **IBKR** | 3×0.25=0.75 | 4×0.20=0.80 | 5×0.15=0.75 | 4×0.15=0.60 | 5×0.10=0.50 | 5×0.10=0.50 | 5×0.05=0.25 | **4.15** |
| **TD/Schwab** | 1×0.25=0.25 | 3×0.20=0.60 | 2×0.15=0.30 | 2×0.15=0.30 | 3×0.10=0.30 | 2×0.10=0.20 | 4×0.05=0.20 | **2.15** |
| **Tradier** | 4×0.25=1.00 | 5×0.20=1.00 | 4×0.15=0.60 | 3×0.15=0.45 | 4×0.10=0.40 | 3×0.10=0.30 | 2×0.05=0.10 | **3.85** |
| **Webull** | 1×0.25=0.25 | 4×0.20=0.80 | 1×0.15=0.15 | 1×0.15=0.15 | 2×0.10=0.20 | 1×0.10=0.10 | 1×0.05=0.05 | **1.70** |

**Rankings:**
1. 🥇 Alpaca: **4.15** — tied for first, wins for paper trading and ease
2. 🥇 IBKR: **4.15** — tied for first, wins for live trading with options
3. 🥈 Tradier: **3.85** — strong second, especially for options cost
4. ❌ TD/Schwab: **2.15** — API uncertainty kills it
5. ❌ Webull: **1.70** — not appropriate for automation

---

## Recommendation

> *"Rule of Acquisition #47: Never trust a man wearing a better suit than your own." — We trust Alpaca for paper trading. We trust IBKR with real money.*

### Use Case: $500K Portfolio, Automated Trading, Covered Calls

**Recommended approach: Two-broker architecture**

```
┌─────────────────────────────────────────────────────┐
│                  PHASE 4: PAPER TRADING              │
│                                                     │
│  Alpaca Paper → Full automated strategy validation  │
│  (Equity orders only, no options needed yet)        │
└──────────────────────────┬──────────────────────────┘
                           │ Validate, iterate, prove profit
                           ▼
┌─────────────────────────────────────────────────────┐
│                  PHASE 6: LIVE TRADING               │
│                                                     │
│  Primary: IBKR (IB Gateway)                         │
│    ├── All equity position management               │
│    ├── Covered call writing (options overlay)       │
│    └── Protective puts when needed                  │
│                                                     │
│  Optional Parallel: Tradier                         │
│    └── If covered call volume makes $0.35/contract  │
│        savings meaningful vs. IBKR's $0.65          │
└─────────────────────────────────────────────────────┘
```

### Decision Rationale

**Why IBKR for live trading:**
1. Options support is non-negotiable for covered calls — Alpaca is immediately eliminated for live trading
2. At $500K, the $10/month inactivity fee is waived (we exceed the threshold)
3. IB Gateway runs headless on a server — perfect fit for our architecture
4. The complexity of TWS API is a one-time cost, and `ib_insync` abstracts most of it
5. 47 years of stability — we are not going to wake up and find IBKR has pivoted

**Why Alpaca for paper trading:**
1. Start immediately — account creation is instant, API keys generated in minutes
2. Paper trading is free, unlimited, and production-identical
3. All our equity strategy logic works without modification
4. Replace our current manual `portfolio_manager.py` simulation with real API calls

**Why Tradier is worth monitoring:**
At $0.35/contract vs. IBKR's $0.65/contract — if we write 40 covered call contracts/month, that's $12/month savings. Negligible now, meaningful at scale. Keep as a secondary option.

---

## Alpaca Paper Trading — Immediate Action Path

This is the zero-cost, zero-risk way to validate our automated strategies before spending a single dollar of real capital.

### Setup Steps

1. **Create Alpaca account:** https://app.alpaca.markets/signup (free, instant)
2. **Generate paper trading API keys** in the dashboard under "Paper Trading"
3. **Store credentials** in `.secrets/` following our existing pattern (see Security section)
4. **Install SDK:** `pip install alpaca-trade-api` or `pip install alpaca-py`

### What We Get Immediately
- $100K paper trading account (adjustable)
- Live IEX market data feed
- WebSocket order updates
- Same endpoints as live trading
- Ability to reset/restart paper account at will

### Replacing Manual Portfolio Simulation

Our current `portfolio_manager.py` tracks positions in SQLite with manual mark-to-market. Alpaca paper trading replaces the "execution" layer while we keep our strategy signals:

```
Current flow:
  Signal → Strategy → portfolio_manager.py → SQLite → Dashboard

Alpaca paper flow:
  Signal → Strategy → Alpaca API (paper) → Alpaca account → Dashboard
```

### Quick Integration Test

```python
import alpaca_trade_api as tradeapi

# Load from .secrets (see Security section)
api = tradeapi.REST(
    key_id=ALPACA_API_KEY,
    secret_key=ALPACA_SECRET_KEY,
    base_url='https://paper-api.alpaca.markets'
)

# Check account
account = api.get_account()
print(f"Portfolio value: ${float(account.portfolio_value):,.2f}")
print(f"Buying power: ${float(account.buying_power):,.2f}")

# Place paper trade
order = api.submit_order(
    symbol='AAPL',
    qty=10,
    side='buy',
    type='market',
    time_in_force='day'
)
print(f"Order placed: {order.id}")
```

---

## Rate Limits Reference

| Broker | Endpoint | Rate Limit | Notes |
|--------|----------|-----------|-------|
| **Alpaca** | REST (Trading) | 200 req/min | Per API key |
| **Alpaca** | REST (Data) | 200 req/min | Separate quota |
| **Alpaca** | WebSocket | 1 connection | Unlimited symbols |
| **IBKR** | TWS API | No hard limit | Practical ~50 req/sec |
| **IBKR** | Client Portal | ~10 req/sec | REST API limit |
| **IBKR** | Historical Data | 60 req/10min | Per symbol |
| **IBKR** | Live Data | ~100 tickers | Concurrent streaming limit |
| **Tradier** | REST | 60 req/min | Trading endpoints |
| **Tradier** | REST | 120 req/min | Market data endpoints |
| **Tradier** | WebSocket | 1 connection | Unlimited symbols |

### Rate Limit Strategy (for our automation)

```python
import time
from functools import wraps

def rate_limited(max_per_minute):
    """Simple rate limiter decorator."""
    min_interval = 60.0 / max_per_minute
    last_called = [0.0]
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator
```

---

## Security & Auth Implementation

### Pattern: Mirror Kraken/Kalshi Approach

The crypto platform stores API credentials in `/home/bob/.openclaw/workspace-pinch/.secrets/`. We follow the same pattern for broker credentials.

**Never commit credentials to the repo.** `.secrets/` is in `.gitignore`.

### File Structure

```
/home/bob/.openclaw/workspace-pinch/.secrets/
├── alpaca_paper.py          # Alpaca paper trading credentials
├── alpaca_live.py           # Alpaca live credentials (when live)
├── ibkr_config.py           # IBKR connection config
└── tradier_sandbox.py       # Tradier sandbox credentials
```

### Credential Files

**`.secrets/alpaca_paper.py`**
```python
# Alpaca Paper Trading Credentials
# Get from: https://app.alpaca.markets/paper-trade/overview
# DO NOT COMMIT — in .gitignore

ALPACA_API_KEY    = "PKxxxxxxxxxxxxxxxxxxxxxxx"
ALPACA_SECRET_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ALPACA_BASE_URL   = "https://paper-api.alpaca.markets"
ALPACA_DATA_URL   = "https://data.alpaca.markets"
ALPACA_DATA_FEED  = "iex"  # "iex" (free) or "sip" (paid)
```

**`.secrets/ibkr_config.py`**
```python
# IBKR IB Gateway Connection Config
# No credentials stored here — IBKR auth is handled via TWS/Gateway login
# Gateway manages session; we connect via local socket only

IBKR_HOST         = "127.0.0.1"
IBKR_PAPER_PORT   = 7497    # Paper trading
IBKR_LIVE_PORT    = 4001    # Live (IB Gateway)
IBKR_CLIENT_ID    = 1       # Increment if running multiple connections
IBKR_ACCOUNT_ID   = ""      # IBKR account number (set when known)
```

**`.secrets/tradier_sandbox.py`**
```python
# Tradier Sandbox Credentials
# Get from: https://developer.tradier.com/
# DO NOT COMMIT — in .gitignore

TRADIER_ACCESS_TOKEN   = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TRADIER_ACCOUNT_ID     = "xxxxxxxxxx"
TRADIER_BASE_URL       = "https://sandbox.tradier.com/v1"
```

### Loading Pattern in Code

```python
import sys
import os

# Load secrets — same pattern as kill_switch.py in crypto repo
SECRETS_PATH = '/home/bob/.openclaw/workspace-pinch/.secrets'
sys.path.insert(0, SECRETS_PATH)

# Alpaca
from alpaca_paper import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

# IBKR (no secret import needed — socket-only)
from ibkr_config import IBKR_HOST, IBKR_PAPER_PORT, IBKR_CLIENT_ID
```

### Kill Switch Design

Our kill switch must work for both brokers. The crypto platform's `kill_switch.py` is the template:

```python
# live/execution/kill_switch.py

class BrokerKillSwitch:
    """
    Emergency kill: cancel all open orders, flatten all positions.
    Runs independently of main strategy loop.
    """
    
    def __init__(self, broker='alpaca_paper'):
        self.broker = broker
        self.armed = True
        
    def execute(self, trigger_reason: str):
        """Flatten everything immediately."""
        if not self.armed:
            print("Kill switch disarmed — no action taken")
            return
            
        print(f"[KILL SWITCH] Triggered: {trigger_reason}")
        
        if 'alpaca' in self.broker:
            self._kill_alpaca()
        elif 'ibkr' in self.broker:
            self._kill_ibkr()
            
    def _kill_alpaca(self):
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
        
        # Cancel all open orders
        api.cancel_all_orders()
        print("[KILL] All orders cancelled")
        
        # Liquidate all positions
        api.close_all_positions()
        print("[KILL] All positions closed")
        
    def _kill_ibkr(self):
        from ib_insync import IB
        ib = IB()
        ib.connect(IBKR_HOST, IBKR_PAPER_PORT, clientId=99)  # clientId=99 reserved for kill switch
        
        # Cancel all orders
        for order in ib.orders():
            ib.cancelOrder(order)
        print("[KILL] All IBKR orders cancelled")
        
        # Close all positions with market orders
        for pos in ib.positions():
            if pos.position != 0:
                side = 'SELL' if pos.position > 0 else 'BUY'
                order = MarketOrder(side, abs(pos.position))
                ib.placeOrder(pos.contract, order)
        print("[KILL] All IBKR positions submitted for closure")
        
        ib.disconnect()
```

### Order Limits & Circuit Breakers

```python
# live/execution/risk_manager.py additions for broker integration

RISK_LIMITS = {
    'max_single_order_value': 50_000,     # $50K max per single order
    'max_daily_orders': 100,               # No more than 100 orders per day
    'max_position_size_pct': 0.10,         # 10% max per position
    'max_drawdown_pct': 0.05,              # 5% drawdown triggers kill switch
    'paper_mode': True,                    # MUST be flipped explicitly for live
}

def validate_order(symbol, qty, price, side, portfolio_value):
    """Pre-flight check before submitting any order."""
    order_value = qty * price
    
    if order_value > RISK_LIMITS['max_single_order_value']:
        raise ValueError(f"Order value ${order_value:,.0f} exceeds limit")
    
    position_pct = order_value / portfolio_value
    if position_pct > RISK_LIMITS['max_position_size_pct']:
        raise ValueError(f"Position size {position_pct:.1%} exceeds {RISK_LIMITS['max_position_size_pct']:.1%} limit")
    
    if RISK_LIMITS['paper_mode'] and 'live' in ALPACA_BASE_URL:
        raise RuntimeError("paper_mode=True but live URL configured — ABORT")
    
    return True
```

---

## Implementation Roadmap

### Phase 1: Alpaca Paper Trading (Now — 2 weeks)

**Goal:** Replace manual portfolio simulation with live API-connected paper trading.

**Week 1:**
- [ ] Create Alpaca paper trading account
- [ ] Add `.secrets/alpaca_paper.py` with credentials
- [ ] Write `live/execution/alpaca_client.py` — thin wrapper around `alpaca-trade-api`
- [ ] Write `live/execution/kill_switch.py` — Alpaca kill switch (cancel orders + close all positions)
- [ ] Write `live/execution/risk_manager.py` — order validation + position size limits

**Week 2:**
- [ ] Connect strategy signals → Alpaca paper order submission
- [ ] WebSocket order status tracking
- [ ] Reconcile Alpaca positions with our state/portfolio.db
- [ ] Test kill switch

**Files to create:**
```
live/execution/
├── alpaca_client.py         # Alpaca API wrapper
├── order_router.py          # Route orders to correct broker
├── risk_manager.py          # Pre-order validation, circuit breakers
├── kill_switch.py           # Emergency stop
└── position_reconciler.py   # Keep local state in sync with broker
```

### Phase 2: Strategy → Order Pipeline (Weeks 3–4)

**Goal:** Wire existing strategy signals to actual order execution.

```python
# Conceptual pipeline
signal = strategy.generate_signal(symbol)  # returns BUY/SELL/HOLD + size
if signal.action != 'HOLD':
    risk_manager.validate_order(signal)
    order_id = alpaca_client.place_order(signal)
    position_reconciler.update(order_id)
```

- [ ] Adapt `live/signals/*.py` to produce normalized `Signal` objects
- [ ] Write `order_router.py` to translate signals to broker orders
- [ ] Add order tracking to state/portfolio.db

### Phase 3: IBKR Integration (When going live)

**Goal:** Full broker integration for live trading with options overlay.

**Prerequisites:**
- IBKR account funded and approved for options
- IB Gateway installed on trading server
- Paper trading validated for 4–8 weeks

**Steps:**
- [ ] Install IB Gateway (headless) on server
- [ ] Install `pip install ib_insync`
- [ ] Write `live/execution/ibkr_client.py` — IBKR wrapper
- [ ] Extend `order_router.py` to route to IBKR for options orders
- [ ] Write `live/execution/covered_call_manager.py` — finds, writes, tracks covered calls
- [ ] Extend `kill_switch.py` to handle IBKR positions
- [ ] Paper test IBKR before live

### Phase 4: Covered Call Automation (Post-live launch)

```
For each equity position > 100 shares:
  1. Query options chain via IBKR
  2. Select call option at target delta (0.20–0.30)
  3. Validate premium meets minimum yield threshold
  4. Write covered call
  5. Track expiry and roll/close as needed
```

---

## Code Architecture

### Broker Abstraction Layer

Both Alpaca and IBKR should implement a common interface so strategy code doesn't care which broker is active:

```python
# live/execution/broker_base.py

from abc import ABC, abstractmethod

class BrokerBase(ABC):
    """Abstract broker interface — all brokers implement this."""
    
    @abstractmethod
    def get_account(self) -> dict:
        """Return portfolio value, buying power, etc."""
        pass
    
    @abstractmethod
    def get_positions(self) -> list:
        """Return current open positions."""
        pass
    
    @abstractmethod
    def place_order(self, symbol, qty, side, order_type, limit_price=None) -> str:
        """Submit an order. Returns order ID."""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str):
        """Cancel a specific open order."""
        pass
    
    @abstractmethod
    def cancel_all_orders(self):
        """Cancel all open orders."""
        pass
    
    @abstractmethod
    def close_all_positions(self):
        """Market-sell all open positions."""
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> dict:
        """Get latest quote for a symbol."""
        pass
```

### Configuration Pattern

```python
# live/execution/config.py

BROKER_MODE = 'alpaca_paper'  # Options: alpaca_paper | alpaca_live | ibkr_paper | ibkr_live

BROKER_CONFIG = {
    'alpaca_paper': {
        'client': 'AlpacaClient',
        'base_url': 'https://paper-api.alpaca.markets',
        'secrets_file': 'alpaca_paper',
    },
    'alpaca_live': {
        'client': 'AlpacaClient',
        'base_url': 'https://api.alpaca.markets',
        'secrets_file': 'alpaca_live',
    },
    'ibkr_paper': {
        'client': 'IBKRClient',
        'port': 7497,
        'secrets_file': 'ibkr_config',
    },
    'ibkr_live': {
        'client': 'IBKRClient',
        'port': 4001,
        'secrets_file': 'ibkr_config',
    },
}
```

---

## Appendix: Useful Links

| Resource | URL |
|----------|-----|
| Alpaca Paper Trading Dashboard | https://app.alpaca.markets/paper-trade/overview |
| Alpaca API Docs | https://docs.alpaca.markets/reference/getallorders |
| alpaca-py (new SDK) | https://github.com/alpacahq/alpaca-py |
| IBKR TWS API Docs | https://interactivebrokers.github.io/tws-api/ |
| ib_insync Docs | https://ib-insync.readthedocs.io/ |
| IB Gateway Download | https://www.interactivebrokers.com/en/trading/ibgateway-stable.php |
| Tradier API Docs | https://documentation.tradier.com/ |
| Alpaca Rate Limits | https://docs.alpaca.markets/reference/rate-limits |

---

*Research complete. Rule of Acquisition #22: A wise man can hear profit in the wind — and this wind says start paper trading today.*

*— Pinch, Chief of Finance, USS Clawbot*
