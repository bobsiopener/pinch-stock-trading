# Options Strategies for the Pinch Portfolio

> *"Rule of Acquisition #74: Knowledge equals profit."*

**Status:** Research Complete  
**Date:** 2026-03-13  
**Author:** Pinch, Chief of Finance  
**Applies to:** Stock/ETF portfolio, $500,000 imaginary capital  

---

## Overview

Options are tools. Like any tool, they can build wealth or cause catastrophic damage depending on whether the user understands what they're doing. This document covers income-generating strategies (covered calls, cash-secured puts, the wheel), protective strategies (collars, put spreads), and index strategies (iron condors). Each section includes specific parameters, examples using actual portfolio holdings, and risk warnings.

**Core principle**: Options should serve the portfolio's goals, not become a gambling vehicle.

---

## 1. Covered Calls

### Mechanics
- **Requirement**: Own 100 shares of the underlying stock
- **Action**: Sell 1 call contract at your chosen strike price
- **Income**: Collect premium upfront — yours to keep regardless of outcome
- **Risk**: Your upside is capped at the strike price

If the stock closes above your strike at expiration, your shares get called away at that strike. You keep the premium. If it closes below, the option expires worthless and you keep shares + premium.

### Strike Selection

| Strike Type | Premium | Upside Captured | Best Use |
|-------------|---------|-----------------|----------|
| ATM (at-the-money) | Highest | None beyond entry | Neutral/mildly bearish view |
| OTM 5% | Moderate | Up to 5% | Neutral/mildly bullish |
| OTM 10% | Lower | Up to 10% | Moderately bullish |
| Deep OTM 15%+ | Minimal | Up to 15%+ | Strong uptrend — barely worth it |

**Recommendation**: For the Pinch Portfolio, use **OTM 5-7%** strikes. Captures most of the income while allowing moderate appreciation.

### Optimal Duration: 30-45 DTE (Days to Expiration)

Theta decay (time value erosion) accelerates in the final 30 days. The relationship is non-linear:
- 60 DTE → 45 DTE: theta accelerates
- 45 DTE → 30 DTE: fastest decay per day
- <21 DTE: gamma risk increases (stock move can overwhelm theta)

**Rule**: Sell at 30-45 DTE, close/roll at 21 DTE or when 50% of max profit is captured.

### Example: AAPL Covered Call

Current data from pinch_market.db:
- AAPL price: **$250.12**
- AAPL annual volatility (realized, 252-day): **31.6%**
- Monthly volatility: 31.6% / √12 = **9.1%**
- Estimated ATM 30DTE call premium: **~$9.14** (~3.7% yield)
- OTM 5% strike = $262.50 call: estimated premium **~$5-7** (~2.2-2.8% yield)
- Annualized at 10 contracts/year (selling monthly): **~26-34% annualized yield on premium alone**

Note: This yield is not guaranteed. If AAPL rallies 20% in a month, you gave up the majority of that gain.

### Example: WFC Covered Call

Current data:
- WFC price: **$74.10**  
- WFC annual vol: **29.1%**, monthly vol: **8.4%**
- ATM 30DTE call: **~$2.49** per share (~3.4% yield)
- WFC gain since 2010: **+311%** — a large unrealized gain position

**Use case**: WFC is a stable, slightly bullish position. Covered calls work well here. Selling OTM 5% calls monthly could generate $35-50/month per 100 shares at current pricing.

### When NOT to Sell Covered Calls

1. **Earnings announcement within 30 days**: IV spikes before earnings, then collapses. Sell AFTER earnings, not before. Selling into earnings gives away the "IV crush" opportunity.
2. **Ex-dividend within 30 days**: Risk of early assignment if call is in the money. The dividend makes early exercise rational for the call buyer.
3. **Strong uptrend**: If NVDA is running +5% per week, a covered call caps your gain at the strike. You'll get called away at $5 above entry while the stock keeps climbing.
4. **IV rank below 30%**: Low IV = low premium. Not worth the capped upside for thin income.

---

## 2. Cash-Secured Puts (CSPs)

### Mechanics
- **Requirement**: Hold enough cash to buy 100 shares at the strike price
- **Action**: Sell 1 put contract at your desired entry price
- **Income**: Collect premium. If stock stays above strike, option expires worthless.
- **Assignment**: If stock drops below strike, you buy 100 shares at strike price. Effective cost = strike - premium received.

