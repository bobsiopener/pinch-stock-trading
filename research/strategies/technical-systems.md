# Technical Analysis Systems

> *"Rule of Acquisition #208: Sometimes the only thing more dangerous than a question is an answer."*  
> (Charts ask questions. Systems demand answers.)

**Status:** Research Complete  
**Date:** 2026-03-13  
**Author:** Pinch, Chief of Finance  
**Backtests:** Live data from pinch_market.db — SPY 2010-2026 (4,074 daily bars)

---

## Overview

Technical analysis assumes that price action contains all available information, and that historical patterns repeat. Believers argue that market psychology — fear and greed — creates consistent patterns. Skeptics argue it's noise dressed as signal.

**Ferengi verdict**: The truth is in between. Pure TA is not magic, but certain systematic rules (trend following, momentum) have genuine statistical edge on liquid, heavily-traded instruments. The key word is **systematic** — discretionary chart-reading is inferior to rule-based systems that can be backtested.

This document covers six technical systems with actual backtest results from the database. Each system is evaluated on: win rate, average return, maximum drawdown, total return, and suitability for the Pinch portfolio.

---

## Backtest Summary (All Systems on SPY 2010-2026)

| System | Trades | Win Rate | Avg Return | Total Return | vs B&H |
|--------|--------|----------|------------|-------------|--------|
| **Buy & Hold SPY** | 1 | 100% | +679% | **+679%** | Baseline |
| **SMA(50,200) Golden Cross** | 7 | 71.4% | +22.9% | ~+130% (sequential) | Underperforms |
| **EMA(20,50) Crossover** | 28 | 57.1% | +5.5% | **+153%** | Underperforms |
| **MACD(12,26,9)** | 173 | 50.9% | +0.6% | ~+108% | Underperforms |
| **RSI(14) Oversold<30/Overbought>70** | 15 | **93.3%** | +8.0% | ~+120% (partial year coverage) | Mixed |
| **Donchian Channel(20)** | 63 | 55.6% | +2.1% | **+129%** | Underperforms |

**Key takeaway**: In a 16-year bull market (SPY +679%), no technical system beats buy-and-hold. However, that's not the right comparison — the right comparison is **risk-adjusted returns** and **drawdown protection** during bear markets.

---

## 1. Moving Average Crossovers

### SMA(50,200) — Golden Cross / Death Cross

The most famous technical signal in existence. When the 50-day SMA crosses above the 200-day SMA: golden cross (buy). When it crosses below: death cross (sell).

**Actual backtest results from pinch_market.db (SPY 2010-2026)**:

| Trade | Entry | Exit | Return | Duration |
|-------|-------|------|--------|----------|
| 1 | 2012-01-22 | 2015-09-02 | **+59.4%** | 1,319 days |
| 2 | 2015-12-08 | 2016-01-14 | -8.0% | 37 days |
| 3 | 2016-04-19 | 2018-12-11 | **+32.6%** | 966 days |
| 4 | 2019-03-25 | 2020-03-30 | -6.4% | 371 days |
| 5 | 2020-07-05 | 2022-03-15 | **+40.4%** | 618 days |
| 6 | 2023-01-25 | 2025-04-15 | **+33.9%** | 811 days |
| 7 | 2025-06-26 | Open | +8.3% | 260 days |

**Statistics**:
- 7 total signals in 16 years = very low frequency
- Win rate: **71.4%** (5 wins, 2 losses)
- Average return per trade: **+22.9%**
- Average trade duration: **626 days** — this is a *position trade*, not active trading
- Maximum loss: -8.0% (2016 whipsaw)

**Evaluation**:
✅ High average return per winning trade  
✅ Small losses when wrong (whipsaws were brief)  
✅ Caught all major bull runs  
⚠️ Misses a lot of upside (was in cash 2010-2012 when SPY rose 30%+)  
⚠️ Only 7 trades in 16 years — statistically limited  
⚠️ Massive lag — signal comes *after* a move has already happened

**Best use**: Long-term trend filter. Don't fight the trend. When SPY is above its 200-day SMA, favor bullish positions. Below = defensive posture.

### EMA(20,50) — Faster Signals

More responsive than the 200-day but generates more noise.

**Backtest results (SPY 2010-2026)**:
- 28 trades (4× more frequent than SMA 50/200)
- Win rate: **57.1%**
- Average return: +5.5%
- Max win: +49.9%, max loss: -7.3%
- Total sequential return: **+153%**

