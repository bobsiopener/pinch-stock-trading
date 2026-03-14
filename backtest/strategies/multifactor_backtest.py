"""
Multi-Factor Combined Strategy Backtest (Issue #17)
Pinch Stock Trading Platform

Master strategy combining best elements from all backtests:
  Composite score = 40% Momentum + 30% Value + 20% Low-Vol + 10% Trend

Variants:
  A) Top 5 Multi-Factor, monthly rebalance
  B) Top 10 Multi-Factor, monthly rebalance
  C) Top 5 with VIX filter (50% cash when VIX > 25)
  D) Top 5 with regime filter (SPY vs 200-SMA)

Benchmarks: SPY B&H, Momentum-only top 5, Equal-weight all
Test period: 2012-01-01 to 2025-12-31
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DB_PATH = '/mnt/media/market_data/pinch_market.db'
RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

START_DATE = '2012-01-01'
END_DATE = '2025-12-31'

# Factor weights
W_MOMENTUM = 0.40
W_VALUE = 0.30
W_LOWVOL = 0.20
W_TREND = 0.10

VIX_CASH_THRESHOLD = 25   # Strategy C: 50% cash when VIX > 25
CASH_ALLOCATION = 0.50    # Cash fraction during high-risk regime


# ─── Data Loading ─────────────────────────────────────────────────────────────

def get_prices_raw(symbol: str, start_date: str = '2010-01-01') -> pd.DataFrame:
    db = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT timestamp, close FROM prices "
        "WHERE symbol=? AND timeframe='1d' AND close IS NOT NULL ORDER BY timestamp",
        db, params=(symbol,))
    db.close()
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.set_index('date').drop(columns=['timestamp'])
    df = df[~df.index.duplicated(keep='last')]
    df = df[df.index >= pd.Timestamp(start_date)]
    return df


def get_all_stock_etf_symbols() -> list:
    db = sqlite3.connect(DB_PATH)
    rows = db.execute(
        "SELECT DISTINCT symbol FROM prices "
        "WHERE timeframe='1d' AND asset_class IN ('stock','etf') AND symbol != 'VIX'"
    ).fetchall()
    db.close()
    return sorted([r[0] for r in rows])


def load_close_matrix(symbols: list, start_date: str = '2010-01-01') -> pd.DataFrame:
    frames = {}
    for sym in symbols:
        df = get_prices_raw(sym, start_date)
        if not df.empty:
            frames[sym] = df['close']
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).sort_index()


def load_vix(start_date: str = '2010-01-01') -> pd.Series:
    df = get_prices_raw('VIX', start_date)
    if df.empty:
        return pd.Series(dtype=float)
    return df['close'].rename('VIX')


def get_monthly_dates(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start=start, end=end, freq='ME')


# ─── Performance Metrics ──────────────────────────────────────────────────────

def calc_metrics(returns: pd.Series, rf: float = 0.02) -> dict:
    returns = returns.dropna()
    if len(returns) < 2:
        return {}
    total = (1 + returns).prod() - 1
    n_years = len(returns) / 12
    cagr = (1 + total) ** (1 / n_years) - 1 if n_years > 0 else 0
    vol = returns.std() * np.sqrt(12)
    sharpe = (cagr - rf) / vol if vol > 0 else 0
    cumulative = (1 + returns).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    max_dd = drawdown.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0
    win_rate = (returns > 0).mean()
    return {
        'Total Return': f'{total:.1%}',
        'CAGR': f'{cagr:.1%}',
        'Volatility (ann)': f'{vol:.1%}',
        'Sharpe Ratio': f'{sharpe:.2f}',
        'Max Drawdown': f'{max_dd:.1%}',
        'Calmar Ratio': f'{calmar:.2f}',
        'Win Rate': f'{win_rate:.1%}',
        'Months': len(returns),
    }


# ─── Factor Computation ───────────────────────────────────────────────────────

def compute_factors(prices: pd.DataFrame, rebal_date: pd.Timestamp) -> pd.DataFrame:
    """
    For each symbol at rebal_date, compute:
      - momentum_score: percentile rank of 6-month return
      - value_score: percentile rank of 1/price_sma200 (inverted)
      - lowvol_score: percentile rank of 1/60d_vol (inverted)
      - trend_score: 1 if above 200-day SMA, else 0
    Returns DataFrame indexed by symbol.
    """
    current_prices = prices[prices.index <= rebal_date]
    if len(current_prices) < 200:
        return pd.DataFrame()

    latest = current_prices.iloc[-1]

    # SMA200
    sma200 = current_prices.rolling(200, min_periods=150).mean().iloc[-1]

    # 6-month momentum
    lookback_6m = rebal_date - pd.DateOffset(months=6)
    prices_6m_ago = current_prices[current_prices.index >= lookback_6m]
    if len(prices_6m_ago) < 100:
        return pd.DataFrame()
    start_price = prices_6m_ago.iloc[0]

    # 60-day realized vol
    returns_60d = current_prices.pct_change().rolling(60, min_periods=40).std().iloc[-1] * np.sqrt(252)

    records = []
    for sym in prices.columns:
        p = latest.get(sym)
        s = sma200.get(sym)
        sp = start_price.get(sym)
        vol60 = returns_60d.get(sym)

        if pd.isna(p) or pd.isna(s) or pd.isna(sp) or pd.isna(vol60):
            continue
        if s <= 0 or sp <= 0 or vol60 <= 0:
            continue

        mom_6m = p / sp - 1
        sma_ratio = p / s
        trend = 1 if p > s else 0

        records.append({
            'symbol': sym,
            'price': p,
            'sma200': s,
            'mom_6m': mom_6m,
            'sma_ratio': sma_ratio,
            'vol_60d': vol60,
            'trend': trend,
        })

    if len(records) < 5:
        return pd.DataFrame()

    df = pd.DataFrame(records).set_index('symbol')

    # Percentile ranks (0-100)
    df['momentum_score'] = df['mom_6m'].rank(pct=True) * 100
    # Value: lower SMA ratio = better value → invert ranking
    df['value_score'] = (1 - df['sma_ratio'].rank(pct=True)) * 100
    # LowVol: lower vol = better → invert ranking
    df['lowvol_score'] = (1 - df['vol_60d'].rank(pct=True)) * 100
    # Trend: binary (scaled to 0-100 for weighted sum)
    df['trend_score_raw'] = df['trend'] * 100

    # Combined score
    df['combined_score'] = (
        W_MOMENTUM * df['momentum_score'] +
        W_VALUE * df['value_score'] +
        W_LOWVOL * df['lowvol_score'] +
        W_TREND * df['trend_score_raw']
    )

    return df.sort_values('combined_score', ascending=False)


def compute_month_returns(prices: pd.DataFrame, picks: list,
                           rebal_date: pd.Timestamp, next_date: pd.Timestamp,
                           equity_weight: float = 1.0) -> float:
    """Equal-weight return for picks over [rebal_date, next_date]."""
    month_window = prices[(prices.index > rebal_date) & (prices.index <= next_date)]
    if month_window.empty:
        return np.nan

    pick_rets = []
    for sym in picks:
        col = month_window[sym].dropna() if sym in month_window.columns else pd.Series()
        if len(col) >= 1:
            prior = prices[sym][prices.index <= rebal_date].dropna() if sym in prices.columns else pd.Series()
            if not prior.empty:
                ret = col.iloc[-1] / prior.iloc[-1] - 1
                pick_rets.append(ret)

    if not pick_rets:
        return np.nan

    equity_ret = np.mean(pick_rets)
    # Cash earns ~0% (T-bill approximation; could parameterize)
    return equity_weight * equity_ret


# ─── Strategy A: Top 5 Multi-Factor ─────────────────────────────────────────

def strategy_a_top5(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """Top 5 by combined score, monthly rebalance, 100% equity."""
    monthly_dates = get_monthly_dates(start, end)
    returns = []

    for i, date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]
        factors = compute_factors(prices, date)

        if factors.empty or len(factors) < 5:
            returns.append(np.nan)
            continue

        picks = factors.index[:5].tolist()
        ret = compute_month_returns(prices, picks, date, next_date, equity_weight=1.0)
        returns.append(ret)

    return pd.Series(returns, index=monthly_dates[1:], name='A_Top5_MultiFactor')


# ─── Strategy B: Top 10 Multi-Factor ─────────────────────────────────────────

def strategy_b_top10(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """Top 10 by combined score, monthly rebalance, 100% equity."""
    monthly_dates = get_monthly_dates(start, end)
    returns = []

    for i, date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]
        factors = compute_factors(prices, date)

        if factors.empty or len(factors) < 10:
            returns.append(np.nan)
            continue

        picks = factors.index[:10].tolist()
        ret = compute_month_returns(prices, picks, date, next_date, equity_weight=1.0)
        returns.append(ret)

    return pd.Series(returns, index=monthly_dates[1:], name='B_Top10_MultiFactor')


# ─── Strategy C: Top 5 with VIX Filter ───────────────────────────────────────

def strategy_c_vix_filter(prices: pd.DataFrame, vix: pd.Series,
                            start: str, end: str) -> pd.Series:
    """
    Top 5 multi-factor, but go 50% cash when VIX > 25.
    """
    monthly_dates = get_monthly_dates(start, end)
    vix_monthly = vix.resample('ME').last()
    returns = []
    months_defensive = 0

    for i, date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]

        vix_val = vix_monthly.get(date)
        factors = compute_factors(prices, date)

        if factors.empty or len(factors) < 5:
            returns.append(np.nan)
            continue

        picks = factors.index[:5].tolist()

        if pd.notna(vix_val) and vix_val > VIX_CASH_THRESHOLD:
            equity_weight = 1.0 - CASH_ALLOCATION
            months_defensive += 1
        else:
            equity_weight = 1.0

        ret = compute_month_returns(prices, picks, date, next_date, equity_weight=equity_weight)
        returns.append(ret)

    print(f"  VIX Filter: {months_defensive} months in 50% cash (VIX > {VIX_CASH_THRESHOLD})")

    return pd.Series(returns, index=monthly_dates[1:], name='C_Top5_VIX_Filter')


# ─── Strategy D: Top 5 with Regime Filter ────────────────────────────────────

def strategy_d_regime_filter(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """
    Top 5 multi-factor with SPY regime filter:
    - SPY above 200 SMA → full invest
    - SPY below 200 SMA → 50% cash, shift to defensive (bonds/gold)
    """
    monthly_dates = get_monthly_dates(start, end)
    sma200_spy = prices['SPY'].rolling(200, min_periods=150).mean() if 'SPY' in prices.columns else None
    returns = []
    months_defensive = 0

    # Defensive assets (use TLT, GLD if available)
    defensive_symbols = [s for s in ['TLT', 'GLD', 'SHY'] if s in prices.columns]

    for i, date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]
        factors = compute_factors(prices, date)

        if factors.empty or len(factors) < 5:
            returns.append(np.nan)
            continue

        picks = factors.index[:5].tolist()

        # SPY regime check
        in_bull = True
        if sma200_spy is not None:
            sma_at_date = sma200_spy[sma200_spy.index <= date]
            spy_at_date = prices['SPY'][prices['SPY'].index <= date]
            if not sma_at_date.empty and not spy_at_date.empty:
                current_sma = sma_at_date.iloc[-1]
                current_spy = spy_at_date.iloc[-1]
                if pd.notna(current_sma) and pd.notna(current_spy):
                    in_bull = current_spy > current_sma

        if in_bull:
            equity_weight = 1.0
        else:
            equity_weight = 1.0 - CASH_ALLOCATION
            months_defensive += 1
            # Replace some picks with defensive assets
            if defensive_symbols:
                # Add defensive assets to picks proportionally
                n_defensive = min(len(defensive_symbols), 2)
                picks = picks[:3] + defensive_symbols[:n_defensive]

        ret = compute_month_returns(prices, picks, date, next_date, equity_weight=equity_weight)
        returns.append(ret)

    print(f"  Regime Filter: {months_defensive} months in bear regime (SPY below 200 SMA)")

    return pd.Series(returns, index=monthly_dates[1:], name='D_Top5_Regime_Filter')


# ─── Benchmark: Momentum-Only Top 5 ──────────────────────────────────────────

def benchmark_momentum_only(prices: pd.DataFrame, start: str, end: str, top_n: int = 5) -> pd.Series:
    """Top 5 by 6-month momentum only (no value/vol/trend)."""
    monthly_dates = get_monthly_dates(start, end)
    returns = []

    for i, date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]

        lookback_6m = date - pd.DateOffset(months=6)
        window = prices[(prices.index >= lookback_6m) & (prices.index <= date)]
        if len(window) < 100:
            returns.append(np.nan)
            continue

        latest = prices[prices.index <= date].iloc[-1]
        start_p = window.iloc[0]

        mom = {}
        for sym in prices.columns:
            p = latest.get(sym)
            sp = start_p.get(sym)
            if pd.notna(p) and pd.notna(sp) and sp > 0:
                mom[sym] = p / sp - 1

        if len(mom) < top_n:
            returns.append(np.nan)
            continue

        picks = pd.Series(mom).nlargest(top_n).index.tolist()
        ret = compute_month_returns(prices, picks, date, next_date, equity_weight=1.0)
        returns.append(ret)

    return pd.Series(returns, index=monthly_dates[1:], name='Benchmark_Momentum5')


def benchmark_equal_weight(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """Equal-weight all available symbols."""
    monthly_dates = get_monthly_dates(start, end)
    returns = []

    for i, date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]
        picks = [s for s in prices.columns if prices[s][prices.index <= date].dropna().shape[0] >= 200]
        ret = compute_month_returns(prices, picks, date, next_date, equity_weight=1.0)
        returns.append(ret)

    return pd.Series(returns, index=monthly_dates[1:], name='Benchmark_EqualWeight')


def benchmark_spy(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    spy = prices['SPY'].resample('ME').last()
    spy_ret = spy.pct_change().dropna()
    spy_ret = spy_ret[(spy_ret.index >= pd.Timestamp(start)) & (spy_ret.index <= pd.Timestamp(end))]
    return spy_ret.rename('SPY_BuyHold')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== Multi-Factor Combined Strategy Backtest (Issue #17) ===\n")
    print(f"Factor weights: Momentum={W_MOMENTUM:.0%}, Value={W_VALUE:.0%}, "
          f"LowVol={W_LOWVOL:.0%}, Trend={W_TREND:.0%}\n")

    # Load data
    symbols = get_all_stock_etf_symbols()
    print(f"Loading {len(symbols)} symbols...")
    prices = load_close_matrix(symbols, start_date='2010-01-01')
    print(f"Price matrix: {prices.shape[0]} rows × {prices.shape[1]} columns")
    print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")

    vix = load_vix('2010-01-01')
    print(f"VIX: {len(vix)} days\n")

    # Benchmarks
    print("Building benchmarks...")
    spy_ret = benchmark_spy(prices, START_DATE, END_DATE)
    print("  - SPY buy-and-hold ✓")
    mom5_ret = benchmark_momentum_only(prices, START_DATE, END_DATE, top_n=5)
    print("  - Momentum-only top 5 ✓")
    ew_ret = benchmark_equal_weight(prices, START_DATE, END_DATE)
    print("  - Equal-weight all ✓")

    # Strategies
    print("\nRunning Strategy A: Top 5 Multi-Factor (monthly rebalance)...")
    ret_a = strategy_a_top5(prices, START_DATE, END_DATE)

    print("Running Strategy B: Top 10 Multi-Factor (monthly rebalance)...")
    ret_b = strategy_b_top10(prices, START_DATE, END_DATE)

    print("Running Strategy C: Top 5 with VIX Filter...")
    ret_c = strategy_c_vix_filter(prices, vix, START_DATE, END_DATE)

    print("Running Strategy D: Top 5 with SPY Regime Filter...")
    ret_d = strategy_d_regime_filter(prices, START_DATE, END_DATE)

    # Assemble results
    all_returns = pd.DataFrame({
        'SPY_BuyHold': spy_ret,
        'Momentum_Top5': mom5_ret,
        'EqualWeight_All': ew_ret,
        'A_Top5_MultiFactor': ret_a,
        'B_Top10_MultiFactor': ret_b,
        'C_Top5_VIX_Filter': ret_c,
        'D_Top5_Regime_Filter': ret_d,
    }).loc[START_DATE:END_DATE]

    # Save CSV
    csv_path = RESULTS_DIR / 'multifactor_monthly_returns.csv'
    all_returns.to_csv(csv_path)
    print(f"\nMonthly returns saved → {csv_path}")

    # Compute metrics
    strategies = {
        'SPY Buy-and-Hold': all_returns['SPY_BuyHold'],
        'Momentum-Only Top 5': all_returns['Momentum_Top5'],
        'Equal-Weight All': all_returns['EqualWeight_All'],
        'A) Top 5 Multi-Factor': all_returns['A_Top5_MultiFactor'],
        'B) Top 10 Multi-Factor': all_returns['B_Top10_MultiFactor'],
        'C) Top 5 + VIX Filter': all_returns['C_Top5_VIX_Filter'],
        'D) Top 5 + Regime Filter': all_returns['D_Top5_Regime_Filter'],
    }

    results = {}
    for name, rets in strategies.items():
        results[name] = calc_metrics(rets)

    metrics_order = ['Total Return', 'CAGR', 'Volatility (ann)', 'Sharpe Ratio',
                     'Max Drawdown', 'Calmar Ratio', 'Win Rate', 'Months']

    print("\n" + "=" * 130)
    print(f"{'Metric':<25}", end='')
    for name in strategies:
        print(f"  {name[:17]:<17}", end='')
    print()
    print("-" * 130)
    for metric in metrics_order:
        print(f"{metric:<25}", end='')
        for name in strategies:
            val = results[name].get(metric, 'N/A')
            print(f"  {str(val):<17}", end='')
        print()

    # Sample factor scores at a recent date
    sample_date = prices.index[prices.index <= '2025-01-31'][-1] if '2025-01-31' in str(prices.index[-1]) else prices.index[-2]
    try:
        sample_factors = compute_factors(prices, sample_date)
        if not sample_factors.empty:
            print(f"\n--- Factor Scores at {sample_date.date()} (Top 10) ---")
            display_cols = ['momentum_score', 'value_score', 'lowvol_score', 'trend', 'combined_score']
            print(sample_factors[display_cols].head(10).round(1).to_string())
    except Exception as e:
        print(f"\n(Factor score sample unavailable: {e})")

    # Final cumulative returns
    final_cum = {col: (1 + all_returns[col].dropna()).prod() - 1 for col in all_returns.columns}

    # ─── Markdown Report ────────────────────────────────────────────────────────
    md = f"""# Multi-Factor Combined Strategy Backtest Results
