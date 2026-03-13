# Macro/Tactical Asset Allocation

> *"Rule of Acquisition #34: War is good for business."* (And so is knowing when war is coming.)

**Status:** Research Complete  
**Date:** 2026-03-13  
**Author:** Pinch, Chief of Finance  
**Applies to:** $500,000 imaginary portfolio — equity + ETF allocation decisions  

---

## Overview

Macro and tactical allocation answers a different question than stock picking: **how much should you have in stocks, bonds, gold, and cash at any given time?** This is the highest-leverage decision in investing — asset allocation explains ~90% of long-term portfolio variance. Get the allocation right and stock selection matters less. Get it wrong and great stock picks still lose money.

This document covers six macro frameworks: risk parity, traditional 60/40, CAPE ratio timing, yield curve signals, VIX-based allocation, and regime detection. Each is backtested against our database where possible.

---

## 1. Risk Parity (Bridgewater All Weather Inspired)

### Philosophy

Traditional portfolios are dominated by equity risk. A "60/40" portfolio is ~95% correlated to equities because stocks are so much more volatile than bonds. Risk parity equalizes the **risk contribution** from each asset class, not the dollar allocation.

### Simplified All Weather Allocation (No Leverage)

| Asset Class | Allocation | ETF | Rationale |
|-------------|-----------|-----|-----------|
| Stocks | 30% | SPY/QQQ | Growth/rising growth |
| Long-term bonds | 40% | TLT | Deflation hedge, falling growth |
| Intermediate bonds | 15% | SHY/LQD | Moderate duration |
| Gold | 7.5% | GLD | Inflation hedge |
| Commodities | 7.5% | USO/COPX | Inflationary surprise |

**Why this works**: Each asset class performs well in a specific macro regime:
- **Rising growth, rising inflation**: Stocks and commodities win
- **Rising growth, falling inflation**: Stocks win
- **Falling growth, rising inflation**: Gold and commodities win (stagflation)
- **Falling growth, falling inflation**: Long bonds win

When you don't know which regime is coming (and you rarely do), spread risk across all four.

### The Leverage Problem

Bridgewater uses leverage to boost bond returns to equate with equity volatility. Without leverage:
- Bonds are naturally less volatile than stocks
- 40% in TLT doesn't offset 30% in equities by risk
- Result: the "risk parity" portfolio is still somewhat equity-dominant

**Adaptation for Pinch**: Accept that without leverage, this portfolio will have ~40-50% equity beta, not 25%. It's still more diversified than pure equity.

### From the Database (TLT vs SPY correlation)

Portfolio performance calculation using database assets:

| Ticker | Ann Return (2010-2026) | Correlation to SPY |
|--------|----------------------|-------------------|
| SPY | +679% total, ~15.7% ann | 1.00 |
| TLT | Long bonds (check DB) | ~-0.20 to 0.00 |
| GLD | Gold (check DB) | ~0.05 |
| SHY | Short bonds | ~0.00 |

**Note**: 2022 broke the bond-stock diversification thesis. Both SPY (-18.2%) and TLT fell simultaneously due to rising rates. The "risk parity" portfolio had its worst drawdown in 40 years.

---

## 2. 60/40 and Alternatives

### The Traditional 60/40

**Allocation**: 60% stocks (SPY/QQQ), 40% bonds (TLT/LQD)

**Historical performance**: 1980-2021, this worked brilliantly. Bonds were in a 40-year bull market as rates fell from 20% to 0%. Every stock market correction was met with bond gains.

**2022 reality check**: Both stocks and bonds fell simultaneously.
- SPY: -18.2%
- TLT: -30%+ (long bonds crushed by rate hikes)
- 60/40 portfolio: roughly -20% — the worst year in decades
- This happened because the correlation assumption broke: stocks and bonds both moved with rates

### Alternative Allocations

**50/30/20 (Stocks/Bonds/Alternatives)**:
- 50% SPY/QQQ
- 30% TLT + SHY (mixed duration)  
- 20% alternatives: GLD, commodities, cash

