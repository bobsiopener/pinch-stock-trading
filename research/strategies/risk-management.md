# Risk Management Framework

> *"Rule of Acquisition #62: The riskier the road, the greater the profit."*  
> *"Rule of Acquisition #9: Opportunity plus instinct equals profit."*  
> But the meta-rule that supersedes all others: **don't lose the latinum.**

**Status:** Research Complete — **HIGHEST PRIORITY DOCUMENT**  
**Date:** 2026-03-13  
**Author:** Pinch, Chief of Finance  
**Applies to:** All trading activity — stocks, ETFs, options, and in coordination with crypto portfolio  

---

## Overview

Risk management is not a constraint on profit — it's what enables profit to survive. Every trading strategy eventually encounters an adversarial market. The question is not whether you'll face a -20% drawdown, but whether you'll still have capital to recover from it.

This framework governs ALL decisions in the Pinch portfolio. When a strategy rule conflicts with a risk rule, **risk management wins**. Every time.

**Current risk profile assessment (March 2026)**:
- Portfolio: $500,000 (imaginary)
- Tech concentration: ~56% (dangerous — maximum should be 30%)
- VIX: 25.7 (elevated — above 75th percentile)
- Yield curve: Post-inversion normalization (historically precedes recession)
- Cash reserve: Unknown (needs measurement)
- Protective positions: None documented

---

## 1. Position Sizing Methods

### Method A: Fixed Fractional (Recommended Baseline)

Risk a fixed percentage of portfolio on each trade. The most important rule: **define maximum loss before entering any position**.

```
Position Size = (Portfolio × Risk%) / (Entry Price - Stop Price)

Example:
  Portfolio: $500,000
  Risk per trade: 1% = $5,000
  NVDA entry: $180.25
  Stop loss: $166.00 (2× ATR below entry, ATR ~$7)
  Risk per share: $14.25
  
  Position size = $5,000 / $14.25 = 351 shares ≈ 3.5% of portfolio value
```

**Recommended tiers**:
| Trade Type | Risk Per Trade | Max Position Size |
|------------|---------------|------------------|
| High conviction, long-term hold | 2% ($10,000) | 10% of portfolio |
| Standard swing trade | 1% ($5,000) | 5-7% of portfolio |
| Speculative / earnings play | 0.5% ($2,500) | 2-3% of portfolio |
| Options / high-risk strategies | 0.5% ($2,500) | 2-5% of portfolio |

**Why not risk more?** The math of losses is asymmetric:
```
-10% loss requires +11.1% gain to recover
-20% loss requires +25.0% gain to recover
-33% loss requires +50.0% gain to recover
-50% loss requires +100.0% gain to recover
```
The deeper the drawdown, the harder the recovery. Stay small.

### Method B: Kelly Criterion

The Kelly formula optimizes bet size based on edge:

```
f* = (p × b - q) / b

Where:
  f* = fraction of portfolio to risk
  p  = probability of winning
  q  = probability of losing (1 - p)
  b  = win/loss ratio (average win ÷ average loss)

Example (SMA 50/200 crossover system):
  Win rate = 71.4% → p = 0.714
  Avg win = +22.9%, avg loss = -7.2%
  b = 22.9 / 7.2 = 3.18
  
  f* = (0.714 × 3.18 - 0.286) / 3.18
  f* = (2.27 - 0.286) / 3.18
  f* = 1.984 / 3.18 = 0.624 = 62.4% of portfolio!
```

**Warning**: Full Kelly sizing leads to extreme volatility and gut-wrenching drawdowns, even with a positive expectancy system. Most professional traders use **quarter Kelly** or **half Kelly**:

```
Quarter Kelly: 62.4% × 0.25 = 15.6% per position
Half Kelly: 62.4% × 0.50 = 31.2% per position
```

Even quarter Kelly at 15.6% is aggressive. **Use Kelly as a ceiling, never as a floor.**

### Method C: Volatility-Based Sizing (ATR Method)

Size positions inversely to their volatility. Higher vol = smaller position. Lower vol = larger position.