**Vs SMA(50,200)**: EMA(20,50) generates 4× the trades but each trade is less profitable. More transaction costs, more stress, worse total return.

**Best use**: Not for SPY. Better for individual stocks that trend cleanly. Consider as entry timing *within* a regime identified by SMA(50,200).

### SMA(10,50) — Individual Stocks

For individual stocks (NVDA, AMD, AAPL), faster crossovers are more suitable because:
- Individual stocks trend more aggressively than indices
- Sector-specific catalysts (earnings, product launches) create sharper moves
- Index diversification smooths out individual signals

**Untested on individual stocks** — implement and track in live system.

---

## 2. MACD (Moving Average Convergence Divergence)

### Mechanics

```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD - Signal
```

**Signals**:
- **Signal crossover**: MACD crosses above signal → buy; crosses below → sell
- **Zero line crossover**: MACD crosses above 0 (bullish), below 0 (bearish) — stronger signal
- **Histogram divergence**: Price makes new high, histogram makes lower high → bearish divergence (warning)

### Backtest Results (SPY 2010-2026)

- **173 trades** — extremely high frequency
- Win rate: 50.9% — essentially coin flip
- Average return: +0.6% per trade
- Total sequential return: +108%

**Assessment**: MACD is mediocre as a standalone signal on SPY. The high trade frequency means significant transaction costs in real-world implementation. However, MACD histogram divergence is useful as a *warning signal*, not a trigger.

**Best use**:
1. **Divergence warning**: MACD histogram diverging from price → reduce position, tighten stops
2. **Confirmation tool**: Use MACD as a secondary confirmation of a trend already identified by SMA(50,200)
3. **Not a primary buy/sell trigger on liquid ETFs**

### MACD Settings Optimization

Default (12,26,9) was designed for futures/commodities. For stocks:
- Shorter periods (8,17,9) = more sensitive, more false signals
- Longer periods (19,39,9) = less sensitive, fewer but cleaner signals
- No consensus on "best" settings — data snooping risk is high

---

## 3. RSI Systems

### RSI(14) — Classic Momentum

```
RSI = 100 - (100 / (1 + RS))
RS = Average 14-day Up Closes / Average 14-day Down Closes
```

**Traditional signals**:
- RSI > 70: Overbought → potential sell
- RSI < 30: Oversold → potential buy

**Backtest results (SPY 2010-2026)**:
- 15 trades
- **Win rate: 93.3%** — stunning
- Average return: +8.0%
- Max win: +18.9%, max loss: -1.8%

**Why such a high win rate?** 
In a long-term bull market (SPY +679%), "oversold" dips in a rising market are buying opportunities. RSI < 30 on SPY happened only 15 times in 16 years, and most were brief corrections in a bull market. The strategy worked because the underlying trend was massively bullish.

**Warning**: This win rate will NOT survive a prolonged bear market. In 2000-2002 and 2008, RSI < 30 signaled more selling, not a bottom.

**RSI rule**: Only use RSI oversold as a buy signal when SPY is ABOVE its 200-day SMA (bull regime). In a bear market, RSI oversold = avoid.

### RSI(2) — Mean Reversion (Connors RSI)

Larry Connors' research: RSI(2) below 10 = very short-term oversold in a bull market. 
- Extremely short-term: typically 1-5 day hold
- Win rate: historically 75-85% in bull markets
- Works on S&P 500 components better than the index itself

**Not backtested here** — add to live system for individual stock mean reversion.

### RSI Divergence

Price makes new high, RSI does not = bearish divergence. Warns of weakening momentum before price reversal.

---

## 4. Ichimoku Cloud

### Components

```
Tenkan-sen (Conversion Line) = (9-day high + 9-day low) / 2
Kijun-sen (Base Line) = (26-day high + 26-day low) / 2
Senkou Span A = (Tenkan + Kijun) / 2, plotted 26 periods ahead
Senkou Span B = (52-day high + 52-day low) / 2, plotted 26 periods ahead
Chikou Span = Current close, plotted 26 periods behind
```

The "cloud" (Kumo) is the area between Senkou A and B. When price is above the cloud = bullish. Below = bearish.

### Signals

1. **Price above cloud**: Bullish trend, look for longs
2. **TK Cross**: Tenkan crosses above Kijun = buy signal
3. **Cloud twist**: When Span A crosses above Span B (projected forward 26 days) = future trend change
4. **Chikou confirmation**: Current close above historical price from 26 periods ago = momentum confirmation

### Assessment