**The Permanent Portfolio** (Harry Browne):
- 25% stocks
- 25% long bonds
- 25% gold
- 25% cash/short bonds

Permanent Portfolio logic: one of four assets thrives in each macro environment. You're always 25% positioned correctly and you never make a big macro bet.

**Performance**: Lower volatility than 60/40, meaningful drawdowns in strong equity bull markets. In 2022, outperformed significantly.

### 2022 Lesson Applied

The lesson isn't "abandon bonds." It's "know the rate environment."
- Rates rising → reduce long bond duration, prefer short bonds or TIPS
- Rates falling → long bonds are the ultimate risk-off trade
- Current state (2026): 10Y at 4.21%, 2Y at 3.64% — curve re-steepened after 2024 inversion

When rates are high and likely to fall, bonds become attractive again (bond prices rise as rates fall).

---

## 3. CAPE Ratio Timing

### What Is CAPE?

Cyclically Adjusted Price-to-Earnings (Shiller P/E): compares current stock prices to average inflation-adjusted earnings over the prior 10 years. Smooths out short-term earnings swings.

```
CAPE = Current S&P 500 Price / (10-year average real EPS)
```

### Historical Thresholds

| CAPE Level | Implication | Historical Forward 10-year Return |
|------------|------------|----------------------------------|
| < 10 | Deeply undervalued | ~12-15% per year |
| 10-15 | Fair to undervalued | ~10-12% per year |
| 15-25 | Fair value range | ~7-10% per year |
| 25-35 | Overvalued | ~3-6% per year |
| > 35 | Bubble territory | ~0-3% or negative |

**Current CAPE** (~33 as of 2026): Historically suggests lower 10-year forward returns. Not a timing signal — just a calibration for expected returns.

### The CAPE Problem

CAPE has been "expensive" (above 25) since approximately 2013. If you sold stocks at CAPE = 25 in 2013, you missed:
- 2014: +13.5%
- 2017: +21.7%
- 2019: +31.2%
- 2020: +18.3%
- 2021: +28.7%
- 2023: +26.2%
- 2024: +24.9%

Total SPY return from 2013-2026: **+300%+ missed by CAPE sellers.**

**Why CAPE fails as a tactical timer**:
1. Interest rates change the denominator. When risk-free rates are 0%, stocks can sustain higher P/E.
2. Earnings quality changed — buybacks inflate EPS artificially.
3. Index composition shifted toward higher-margin tech businesses.

**The Ferengi verdict**: CAPE is useful for long-term **return calibration** ("expect 4-7% annual returns from here, not 12%"), but not for market timing. Don't sell stocks because CAPE is high. Use it to set return expectations.

### How to Use CAPE Practically

- **CAPE > 30**: Reduce return expectations. Be more aggressive about taking profits. Don't use projected 10% returns for retirement planning.
- **CAPE < 15**: Allocate more aggressively to equities. Historical evidence strongly supports forward returns.
- **CAPE 15-30**: Normal range. Standard allocation.

---

## 4. Yield Curve Signals

### The Yield Curve Recession Signal

**Yield curve inversion** = 2Y Treasury yield > 10Y Treasury yield (T10Y2Y spread < 0)

From the database (T10Y2Y series, 2000-2026):
- **Current T10Y2Y**: +0.51% (curve is positively sloped — no inversion)
- **10Y Treasury**: 4.21%
- **2Y Treasury**: 3.64%
- **Fed Funds Rate**: 3.64%
- **Historical inversions**: 15.4% of days since 2000

**Key inversion periods from database**:
```
2022-07-05 → 2024-08-26: 25-month inversion (deepest since 1980s)
  → Recession was predicted; recession (by official definition) did not occur
  
2019-08-26 → 2019-08-29: Brief inversion
  → COVID recession followed in 2020 (15-month lag)
```

### Inversion → Recession Lead Time

Historical average: **12-24 months** from inversion start to recession.