### The Income Math

```
Premium collected: $3.50/share = $350 total
Strike price: $95.00 (5% below current $100)
If assigned: buy at $95.00, effective cost = $91.50
If not assigned: collect $350 for tying up $9,500 in cash = 3.7% yield in 30 days
Annualized: ~44% (but this assumes every month you find a trade — unrealistic)
```

### Strike and Duration Selection

**Target**: 5-10% below current price
- At 5% OTM: higher probability of expiring worthless (~75-80%), lower premium
- At 10% OTM: lower probability (~85-90%), even lower premium
- ATM: highest premium but 50% chance of assignment

**Duration**: Same logic as covered calls — 30-45 DTE.

### Best Use Cases

1. **Building positions gradually on pullbacks**: Want to own MSFT? Sell puts at prices where you'd gladly buy. If you don't get assigned, you collect premium. If you do get assigned, you got the price you wanted.
2. **Accumulating tech positions in dips**: NVDA volatile at 41.4% annual vol — meaningful premium on puts during elevated IV.
3. **Not on positions you don't actually want**: If assigned and you hate the stock, you now have a problem.

### Example: NVDA Cash-Secured Put

- NVDA price: **$180.25**
- NVDA annual vol: **41.4%** (highest in portfolio), monthly vol: **11.9%**
- ATM put premium estimate: **~$8.61**
- OTM 5% strike = $171.24 put: estimated premium **~$5-6**
- Cash required to secure: $17,124 per contract
- Return on capital if not assigned: ~3.3% in 30 days

**Warning**: NVDA has extreme event risk (earnings, chip export restrictions). Do not sell puts into earnings. NVDA dropped 30%+ multiple times. Check your collar or stop.

---

## 3. The Wheel Strategy

### Mechanics (Three Stages)

```
Stage 1: Sell cash-secured put
  → If expires worthless: collect premium, repeat Stage 1
  → If assigned: move to Stage 2

Stage 2: Sell covered call (after assignment)
  → If expires worthless: collect premium, repeat Stage 2  
  → If called away: collect premium + any appreciation up to strike, move to Stage 3

Stage 3: Position closed. Return to cash. Restart from Stage 1.
```

### Target Economics

**Goal**: Generate 1-2% per month in combined premium.

On a $100 stock, 1% = $1/share = $100/contract/month. This is achievable on high-volatility stocks but not on low-vol ones.

| Stock | Vol | Monthly Premium (ATM) | Monthly Yield |
|-------|-----|----------------------|---------------|
| AMD | 64.4% | ~$18.60 | ~9.6% |
| NVDA | 41.4% | ~$8.61 | ~4.8% |
| AAPL | 31.6% | ~$9.14 | ~3.7% |
| WFC | 29.1% | ~$2.49 | ~3.4% |
| MSFT | 26.1% | ~$11.92 | ~3.0% |

Note: These are estimates based on realized vol. Actual market premiums vary with implied vol (IV).

### Best Stocks for the Wheel

**Good candidates** (high vol, willing to own):
- NVDA: high vol, strong fundamentals, long-term hold
- AMD: highest vol in portfolio at 64.4% — juicy premiums
- WFC: lower vol but stable, already a large winner (+311%)

**Poor candidates**:
- Index ETFs (SPY, QQQ): lower vol means thinner premiums
- Stocks near earnings: IV crush after earnings destroys selling edge
- Stocks in strong uptrends: keeps getting called away before you can ride the move

### Risk: Permanent Assignment

The wheel fails when the stock craters and doesn't recover:
- Sell put at $100 → assigned at $100 (effective $97 after premium)
- Stock drops to $60 → sell covered call at $95 → stock stays at $60 for 6 months
- You're sitting on a -$37/share loss while collecting $2/month
- **Never wheel a stock you wouldn't buy and hold for 2+ years**

---

## 4. Collar Strategy

### Mechanics

```
You own: 100 shares of stock
Buy: 1 put option (protection below put strike)
Sell: 1 call option (give up upside above call strike)
Net: Defined range for your P&L
```

### Zero-Cost Collar

Sell the call at a premium equal to or exceeding the put premium. Your cost of insurance is zero (or even positive).