*Issue #17 | Generated by Pinch Stock Trading Platform*

**Test Period:** {START_DATE} to {END_DATE}
**Universe:** {len(symbols)} stocks/ETFs
**Benchmarks:** SPY Buy-and-Hold, Momentum-Only Top 5, Equal-Weight All

---

## Factor Model

**Composite Score = {W_MOMENTUM:.0%} × Momentum + {W_VALUE:.0%} × Value + {W_LOWVOL:.0%} × LowVol + {W_TREND:.0%} × Trend**

| Factor | Measurement | Direction | Weight |
|--------|-------------|-----------|--------|
| **Momentum** | 6-month trailing return (percentile rank) | Higher = better | {W_MOMENTUM:.0%} |
| **Value** | Price/200-SMA ratio (inverted percentile rank) | Lower ratio = better value | {W_VALUE:.0%} |
| **Low-Vol** | 60-day realized volatility (inverted percentile rank) | Lower vol = better | {W_LOWVOL:.0%} |
| **Trend** | Price above 200-day SMA (binary) | 1 = bullish, 0 = bearish | {W_TREND:.0%} |

All factor scores are normalized to 0-100 (percentile ranks within the universe).

---

## Strategy Variants

| Strategy | Holdings | Rebalance | Risk Control |
|----------|----------|-----------|--------------|
| **A) Top 5 Multi-Factor** | Top 5 by combined score | Monthly | None |
| **B) Top 10 Multi-Factor** | Top 10 by combined score | Monthly | None (more diversified) |
| **C) Top 5 + VIX Filter** | Top 5 by combined score | Monthly | 50% cash when VIX > {VIX_CASH_THRESHOLD} |
| **D) Top 5 + Regime Filter** | Top 5 + defensive when bearish | Monthly | 50% cash + defensive assets when SPY < 200 SMA |

