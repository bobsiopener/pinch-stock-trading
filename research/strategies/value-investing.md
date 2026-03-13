# Value Investing Strategy Research
**Pinch Stock Trading Project**
*Research Date: March 2026 | Analyst: Pinch (Chief of Finance, USS Clawbot)*

---

> "Rule of Acquisition #9: Opportunity plus instinct equals profit." — Value investing is opportunity in disguise.

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Classic Value Metrics](#classic-value-metrics)
3. [Graham & Dodd: The Foundation](#graham--dodd-the-foundation)
4. [Buffett's Evolution: Quality at a Fair Price](#buffetts-evolution-quality-at-a-fair-price)
5. [Magic Formula (Joel Greenblatt)](#magic-formula-joel-greenblatt)
6. [Piotroski F-Score](#piotroski-f-score)
7. [Deep Value vs. Quality Value](#deep-value-vs-quality-value)
8. [Value Traps: How to Avoid Them](#value-traps-how-to-avoid-them)
9. [The Value Factor "Death" (2018–2020)](#the-value-factor-death-20182020)
10. [Implementation Without Fundamental Data](#implementation-without-fundamental-data)
11. [Price-Based Value Analysis: Our 38-Symbol Universe](#price-based-value-analysis-our-38-symbol-universe)
12. [What Fundamental Data We Need](#what-fundamental-data-we-need)
13. [Rebalancing Considerations](#rebalancing-considerations)
14. [Recommendation for Pinch Portfolio](#recommendation-for-pinch-portfolio)
15. [Data Requirements](#data-requirements)
16. [Implementation Plan](#implementation-plan)

---

## Executive Summary

Value investing — buying securities for less than their intrinsic worth — is the most academically documented equity strategy. Fama & French (1992) codified it as the "value premium" (HML factor): high book-to-market stocks outperform low book-to-market stocks by ~4.5%/year over long periods.

**However, our DB currently lacks the fundamental data** (P/E, P/B, earnings) required for classic value screening. This document covers:
1. The academic and practitioner foundations of value investing
2. What metrics work best and why
3. Price-based value proxies we CAN implement today
4. Analysis of our 38-symbol universe using available price data
5. The roadmap to full fundamental value implementation

**Current price-based opportunities identified (March 2026):**
- MSTR: 48% below 200d SMA (z-score: -1.45) — deep oversold, likely value trap risk
- MSFT: 18% below 200d SMA (z-score: -1.41) — quality stock at discount, worth monitoring
- XLF (Financials): z-score -1.23 — sector rotation opportunity
- ORCL: 29% below 200d SMA (z-score: -0.94)

---

## Classic Value Metrics

### The Core Valuation Multiples

**1. Price-to-Earnings (P/E)**
- Most widely used metric. Price per share / earnings per share (TTM)
- "Normal" S&P 500 long-run average: ~16x
- Cyclical issue: earnings collapse in recessions, inflating P/E (Shiller CAPE addresses this)
- **Predictive power**: Graham & Dodd P/E (using 10-year avg earnings) = Shiller CAPE. CAPE above 25 predicts below-average 10-year returns (Shiller 2015)
- Limitation: doesn't account for growth; GARP uses PEG (P/E / growth rate) — PEG < 1 is attractive

**2. Price-to-Book (P/B)**
- Price / book value per share. Classic "asset value" measure.
- Fama & French (1992): High B/P (low P/B) → highest future returns
- Berkshire Hathaway historically traded at 1.1–1.5x book; Buffett would buy back shares when P/B < 1.2
- Limitation: Book value is accounting construct; intangible-heavy businesses (software, brands) have inflated P/B ratios because intangibles are often expensed, not capitalized
- **Post-2000**: P/B has weakened as a value signal due to rising intangible economy

**3. Price-to-Sales (P/S)**
- Revenue is harder to manipulate than earnings
- Works better for early-stage or unprofitable companies
- O'Shaughnessy (1998): P/S < 1 was the single best value predictor in 1951–1996 US data
- Current (March 2026): SPY trades at ~2.8x sales (historically elevated)

**4. EV/EBITDA**
- Enterprise Value / EBITDA — capital structure-neutral metric
- Avoids distortion from leverage, depreciation differences
- Greenblatt's "earnings yield" uses EBIT/EV (inverse of EV/EBIT)
- Academic finding (Loughran & Wellman 2011): EV/EBITDA is strongest value predictor when tested on US stocks 1963–2009
- Typical "cheap": EV/EBITDA < 8x; "expensive": >20x; S&P 500 current ~14x

**5. Free Cash Flow Yield (FCF/Market Cap)**
- Most reliable because FCF is cash, not accounting earnings
- Buffett calls it "owner's earnings": Net income + D&A - capex - working capital changes
- Strong predictor: FCF yield > 5% typically cheap; < 2% expensive
- Best for mature, asset-light businesses (poor for growth companies reinvesting all FCF)

### Which Metric Predicts Returns Best?

**Evidence (Gray & Carlisle, "Quantitative Value" 2012):**

| Metric | Decile Spread (top vs bottom) | Notes |
|---|---|---|
| EV/EBITDA | **~7%/year** | Best overall |
| EV/EBIT | ~6.5%/year | Removes D&A distortion |
| P/FCF | ~6.2%/year | Strong for mature cos |
| P/B | ~5.5%/year | Weaker post-2000 |
| P/E | ~5.0%/year | Cyclically distorted |
| P/S | ~4.8%/year | Industry-dependent |

**Recommendation**: Use EV/EBITDA as primary screen, supplemented by FCF yield for quality confirmation.

### Shiller CAPE (Cyclically Adjusted P/E)

Robert Shiller's 10-year inflation-adjusted P/E ratio:
- Current (March 2026): ~34–36x (historically elevated; long-run average ~16x)
- Predictive: CAPE explains ~40% of variance in 10-year subsequent S&P 500 returns
- CAPE > 30: predicts ~3–5% real annual return over next decade vs. long-run 7%
- **Implication**: Broad market is expensive; stock-picking (or international value) is more attractive

---

## Graham & Dodd: The Foundation

### The Seminal Text: *Security Analysis* (1934)

Benjamin Graham and David Dodd established the intellectual framework for value investing during the Great Depression. Key principles:

**1. Margin of Safety**
- Always buy at a significant discount to intrinsic value
- "The three most important words in investing" (Graham)
- Provides buffer against estimation errors and adverse events
- Graham's target: buy at ≥ 33% discount to intrinsic value

**2. Mr. Market Metaphor**
- The market is a manic-depressive business partner offering to buy/sell each day
- When Mr. Market is depressed (prices low) → buy
- When Mr. Market is euphoric (prices high) → sell
- Lesson: market price is not the same as business value

**3. Intrinsic Value**
Graham's formula (1962 edition of *The Intelligent Investor*):
```
Intrinsic Value = EPS × (8.5 + 2g)
```
Where g = expected annual growth rate (%), 8.5 = P/E for a no-growth company

Modern modified version:
```
Intrinsic Value = EPS × (8.5 + 2g) × (4.4 / AAA bond yield)
```

**4. Net-Net Working Capital (NNWC)**
Graham's "deep value" approach:
```
NNWC = (Cash + 0.75×Receivables + 0.5×Inventory) - Total Liabilities
```
Buy stocks trading below NNWC ("cigar butt" investing — one puff of value left)

**Historical performance**: Net-nets produced 29.4%/year from 1950–1976 vs. 11.5% for market (Oppenheimer 1986). Mostly unavailable in today's large-cap market.

**5. Graham's 7 Criteria for Defensive Investor**
1. Adequate size (>$2B market cap)
2. Strong financial condition (current ratio > 2x)
3. Earnings stability (positive 10 consecutive years)
4. Dividend record (uninterrupted ≥20 years)
5. Earnings growth (≥33% over 10 years)
6. Moderate P/E (≤15x last 3-year avg earnings)
7. Moderate Price/Book (P/E × P/B ≤ 22.5)

---

## Buffett's Evolution: Quality at a Fair Price

### The Shift from Graham to Munger

Warren Buffett started as a Graham disciple (pure price-based value), but Charlie Munger shifted his thinking: pay a **fair price for an exceptional business** rather than a **bargain price for a mediocre one**.

**Buffett's key insight**: The value of compounding means that a great business held forever generates more value than a cheap business sold after a 50% gain.

### The Three Pillars: Moat, Management, Margin of Safety

**1. Durable Competitive Advantages (Moats)**

Types of economic moats (Morningstar's framework):
- **Network effects**: Value increases with users (Visa, Mastercard, Microsoft Windows)
- **Intangible assets**: Brands, patents, regulatory licenses (Coca-Cola, J&J, AAPL brand)
- **Cost advantages**: Structural cost edge (Amazon AWS, Berkshire insurance float)
- **Switching costs**: Expensive or difficult to change providers (Salesforce, Oracle, Adobe)
- **Efficient scale**: Natural monopoly in niche market (Moody's, ratings duopoly)

**Moats in our universe:**
- MSFT: Network effects (Office 365, Teams, Azure), switching costs → Wide moat
- AAPL: Ecosystem lock-in, brand, switching costs → Wide moat
- GOOG: Network effects (search), switching costs (Android) → Wide moat
- NVDA: Technology edge (CUDA ecosystem), switching costs → Narrow to wide
- AMZN: Cost advantages (AWS), network effects (marketplace) → Wide moat
- CSCO: Switching costs (enterprise networking infrastructure) → Narrow moat

**2. ROIC > WACC (Return on Invested Capital > Weighted Average Cost of Capital)**

This is the quantitative test for a moat:
- If ROIC > WACC consistently → company creating value, has competitive advantage
- If ROIC < WACC consistently → value destruction, avoid
- Buffett: Looks for ROIC consistently above 15% without leverage

**WACC assumptions (2026 environment):**
- Risk-free rate: ~4.5% (10-year Treasury)
- Equity risk premium: 5–6%
- WACC for most large-caps: 8–11%
- Required ROIC to add value: >10–12%

**Estimated ROIC for our universe stocks** (approximate, based on public data):
- NVDA: ~90%+ ROIC (asset-light chip design, high margins)
- MSFT: ~35–40% ROIC (software/cloud)
- AAPL: ~150%+ ROIC (negative working capital business model)
- GOOG: ~25–30% ROIC
- AVGO: ~15–20% ROIC
- WFC: N/A (bank, use ROE; WFC ROE ~11%)
- CSCO: ~20–25% ROIC

**3. Management Quality**
- Capital allocation: Are they buying back shares when cheap? Avoiding dilutive acquisitions?
- Insider ownership: High ownership aligns interests
- Long tenure: Stability and track record

---

## Magic Formula (Joel Greenblatt)

### From *The Little Book That Beats the Market* (2006)

Joel Greenblatt's system ranks stocks on two combined factors:
1. **Earnings Yield** = EBIT / Enterprise Value (inverse of EV/EBIT, measures cheapness)
2. **Return on Capital** = EBIT / (Net Fixed Assets + Working Capital) (measures quality)

**Procedure:**
1. Screen universe: >$50M market cap, no financials, no utilities
2. Rank all stocks by earnings yield (1 = highest yield)
3. Rank all stocks by return on capital (1 = highest ROIC)
4. Add the two ranks: combined rank = quality + cheapness composite
5. Buy the 20–30 stocks with lowest combined rank
6. Hold 1 year, then rebalance
7. Hold each position for 1 year and one day (for tax purposes — long-term capital gains treatment)

**Historical performance (Greenblatt, 1988–2004):**
- Magic Formula: 30.8%/year
- S&P 500: 12.4%/year
- Note: concentrated in large-caps (>$1B universe), no leverage

**Independent replication (Persson & Selander 2009, US stocks):**
- CAGR: 26.2% vs 14.8% S&P 500 (1998–2008)
- Magic Formula underperformed in 2-3 year periods but outperformed 85% of rolling 5-year windows

**Why it works:**
- Earnings yield catches cheap stocks (cheap = high E/P)
- ROIC filter avoids value traps (profitable cheap = not broken)
- Combining both eliminates cheap-but-dying companies and expensive-but-great companies

**Implementation for our universe** (once fundamental data is added):
```python
# Magic Formula rank calculation
stocks['earnings_yield_rank'] = stocks['earnings_yield'].rank(ascending=False)
stocks['roic_rank'] = stocks['roic'].rank(ascending=False)
stocks['magic_rank'] = stocks['earnings_yield_rank'] + stocks['roic_rank']
top_picks = stocks.nsmallest(5, 'magic_rank')  # Top 5 from our small universe
```

---

## Piotroski F-Score

### From "Value Investing: The Use of Historical Financial Statement Information" (2000)

Joseph Piotroski's 9-point scoring system using accounting data to separate winners from losers within cheap stocks (high B/M stocks).

**F-Score Components (1 point each):**

**Profitability (4 points):**
| # | Signal | Criterion |
|---|---|---|
| F1 | ROA | Return on assets > 0 (profitable) |
| F2 | ΔROA | ROA improving year-over-year |
| F3 | CFO | Cash flow from operations > 0 |
| F4 | Accruals | CFO/Assets > ROA (cash earnings quality) |

**Leverage & Liquidity (3 points):**
| # | Signal | Criterion |
|---|---|---|
| F5 | ΔLeverage | Long-term debt/avg assets decreased |
| F6 | ΔLiquidity | Current ratio improved |
| F7 | Dilution | No new shares issued this year |

**Operating Efficiency (2 points):**
| # | Signal | Criterion |
|---|---|---|
| F8 | ΔMargin | Gross margin improved |
| F9 | ΔTurnover | Asset turnover improved |

**F-Score interpretation:**
- 8–9: Strong (buy signal among cheap stocks)
- 5–7: Average
- 0–2: Weak (short signal or avoid)

**Performance (Piotroski 2000):**
- High F-Score (≥7) high B/M stocks: +13.4%/year above market
- Low F-Score (≤2) high B/M stocks: -5.6%/year below market
- Long-short spread: ~19%/year (before costs)

**Post-2010 evidence**: Hyde (2021) finds Piotroski F-Score still significant in US large-caps (1988–2020), generating ~4–6%/year alpha after costs.

**Application**: In our universe, once we have fundamental data, screen for:
1. Identify stocks trading below 200d SMA (price-based value proxy for cheap)
2. Compute Piotroski F-Score
3. Buy only F-Score ≥ 7 stocks from the cheap group
4. Avoid all F-Score ≤ 3 stocks regardless of price cheapness

---

## Deep Value vs. Quality Value

### Deep Value (Graham Net-Nets, Statistical Cheapness)

**Definition**: Buy the statistically cheapest stocks by any valuation metric (bottom P/E decile, lowest P/B stocks).

**Characteristics:**
- Often distressed, declining businesses
- "Cigar butt" quality — one puff left
- High failure rate (20–30% of deep value positions go bankrupt or stay cheap)
- But the surviving winners more than compensate (positively skewed returns)

**Academic evidence**: Lakonishok, Shleifer & Vishny (LSV 1994): "Contrarian Investment, Extrapolation, and Risk" — found value stocks outperform growth by 10%+/year, driven by investor overreaction (too pessimistic on value stocks)

**Worked historically** but with high volatility and psychological pain: must hold through years of underperformance.

### Quality Value (Buffett Style)

**Definition**: Cheap relative to intrinsic value, but intrinsic value supported by high-quality earnings, moat, and management.

**Characteristics:**
- P/E reasonable (15–25x) relative to growth rate (PEG < 1.5)
- ROIC > 15%
- Revenue and earnings growing consistently
- Strong free cash flow
- No bankruptcy risk (Altman Z > 3)

**Example in our universe** (hypothetical, based on public data):
- AAPL trading at P/E of 25x with 10% EPS growth → PEG = 2.5 (expensive)
- AAPL at P/E of 18x with 10% EPS growth → PEG = 1.8 (borderline)
- MSFT at P/E of 28x with 15% EPS growth → PEG = 1.87 (reasonably priced for quality)
- CSCO at P/E of 14x with 5% EPS growth → PEG = 2.8 (cheap but slow-growing)

**Quality value screening criteria:**
1. P/E < 25x AND PEG < 2.0
2. ROIC > 15%
3. Revenue growth > 5%/year (last 3 years)
4. Piotroski F-Score ≥ 6
5. Altman Z-Score > 3 (financially healthy)
6. Gross margin stable or improving

---

## Value Traps: How to Avoid Them

A value trap is a stock that appears cheap but keeps falling because the business is structurally declining.

### Red Flags: Classic Value Trap Signals

**1. Altman Z-Score < 1.8**
Predicts bankruptcy risk within 2 years.
```
Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
```
Where:
- X1 = Working Capital / Total Assets
- X2 = Retained Earnings / Total Assets
- X3 = EBIT / Total Assets
- X4 = Market Cap / Total Liabilities
- X5 = Revenue / Total Assets

Z > 2.99: Safe zone | 1.81–2.99: Grey zone | < 1.81: Distress zone

**2. Revenue Decline**
- Revenue declining 3+ consecutive years = structural problem, not cyclical
- Rule: Never buy a cheap stock with declining revenue unless clear catalyst exists

**3. Rising Debt / Declining Coverage**
- Debt/EBITDA > 4x: High leverage risk
- Interest coverage ratio < 2x: Cash flow barely covering interest payments
- Any covenant violations: Early warning sign

**4. Payout Ratio > 80% (for dividend-paying "cheap" stocks)**
- High payout ratio + cheap stock + low growth = dividend cut coming
- Dividend cuts cause 20–30% price drops immediately

**5. Negative Free Cash Flow + High P/FCF**
- Stock appears cheap on P/E but FCF is negative (earnings are not cash)
- Revenue recognition games (channel stuffing, aggressive accruals)
- Always cross-check earnings against cash flow from operations

**6. Industry Disruption**
- Cheap for a reason: new technology rendering business model obsolete
- Examples: print newspapers (cheap on P/E for years before collapse), video rental, physical retail
- In our universe: WFC (bank disruption by fintech?), CSCO (SDN disrupting hardware routers?)

### Value Trap vs. Genuine Value: Decision Framework

```
Is it cheap?
  ↓ Yes
Is revenue growing or stable?
  ↓ Yes → Is ROIC > cost of capital?
               ↓ Yes → Is Altman Z > 2?
                          ↓ Yes → POTENTIAL VALUE — continue analysis
                          ↓ No → TRAP: Balance sheet risk
               ↓ No → TRAP: Poor returns on capital
  ↓ No → TRAP: Declining business (avoid regardless of cheapness)
```

---

## The Value Factor "Death" (2018–2020)

### What Happened?

From 2017–2020, value (HML factor) suffered its worst extended drawdown since the 1930s:
- Fama-French HML factor: -26% cumulative 2018–2020
- Growth (QQQ) vs. Value (IWD): Growth outperformed by 50%+ over 3 years

### Why Growth Won (Structural Explanations)

**1. Zero Interest Rate Environment (ZIRP)**
- Value stocks are often "bond proxies" — low-growth, high-dividend mature businesses
- When rates fall to zero, discount rates compress → higher P/E multiples justified for ALL stocks
- But growth stocks benefit more: the value of future cash flows (far out) increases more when discounting at 0%
- Duration analogy: growth stocks are like 30-year bonds; they rally harder on rate cuts

**2. Technology Disruption / Winner-Take-All Economics**
- Platform businesses (GOOG, META, AMZN) have nearly zero marginal cost of serving additional users
- Network effects mean the winner captures 70–90% of market value
- Traditional "value" sectors (banks, telecom, utilities) face structural disruption

**3. Intangible Economy**
- Book value increasingly irrelevant (intangibles not on balance sheet)
- Software companies have near-100% gross margins; their "book value" understates economic assets
- P/B factor becomes meaningless when brand, IP, and human capital are the real assets

**4. Factor Crowding**
- Quantitative funds systematically short value stocks (cheap = low momentum)
- Factor arbitrage compressed the value premium

### Is Value Reversing Post-2022?

**Evidence for value revival:**
- 2022: Value (IWD) beat Growth (IWW) by ~20% as rates rose from 0% to 5%
- Rising interest rates compress growth stock valuations more severely (long-duration asset re-pricing)
- AQR (Asness 2021): "The value spread" (cheapest vs. most expensive) reached record levels in 2020 — the more expensive relative to each other, the stronger eventual reversion

**Evidence against value permanently recovering:**
- Structural tech dominance continues (AI accelerating winner-takes-most dynamics)
- If rates fall again (Fed easing cycle), growth likely resumes dominance
- Intangible economy trend is permanent

**Verdict**: Value works cyclically, especially in rising rate environments. In falling rate / tech-boom environments, quality growth (not pure value) outperforms. Consider blending: value timing depends on 10Y-2Y yield curve and Fed policy direction.

**Our FRED data has T10Y2Y** — we can build a regime-switching model: value tilt when yield curve steepening, growth tilt when flattening.

---

## Implementation Without Fundamental Data

Since our DB lacks earnings, book value, and revenue data, we use price-based proxies.

### Proxy 1: Price-to-200-Day SMA Ratio

A security trading below its 200d SMA is in a "cheap zone" relative to its recent trend.

**Formula**: `value_ratio = current_price / SMA_200`

- < 0.85 = significantly below trend (potential value)
- 0.85–0.95 = moderately below trend (watch list)
- > 1.05 = above trend (not cheap)

**Current Values (March 2026)** from our DB:

| Symbol | Price/200d SMA | Category |
|---|---|---|
| MSTR | 0.517 | ⚠️ Deep value (or trap) |
| ORCL | 0.706 | 📉 Significantly below trend |
| MSFT | 0.822 | 📉 Below trend (quality discount) |
| WFC | 0.886 | 📉 Moderately cheap |
| META | 0.888 | 📉 Moderately cheap |
| ARKK | 0.915 | 📉 Moderately cheap |
| AMZN | 0.924 | 📉 Moderately cheap |
| PLTR | 0.926 | 📉 Moderately cheap |
| XLF | 0.929 | 📉 Sector discount |

### Proxy 2: Z-Score vs. 252-Day Rolling Mean

Measures how many standard deviations the price is below its rolling average.

**Current Z-scores (March 2026)** from our DB:

| Symbol | Z-Score | Signal |
|---|---|---|
| MSTR | -1.45 | 🔴 Extreme oversold (but volatile) |
| MSFT | -1.41 | 🟡 Oversold quality name |
| XLF | -1.23 | 🟡 Sector oversold |
| ORCL | -0.95 | 🟡 Below average |
| WFC | -0.82 | 🟡 Below average |
| META | -0.81 | 🟡 Below average |
| UNG | -0.73 | ⚠️ Commodity trap risk |
| AMZN | -0.58 | 🟡 Mild discount |

### Proxy 3: Proximity to 52-Week Low

Stocks near 52-week lows are candidates for mean reversion / value recovery.

**Current % from 52-week high (March 2026):**

| Symbol | % from 52w High |
|---|---|
| MSTR | -69.4% |
| ORCL | -52.6% |
| UNG | -43.5% |
| AMD | -26.8% |
| MSFT | -26.7% |
| ARKK | -24.1% |
| WFC | -23.1% |
| META | -22.2% |

### Mean Reversion as "Poor Man's Value"

Research shows stocks significantly below trend mean-revert over 3–12 month horizons:

- **DeBondt & Thaler (1985)** — *Journal of Finance*: "Does the Stock Market Overreact?"
  - Prior 3–5 year losers outperform prior 3–5 year winners by ~25% over the following 3 years
  - Long-term reversal (3–5 years) is the counterpart to short-term momentum (3–12 months)

- **Rosenberg, Reid & Lanstein (1985)**: First documented book-to-market effect (reversal of "glamour" stocks)

**Implementation**: Identify stocks with:
1. Z-score < -1.5 (statistically oversold)
2. Price/200d SMA < 0.85
3. Not a fundamental breakdown (revenue still growing — need fundamental data to confirm)
4. Hold for 3–6 months target mean reversion

**Caution**: Mean reversion strategies fail spectacularly on true value traps. Without fundamental data to confirm business health, this is high-risk.

---

## Price-Based Value Analysis: Our 38-Symbol Universe

### Composite Value Score (Price-Based Only)

Using our three price proxies (equal weight):

```python
# Composite value score (lower = cheaper)
# Score 1: price/200d SMA (lower better)
# Score 2: z-score (lower better, i.e., more oversold)  
# Score 3: % from 52-week high (lower better)
```

**Composite Rankings (March 2026):**

| Rank | Symbol | P/200d SMA | Z-Score | %from52w High | Composite |
|---|---|---|---|---|---|
| 1 | MSTR | 0.517 | -1.45 | -69.4% | Most Oversold |
| 2 | ORCL | 0.706 | -0.95 | -52.6% | Very Cheap (price) |
| 3 | MSFT | 0.822 | -1.41 | -26.7% | Quality at discount |
| 4 | WFC | 0.886 | -0.82 | -23.1% | Moderate discount |
| 5 | META | 0.888 | -0.81 | -22.2% | Moderate discount |
| 6 | AMZN | 0.924 | -0.58 | -18.2% | Mild discount |
| 7 | XLF | 0.929 | -1.23 | -13.3% | Sector discount |

### Analysis Notes

**MSTR (MicroStrategy)**: Deepest discount in our universe. However, MSTR is essentially a leveraged Bitcoin proxy — its "cheapness" tracks BTC price, not traditional value metrics. Its 69% drawdown from 52-week high reflects Bitcoin winter. Without earnings/book data, hard to assess fundamental value.

**MSFT (Microsoft)**: Most interesting opportunity. A wide-moat, high-ROIC technology company trading 18% below 200d SMA with a z-score of -1.41. If this is sector rotation / rate-driven selloff rather than fundamental deterioration, this is a classic "quality at a discount" opportunity. Requires earnings confirmation (adding yfinance data is high priority).

**ORCL (Oracle)**: 53% below 52-week high, 29% below 200d SMA. Large enterprise software company. Has meaningful switching costs (enterprise databases). Price decline may reflect valuation compression from AI-driven disruption concerns or earnings miss. Need fundamental data to assess.

**XLF (Financials ETF)**: Z-score -1.23 suggests sector oversold. Banks face interest rate sensitivity and potential credit quality concerns. Mean reversion candidate for 3–6 month horizon.

**META (Meta Platforms)**: 22% below 52-week high. Wide-moat platform business with network effects across Facebook/Instagram/WhatsApp. If fundamental earnings remain intact, this is a quality-at-discount opportunity.

---

## What Fundamental Data We Need

### Priority 1: Earnings Data (yfinance)

```python
import yfinance as yf

def get_fundamentals(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    
    # Income statement
    income = ticker.income_stmt  # Annual and quarterly
    
    # Balance sheet
    balance = ticker.balance_sheet
    
    # Cash flow statement
    cashflow = ticker.cashflow
    
    # Key stats
    info = ticker.info
    
    return {
        'eps_ttm': info.get('trailingEps'),
        'forward_pe': info.get('forwardPE'),
        'pe_ratio': info.get('trailingPE'),
        'pb_ratio': info.get('priceToBook'),
        'ps_ratio': info.get('priceToSalesTrailing12Months'),
        'ev_ebitda': info.get('enterpriseToEbitda'),
        'fcf': info.get('freeCashflow'),
        'market_cap': info.get('marketCap'),
        'revenue_growth': info.get('revenueGrowth'),
        'profit_margins': info.get('profitMargins'),
        'return_on_equity': info.get('returnOnEquity'),
        'return_on_assets': info.get('returnOnAssets'),
        'debt_to_equity': info.get('debtToEquity'),
        'current_ratio': info.get('currentRatio'),
        'dividend_yield': info.get('dividendYield'),
        'payout_ratio': info.get('payoutRatio'),
    }
```

### Priority 2: Historical Fundamentals (SEC EDGAR)

For backtesting value strategies, we need point-in-time historical fundamentals (avoid look-ahead bias):

**Sources:**
1. **SEC EDGAR XBRL API**: Free, official. Company facts API: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
2. **Simfin.com**: Free tier, standardized financial statements, good for academic use
3. **Financial Modeling Prep**: $15/month for full historical statements with 20+ years of data
4. **Intrinio**: Professional grade, clean data, ~$50/month

### Priority 3: Computed Metrics to Add to DB

```sql
-- Add to derived_metrics table:
-- 'pe_ratio' (requires earnings data)
-- 'pb_ratio' (requires book value)
-- 'ev_ebitda' (requires ebitda + debt + cash)
-- 'fcf_yield' (requires fcf + market cap)
-- 'piotroski_fscore' (requires full income/balance/cashflow)
-- 'altman_z' (requires multiple balance sheet items)
-- 'magic_formula_rank' (requires earnings yield + roic)
-- 'roic' (requires ebit + invested capital)

-- Already computable from price data (add now):
-- 'price_to_200d_sma' 
-- 'zscore_252d'
-- 'pct_from_52w_high'
-- 'pct_from_52w_low'
```

---

## Rebalancing Considerations

### Greenblatt's Annual Recommendation

Greenblatt specifically recommends holding each Magic Formula position for exactly 1 year for tax efficiency:
- Losses: Sell just before 1 year → short-term capital loss (offsets ordinary income at higher rate)
- Gains: Sell just after 1 year → long-term capital gains (15–20% vs. 37% ordinary rate)
- Net after-tax return improvement: 2–4%/year vs. monthly rebalancing (for taxable accounts)

### Value Strategy Optimal Rebalancing

| Frequency | Evidence | Recommendation |
|---|---|---|
| Monthly | Too frequent; value is a slow-moving signal | Not recommended |
| Quarterly | Balances responsiveness with costs | OK for price-based proxies |
| Semi-annual | Captures fundamental update cycle (earnings every quarter) | Good default |
| Annual | Tax-optimal (Greenblatt); misses some deteriorations | Best for full fundamental strategy |

**For our current price-based approach**: Quarterly rebalancing is appropriate. Value signals based on price/SMA and z-score are more time-sensitive than fundamental value.

**When fundamentals are added**: Switch to semi-annual or annual rebalancing to align with earnings release cycles.

---

## Recommendation for Pinch Portfolio

> "Rule of Acquisition #217: You can't free a fish from water." — And you can't screen for value without fundamental data. Get the data first.

### Phase 1 (Now — Price-Based Value, 10% Portfolio Allocation)

**Strategy**: Mean Reversion on Oversold Quality Names

**Screen** (monthly):
1. Symbol in our 38-name universe
2. Price/200d SMA < 0.90 (below trend)
3. Z-score < -0.75 (statistically below average)
4. SPY > 200d SMA (avoid catching falling knives in bear markets)
5. Manual check: Is there a known fundamental issue (earnings collapse, scandal)?

**Current candidates** (March 2026):
- MSFT: Quality wide-moat at significant discount — highest conviction
- META: Platform business at moderate discount — secondary conviction
- XLF: Sector mean reversion — diversified ETF, lower single-name risk

**Position sizing**: 3–4% max per position (value traps are possible without fundamental data)

**Exit**: When price/200d SMA > 1.05 OR Z-score reverts to +0.5 OR at 6-month mark, whichever first

### Phase 2 (Once Fundamentals Added — Full Value Strategy)

1. Implement Magic Formula ranking on our stock universe
2. Add Piotroski F-Score screening to separate real value from traps
3. Buy top 3–5 quality-value stocks (Magic Formula rank ≤ 5, F-Score ≥ 6)
4. Rebalance semi-annually
5. Position size: 5–8% each (higher conviction with fundamental confirmation)

### Portfolio Role of Value Strategy
- **Complement to momentum**: Value and momentum are negatively correlated (value buys losers, momentum buys winners). Combining reduces portfolio drawdown.
- **Target allocation**: 15–20% of portfolio to value/mean reversion when fundamental data available
- **Beta**: Value portfolio typically beta 0.7–0.9 (lower than momentum)

---

## Data Requirements

### Currently Available
- ✅ Daily OHLCV prices (all price-based proxies)
- ✅ VIX data (risk regime filter)
- ✅ FRED yield curve data (T10Y2Y — value/growth regime timing)
- ✅ FRED Fed Funds rate (interest rate environment assessment)
- ✅ Derived metrics table (add price-based value scores here)

### Missing — High Priority
- ❌ **EPS / P/E ratio**: Core value metric — collect via yfinance quarterly
- ❌ **Book value / P/B ratio**: Classic Graham metric — SEC EDGAR
- ❌ **Revenue / P/S ratio**: Manipulation-resistant metric — yfinance
- ❌ **EBITDA / EV/EBITDA**: Best fundamental predictor — yfinance
- ❌ **Free cash flow / FCF yield**: Buffett's preferred metric — yfinance
- ❌ **Debt / equity, current ratio**: Altman Z inputs — yfinance
- ❌ **ROIC**: Magic Formula input — compute from EBIT + invested capital (SEC EDGAR)
- ❌ **Dividend history**: For dividend safety screening — yfinance

### Missing — Medium Priority
- ❌ **Gross profit margin**: Novy-Marx quality factor — yfinance
- ❌ **Revenue growth history**: Value trap detection — yfinance
- ❌ **Shares outstanding history**: Dilution detection — SEC EDGAR

---

## Implementation Plan

### Phase 1: Price-Based Value Signals (1 week)

1. Create `backtest/signals/value_price_based.py`:
   - Compute price/200d SMA ratio for each symbol
   - Compute 252-day z-score
   - Compute 52-week high/low proximity
   - Write composite value score to derived_metrics table
   - Add market filter (SPY > 200d SMA check)

2. Create `live/signals/value_screener.py`:
   - Daily run after market close
   - Flag symbols entering "value zone" (price/SMA < 0.90)
   - Send Discord alert with candidate list

### Phase 2: Fundamental Data Collection (2 weeks)

1. Create `live/collectors/fundamentals_yfinance.py`:
   - Collect key stats for all 38 symbols via yfinance
   - Run quarterly (aligned with earnings season)
   - Store in fundamentals table (new table or derived_metrics)
   - Fields: pe_ratio, pb_ratio, ps_ratio, ev_ebitda, fcf, debt_equity, current_ratio, roic

2. Schema migration: Add `fundamentals` table to pinch_market.db

3. Historical backfill: Use Simfin free tier for 10+ years of historical fundamentals

### Phase 3: Piotroski F-Score Calculator (1 week)

1. Create `backtest/signals/piotroski.py`:
   - Compute all 9 F-Score components
   - Requires quarterly income statement, balance sheet, cash flow
   - Output: F-Score per symbol per quarter
   - Write to derived_metrics table

### Phase 4: Magic Formula Implementation (1 week)

1. Create `backtest/signals/magic_formula.py`:
   - Compute earnings yield (EBIT/EV) for each symbol
   - Compute ROIC (EBIT / (Net PP&E + Working Capital))
   - Combined rank
   - Backtest: rebalance annually, track vs. SPY

### Phase 5: Altman Z-Score (1 week)

1. Create `backtest/signals/altman_z.py`:
   - Compute Z-Score for each stock
   - Flag any symbol with Z < 1.8 as distress risk
   - Integrate as exclusion filter in value screening

### Phase 6: Backtesting & Validation (2 weeks)

1. Compare pure P/B value (Fama-French HML factor) vs. Magic Formula vs. our implementation
2. Test 2010–2022 (training), 2022–2026 (test)
3. Compare value vs. momentum returns in different rate regimes (using T10Y2Y from FRED)
4. Show value/momentum correlation — confirm negative correlation (diversification benefit)

### Code Example: Price-Based Value Screener

```python
import sqlite3
import pandas as pd
import numpy as np

def compute_value_signals(db_path: str) -> pd.DataFrame:
    """
    Compute price-based value signals for all equity symbols.
    Returns ranked list of oversold quality candidates.
    """
    db = sqlite3.connect(db_path)
    
    df = pd.read_sql('''
        SELECT symbol, timestamp, close
        FROM prices
        WHERE timeframe = "1d"
        AND asset_class IN ("stock", "etf")
        ORDER BY symbol, timestamp
    ''', db)
    
    df['date'] = pd.to_datetime(df['timestamp'], unit='s')
    pivot = df.pivot(index='date', columns='symbol', values='close').ffill()
    
    # Market filter
    spy_ok = pivot['SPY'].iloc[-1] > pivot['SPY'].rolling(200).mean().iloc[-1]
    
    results = []
    for sym in pivot.columns:
        s = pivot[sym].dropna()
        if len(s) < 252:
            continue
        
        price = s.iloc[-1]
        sma200 = s.rolling(200).mean().iloc[-1]
        sma50 = s.rolling(50).mean().iloc[-1]
        high52 = s.rolling(252).max().iloc[-1]
        low52 = s.rolling(252).min().iloc[-1]
        
        roll_mean = s.rolling(252).mean().iloc[-1]
        roll_std = s.rolling(252).std().iloc[-1]
        zscore = (price - roll_mean) / roll_std if roll_std > 0 else 0
        
        results.append({
            'symbol': sym,
            'price': price,
            'price_to_sma200': price / sma200,
            'price_to_sma50': price / sma50,
            'zscore_252d': zscore,
            'pct_from_52w_high': (price / high52 - 1),
            'pct_from_52w_low': (price / low52 - 1),
            'market_filter': spy_ok,
        })
    
    df_out = pd.DataFrame(results)
    
    # Composite value score (lower = cheaper)
    df_out['value_score'] = (
        df_out['price_to_sma200'].rank() +
        df_out['zscore_252d'].rank() +
        df_out['pct_from_52w_high'].rank()
    ) / 3
    
    df_out = df_out.sort_values('value_score')
    
    # Apply market filter
    if not spy_ok:
        print("⚠️  Market filter: SPY below 200d SMA. Value signals may be value traps.")
    
    return df_out

# Usage:
# signals = compute_value_signals('/mnt/media/market_data/pinch_market.db')
# candidates = signals[signals['price_to_sma200'] < 0.90]
# print(candidates[['symbol', 'price_to_sma200', 'zscore_252d', 'pct_from_52w_high']].head(10))
```

---

## References

1. Fama, E. & French, K. (1992). "The Cross-Section of Expected Stock Returns." *Journal of Finance*, 47(2), 427–465.
2. Graham, B. & Dodd, D. (1934). *Security Analysis*. McGraw-Hill.
3. Graham, B. (1949). *The Intelligent Investor*. Harper & Brothers.
4. Greenblatt, J. (2006). *The Little Book That Beats the Market*. Wiley.
5. Piotroski, J. (2000). "Value Investing: The Use of Historical Financial Statement Information." *Journal of Accounting Research*, 38, 1–41.
6. Lakonishok, J., Shleifer, A., & Vishny, R. (1994). "Contrarian Investment, Extrapolation, and Risk." *Journal of Finance*, 49(5), 1541–1578.
7. DeBondt, W. & Thaler, R. (1985). "Does the Stock Market Overreact?" *Journal of Finance*, 40(3), 793–805.
8. Shiller, R. (2015). *Irrational Exuberance* (3rd ed.). Princeton University Press.
9. Gray, W. & Carlisle, T. (2012). *Quantitative Value*. Wiley.
10. Loughran, T. & Wellman, J. (2011). "New Evidence on the Relation Between the Enterprise Multiple and Average Stock Returns." *Journal of Financial and Quantitative Analysis*, 46(6), 1629–1650.
11. Oppenheimer, H. (1986). "Ben Graham's Net Current Asset Values." *Financial Analysts Journal*, 42(6), 28–34.
12. Asness, C. (2021). "AQR: Is (Systematic) Value Investing Dead?" AQR Capital Management white paper.
13. Hyde, C. (2021). "The Piotroski F-Score: Evidence from Australia, Canada, and the US." *The Journal of Investing*, 30(5), 39–54.
14. O'Shaughnessy, J. (1998). *What Works on Wall Street*. McGraw-Hill.

---

*Document generated: March 2026 | pinch-stock-trading project | DB: pinch_market.db (205K+ records)*
*Price-based analysis uses 38-symbol universe with actual DB query results*