**Typical setup**: 
- Stock at $100
- Buy 90-day put at $90 strike: costs $2.50
- Sell 90-day call at $110 strike: earns $2.50
- Net cost: $0. Floor at $90, cap at $110. 

### Best Use Case: Protecting Large Unrealized Gains

WFC is a perfect example:
- Entry (assumed): ~$25-30 range
- Current price: **$74.10**
- Gain: **+178-196%** (total since 2010: +311%)
- Tax liability on full sale would be substantial

**Collar strategy for WFC**:
1. Own 100 shares at $74.10
2. Buy 90-day put at $68.00 strike (downside protection)
3. Sell 90-day call at $80.00 strike (fund the put)
4. Lock in: floor at $68 (8% downside max), cap at $80 (8% upside max)

This protects the unrealized gain without triggering a taxable sale. The call premium helps fund the put.

**When the collar makes sense**:
- Position size > 10% of portfolio (concentration risk)
- Near retirement or major liquidity event
- Uncertain macro environment (current VIX at 25.7 — elevated)
- Large tax bill if sold outright

**Drawback**: You're paying to limit gains. If WFC runs to $100, you're capped at $80.

---

## 5. Iron Condor on Indices

### Mechanics

```
Sell OTM call (upper strike)
Buy further OTM call (cap your loss)
Sell OTM put (lower strike)  
Buy further OTM put (cap your loss)
```

You collect net premium for taking on defined, bounded risk. You profit if the index stays within your range until expiration.

### SPY Iron Condor Setup

Current SPY: **$662.29**

**30-45 DTE iron condor**:
- Sell $690 call / buy $700 call (upper spread)
- Sell $635 put / buy $625 put (lower spread)
- Width: $10 each side on SPY
- Target premium collected: $2.50-3.50 combined
- Max loss per side: $10 - $2.50-3.50 = $6.50-7.50
- Probability of profit: ~70% if strikes are ~1 standard deviation OTM

### Why SPY/QQQ for Condors

- European-style exercise on SPX options (no early assignment risk)
- Massive liquidity — tight bid/ask spreads
- Easier to manage and roll
- Index cannot go to zero

**SPY Annual Volatility by Year** (from database):
| Year | Return | Realized Vol |
|------|--------|-------------|
| 2017 | +21.7% | 6.7% | ← Perfect condor year (low vol, steady drift)
| 2020 | +18.3% | 33.4% | ← Death zone for condors
| 2021 | +28.7% | 12.9% | ← Decent condor year
| 2022 | -18.2% | 24.2% | ← Condors lose badly in trending down markets
| 2023 | +26.2% | 13.1% | ← Good condor environment
| 2024 | +24.9% | 12.6% | ← Good condor environment

**Current VIX: 25.7** — above long-term mean of 19.5. This means:
1. Premiums are elevated (good for selling)
2. Market is uncertain (condor may blow out quickly)
3. Wider strikes needed for safety

### Iron Condor Rules

1. Only enter when **IV rank > 50%** — elevated premiums justify the risk
2. Maximum loss on one condor: no more than 3-5% of portfolio
3. **Never hold to expiration** — close at 50% of max profit (take the win early)
4. **Roll or close** if either short strike is tested (price reaches your short strike)
5. **Never double down** on a losing condor — the loss is defined, take it

---

## 6. Put Spread Hedging

### Mechanics

```
Buy ATM put (expensive protection)
Sell OTM put (fund some of the cost)
Net: cheaper insurance than naked put, with defined protection range
```

**Example for $500K portfolio**:
- SPY at $662.29
- Buy 10 contracts of $660 put at $15.00 → pay $15,000
- Sell 10 contracts of $630 put at $7.00 → collect $7,000
- Net cost: $8,000 for protection on $66,229 of SPY exposure (10 contracts × 100 shares)
- Protection range: SPY $660 down to $630 (4.5% decline coverage)
- Cost: 1.2% of the protected notional

**Why not naked puts?**
- ATM put at current SPY: ~$15/share = $15,000 for 10 contracts
- Put spread: $8,000 for same notional, but protection only to $630, not unlimited

**Portfolio hedge sizing**: To hedge a $500K portfolio with 60% equity exposure ($300K in SPY-correlated assets), you need roughly 4-5 put spreads on SPY.

---