---

## Performance Summary

| Metric | SPY B&H | Mom-5 | EW-All | A) Top5 | B) Top10 | C) +VIX | D) +Regime |
|--------|---------|-------|--------|---------|---------|---------|-----------|
"""

    for metric in metrics_order:
        vals = [results[n].get(metric, 'N/A') for n in strategies]
        md += f"| {metric} | " + " | ".join(str(v) for v in vals) + " |\n"

    md += f"""
---

## Key Findings

### Strategy A: Top 5 Multi-Factor (Recommended Baseline)
- Pure factor model, maximum exposure to combined alpha
- **Total Return:** {final_cum.get('A_Top5_MultiFactor', 0):.1%}
- Higher concentration risk vs B, but captures best signals

### Strategy B: Top 10 Multi-Factor
- Wider net — reduces single-stock risk at cost of diluted factor exposure
- **Total Return:** {final_cum.get('B_Top10_MultiFactor', 0):.1%}
- Better for larger portfolios where position sizing matters

### Strategy C: Top 5 + VIX Filter (Recommended for Risk-Managed Accounts)
- Reduces exposure during high-fear environments (VIX > {VIX_CASH_THRESHOLD})
- Cash earns ~0% but protects from gap-down losses
- **Total Return:** {final_cum.get('C_Top5_VIX_Filter', 0):.1%}