```
Target $ Volatility per Position = Portfolio × 0.5%  ($2,500 on $500K)
ATR-based size = Target $ Volatility / (ATR × multiplier)

Example — NVDA (ATR ~$7, high vol stock):
  Position = $2,500 / ($7 × 2) = 179 shares = ~$32,265 = 6.5% of portfolio

Example — WFC (ATR ~$1.80, lower vol):
  Position = $2,500 / ($1.80 × 2) = 694 shares = ~$51,425 = 10.3% of portfolio
```

This method automatically gives larger allocations to stable stocks and smaller allocations to volatile ones. **Recommended for the Pinch portfolio** as it naturally limits NVDA/AMD overweight.

### Method D: Equal Weight

Simply allocate equal dollar amounts to each position.
- Simple to implement and understand
- No edge beyond simplicity
- Works well in diversified portfolios with 20+ positions
- Poor fit for a concentrated portfolio of high-conviction positions

**Verdict**: Use **ATR-based sizing** as primary method with **fixed fractional** as a hard upper limit. Equal weight as a sanity check.

---

## 2. Portfolio-Level Risk Limits

### The Hard Limits

These are non-negotiable. No strategy justification overrides these:

```
MAX SINGLE POSITION:    10% of portfolio ($50,000)
MAX SINGLE SECTOR:      30% of portfolio ($150,000) 
MIN CASH RESERVE:       10% of portfolio ($50,000)
MAX INVESTED (equity):  80% of portfolio ($400,000)
MAX DRAWDOWN (kill):    15% of portfolio ($75,000 loss)
```

### Current Violation: Tech Concentration at ~56%

This is the most critical risk issue in the portfolio. Tech concentration at 56% means:
- A 30% tech sector correction = **-16.8% total portfolio loss** (already exceeds our 15% kill switch)
- The AI/semiconductor narrative could unwind rapidly (regulation, China conflict, earnings miss)
- NVDA, AMD, ANET, MSFT, GOOG are all correlated in a tech risk-off event

**Immediate action required**: Reduce tech exposure below 30% through a combination of:
1. Not adding new tech positions
2. Selling covered calls on tech positions (reducing effective exposure)
3. Directing all new capital to non-tech (bonds, GLD, defensive equities)
4. Gradual rotation as tax-efficient opportunities arise (tax-loss harvesting on any losers)

### Sector Maximum (30%) — Why It Matters

```
Portfolio: $500,000
Tech at 56% = $280,000 in tech
A -30% tech event (common in sector rotations): -$84,000 = -16.8% total portfolio
A -50% tech correction (e.g., 2000-2002, semiconductors 2022): -$140,000 = -28% total portfolio
```

Historical sector crashes:
- XLK (tech): -80% in dot-com bust
- XLF (financials): -75% in 2008 financial crisis
- XLE (energy): -60% in 2015-2016 oil crash
- Any sector can get cut in half. Concentration = catastrophic risk.

### Correlation Monitoring

Holding 5 highly correlated positions provides no diversification benefit.

**Current portfolio correlation risk**:
- NVDA, AMD, ANET, XLK, SMH, QQQ: All semiconductor/tech — correlation likely 0.80-0.95
- During tech sell-offs, they all fall together
- No offsetting positions in current portfolio (no bonds, no gold, no defensive sectors)

**Correlation monitoring rule**:
```
If correlation(Position A, Position B) > 0.80:
  → Count as a single position for sizing purposes
  → Combined allocation capped at 10% (single position max)
```

Calculate rolling 90-day correlation using price data from pinch_market.db.

---

## 3. Stop-Loss Optimization

### Backtest: Fixed Stop Losses on SPY

From SPY annual volatility data (pinch_market.db):
```
Average annual SPY volatility: ~14-15%
Average monthly SPY volatility: ~4.0%
Average SPY ATR(14): $9.17 (1.4% of price)
Max drawdown 2010-2026: -33.7% (March 2020)
```

**Fixed stop loss analysis**:

| Stop Level | Characteristics | Best For |
|------------|----------------|----------|
| -5% | Triggers on normal volatility; constant whipsaws | Scalp trades only |
| -8% | Standard swing trade stop | 2-4 week holds |
| -10% | Industry standard for position trades | 1-3 month holds |
| -15% | Allows significant noise before exit | Long-term holds |
| -20% | SPY's "bear market" definition; very late exit | Index ETFs only |