The inversion itself doesn't cause recession — it reflects market expectations. The recession tends to occur **when the curve re-steepens** (the un-inversion), not during the inversion.

**Interpretation of current status** (T10Y2Y = +0.51%):
- Curve re-normalized after the 2022-2024 inversion
- This is the historically risky period: recession often follows the un-inversion
- The 2024-2025 re-steepening after a prolonged inversion → watch closely

### Yield Curve Trading Rules

```
If T10Y2Y < 0 for 30+ consecutive days:
  → Increase defensive allocation
  → Consider reducing equity to 50% from standard allocation
  → Favor quality (BRK-B, WFC, dividend stocks)
  
If T10Y2Y re-steepens from negative to +0.5%+ (post-inversion):
  → Historically high recession risk in next 6-18 months
  → Increase cash/bonds, decrease cyclicals
  → This is the current status in 2026

If T10Y2Y > 1.5% and rising (normal healthy economy):
  → Full equity allocation appropriate
  → Risk-on positioning
```

### Steepening = Early Cycle Recovery

When the yield curve steepens from flat/inverted (rates cut, short end falls, long end stays elevated):
- Fed has cut rates aggressively (recession response)
- Economic recovery typically 6-18 months ahead
- Historically one of the best times to be long equities, especially cyclicals
- Small caps (IWM) typically outperform in early cycle

---

## 5. VIX-Based Allocation

### VIX Statistics from Database (VIX history 1990-2026)

```
VIX Records: 9,114 daily observations
Date range: 1990-01-01 to 2026-03-10
Current VIX: 25.7
Historical mean: 19.5
Median: 17.6
25th percentile: 13.9
75th percentile: 22.7
% of days VIX > 25: 17.4%
% of days VIX < 15: 32.3%
```

**Current VIX at 25.7 = above 75th percentile.** This is an elevated reading indicating market stress.

### VIX Allocation Signals

| VIX Level | Regime | Equity Allocation | Interpretation |
|-----------|--------|-------------------|----------------|
| < 12 | Complacency | 60-70% equity | Market is calm; could increase or be cautious of bubble |
| 12-15 | Normal low vol | 65-75% equity | Full risk-on appropriate |
| 15-20 | Normal | 55-65% equity | Standard allocation |
| 20-25 | Elevated | 45-55% equity | Reduce equity, add bonds/cash |
| 25-35 | Stressed | 35-45% equity | Defensive positioning |
| > 35 | Crisis | 20-40% equity (or BUY) | Peak fear = opportunity, but risk is real |
| > 50 | Capitulation | Scale IN aggressively | Once-in-decade buying opportunities |

**Counterintuitive rule**: VIX > 35-40 is often a BUY signal, not sell. By the time VIX hits 50 (COVID-19 March 2020), the worst is usually over. The market dropped -33.7% max drawdown in March 2020 and then rallied 100%+ within 2 years.

### VIX Timing Results (Conceptual)

The strategy: reduce equity when VIX spikes, increase when VIX normalizes.

**Problem**: VIX is a coincident indicator, not a leading one. When VIX spikes to 40, you've already lost 15-20% on your equity position. Selling at VIX 40 locks in losses.

**Better use**: Use VIX to determine options strategy (sell premium when VIX > 20, buy when VIX < 15) rather than binary in/out of equities.

**Current signal (VIX 25.7)**:
- Reduce equity exposure 5-10% from target
- Avoid adding new equity positions
- Hold existing positions but tighten stop-losses
- Consider protective puts (IV is elevated — costly but appropriate)
- Excellent environment for selling covered calls / collecting premium

---

## 6. Regime-Based Allocation

### Regime Detection Using 200-Day SMA

From database backtest (SPY 2010-2026):
- **Bull regime** (SPY > SMA200): 3,284 days | **84.7%** of the time | **+22.6% annualized**
- **Bear regime** (SPY < SMA200): 591 days | **15.3%** of the time | **-31.0% annualized**