### Strategy D: Top 5 + SPY Regime Filter
- Goes defensive when SPY breaks below 200-day SMA
- Adds TLT/GLD allocation during bear markets
- **Total Return:** {final_cum.get('D_Top5_Regime_Filter', 0):.1%}
- **Best for:** Investors who cannot tolerate 30%+ drawdowns

---

## Factor Analysis

### Why This Factor Weighting?

| Factor | Weight Rationale |
|--------|-----------------|
| **Momentum (40%)** | Strongest risk-adjusted factor in academic literature; persists 6-12 months |
| **Value (30%)** | Mean-reversion counterweight; helps avoid chasing peaks |
| **Low-Vol (20%)** | Low-volatility anomaly — lower-risk stocks historically outperform on risk-adjusted basis |
| **Trend (10%)** | Simple but effective market regime filter; reduces bear market exposure |

### Comparison vs Single-Factor Benchmarks

| Strategy | Total Return | CAGR | Sharpe |
|----------|-------------|------|--------|
| SPY Buy-and-Hold | {results.get('SPY Buy-and-Hold', {}).get('Total Return', 'N/A')} | {results.get('SPY Buy-and-Hold', {}).get('CAGR', 'N/A')} | {results.get('SPY Buy-and-Hold', {}).get('Sharpe Ratio', 'N/A')} |
| Momentum-Only Top 5 | {results.get('Momentum-Only Top 5', {}).get('Total Return', 'N/A')} | {results.get('Momentum-Only Top 5', {}).get('CAGR', 'N/A')} | {results.get('Momentum-Only Top 5', {}).get('Sharpe Ratio', 'N/A')} |
| Equal-Weight All | {results.get('Equal-Weight All', {}).get('Total Return', 'N/A')} | {results.get('Equal-Weight All', {}).get('CAGR', 'N/A')} | {results.get('Equal-Weight All', {}).get('Sharpe Ratio', 'N/A')} |
| **Top 5 Multi-Factor** | **{results.get('A) Top 5 Multi-Factor', {}).get('Total Return', 'N/A')}** | **{results.get('A) Top 5 Multi-Factor', {}).get('CAGR', 'N/A')}** | **{results.get('A) Top 5 Multi-Factor', {}).get('Sharpe Ratio', 'N/A')}** |