**For SPY specifically**:
- Average annual vol of 14% means -8% stops get triggered ~50% of years by normal drawdowns
- Better: Use ATR-based stops that adapt to the current volatility environment

### ATR-Based Stop Loss (Recommended)

```
SPY current ATR(14): $9.17
2× ATR stop: $9.17 × 2 = $18.34 below entry
3× ATR stop: $9.17 × 3 = $27.51 below entry

For $662.29 entry:
  2× ATR stop: $643.95 (-2.8% from entry)
  3× ATR stop: $634.78 (-4.1% from entry)
```

For individual volatile stocks:
- NVDA ATR(14): estimated ~$7-8 (3.9-4.4% of price)
- 2× ATR = ~$15 below entry: reasonable for swing trade
- 3× ATR = ~$22 below entry: for position trade

**Trailing ATR stop** (for running positions):
```
Trailing stop = Max close since entry - (2 × ATR at that time)
Updates daily. Only moves up, never down.
Locks in gains while giving trend room to run.
```

### Time-Based Stop

If a position is not performing after N days, exit and redeploy capital.

```
Swing trade: exit after 15 trading days if return < +2%
Position trade: exit after 30 trading days if return < +5%
Long-term hold: no time stop, but re-evaluate thesis quarterly
```

**Rationale**: Capital sitting in a flat position is not "safe" — it's dead capital. The opportunity cost of holding a non-performer is real.

---

## 4. Cash Allocation Rules

### Baseline Rules

```
MINIMUM CASH: 10% ($50,000) — always. Emergency liquidity.
MAXIMUM INVESTED: 80% ($400,000) — never go full-tilt
NORMAL RANGE: 15-25% cash
```

### VIX-Triggered Cash Levels

| VIX Level | Target Cash | Target Equity | Rationale |
|-----------|-------------|---------------|-----------|
| < 15 | 10-15% | 70-80% | Low risk, deploy capital |
| 15-20 | 15-20% | 65-75% | Normal environment |
| 20-25 | 20-25% | 55-65% | Elevated volatility |
| 25-35 | 25-35% | 45-55% | Current (VIX 25.7) — defensive |
| > 35 | 30-40% cash OR selective buying | 40-50% | Fear peak = opportunity |
| > 50 | Consider aggressive buying | — | Once-in-decade entry |

**Current recommendation** (VIX = 25.7): Target **25-30% cash**. Portfolio should not be deploying new capital into equity aggressively right now.

### Cash Management During Drawdowns

**Circuit breaker cascade**:
```
Portfolio at -5%:  Alert. Review all positions. Tighten stops.
Portfolio at -8%:  Reduce each position size by 25%.
Portfolio at -10%: Reduce total equity exposure to 50% of portfolio.
Portfolio at -12%: Reduce to 30% equity. 
Portfolio at -15%: KILL SWITCH — go to 100% cash. 1-week minimum cooldown.
```

The cascade prevents a small drawdown from becoming a catastrophic one by systematically reducing exposure as losses mount.

---

## 5. Cross-Asset Risk: Stock + Crypto Correlation

### The Combined Exposure Problem

Both the Pinch stock portfolio and the pinch-crypto-trading portfolio are active. If they both draw down simultaneously, the total loss compounds dramatically.

**Historical stock-crypto correlation**:
- During normal markets: low correlation (0.10-0.30)
- During risk-off events (March 2020, Q4 2018): correlation spikes to 0.80-0.90
- Both fall hard together when investors flee ALL risk assets

**The risk calculation**:
```
If stock portfolio is $500K and crypto is another $100K:
  Combined "at risk" capital: $600,000
  A -30% correlated crash: -$180,000 = 30% of combined

The circuit breaker needs to account for BOTH portfolios.
```

### Cross-Asset Rules

1. **Combined max drawdown**: Total across both portfolios: 20% of combined capital before full defensive mode
2. **Correlation tracking**: Monitor 30-day rolling correlation between SPY and BTC daily close
3. **When BTC drops >20% in a week**: Reduce stock portfolio risk by 10-15% (risk-off contagion expected)
4. **Position limits**: If crypto portfolio > 15% of combined portfolio value, reduce crypto first before adding stocks