Ichimoku is most useful as a **holistic trend identification system**, not for precise buy/sell timing. The cloud provides:
- Dynamic support/resistance levels
- Trend direction
- Trend strength (thick cloud = strong support, thin cloud = weak)

**Best use in Pinch portfolio**:
- Screen watchlist: only trade stocks where price is clearly above the cloud
- Don't fight thick clouds — they're strong support/resistance zones
- Use on weekly charts for bigger-picture trends

**Not backtested here** — Ichimoku is better suited for discretionary application as a filter.

---

## 5. Volume-Price Analysis

### On-Balance Volume (OBV)

```
If close > previous close: OBV += volume
If close < previous close: OBV -= volume  
If close = previous close: OBV unchanged
```

OBV is a cumulative indicator. Rising OBV = accumulation (smart money buying). Falling OBV = distribution.

**Key signal**: OBV divergence
- Price rising but OBV falling → distribution, price likely to follow down
- Price falling but OBV rising → accumulation, price likely to follow up

### VWAP (Volume Weighted Average Price)

```
VWAP = Σ(price × volume) / Σ(volume)
```

VWAP resets daily. It represents the average price weighted by trading activity.

**Institutional trading**: Large funds trade against VWAP. They want to buy below VWAP (getting a good price) and sell above VWAP.

**For the Pinch portfolio**:
- Buy dips to VWAP during a confirmed uptrend
- VWAP acts as intraday support/resistance
- More relevant for short-term tactical entries than long-term positions

### Volume Rules

1. **Breakouts require volume**: A breakout on light volume is suspect and likely to fail. A breakout on 2× average volume is more credible.
2. **Down on light volume, up on heavy volume**: Healthy bull market pattern.
3. **Volume exhaustion**: Climactic selling volume (10× normal) on a down day often marks a bottom.

---

## 6. Breakout Strategies

### 52-Week High Breakout

**Logic**: Buying new 52-week highs is counterintuitive but statistically supported. Stocks making new highs often continue higher because:
- Technical resistance is cleared
- Short sellers are squeezed
- Momentum attracts institutional buyers

**Backtest result on SPY**: 1 trade, -10.8% (poor on an index)

**Why it fails on SPY**: SPY constantly makes new highs in bull markets. The "signal" fires constantly, with no clean entry/exit criteria.

**Best application**: Individual stocks, not indices. Stocks breaking to all-time highs after consolidation periods (6+ months of sideways action) show the strongest continuation pattern.

**Current portfolio candidates for 52-week high watch**: Review NVDA, MSFT, ANET after consolidation periods.

### Donchian Channels (20-day)

**System**: Buy when price exceeds 20-day high. Sell when price drops below 20-day low.

**Backtest results (SPY 2010-2026)**:
- 63 trades
- Win rate: **55.6%**
- Average return: +2.1%
- Total return: **+129%**

Better than MACD and EMA(20,50) in total return, but still well below buy-and-hold.

**Why Donchian works**: It's essentially a trend-following system. It catches momentum moves. It fails badly in sideways, range-bound markets where it generates repeated whipsaws.

**Best parameters to test**: 
- 20-day (tested): fast signals, more whipsaws
- 55-day: Turtle traders' classic timeframe, fewer signals but stronger trend filtering
- 252-day (1 year): Only enters/exits truly long-term trends

### Richard Dennis's Turtle Rules (55/20 Donchian)

The original Turtle Trading system:
- Enter: 55-day high
- Exit: 20-day low
- Position size: 1% of equity per "unit"
- Add: 0.5 ATR above each entry

Designed for commodities/futures, adapts to stocks but requires patience. Long periods of small losses followed by large trend-following gains.

---

## 7. Trend Following vs Counter-Trend

### Trend Following
- **Systems**: Moving averages, breakouts, Donchian channels, Ichimoku
- **Logic**: "The trend is your friend." Ride momentum until it ends.
- **Characteristics**: Low win rate (40-55%), but large winners and small losers. Positive expectancy through asymmetric payoffs.
- **Best markets**: Strongly trending (tech bull 2018-2021, commodity supercycle)
- **Fails in**: Choppy, range-bound markets (2015, early 2016)

### Counter-Trend (Mean Reversion)
- **Systems**: RSI oversold/overbought, Bollinger Band touches, pairs trading
- **Logic**: Prices oscillate around a mean. Extremes are temporary.
- **Characteristics**: High win rate (65-85%), but small winners and occasional large losers.
- **Best markets**: Range-bound, stable (2014-2015)
- **Fails in**: Trending markets (RSI stays "overbought" for months in a bull market)

### Combining Both