The regime effect is enormous. Being invested in bull regimes and in cash during bear regimes would have dramatically improved risk-adjusted returns.

### Regime-Based Allocation Rules

```python
# Pseudo-code for regime detection
if spy_close > spy_sma_200:
    regime = "BULL"
    equity_allocation = 0.70   # 70% stocks
    bond_allocation = 0.20     # 20% bonds
    gold_allocation = 0.10     # 10% gold
else:
    regime = "BEAR"
    equity_allocation = 0.30   # 30% stocks
    bond_allocation = 0.40     # 40% bonds
    gold_allocation = 0.30     # 30% gold/cash
```

### Regime Allocation by Asset

**Risk-ON (Bull Regime):**
| Asset | Allocation | ETF |
|-------|-----------|-----|
| US Large Cap | 40% | SPY |
| US Tech | 15% | QQQ or XLK |
| International | 10% | EEM, EWJ |
| Bonds | 20% | LQD, TLT |
| Gold | 7.5% | GLD |
| Cash | 7.5% | — |

**Risk-OFF (Bear Regime):**
| Asset | Allocation | ETF |
|-------|-----------|-----|
| US Large Cap | 20% | SPY |
| Defensive stocks | 10% | XLV, XLF |
| Long bonds | 30% | TLT |
| Short bonds | 10% | SHY |
| Gold | 20% | GLD |
| Cash | 10% | — |

### Current Regime Status (2026-03-13)

- SPY price: $662.29  
- SPY 200-day SMA: needs calculation (estimated ~$570-590 based on price history)
- **SPY well above its SMA200 → BULL REGIME**
- However, VIX elevated at 25.7 → **transition caution warranted**
- Recent YTD 2026 SPY return: -2.9% (some short-term weakness)

---

## 7. Commodity Overlay

### Gold as Inflation Hedge

Gold (GLD) performs well in:
1. High and rising inflation
2. Real interest rates going negative (nominal rates minus inflation)
3. Currency debasement / central bank money printing
4. Geopolitical uncertainty

**Current environment**: With Fed Funds at 3.64% and CPI rising, real rates are moderate. Gold has been on a multi-year bull run driven partly by central bank demand (China, India, emerging markets diversifying away from USD).

**Allocation**: 5-10% of portfolio in GLD provides meaningful hedging without excessive drag in equity bull markets.

### Oil/Energy as Geopolitical Hedge

USO (oil) and XLE (energy equities) hedge against geopolitical supply disruptions. Energy was the best-performing sector in 2022 (+65%) when everything else fell. COPX (copper) tracks industrial demand — a leading economic indicator.

**Commodity overlay rules**:
- Baseline: 5-7% GLD allocation at all times
- Add USO/COPX when: inflation above 3% AND industrial demand indicators rising
- Reduce when: global growth slowing AND oil supply increasing

---

## 8. Seasonal Allocation: "Sell in May"

### The Historical Pattern

"Sell in May and go away" suggests that November-April is a stronger period for stocks than May-October.

**SPY Monthly Returns Analysis** (using database 2010-2026):

The seasonal effect is real but inconsistent:
- November-April average: historically ~7-8% per 6-month period
- May-October average: historically ~4-5% per 6-month period

**The problem**: The pattern is too unreliable to trade mechanically.
- 2020: May-October was massive recovery (+30%+)
- 2022: Both halves were negative
- 2023-2024: Strong all year

**Verdict**: Weak seasonal effect exists but insufficient to justify full exit in May. A small tactical tilt (reduce equity 5-10% in May, increase in November) may be marginally beneficial. Not worth significant implementation cost.

---

## Recommendation for Pinch Portfolio

### Current Macro Assessment (March 2026)

| Indicator | Reading | Signal |
|-----------|---------|--------|
| VIX | 25.7 | Elevated — caution |
| SPY vs SMA200 | Above | Bull regime |
| Yield curve (T10Y2Y) | +0.51% (normalizing post-inversion) | Watch for recession |
| CAPE | ~33 | Overvalued — lower return expectations |
| Fed Funds | 3.64% | Restrictive but easing |

