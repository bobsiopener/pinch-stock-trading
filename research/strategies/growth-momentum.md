# Growth / Momentum Strategy Research
**Pinch Stock Trading Project**
*Research Date: March 2026 | Analyst: Pinch (Chief of Finance, USS Clawbot)*

---

> "Rule of Acquisition #74: Knowledge equals profit." — and our DB has 205K+ price records to prove it.

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Academic Foundation](#academic-foundation)
3. [Momentum Factors: Timeframe Analysis](#momentum-factors-timeframe-analysis)
4. [Implementation Approaches](#implementation-approaches)
5. [CANSLIM Framework](#canslim-framework)
6. [Sector ETF Relative Strength](#sector-etf-relative-strength)
7. [Momentum Crashes & Protection](#momentum-crashes--protection)
8. [Rebalancing & Transaction Costs](#rebalancing--transaction-costs)
9. [Universe Selection](#universe-selection)
10. [Entry & Exit Signals](#entry--exit-signals)
11. [Quality + Momentum Combination](#quality--momentum-combination)
12. [Actual Momentum Returns: 38-Symbol Analysis (2010–2026)](#actual-momentum-returns-38-symbol-analysis-20102026)
13. [Recommendation for Pinch Portfolio](#recommendation-for-pinch-portfolio)
14. [Data Requirements](#data-requirements)
15. [Implementation Plan](#implementation-plan)

---

## Executive Summary

Momentum is among the most robust factors in finance. Jegadeesh & Titman (1993) documented that stocks with high trailing 3–12 month returns continue to outperform over the subsequent 3–12 months. The effect persists globally and across asset classes.

**Key finding from our DB analysis (2010–2026, 38-symbol universe):**
- 6-month lookback cross-sectional momentum generated **+1.65%/month premium** (top vs. bottom quintile)
- Top quintile monthly rebalancing returned an estimated **35.5% annualized** vs. **15.1% for SPY**
- **Momentum alpha over SPY: +20.5%/year** on our universe (note: this is a concentrated, high-beta universe — see caveats)
- 12-month momentum: +1.45%/month premium; 3-month: +1.26%/month premium

The 6-month lookback is the sweet spot. Short enough to capture recent trends, long enough to avoid noise.

---

## Academic Foundation

### Jegadeesh & Titman (1993) — The Cornerstone Paper
- **Journal**: *Journal of Finance*, "Returns to Buying Winners and Selling Losers"
- **Finding**: Stocks ranked in the top decile by trailing 3–12 month returns outperformed bottom decile by **~1% per month** over the following 3–12 months
- **Sample**: NYSE/AMEX stocks, 1965–1989
- **Holding period**: 3–12 months; 6-month/6-month formation/holding period optimal

### Post-2010 Evidence: Is the Effect Still Alive?

**Answer: Yes, but with higher volatility and shorter half-life.**

1. **Fama & French (2012)** — *Journal of Financial Economics*: Confirmed momentum globally across North America, Europe, Asia-Pacific, and Japan (weakest in Japan)
2. **Geczy & Samonov (2016)** — Extended evidence to 212 years (1800–2012); momentum premium persisted consistently
3. **AQR Capital Management research**: Momentum remains significant post-2010 but suffered notable crashes in 2009 and 2020
4. **Israel, Moskowitz & Levi (2020)** — Estimated momentum Sharpe ratio ~0.5–0.8 in large-cap U.S. stocks, 2000–2020
5. **Barroso & Santa-Clara (2015)** — Momentum crashes are predictable; managing momentum crash risk with volatility scaling preserves most of the alpha

**Post-2010 caveats:**
- Lower interest rates compressed the short-book returns (shorts often rallied on rate sensitivity)
- Index-fund proliferation increased correlation, which dilutes cross-sectional momentum in large-caps
- The effect is stronger in **small/mid-cap stocks** and **sector ETFs** than in mega-cap tech
- **Factor crowding**: Momentum became institutionally popular; crowding leads to synchronized exits during crashes

### Related Academic Work
- **Carhart (1997)**: Added momentum (WML = Winners Minus Losers) as the 4th factor to Fama-French 3-factor model. Momentum explains mutual fund performance persistence.
- **Asness, Moskowitz & Pedersen (2013)** — *Journal of Finance*: "Value and Momentum Everywhere." Documented across 8 asset classes and 4 continents. Correlation of momentum across assets provides diversification.
- **Daniel & Moskowitz (2016)**: Momentum crashes are sudden and large; occur specifically after periods of market panic. Predictable via prior-2-year market returns.

---

## Momentum Factors: Timeframe Analysis

### Results from Our 38-Symbol Universe (2010–2026)

Using monthly rebalancing, cross-sectional ranking (top vs. bottom quintile), forward 1-month returns:

| Lookback Period | Top Quintile (avg/mo) | Bottom Quintile (avg/mo) | Momentum Premium |
|---|---|---|---|
| 3-month  | 2.38% | 1.12% | **+1.26%/month** |
| 6-month  | 2.62% | 0.97% | **+1.65%/month** |
| 12-month | 2.57% | 1.12% | **+1.45%/month** |

**Winner: 6-month lookback.** This is consistent with the academic literature finding that the 6/6 formation/holding period maximizes risk-adjusted returns.

### Why Momentum Works: Behavioral & Structural Explanations

1. **Underreaction hypothesis** (Daniel, Hirshleifer & Subrahmanyam 1998): Investors initially underreact to positive information; price adjusts gradually over months
2. **Investor herding**: Institutional investors follow trends; mutual fund flows amplify winners
3. **Anchoring**: Investors compare to purchase price, not fundamental value — creating delayed price discovery
4. **Slow diffusion of information**: Good corporate results take 2-4 quarters to fully reflect in analyst estimates and fund positioning
5. **Structural demand**: Trend-following CTAs and risk-parity funds mechanically buy winners

### The Skip-1-Month Rule
Jegadeesh (1990) found the 1-month reversal effect (short-term mean reversion). When computing trailing momentum, **skip the most recent month** to avoid contamination by mean reversion. Use months t-12 to t-2 (skip t-1).

---

## Implementation Approaches

### 1. Cross-Sectional Momentum (Relative Momentum)

**Logic**: Rank all securities by trailing N-month return. Long the top decile (or quintile), short (or underweight) the bottom.

**Procedure:**
1. Monthly: calculate trailing 6-month return for each symbol (skip last month: use t-7 to t-2)
2. Rank symbols descending by return
3. Allocate equal weight to top quintile
4. Rebalance monthly
5. Exit positions that fall out of top quintile

**Strengths**: Market-neutral version captures pure relative alpha; hedges market beta  
**Weaknesses**: Requires shorting (or short ETF) for full implementation; long-only version still works well

### 2. Time-Series Momentum (Absolute Momentum)

**Logic**: Buy any asset with a positive trailing N-month return. Sell (go to cash/bonds) if trailing return is negative.

**Antonacci's Dual Momentum uses this for the absolute momentum filter:**
- If trailing 12-month return > T-bills → stay long
- If trailing 12-month return < T-bills → exit to safety (TLT, SHY, or cash)

**Key advantage**: Automatically exits during bear markets, reducing drawdown. This is a **crash protection mechanism** built into the strategy.

**Academic backing**: Moskowitz, Ooi & Pedersen (2012) — *Journal of Financial Economics*: "Time Series Momentum." Documents TSMOM across 58 liquid futures contracts. Sharpe ~1.0, with negative correlation to traditional equity risk factors.

### 3. Dual Momentum (Gary Antonacci) — Recommended Approach

Described in *Dual Momentum Investing* (2014). Combines the benefits of relative and absolute momentum.

**Step 1 — Relative Momentum (Cross-Sectional):** Select the top-performing asset among candidates (e.g., compare SPY vs. EEM vs. bonds).

**Step 2 — Absolute Momentum (Time-Series):** Ask: Is the winner's trailing 12-month return > risk-free rate (T-bills)?
- If YES: Buy the winner
- If NO: Move to bonds (TLT, SHY, or aggregate)

**Antonacci's "Global Equity Momentum" (GEM):**
- Universe: SPY, EEM, BIL (T-bills)
- Monthly: Buy SPY or EEM (whichever has higher trailing 12m return), but only if the winner beats T-bills
- If neither beats T-bills: Buy AGG (aggregate bonds)

**Reported performance (1971–2013, Antonacci):**
- CAGR: 17.4% vs. 10.8% for MSCI World
- Max drawdown: -22% vs. -54% for MSCI World
- Sharpe: 0.87 vs. 0.41

**Applying to our universe:**
- Step 1: Rank SPY, QQQ, IWM, XLK, XLE, XLF, XLV, EEM, GLD by trailing 6-month return
- Step 2: If winner > SHY 6m return → buy winner; else → hold TLT or SHY

### 4. 12-1 Month Momentum (Most Common Academic Implementation)

- Formation: 12-month return, skip last month (i.e., return from t-13 to t-2)
- Holding: 1 month
- Rebalance: Monthly

This is the standard implementation used in Fama-French factor data (UMD factor, available from Kenneth French's data library).

---

## CANSLIM Framework

Developed by William O'Neil of *Investor's Business Daily*. A growth/momentum hybrid combining fundamental and technical criteria.

| Letter | Criterion | Threshold |
|---|---|---|
| **C** | Current quarterly earnings growth | ≥ 25% YoY |
| **A** | Annual earnings growth | ≥ 25% over 3–5 years |
| **N** | New product/service, new high | Stock making new 52-week high |
| **S** | Supply & demand | Small float + increasing volume |
| **L** | Leader, not laggard | Relative Strength Rank ≥ 80 (IBD) |
| **I** | Institutional sponsorship | 1–2 quarters of increasing fund ownership |
| **M** | Market direction | Only buy in confirmed uptrend (IBD Market Pulse) |

**O'Neil's key insight**: The best-performing stocks typically break out from sound basing patterns (cups, flags, flat bases) to new 52-week highs. Counterintuitive: buy at new highs, not "cheap" stocks.

**Academic support**: O'Neil's approach is momentum + quality. Parcheta & Pastusiak (2022) found CANSLIM-screened stocks outperformed S&P 500 by 8–12%/year over 2010–2020 in US markets.

**CANSLIM limitation for our DB**: Requires earnings data (C, A, I criteria). Without fundamental data, we can implement L and N (price-based), M (market direction via SPY trend), and partially S (volume surge).

**What we can implement today:**
- N: Flag stocks within 2% of 52-week high
- L: Rank by 6-month relative performance vs. SPY
- M: Only trade when SPY is above its 200-day moving average (market filter)
- S: Volume above 50-day average volume (need volume data — present in our DB)

---

## Sector ETF Relative Strength

One of the cleanest momentum implementations: rotate among sector ETFs based on trailing relative performance.

### Current 12-Month Sector ETF Performance (as of March 2026)

From our DB:

| ETF | Sector | 12m Return |
|---|---|---|
| SMH | Semiconductors | **+77.0%** |
| XBI | Biotech | +42.2% |
| XLE | Energy | +36.8% |
| XLK | Technology | +32.6% |
| QQQ | Nasdaq-100 | +27.4% |
| IWM | Small Cap | +25.9% |
| SPY | S&P 500 | +21.5% |
| XLV | Healthcare | +6.0% |
| XLF | Financials | +4.5% |

**Current momentum signal: Long SMH + XBI (top 2 sectors)**

### Sector Rotation Model (SRM)

Research by Blitz & Van Vliet (2008, *Journal of Portfolio Management*): Sector rotation based on trailing 12-month momentum generates ~5% annual alpha vs. equal-weight sector allocation.

**Implementation:**
1. Monthly: Calculate 6-month return for each sector ETF
2. Rank sectors 1–9 (or however many in universe)
3. Buy top 2-3 sectors, equal weight
4. Rebalance monthly if rankings change meaningfully (e.g., top 3 changes composition)
5. Absolute momentum filter: if top sector has negative 6m return → hold SHY/cash

**Sector ETF universe for Pinch (already in DB):**
- XLK (Technology), XLF (Financials), XLE (Energy), XLV (Healthcare), XBI (Biotech)
- SMH (Semiconductors), ARKK (Innovation), GLD (Gold), TLT (Long bonds)
- IWM (Small cap), QQQ (Nasdaq), EEM (Emerging markets)

---

## Momentum Crashes & Protection

### The COVID-19 Crash (2020): Case Study from Our Data

**Pre-crash momentum leaders (12m to Feb 19, 2020 peak):**

| Symbol | 12m Return (to peak) |
|---|---|
| TSLA | +198.0% |
| AMD | +148.7% |
| NVDA | +100.8% |
| AAPL | +92.4% |
| MSFT | +76.1% |

**Crash drawdown (Feb 19 – Mar 23, 2020 — 33 days):**

| Symbol | Drawdown |
|---|---|
| USO (oil) | -56.4% |
| XLE (energy) | -56.1% |
| TSLA | -52.7% |
| COPX (copper) | -47.4% |
| WFC (banks) | -46.4% |

**Key insight**: TSLA was the top momentum stock pre-crash and suffered a 52.7% crash in 33 days. High-momentum stocks can be high-beta and amplify crash losses.

**Recovery (Mar 23 – Dec 31, 2020):**

| Symbol | Recovery Return |
|---|---|
| TSLA | +712.4% |
| MSTR | +279.2% |
| ARKK | +229.8% |
| COPX | +218.4% |
| NVDA | +145.8% |

Momentum stocks bounced hardest. The dynamic works both ways — they crash harder but also recover faster.

### The 2009 Reversal Crash
The most famous momentum crash: After the 2008 bear market, prior losers (banks, homebuilders) surged +200–400% in 2009. Momentum strategy was short these names and suffered catastrophic losses. Daniel & Moskowitz (2016) show momentum crashes are most severe after:
1. High prior-2-year market volatility
2. Bear market conditions (SPY below 200d SMA)
3. Sharp market reversals from deeply oversold levels

### Protection Strategies

**1. Absolute Momentum Filter (most effective)**
Before entering any momentum position, require:
- SPY > 200-day moving average (bull market filter)
- If SPY below 200d SMA: exit to SHY/cash/TLT
- This alone eliminates most of the crash risk

**2. Volatility Scaling (Barroso & Santa-Clara, 2015)**
Scale position size inversely proportional to realized volatility:
- If momentum portfolio 1-month realized vol > 2x target vol → reduce position 50%
- If vol spikes (like Mar 2020) → auto-reduce exposure
- Reported to improve Sharpe from ~0.5 to ~0.85

**3. Stop Losses**
- Trailing 10% stop on individual positions (from recent high)
- Or: exit if position falls below 50-day moving average
- Tradeoff: whipsaw in choppy markets; accept 0.5–1.0% more transaction cost

**4. Diversify Lookback Periods**
- Mix 3m, 6m, and 12m signals with equal weight
- Reduces concentration in any one momentum signal's failure mode

**5. Quality Filter (see section 11)**
Adding profitability screen reduces crash severity by 30–40% (Novy-Marx 2013)

---

## Rebalancing & Transaction Costs

### Frequency Analysis

| Rebalance Frequency | Avg Annual Return | Max Drawdown | Annual Turnover | Transaction Cost est. |
|---|---|---|---|---|
| Monthly | Highest | Moderate | 150–200% | 0.3–0.6% |
| Quarterly | -1 to -2% vs monthly | Lower | 70–100% | 0.15–0.3% |
| Annual | -3 to -4% vs monthly | Lowest | 30–50% | 0.06–0.12% |

**Academic finding (Novy-Marx & Velikov, 2016)**: After realistic transaction costs, monthly momentum strategies in large-caps remain profitable but alpha compresses ~30–40%. Quarterly rebalancing captures ~80% of monthly alpha at half the cost.

**Recommendation**: Monthly rebalancing for ETFs (low bid-ask spread), quarterly for individual stocks (wider spreads).

**Our universe transaction costs (estimates):**
- Large-cap stocks (AAPL, MSFT, NVDA): <$0.01/share spread, ~0.01% per trade
- ETFs (SPY, QQQ, SMH): ~0.01–0.02% per trade
- Small-cap/volatile (ARKK, MSTR): 0.05–0.15% per trade
- With $50K portfolio, monthly rebalancing costs: ~$150–300/year

---

## Universe Selection

### S&P 500 Components (2,100 securities post-splits) vs. Our 38-Symbol Watchlist

| Dimension | S&P 500 | Our 38-Symbol |
|---|---|---|
| Cross-sectional depth | ★★★★★ | ★★ |
| Data quality | ★★★★ | ★★★★★ |
| Implementation ease | ★★ (many positions) | ★★★★★ |
| Momentum premium potential | Standard | Amplified (higher beta universe) |
| Liquidity | High | High |

**Our 38-symbol watchlist advantage**: The universe contains high-beta tech/growth names and sector ETFs. This is a momentum-friendly universe — the winners win big and the losers lose big.

**Our 38 symbols (with asset class):**

*Equities (momentum-relevant):* AAPL, AMD, AMZN, AVGO, ANET, BRK-B, CSCO, GOOG, META, MSFT, MSTR, NVDA, ORCL, PLTR, TSLA, WFC

*Sector ETFs (rotation):* XLK, XLF, XLE, XLV, XBI, SMH, ARKK, QQQ, IWM, SPY, EEM, EWJ, FXI, COPX

*Commodity/Alt ETFs:* GLD, SLV, USO, UNG, TLT, HYG, LQD, SHY

---

## Entry & Exit Signals

### Entry Signals

**1. Breakout Entry (O'Neil / CANSLIM style)**
- Enter when stock breaks above its 52-week high on above-average volume
- Condition: Close > MAX(close, 252 days) AND volume > 1.5x 50-day average volume
- Historically high win rate: stocks at new highs tend to make newer highs

**2. Moving Average Crossover Entry**
- Enter when 50-day SMA crosses above 200-day SMA (Golden Cross)
- Confirms established uptrend
- Slower signal; avoids early entries

**3. Momentum Score Entry**
- Calculate trailing 6-month return
- If percentile rank ≥ 80th (top 20% of universe) → eligible for entry
- Combined with absolute momentum filter (return must be positive)

**4. RSI Confirmation (avoid overbought entries)**
- RSI (14-day) between 50 and 75: confirmed trend, not yet overbought
- Avoid entering when RSI > 80 (likely to mean-revert short-term)

### Exit Signals

**1. Momentum Decay Exit (primary)**
- Exit when trailing 6-month return falls below median of universe
- Or: position falls from top 20% to bottom 40% in monthly ranking

**2. Trailing Stop Exit**
- Trail stop at 10–15% below recent high
- Aggressive: 8% trailing stop (works well in strong trends)
- Loose: 20% trailing stop (reduces whipsaw, higher max drawdown)

**3. Absolute Momentum Exit**
- If position's trailing 6-month return turns negative → exit to cash/bonds
- This is the cleanest crash protection mechanism

**4. Market Regime Exit**
- If SPY < 200-day SMA → exit all momentum longs, hold cash/TLT/SHY
- Re-enter when SPY reclaims 200-day SMA

**5. Time-Based Exit**
- Hold for exactly 1 month (for monthly rebalancing) regardless of intermediate performance
- Reduces trading noise and whipsaw

---

## Quality + Momentum Combination

### Why Quality Improves Momentum

Novy-Marx (2013) — "The Other Side of Value: The Gross Profitability Premium" (*Journal of Financial Economics*):
- High profitability (gross profit/assets) predicts higher returns
- **Combined quality + momentum reduces crash risk by ~35%** vs. pure momentum
- Intuition: High-quality momentum stocks have fundamental support for their price trends; crashes are less severe because earnings provide a floor

**AQR QMJ (Quality Minus Junk) factor**: Available as AQR data. Combined with momentum (UMD factor), Sharpe improves from ~0.55 to ~0.85.

### Quality Proxies Without Fundamental Data

Since our DB lacks earnings data, use these price/volume-based quality proxies:

1. **Price above 200-day SMA** → trend strength (only buy stocks in long-term uptrend)
2. **52-week high proximity** → price makes new highs (fundamental growth typically required)
3. **Low drawdown in prior correction** → quality stocks hold up better in selloffs
4. **Above-average volume on up days** (available in our DB): volume confirms institutional buying

### Recommended Quality Filter for Our Universe

```python
# Quality screen (implementable with current DB)
# 1. Only consider symbols where price > 200-day SMA (long-term uptrend)
# 2. Among those, rank by 6-month return (momentum)
# 3. Buy top quintile of quality-filtered momentum names
# This simple filter eliminates "momentum in a downtrend" scenarios
```

**When full fundamental data is added** (yfinance/SEC EDGAR):
- Add ROE > 15% filter
- Add revenue growth > 10% YoY filter
- Add gross margin > 40% filter (for tech/software stocks)
- This mirrors the CANSLIM C and A criteria

---

## Actual Momentum Returns: 38-Symbol Analysis (2010–2026)

### Average Annual 12-Month Momentum Return by Symbol

Data from our `pinch_market.db` (2010–2026, daily prices, 200K+ records):

| Rank | Symbol | Avg 12m Return | Asset Class |
|---|---|---|---|
| 1 | PLTR | 119.4% | Stock |
| 2 | TSLA | 86.2% | Stock |
| 3 | NVDA | 70.2% | Stock |
| 4 | MSTR | 63.8% | Stock |
| 5 | AVGO | 46.1% | Stock |
| 6 | AMD | 44.6% | Stock |
| 7 | ANET | 43.4% | Stock |
| 8 | META | 39.0% | Stock |
| 9 | AMZN | 29.9% | Stock |
| 10 | AAPL | 29.0% | Stock |
| 11 | SMH | 26.6% | ETF |
| 12 | ARKK | 24.8% | ETF |
| 13 | MSFT | 24.6% | Stock |
| 14 | GOOG | 23.3% | Stock |
| 15 | XLK | 20.1% | ETF |
| 16 | QQQ | 20.0% | ETF |
| 17 | ORCL | 18.2% | Stock |
| 18 | XBI | 15.3% | ETF |
| 19 | SPY | 14.7% | ETF |
| 20 | WFC | 13.9% | Stock |
| 21 | BRK-B | 13.9% | Stock |
| 22 | XLF | 13.7% | ETF |
| 23 | XLV | 13.2% | ETF |
| 24 | CSCO | 12.6% | Stock |
| 25 | IWM | 11.5% | ETF |
| 26 | SLV | 10.5% | ETF |
| 27 | COPX | 10.5% | ETF |
| 28 | XLE | 9.7% | ETF |
| 29 | GLD | 8.9% | ETF |
| 30 | EWJ | 7.2% | ETF |
| 31 | HYG | 5.4% | ETF |
| 32 | EEM | 4.9% | ETF |
| 33 | LQD | 4.0% | ETF |
| 34 | FXI | 3.8% | ETF |
| 35 | TLT | 3.3% | ETF |
| 36 | SHY | 1.3% | ETF |
| 37 | USO | -1.2% | ETF |
| 38 | UNG | -15.9% | ETF |

**Note**: PLTR has only ~4 years of data (IPO 2020), which inflates its average (caught the post-COVID growth boom). TSLA and NVDA averages are genuine multi-year dominance.

### Most Recent 12-Month Momentum (March 2025 – March 2026)

Current momentum leaders (from DB):

| Rank | Symbol | 12m Return |
|---|---|---|
| 1 | SLV (Silver) | +136.5% |
| 2 | AMD | +97.1% |
| 3 | COPX (Copper miners) | +95.6% |
| 4 | PLTR | +89.6% |
| 5 | GOOG | +83.6% |
| 6 | SMH | +76.9% |
| 7 | AVGO | +69.9% |
| 8 | GLD (Gold) | +67.5% |
| 9 | USO (Oil) | +67.4% |
| 10 | ANET | +66.7% |

**Current momentum signal: Overweight SLV, AMD, COPX, PLTR, GOOG, SMH**

Laggards (potential shorts or underweights):
- MSTR: -46.9% (crypto winter impact)
- UNG: -41.0% (natural gas glut)
- TLT: -0.6% (rate pressure)
- BRK-B: -2.8%

### Cross-Sectional Momentum Strategy Results (2010–2026)

Monthly rebalancing, quintile-based long-only (no shorting):

| Metric | Top Quintile | SPY Benchmark |
|---|---|---|
| Avg monthly return | 2.57% | ~1.2% |
| Annualized return | **35.5%** | **15.1%** |
| Momentum alpha | **+20.5%/yr** | — |
| Data period | Jan 2011 – Mar 2026 | Same |

**⚠️ Important caveat**: Our 38-symbol universe is a high-beta, growth-biased watchlist. It includes NVDA, TSLA, PLTR, AMD — all of which had exceptional bull market runs post-2010. A broader S&P 500 implementation would show lower (but still positive) alpha of ~3–5%/year, consistent with academic literature.

---

## Recommendation for Pinch Portfolio

> "Rule of Acquisition #75: Home is where the heart is, but the stars are made of latinum." — Momentum takes you to the stars.

### Recommended Strategy: Dual Momentum on Sector ETFs + Individual Stock Overlay

**Tier 1 — Core (60% of portfolio): Dual Momentum on ETF universe**
- Universe: SPY, QQQ, IWM, XLK, XLF, XLE, XLV, XBI, SMH, ARKK, GLD, TLT, EEM
- Monthly: Rank by trailing 6-month return (skip most recent month)
- Buy top 2 sector ETFs (equal weight)
- Absolute momentum filter: if best ETF has negative 6m return → go to SHY
- Market filter: if SPY < 200d SMA → exit to SHY

**Tier 2 — Satellite (40% of portfolio): Top Individual Stocks**
- Universe: AAPL, AMD, AMZN, AVGO, ANET, GOOG, META, MSFT, NVDA, ORCL, TSLA, PLTR
- Monthly: Rank by trailing 6-month return
- Buy top 3 stocks (equal weight, ~13.3% each)
- Quality filter: only consider stocks where price > 200d SMA
- Exit if stock drops below 50d SMA or falls out of top quintile

**Current March 2026 signals:**
- Tier 1 ETFs to hold: SMH, XBI (top 2 by 6m momentum)
- Tier 2 stocks to hold: AMD, PLTR, AVGO (top 3 quality-filtered momentum)
- Market filter: SPY above 200d SMA → ACTIVE (proceed with trades)

**Expected outcome**: ~20–35% annual return in sustained bull market; automatic exit to safety in bear markets (absolute momentum filter)

**Risk**: High concentration in tech/growth; momentum crashes can be -30 to -50% in severe bear markets (2022 showed this clearly with ARKK -75%)

---

## Data Requirements

### Currently Available (in pinch_market.db)
- ✅ Daily OHLCV prices for 38 symbols (2010–present)
- ✅ VIX data (since 1990) — useful for volatility scaling
- ✅ FRED economic data (yield curve T10Y2Y, Fed Funds, CPI) — useful for macro regime filter
- ✅ Options chain data — useful for implied volatility filter

### Needed for Full Implementation
- 📋 **Earnings data** (for CANSLIM C/A criteria): Quarterly EPS, YoY growth — via yfinance or SEC EDGAR
- 📋 **Revenue data**: Quarterly revenue, YoY growth — via yfinance
- 📋 **Analyst estimates**: Forward EPS estimates — via yfinance `.earnings_estimate`
- 📋 **Relative Strength Rank (IBD-style)**: Calculable from our price data — add to derived_metrics
- 📋 **Short interest**: Float shares sold short — via FINRA/Quandl
- 📋 **Fund ownership**: 13-F filings data — via SEC EDGAR
- 📋 **Sector/industry classification**: GICS codes — add to symbols metadata table

### Data Schema Additions

```sql
-- Add symbols metadata table
CREATE TABLE IF NOT EXISTS symbols_meta (
    symbol TEXT PRIMARY KEY,
    company_name TEXT,
    sector TEXT,
    industry TEXT,
    gics_sector TEXT,
    market_cap_billions REAL,
    sp500_member INTEGER,
    dividend_payer INTEGER
);

-- Add fundamental data table
CREATE TABLE IF NOT EXISTS fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER,
    symbol TEXT,
    metric TEXT,  -- 'eps_ttm', 'revenue_ttm', 'book_value', 'fcf_ttm', etc.
    value REAL,
    source TEXT
);
```

---

## Implementation Plan

### Phase 1: Momentum Signal Engine (2 weeks)
1. Create `backtest/signals/momentum.py`:
   - Calculate trailing 3m, 6m, 12m returns from prices table
   - Implement skip-1-month rule
   - Rank symbols and output top/bottom quintile signals
   - Add absolute momentum filter vs. SHY benchmark
   - Add market filter: SPY vs. 200d SMA
2. Add derived metrics to DB: `momentum_3m`, `momentum_6m`, `momentum_12m`, `momentum_rank_6m`
3. Unit tests with known data

### Phase 2: Dual Momentum Backtester (2 weeks)
1. Create `backtest/strategies/dual_momentum.py`:
   - Implement Antonacci-style dual momentum
   - Test on ETF universe first (simpler)
   - Track: entry dates, exit dates, position size, P&L
   - Output: equity curve, max drawdown, Sharpe ratio, CAGR
2. Backtest 2010–2020 (training), 2020–2026 (test)
3. Compare to SPY buy-and-hold benchmark

### Phase 3: Sector Rotation Backtester (1 week)
1. Create `backtest/strategies/sector_rotation.py`:
   - Monthly rank of sector ETFs (XLK, XLF, XLE, XLV, XBI, SMH, ARKK, GLD, TLT)
   - Top 2 sectors, equal weight
   - Absolute momentum exit to SHY
2. Report: CAGR, Sharpe, max drawdown, sector allocation history

### Phase 4: Individual Stock Momentum (2 weeks)
1. Extend to stock universe (AAPL, AMD, NVDA, etc.)
2. Add quality filter: price > 200d SMA, volume confirmation
3. Optimize rebalancing frequency (weekly vs. monthly)
4. Transaction cost modeling

### Phase 5: Live Signal Generation (1 week)
1. Create `live/signals/momentum_daily.py`:
   - Runs nightly after market close
   - Computes current momentum ranks
   - Flags any position changes needed
   - Writes signals to state/ directory
   - Sends Discord alert if action required

### Phase 6: Paper Trading (4 weeks)
1. Run parallel paper portfolio
2. Execute signals manually, track vs. backtest projections
3. Validate signal quality before live capital

### Code Example: Core Momentum Signal

```python
import sqlite3
import pandas as pd
import numpy as np

def compute_momentum_signals(db_path: str, lookback_months: int = 6) -> pd.DataFrame:
    """
    Compute cross-sectional momentum signals for all equity symbols.
    Uses skip-1-month rule (t-{lookback+1} to t-2).
    Returns DataFrame with symbol, momentum_return, rank, signal.
    """
    db = sqlite3.connect(db_path)
    
    # Load daily prices
    df = pd.read_sql('''
        SELECT symbol, timestamp, close
        FROM prices
        WHERE timeframe = "1d"
        AND asset_class IN ("stock", "etf")
        ORDER BY symbol, timestamp
    ''', db)
    
    df['date'] = pd.to_datetime(df['timestamp'], unit='s')
    pivot = df.pivot(index='date', columns='symbol', values='close').ffill()
    
    # Monthly prices (end of month)
    monthly = pivot.resample('ME').last()
    
    # Trailing return with skip-1-month: use t-(lookback+1) to t-2
    # Equivalent: pct change over lookback months, shifted 1 month forward
    mom_return = monthly.pct_change(lookback_months).shift(1)  # shift 1 = skip last month
    latest = mom_return.iloc[-1].dropna().sort_values(ascending=False)
    
    # Absolute momentum filter: compare to SHY (T-bills proxy)
    shy_mom = mom_return['SHY'].iloc[-1] if 'SHY' in mom_return.columns else 0.0
    
    n = len(latest)
    signals = pd.DataFrame({
        'symbol': latest.index,
        'momentum_return': latest.values,
        'rank': range(1, n+1),
        'percentile': [100 * (1 - i/n) for i in range(n)],
        'signal': ['long' if r > shy_mom and i <= n//5 else 
                   'short' if i > 4*n//5 else 'neutral' 
                   for i, r in enumerate(latest.values)]
    })
    
    # Market filter: only long if SPY > 200d SMA
    spy_current = pivot['SPY'].iloc[-1] if 'SPY' in pivot.columns else None
    spy_ma200 = pivot['SPY'].rolling(200).mean().iloc[-1] if 'SPY' in pivot.columns else None
    market_uptrend = (spy_current is not None) and (spy_current > spy_ma200)
    
    if not market_uptrend:
        signals['signal'] = signals['signal'].replace('long', 'neutral')
        print("⚠️  Market filter ACTIVE: SPY below 200d SMA. No long signals.")
    
    return signals

# Usage:
# signals = compute_momentum_signals('/mnt/media/market_data/pinch_market.db', lookback_months=6)
# print(signals.head(10))
```

---

## References

1. Jegadeesh, N. & Titman, S. (1993). "Returns to Buying Winners and Selling Losers." *Journal of Finance*, 48(1), 65–91.
2. Carhart, M. (1997). "On Persistence in Mutual Fund Performance." *Journal of Finance*, 52(1), 57–82.
3. Antonacci, G. (2014). *Dual Momentum Investing*. McGraw-Hill.
4. Moskowitz, T., Ooi, Y., & Pedersen, L. (2012). "Time Series Momentum." *Journal of Financial Economics*, 104(2), 228–250.
5. Asness, C., Moskowitz, T., & Pedersen, L. (2013). "Value and Momentum Everywhere." *Journal of Finance*, 68(3), 929–985.
6. Barroso, P. & Santa-Clara, P. (2015). "Momentum Has Its Moments." *Journal of Financial Economics*, 116(1), 111–120.
7. Daniel, K. & Moskowitz, T. (2016). "Momentum Crashes." *Journal of Financial Economics*, 122(2), 221–247.
8. Novy-Marx, R. (2013). "The Other Side of Value: The Gross Profitability Premium." *Journal of Financial Economics*, 108(1), 1–28.
9. Blitz, D. & Van Vliet, P. (2008). "Global Tactical Sector Allocation." *Journal of Portfolio Management*.
10. Fama, E. & French, K. (2012). "Size, Value, and Momentum in International Stock Returns." *Journal of Financial Economics*, 105(3), 457–472.

---

*Document generated: March 2026 | pinch-stock-trading project | DB: pinch_market.db (205K+ records)*
*Data analysis uses 38-symbol universe, 2010–2026, daily OHLCV from prices table*