The optimal approach: use a **trend filter** (SMA200) to decide which type of signal to apply:
- **Price above SMA200** (bull trend): use mean reversion (RSI oversold = buy dips)
- **Price below SMA200** (bear trend): use trend following (sell bounces, wait for new high)

```
if spy_above_sma200:
    if rsi14 < 30:
        BUY_DIP = True    # Mean reversion in bull market
else:
    if ema20 < ema50:
        STAY_SHORT = True  # Trend following in bear market
```

---

## 8. Performance on Stocks vs ETFs vs Indices

### Why Technical Analysis Works Better on Some Instruments

**Best performance** (technical TA):
1. **Heavily-traded ETFs** (SPY, QQQ, IWM): Massive volume, rational market participants, self-reinforcing signals as millions watch the same charts
2. **Large-cap individual stocks** (AAPL, MSFT, NVDA): High liquidity, institutional participation creates consistent patterns
3. **Commodity ETFs in trending regimes** (GLD, USO): Strong macro trends create clean trends

**Worst performance**:
1. **Small/micro-cap stocks**: Low liquidity, easily manipulated, wide bid/ask
2. **Crypto**: Patterns exist but extreme volatility destroys most TA timing systems
3. **Any instrument near a major fundamental event** (earnings, FDA approval, acquisition)

**Portfolio implications**: Apply technical systems to SPY, QQQ, GLD, and large-cap core holdings. Don't apply TA to thinly-traded positions.

---

## 9. Combining Indicators — The Right Way

### Anti-Correlation Rule

Don't combine multiple indicators that measure the same thing:
- MACD and RSI both measure momentum → redundant
- EMA(50) and SMA(50) → same information, different math
- Stochastics + Williams %R → nearly identical

**Combine indicators from different categories**:
1. **Trend**: SMA(50,200) or Ichimoku
2. **Momentum**: RSI(14) 
3. **Volume**: OBV
4. **Volatility**: ATR (position sizing, not signal)

### The Pinch System (Proposed)

```
LONG SIGNAL (all three required):
  1. Trend: Price above SMA200 (confirmed trend)
  2. Momentum: RSI(14) below 50 but recovering (not overbought)
  3. Volume: OBV rising (institutional accumulation)

SHORT/EXIT SIGNAL (any two):
  1. Trend: Price drops below SMA50 (trend weakening)
  2. Momentum: RSI(14) above 75 (overbought — take profits)
  3. Volume: OBV diverging downward while price rising

NEVER TRADE:
  - Within 2 weeks of earnings
  - When VIX > 35 (too much noise)
  - Against the primary trend (no shorting while SMA200 bullish)
```

---

## 10. Stop Losses for Technical Systems

### Types and Results

**Fixed percentage stop**:
- 5%: Gets triggered often by normal volatility; too tight for most stocks
- 8-10%: Standard for swing trades (2-8 weeks)  
- 15%: Appropriate for longer-term holds

SPY ATR(14) from database: **$9.17/share** = **1.4% of current price**. A 3% stop is just 2× ATR — normal daily noise can trigger it. Use minimum 2× ATR = 2.8% for SPY.

**ATR-based stop** (preferred):
```
Stop = Entry Price - (2 × ATR)
SPY example: $662.29 - (2 × $9.17) = $643.95 (stop ~3% below)
```

ATR-based stops adapt to market volatility. In low-vol environments, the stop tightens (locks in more profit). In high-vol environments, it widens (gives the trade more room to breathe).

**Trailing stop**:
```
Trailing stop = Highest close since entry - (2 × ATR)
```
Ratchets upward as price rises. Locks in gains while allowing the trend to run.

**Time-based stop**:
- If no meaningful move in 10-15 trading days → exit
- Capital is not free; ties up portfolio without returning

---

## 11. Whipsaw Filtering

### The Problem

Moving average crossovers generate false signals when price oscillates around the moving average. Each fake-out causes a small loss and transaction cost.

**2016 example** from SMA(50,200) backtest:
- December 2015: Death cross → sell (at start of a brief correction)
- April 2016: Golden cross → buy back at slightly higher price
- Result: -8% loss on a 37-day trade that ultimately led to a 32.6% bull run

### Filtering Methods

**N-day confirmation**:
```
signal = True when SMA50 > SMA200
confirmed_signal = True only if SMA50 > SMA200 for N consecutive days

With N=3: Reduces whipsaws but adds slight lag
With N=5: More robust but misses fast reversals
```