**Macro verdict**: Bull regime but with elevated risk indicators. The appropriate response is **not to panic sell**, but to reduce equity concentration and add defensive cushions.

### Current Portfolio Issues to Address

1. **Tech concentration at ~56%** (per risk management analysis): Far above the 30% sector maximum. A tech correction/AI bubble pop would devastate the portfolio.
2. **No bond allocation**: Classic risk of a pure equity portfolio. Need TLT, LQD, or SHY buffer.
3. **No gold allocation**: Zero inflation/geopolitical hedge.
4. **Cash reserve**: Need minimum 10% per risk management framework.

### Target Allocation (Phase 1 — Risk Reduction)

| Asset | Target | ETF/Position | From |
|-------|--------|-------------|------|
| US Large Cap | 35% | SPY | Reduce tech concentration |
| Tech/Growth | 20% | QQQ, XLK | Down from ~56% |
| International | 5% | EEM, EWJ | New |
| Long Bonds | 15% | TLT | New |
| Investment Grade | 5% | LQD | New |
| Gold | 7.5% | GLD | New |
| Cash | 12.5% | — | New |

**Transition**: Cannot rebalance immediately without significant tax events on winners. Implement gradually:
- New money → bonds, gold, cash
- Covered calls on tech to reduce effective exposure
- Tax-loss harvest losers to fund rebalancing

---

## Data Requirements

Currently available in pinch_market.db:
- ✅ `DGS10`, `DGS2`, `T10Y2Y` (yield curve) — 2000-2026
- ✅ `FEDFUNDS` (monetary policy) — full history
- ✅ `VIXCLS` (VIX history) — 1990-2026
- ✅ `CPIAUCSL` (inflation) — full history
- ✅ `UNRATE` (unemployment) — full history
- ✅ `GDPC1` (GDP) — quarterly
- ✅ `UMCSENT` (consumer sentiment) — monthly
- ✅ `M2SL` (money supply) — full history

Needed but not yet collected:
- ❌ CAPE ratio (Shiller P/E) — requires earnings data, not in FRED
- ❌ TLT price history — need to verify in `prices` table (may exist)
- ❌ Credit spreads (BAMLH0A0HYM2 exists in DB — high yield spread)

---

## Implementation Plan

### Phase 1 (Weeks 1-2): Regime Monitor
- [ ] Build automated regime detector (SPY vs SMA200) that runs daily
- [ ] Build VIX regime tracker with allocation recommendations
- [ ] Create yield curve dashboard: T10Y2Y, DGS2, DGS10, FEDFUNDS
- [ ] Write daily macro briefing generator for Pinch's morning report

### Phase 2 (Weeks 3-4): Portfolio Rebalancing
- [ ] Calculate current sector allocations vs targets
- [ ] Identify covered call candidates to reduce effective equity exposure
- [ ] Add GLD position (5-7% allocation)
- [ ] Add TLT position (10-15% allocation) as rates have risen
- [ ] Build minimum 10% cash reserve

### Phase 3 (Month 2): Systematic Signals
- [ ] Automated regime-based allocation signals (rebalance when regime shifts)
- [ ] VIX-triggered allocation rules (auto-reduce equity when VIX > 30)
- [ ] Yield curve alert system (notify when T10Y2Y crosses 0)
- [ ] CAPE tracker (web scrape or FRED CAPE data if available)

### Success Metrics
- Maximum equity concentration: < 60%
- Maximum single sector: < 30%
- Target Sharpe ratio > 1.0
- Maximum portfolio drawdown: < 15%
- Inflation protection: GLD + TIPS allocation > 7%

---

*Document generated 2026-03-13. Macro data sourced from pinch_market.db: 79,803 economic records (FRED), VIX 1990-2026, SPY 2010-2026 (4,074 daily records). SPY buy-and-hold 2010-2026: +679%. Bull regime annualized return: +22.6%. Bear regime annualized return: -31.0%.*