---

## 6. Tax-Loss Harvesting

### Mechanics

Sell a losing position to realize a capital loss. The loss offsets capital gains elsewhere (or up to $3,000/year of ordinary income if no gains to offset).

**The wash sale rule**: You cannot buy "substantially identical" securities within 30 days before or after the sale. Violating the wash sale rule defers the loss — it's not a permanent disallowance, just timing.

### ETF Substitution Strategy

Sell: SPY at a loss → Buy: VOO (same exposure, different fund, not "substantially identical")
Sell: QQQ at a loss → Buy: QQQM (Invesco's slightly different version, generally accepted)
Sell: GLD at a loss → Buy: IAU (different gold ETF, not substantially identical)

**For individual stocks**: Must wait 30 days to repurchase same stock. Cannot use options to maintain equivalent exposure (covered calls on the same stock within 30 days triggers wash sale).

### Tax-Loss Harvesting Calendar

**Best timing**: 
- November: Last chance to realize losses for current tax year with time to reinvest
- Tax gain harvesting: In years with large deductions or low income, realize gains in the 0% long-term capital gains bracket

**Rule**: Never let the tax tail wag the investment dog. A 20% capital loss carried forward is worth less than a 20% gain passed up. Taxes are a cost, not a reason to hold a bad position indefinitely.

### Current Portfolio Opportunities

For the Pinch portfolio, tax-loss harvesting opportunities would arise from:
- Any tech position down significantly from entry
- Any position no longer fitting the strategy thesis
- Losses can offset gains from positions called away via covered calls

---

## 7. Circuit Breakers

### Individual Position Circuit Breakers

```
Position down 8% from entry:
  → Trigger: Automatic stop if ATR-based stop is violated
  → Manual review: Is the thesis still intact?
  
Position down 15% from entry:
  → Exit immediately. No further analysis. Capital preservation first.
  → Post-mortem: Why was the stop at 8% not triggered?
```

### Trading Performance Circuit Breakers

```
CIRCUIT BREAKER 1: 3 consecutive losing trades
  → Trigger: Third consecutive closed losing trade
  → Action: Reduce position sizes to HALF for next 10 trades
  → Duration: Until 5 consecutive winning trades (or 30 days, whichever later)
  → Rationale: Consecutive losses often indicate system breakdown or adverse regime

CIRCUIT BREAKER 2: 10% portfolio drawdown from peak
  → Trigger: Portfolio down 10% from all-time-high
  → Action: Reduce to 50% invested. No new positions. Review all open.
  → Cooldown: 5 trading days minimum before increasing exposure again
  → Rationale: Trend of losses suggests something systemic

CIRCUIT BREAKER 3: 15% portfolio drawdown (KILL SWITCH)
  → Trigger: Portfolio down 15% from all-time-high
  → Action: EXIT ALL POSITIONS. 100% CASH.
  → Cooldown: Minimum 1 calendar week. No exceptions.
  → Return criteria: VIX must be declining, market must show stabilization
  → Rationale: Cannot risk further compounding of losses
```

**Kill switch portfolio calculation**:
```
Starting capital: $500,000
10% drawdown trigger: portfolio < $450,000
15% drawdown kill switch: portfolio < $425,000
Maximum loss before kill switch: $75,000
```

### The Psychology Problem

Circuit breakers only work if they are **mechanically enforced**, not overridden by emotions. Common psychological failure modes:
1. "I'll just hold until it recovers" — averaging down into a losing trade
2. "This time is different" — ignoring the circuit breaker rule
3. "I need to win back what I lost" — revenge trading after losses

**Solution**: Program circuit breakers into the live trading system. Not manual. When the portfolio hits the drawdown threshold, the system auto-reduces or flat-closes. Bob can override, but the default must be enforcement.

---

## 8. Rebalancing Triggers

### Calendar Rebalancing

**Monthly rebalance review**: First trading day of each month.
- Review current allocation vs target
- Identify positions > 2% above target allocation
- Sell the excess or use new capital to rebalance toward targets

**Why monthly?**: Daily rebalancing creates excessive transaction costs. Annual is too infrequent — drift can become dangerous. Monthly is the industry standard for retail investors.

### Drift-Based Rebalancing (Preferred)

Rebalance when any position drifts more than 5% from its target:

```
If target_weight = 10% and current_weight > 15%:
  → Trim position to 10-12% (don't rebalance all the way back — leave some trend momentum)

If target_weight = 10% and current_weight < 5%:
  → Add to position up to 8-10% (buying the laggard)
```

**The 5% drift rule** balances:
- Allowing winners to run (not cutting them off at the target every day)
- Preventing dangerous concentration

### Tax-Aware Rebalancing

Priority order for where to rebalance:
1. **Tax-advantaged accounts first** (IRA, 401k): No tax consequence on rebalancing
2. **Long-term gains** (held > 1 year): Lower tax rate (0%, 15%, or 20%)
3. **Short-term gains** (held < 1 year): Ordinary income rates — avoid selling if possible
4. **Losses**: Always harvest — creates tax benefit

---

## 9. Kill Switch Design

### The Kill Switch

A kill switch is a **single button** that:
1. Cancels all open orders
2. Closes all open positions (market order)
3. Moves proceeds to cash
4. Locks out new trading for 1 calendar week
5. Sends alert to Bob

**When to use**:
- 15% portfolio drawdown (automated trigger)
- Bob's discretion: major life event, medical emergency, vacation
- System malfunction or data integrity issue
- Market circuit breaker (exchange-level halt lasting > 24 hours)

### Kill Switch Implementation

```python
def execute_kill_switch(reason: str):
    """
    EMERGENCY: Flatten all positions and go to cash.
    Called automatically at 15% drawdown or manually by Bob.
    """
    log_event("KILL SWITCH TRIGGERED", reason=reason)
    
    # 1. Cancel all pending orders
    cancel_all_open_orders()
    
    # 2. Close all positions at market
    for position in get_all_positions():
        place_market_sell(position.symbol, position.quantity)
    
    # 3. Record trigger event
    state.kill_switch_triggered = True
    state.kill_switch_date = datetime.now()
    state.kill_switch_reason = reason
    
    # 4. Lock trading for 1 week
    state.trading_locked_until = datetime.now() + timedelta(days=7)
    
    # 5. Notify Bob
    send_alert(f"⚠️ KILL SWITCH TRIGGERED: {reason}. All positions closed.")
```

### Manual Override

Bob can:
1. Trigger kill switch manually at any time (no conditions required)
2. Override the 1-week cooldown lock **after review and written rationale in logs**
3. Set portfolio drawdown threshold to different level (default 15%)

**The lock is not permanent** — it's a forced pause to think clearly before resuming.

---

## 10. Portfolio Risk Dashboard

### Daily Risk Metrics to Track

```
1. Portfolio Value & Daily P&L
2. Drawdown from Peak (% and $)
3. Current Cash %
4. Sector Concentration (top 3 sectors)
5. Largest Position Size
6. VIX Level + 30-day trend
7. SPY vs SMA200 (regime status)
8. Open circuit breakers (any triggered?)
9. Consecutive win/loss count
10. Total realized + unrealized gains YTD
```

### Weekly Risk Review

Every Friday:
- Review all positions against stop-loss levels
- Check correlations among positions
- Rebalance if any position drifts > 5%
- Verify cash allocation is within bounds
- Review any circuit breaker proximity

---

## Recommendation for Pinch Portfolio

### CRITICAL: Immediate Actions Required

**Priority 1 — Reduce Tech Concentration (URGENT)**:
```
Current tech: ~56%  →  Target: ≤30%
Action: Sell covered calls on all tech positions to reduce effective exposure
Action: No new tech purchases until below 30%
Action: Redirect all new capital to bonds (TLT/LQD), gold (GLD), cash
Timeline: 30-60 days
```

**Priority 2 — Establish Cash Reserve**:
```
Current VIX (25.7) target cash: 25-30% of portfolio
If currently < 25% cash: sell small position in tech lagger
Maintain minimum: 10% ($50,000) at ALL times
```

**Priority 3 — Implement Stop Losses**:
```
Every open position needs a documented stop loss level
Use: ATR-based stops (2× ATR below current price or entry, whichever lower)
Record: Entry price, stop price, max loss $, % of portfolio at risk
```

**Priority 4 — Kill Switch Setup**:
```
Automate: 15% drawdown trigger → close all positions
Current $500K portfolio: kill switch at $425,000
Test the kill switch in paper trading before live deployment
```

### Position Sizing Reference Card

For $500,000 portfolio:
```
Maximum single position:  $50,000 (10%)
Standard position target: $25,000-35,000 (5-7%)
High-risk speculative:    $10,000-15,000 (2-3%)
Options max risk:          $10,000-25,000 (2-5%)
Cash minimum:              $50,000 (10%)
Cash target (current VIX): $125,000-150,000 (25-30%)
```

---

## Data Requirements

Currently available in pinch_market.db:
- ✅ Daily prices for all 58 symbols: ATR calculation, correlation analysis
- ✅ VIX history (1990-2026): VIX-based allocation triggers
- ✅ FRED economic data: Macro risk indicators
- ✅ 203,303 daily price records: Full backtest capability

Needed for complete risk management:
- ❌ **Real-time portfolio positions**: Need to connect to broker API or manual entry
- ❌ **Cost basis by position**: For tax-loss harvesting calculations
- ❌ **Sector classification**: For sector concentration monitoring
- ❌ **Crypto portfolio value**: For cross-asset correlation/risk

---

## Implementation Plan

### Phase 1 (Week 1): Risk Infrastructure
- [ ] Build `portfolio_state.json` — current positions, cost basis, allocation weights
- [ ] ATR calculator for all 58 symbols (using pinch_market.db prices)
- [ ] Sector concentration calculator
- [ ] Circuit breaker monitoring system

### Phase 2 (Week 2): Automation
- [ ] Drawdown tracker: Calculates current drawdown from peak every day
- [ ] VIX-based allocation recommendation engine
- [ ] Stop-loss monitoring: Alert when price approaches 2× ATR stop
- [ ] Kill switch implementation in `live/kill_switch.py`

### Phase 3 (Week 3-4): Integration
- [ ] Connect risk module to position management
- [ ] Paper trade under risk constraints for 2 weeks
- [ ] Verify kill switch works correctly (test in paper environment)
- [ ] Integrate cross-asset (crypto portfolio) drawdown tracking

### Phase 4 (Month 2): Optimization
- [ ] Run backtest: What stop-loss level optimizes Sharpe ratio on historical data?
- [ ] Test Kelly criterion vs fixed fractional on 2-year SPY data
- [ ] Optimize circuit breaker thresholds (is 15% kill switch optimal?)

### Success Metrics
- Zero positions without documented stop losses
- Maximum single sector < 30% (down from 56%)
- Portfolio Sharpe ratio > 1.0
- Maximum drawdown < 15% (kill switch prevents exceeding)
- Cash always ≥ 10%

---

## Quick Reference: The Risk Rules

```
THE NON-NEGOTIABLE RULES (break these = guaranteed loss of capital):

1. NEVER risk more than 2% of portfolio on a single trade
2. NEVER let tech/any sector exceed 30% of portfolio
3. ALWAYS maintain 10% minimum cash reserve
4. ALWAYS have a stop loss before entering a position
5. NEVER average down into a losing trade without thesis review
6. NEVER trade without a pre-defined exit (profit target OR stop)
7. EXECUTE the kill switch at 15% drawdown. No exceptions. No "it'll recover."

THE RULES OF THUMB:

- In doubt → do nothing → wait for clearer signal
- High VIX → smaller positions → more cash
- Losing streak → reduce size → review system
- Winning streak → don't increase size → risk management still applies
- New position → ATR-based stop from day one
```

---

*Document generated 2026-03-13. This is the governing document for all trading decisions in the Pinch portfolio. All strategy documents (options, macro-tactical, technical systems) operate within these risk parameters. Data: pinch_market.db, 203,303 records, 58 symbols, 2010-2026. Current risk status: ELEVATED (VIX 25.7, tech concentration ~56%, post-yield-curve-inversion environment).*