## 7. IV Rank — Timing Premium Sales

### What is IV Rank?

```
IV Rank = (Current IV - 52-week low IV) / (52-week high IV - 52-week low IV)
Range: 0-100%
```

- **IV Rank > 50%**: IV is elevated relative to its own history → sell premium (covered calls, CSPs, iron condors)
- **IV Rank < 20%**: IV is compressed → buy premium (protective puts, long calls)
- **IV Rank 20-50%**: Neutral — evaluate on other factors

### VIX as a Proxy for IV Rank

From the database:
- **Current VIX: 25.7** (above 75th percentile of 22.7)
- Mean VIX since 1990: **19.5**
- Percentage of days VIX > 25: **17.4%** — you are currently in elevated territory

**Implication**: Current environment is favorable for premium selling. IV is elevated, premiums are fat. However, elevated VIX means the market can move dramatically, so manage position size carefully.

---

## 8. Greeks Management

### Delta (Δ)
**What it measures**: How much the option price moves per $1 move in the stock.
- Short call delta: negative (-0.30 to -0.50 for OTM/ATM)
- Short put delta: positive (+0.30 to +0.50)
- **For covered calls**: Your net delta = 1.0 (stock) - 0.30 to 0.50 (call) = 0.50-0.70. You still benefit from moderate upside.

### Theta (Θ)
**What it measures**: Daily time value erosion. Your friend when short premium.
- Short call/put: positive theta (you earn time value daily)
- At 30-45 DTE: theta accelerates — maximum theta collection zone
- **Rule**: Hold positions in the 30-45 DTE zone to maximize theta per day of capital tied up

### Gamma (Γ)
**What it measures**: How much delta changes. Your enemy when short options close to expiry.
- High gamma = options become highly sensitive to small moves
- **Risk**: At <7 DTE, gamma explodes. A 1% move in the stock can move a near-ATM option by 30-50%
- **Rule**: Close or roll positions before entering <14 DTE to avoid gamma risk