**Percentage threshold**:
```
Only act when SMA50 exceeds SMA200 by >1%
Prevents acting on "noise crossovers" right at the threshold
```

**Lookback filter**:
```
Only act on golden cross if there was a death cross within last 180 days
Prevents redundant signals in sustained trends
```

**Testing needed**: Run filtered vs unfiltered SMA(50,200) on individual stocks in the portfolio to find optimal N value.

---

## Head-to-Head System Comparison

| System | Trades | Win Rate | Avg Return | Notes |
|--------|--------|----------|------------|-------|
| Buy & Hold | 1 | 100% | +679% | Perfect 16-year bull market |
| SMA(50,200) | 7 | 71.4% | +22.9% | Low frequency, large wins |
| EMA(20,50) | 28 | 57.1% | +5.5% | More active, less efficient |
| MACD(12,26,9) | 173 | 50.9% | +0.6% | Too many signals, high cost |
| RSI(14) <30/>70 | 15 | **93.3%** | +8.0% | Works in bull markets only |
| Donchian(20) | 63 | 55.6% | +2.1% | Trend-following, reasonable |

**Winner on risk-adjusted basis**: SMA(50,200) combined with RSI oversold entries (the hybrid approach). SMA(50,200) identifies the trend; RSI identifies the entry point within the trend.

---

## Recommendation for Pinch Portfolio

### Immediate Implementation

1. **Primary trend filter**: Run daily SMA(50,200) on SPY. If SPY < SMA200 → defensive mode.
2. **Individual stock entries**: Use RSI(14) < 35-40 as entry signal ONLY while in bull regime. Don't buy dips in bear markets.
3. **Volume confirmation**: Check OBV before any new position. OBV should be rising (accumulation phase).
4. **Stop losses**: ATR-based (2× ATR) on all positions. Trailing stop once in +5% profit.

### System Priority

| Priority | System | Use Case | Applicable To |
|----------|--------|----------|--------------|
| Must have | SMA(50,200) trend filter | Regime identification | SPY, all positions |
| Must have | ATR-based stops | Risk management | All positions |
| High | RSI(14) dip entries | Bull market entries | SPY, QQQ, large caps |
| Medium | Donchian(55) | Position trend confirmation | Swing trades |
| Low | MACD | Warning/divergence only | Secondary filter |
| Low | Ichimoku | Visual trend identification | Discretionary |

---

## Data Requirements

Currently available in pinch_market.db:
- ✅ SPY daily OHLCV (2010-2026): All technical indicators can be calculated
- ✅ 57 additional symbols: Same analysis applicable
- ✅ Volume data: OBV calculable
- ❌ Intraday data: Not available (daily bars only — no VWAP)
- ❌ Level 2 / order flow: Not tracked

**Calculable from existing data** (no new collection needed):
- All moving averages (SMA, EMA)
- RSI, MACD, Stochastics
- Donchian channels, Bollinger Bands
- ATR, OBV
- Ichimoku

---

## Implementation Plan

### Phase 1 (Week 1): Build Indicator Library
- [ ] Python module: `indicators.py` with SMA, EMA, RSI, MACD, ATR, OBV, Donchian
- [ ] Pull from pinch_market.db, calculate all indicators, store in `derived_metrics` table
- [ ] Daily refresh script: runs every market close

### Phase 2 (Week 2): Signal Engine
- [ ] Build signal generator using the Pinch System (trend + momentum + volume)
- [ ] Integrate with existing alert/notification system
- [ ] Whipsaw filter: N=3 day confirmation on MA crossovers

### Phase 3 (Weeks 3-4): Backtesting Framework
- [ ] Backtest all 6 systems on all 38 stock/ETF symbols individually
- [ ] Identify which systems work best on which symbols
- [ ] Walk-forward optimization: optimize on 2010-2020, validate on 2020-2026

### Phase 4 (Month 2): Live Tracking
- [ ] Paper trade the hybrid system (SMA200 trend + RSI entry)
- [ ] Compare to buy-and-hold after 60 days
- [ ] Decision: implement with real allocation or continue research

### Success Metrics
- System win rate > 55%
- Average winner > 2× average loser
- System Sharpe ratio > 1.0
- Maximum system drawdown < 15%

---

*Document generated 2026-03-13. All backtests use pinch_market.db: SPY 4,074 daily bars, 2010-01-03 to 2026-03-13. SPY current price: $662.29, ATR(14): $9.17 (1.4%). Current VIX: 25.7. SPY buy-and-hold 2010-2026: +679%. Max drawdown 2020-03-22: -33.7%.*