---

## Implementation Notes

### Portfolio Construction
- Monthly rebalance on last trading day of each month
- Equal weight within selected portfolio (no position sizing optimization)
- No transaction costs modeled (estimate ~0.1-0.3% monthly round-trip)
- Minimum lookback: 200 trading days (symbols excluded until sufficient history)

### Factor Computation
```python
momentum_score = percentile_rank(6m_return)           # 0-100
value_score    = (1 - percentile_rank(price/SMA200)) * 100  # inverted
lowvol_score   = (1 - percentile_rank(60d_vol)) * 100       # inverted
trend_score    = 100 if price > SMA200 else 0
combined       = 40%*momentum + 30%*value + 20%*lowvol + 10%*trend
```

### Recommended Live Implementation
1. **Start with Strategy C** (VIX-filtered) for capital preservation
2. **Universe:** Restrict to liquid stocks/ETFs with >$10B market cap
3. **Rebalance:** Monthly, within 2 days of month-end
4. **Position size:** Equal weight, ~5-10 positions
5. **Add transaction costs:** ~0.1% round-trip reduces CAGR by ~1-1.5%

---

> *Rule of Acquisition #22: A wise man can hear profit in the wind.*
> The multi-factor model doesn't chase any one signal — it listens for convergence across momentum, value, stability, and trend. When all four align, that's profit on the wind.

---

*Data source: pinch_market.db | {len(symbols)} symbols | {prices.shape[0]} daily observations*
*CSV: `backtest/results/multifactor_monthly_returns.csv`*
"""

    md_path = RESULTS_DIR / 'multifactor_results.md'
    md_path.write_text(md)
    print(f"\nMarkdown report saved → {md_path}")
    print("\n✅ Multi-factor backtest complete.")

    return all_returns, results


if __name__ == '__main__':
    main()