### Vega (V)
**What it measures**: Sensitivity to changes in implied volatility.
- Short premium = negative vega. If IV spikes, your position loses money (even if the stock doesn't move)
- **Risk**: Selling premium before earnings means selling right before IV spikes, then buying it back after IV collapses
- **Rule**: Never sell premium into a known volatility event (earnings, Fed meetings, major data releases)

---

## 9. Tax Treatment

### General Rules (US)

1. **Short-term capital gains** apply to most options profits held < 1 year
2. **Premium income is taxed when realized** (when you close the position or it expires)
3. **Assignment**: If your covered call gets assigned, the strike price + premium becomes your proceeds. Can affect holding period.

### Qualified Covered Calls (IRS Section 1092)

A covered call is NOT a qualified covered call if:
- Deep in-the-money (strike too far below stock price)
- Less than 30 days to expiration on a gain position

Non-qualified covered calls **suspend the holding period** on the underlying stock. If you're trying to achieve long-term capital gain treatment on a stock held 11 months, selling an in-the-money call could reset the clock and cost you the lower LT cap gains rate.

**Rule**: Use OTM calls on positions held near long-term threshold. Consult tax advisor for large positions.

### Wash Sale Rule and Options

Selling a put can create a wash sale if you have a loss on the underlying stock. If you sell stock at a loss and sell a put on the same stock within 30 days, the wash sale rule may apply and your loss gets deferred.

---

## 10. Position Sizing

### Maximum Risk Per Options Position

**Rule**: Never risk more than 2-5% of portfolio on a single options position.

For $500,000 portfolio:
- **2% = $10,000 maximum loss per position**
- **5% = $25,000 maximum loss per position**

**Iron condor example**: 
- 10 SPY condors at $10 wide, collecting $3.00 premium
- Max loss per spread: $7.00 × 10 contracts × 100 shares = $7,000
- That's 1.4% of the $500K portfolio — acceptable

**Covered call example**:
- Covered call on NVDA: you already own the shares
- Additional risk from the option is your lost upside — not a hard capital loss
- Track opportunity cost, not margin risk

### Assignment Risk

**Early assignment on short calls**:
- American-style options (all stock options) can be exercised early
- Most likely to happen: **the day before ex-dividend**
- If your short call is in-the-money and the dividend exceeds the remaining time value, rational holders will exercise to capture the dividend
- **Prevention**: Check ex-dividend dates. Roll or close calls that are ITM approaching ex-dividend.

**American vs European exercise**:
- Stock options: American (early exercise possible at any time)
- SPX index options: European (can only exercise at expiration)
- QQQ/SPY: American (use SPX for avoiding early assignment risk on index plays)

---

## Recommendation for Pinch Portfolio

### Immediate Actions

1. **WFC ($74.10, large position)**: Implement a collar to protect the unrealized gain. Buy 90-day $68 put, fund with $80 call. Zero-cost or slight credit.

2. **NVDA ($180.25, high vol)**: After the next earnings announcement passes, begin selling monthly CSPs 5-8% OTM to accumulate or collect premium. Monthly premium: $5-7/contract.

3. **AAPL ($250.12)**: Ideal covered call candidate. Sell monthly OTM calls at $262-265 (5% OTM). Premium: ~$5-7. Annual income on 100 shares: $700-900.

4. **Index hedging (current VIX 25.7)**: Buy a 2-month SPY put spread to protect portfolio through current uncertainty. Cost: ~$8,000 for meaningful coverage.

### Priority Matrix

| Strategy | Priority | Stocks | Expected Monthly Income |
|----------|----------|--------|------------------------|
| Covered calls | High | WFC, AAPL, MSFT | $500-800/month |
| WFC collar | High | WFC | Protection for $203% gain |
| NVDA/AMD CSPs | Medium | NVDA, AMD | $500-700/month |
| SPY put spread hedge | High | Portfolio-level | Insurance |
| Iron condor on SPY | Low (wait for low vol) | SPY | $300-500/month |

---

## Data Requirements

To properly execute and track these strategies, we need:

1. **Options chain data**: Current IV rank by symbol — not yet in market DB (`options_chain` table exists but needs population)
2. **Earnings calendar**: Required for earnings blackout enforcement
3. **Ex-dividend dates**: For early assignment management
4. **Real-time IV**: VIX is a proxy; per-stock IV requires options chain data
5. **Position tracking**: Current holdings with cost basis and unrealized P&L

**Existing DB assets**:
- `prices` table: 203,303 records, 58 symbols — sufficient for historical backtesting
- `vix_term_structure` table: for regime-based options positioning
- `economic_data` (VIXCLS): VIX history back to 2000

---

## Implementation Plan

### Phase 1 (Weeks 1-2): Infrastructure
- [ ] Populate `options_chain` table with live IV data (via Yahoo Finance or broker API)
- [ ] Build IV rank calculator (per-symbol, rolling 252-day lookback)
- [ ] Create options position tracking module in `live/` directory
- [ ] Add earnings calendar integration

### Phase 2 (Weeks 3-4): First Positions
- [ ] Implement WFC collar (defensive priority)
- [ ] Sell first covered call on AAPL
- [ ] Evaluate NVDA CSP after earnings (check calendar)
- [ ] Buy SPY put spread hedge

### Phase 3 (Month 2+): System
- [ ] Automated 50% profit close alerts
- [ ] Rolling strategy (roll at 21 DTE or when tested)
- [ ] Monthly P&L tracking for options income vs. benchmark
- [ ] Iron condor system when VIX normalizes below 18

### Success Metrics
- Target: 1-2% monthly portfolio income from options premium
- Maximum loss from any single options position: <2% portfolio ($10,000)
- Options income tracking: compare to SPY dividend yield (currently ~1.3% annual)

---

## Key Formulas Reference

```
Monthly income target at 1%: $500,000 × 1% = $5,000/month
Annual premium income target: $60,000/year

ATM call premium (rough estimate):
  Premium ≈ 0.4 × (Annual Vol / √12) × Stock Price

IV Rank = (Current IV - 52wk Low) / (52wk High - 52wk Low)

Collar cost:
  Net debit = Put premium - Call premium
  Zero-cost when: Call premium = Put premium

Kelly Criterion (for position sizing):
  f* = (p × b - q) / b
  Where: p = win rate, q = loss rate, b = win/loss ratio
```

---

*Document generated 2026-03-13. Data sourced from pinch_market.db (203,303 daily price records, 58 symbols, 2010-2026). All premium estimates are approximations based on realized volatility — actual market premiums depend on implied volatility at time of trade.*
