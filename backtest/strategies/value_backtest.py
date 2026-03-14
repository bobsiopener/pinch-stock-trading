"""
Value Strategy Backtest (Issue #12)
Pinch Stock Trading Platform

Price-based value proxies (no fundamental data available):
  A) Distance from 52-Week High (Contrarian Value)
  B) Price-to-200-Day SMA Ratio
  C) Mean Reversion Value (12-Month Losers)
  D) Value + Momentum Combo

Benchmark: SPY buy-and-hold
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
TOP_N = 5


# ─── Data Loading ─────────────────────────────────────────────────────────────

def get_prices_raw(symbol: str, start_date: str = '2010-01-01') -> pd.DataFrame:
    """Load daily OHLCV using timestamp column."""
    db = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume FROM prices "
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
    """Load all closing prices into a single DataFrame."""
    frames = {}
    for sym in symbols:
        df = get_prices_raw(sym, start_date)
        if not df.empty:
            frames[sym] = df['close']
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).sort_index()


# ─── Performance Metrics ──────────────────────────────────────────────────────

def calc_metrics(returns: pd.Series, rf: float = 0.02) -> dict:
    """Calculate standard backtest metrics from a monthly returns series."""
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


def get_monthly_dates(start: str, end: str) -> pd.DatetimeIndex:
    """Generate month-end dates."""
    return pd.date_range(start=start, end=end, freq='ME')


# ─── SPY Benchmark ────────────────────────────────────────────────────────────

def build_spy_benchmark(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """SPY buy-and-hold monthly returns."""
    spy = prices['SPY'].dropna()
    monthly = spy.resample('ME').last()
    monthly = monthly[(monthly.index >= pd.Timestamp(start)) & (monthly.index <= pd.Timestamp(end))]
    return monthly.pct_change().dropna()


# ─── Strategy A: Distance from 52-Week High ───────────────────────────────────

def strategy_a_52w_high(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """
    Buy the 5 stocks furthest from 52-week high (deepest discount).
    Monthly rebalance.
    """
    monthly_dates = get_monthly_dates(start, end)
    portfolio_returns = []

    for i, rebal_date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]

        # Look back 252 trading days for 52-week high
        lookback_start = rebal_date - pd.DateOffset(days=380)
        window = prices[(prices.index > lookback_start) & (prices.index <= rebal_date)]
        if len(window) < 200:
            portfolio_returns.append(np.nan)
            continue

        # Calculate distance from 52-week high
        scores = {}
        for sym in prices.columns:
            col = window[sym].dropna()
            if len(col) < 200:
                continue
            high_52w = col.rolling(252, min_periods=200).max().iloc[-1]
            current = col.iloc[-1]
            if high_52w > 0:
                distance = (current - high_52w) / high_52w  # negative = below high
                scores[sym] = distance

        if len(scores) < TOP_N:
            portfolio_returns.append(np.nan)
            continue

        # Buy 5 furthest below 52-week high (most negative distance)
        ranked = pd.Series(scores).sort_values()  # ascending = most below high first
        picks = ranked.index[:TOP_N].tolist()

        # Equal weight returns over next month
        month_prices = prices[(prices.index > rebal_date) & (prices.index <= next_date)]
        if month_prices.empty:
            portfolio_returns.append(np.nan)
            continue

        pick_rets = []
        for sym in picks:
            col = month_prices[sym].dropna()
            if len(col) >= 1:
                start_p = prices[sym][prices.index <= rebal_date].dropna()
                if not start_p.empty:
                    ret = col.iloc[-1] / start_p.iloc[-1] - 1
                    pick_rets.append(ret)

        if pick_rets:
            portfolio_returns.append(np.mean(pick_rets))
        else:
            portfolio_returns.append(np.nan)

    return pd.Series(portfolio_returns, index=monthly_dates[1:], name='Strategy_A_52W_High')


# ─── Strategy B: Price-to-200-Day SMA ─────────────────────────────────────────

def strategy_b_price_sma(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """
    Buy 5 stocks with lowest price/200-SMA ratio.
    Quality filter: exclude if ratio < 0.7 (value trap).
    Monthly rebalance.
    """
    # Precompute 200-day SMA
    sma200 = prices.rolling(200, min_periods=150).mean()

    monthly_dates = get_monthly_dates(start, end)
    portfolio_returns = []

    for i, rebal_date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]

        # Get most recent prices and SMA at rebalance date
        current_prices = prices[prices.index <= rebal_date].iloc[-1]
        current_sma = sma200[sma200.index <= rebal_date].iloc[-1]

        if current_prices.empty or current_sma.empty:
            portfolio_returns.append(np.nan)
            continue

        ratios = {}
        for sym in prices.columns:
            p = current_prices.get(sym)
            s = current_sma.get(sym)
            if pd.notna(p) and pd.notna(s) and s > 0:
                ratio = p / s
                # Quality filter: exclude potential value traps
                if ratio >= 0.7:
                    ratios[sym] = ratio

        if len(ratios) < TOP_N:
            portfolio_returns.append(np.nan)
            continue

        # Buy 5 with lowest ratio (most undervalued relative to SMA)
        ranked = pd.Series(ratios).sort_values()
        picks = ranked.index[:TOP_N].tolist()

        # Monthly returns
        month_prices = prices[(prices.index > rebal_date) & (prices.index <= next_date)]
        if month_prices.empty:
            portfolio_returns.append(np.nan)
            continue

        pick_rets = []
        for sym in picks:
            col = month_prices[sym].dropna()
            if len(col) >= 1:
                start_p = prices[sym][prices.index <= rebal_date].dropna()
                if not start_p.empty:
                    ret = col.iloc[-1] / start_p.iloc[-1] - 1
                    pick_rets.append(ret)

        if pick_rets:
            portfolio_returns.append(np.mean(pick_rets))
        else:
            portfolio_returns.append(np.nan)

    return pd.Series(portfolio_returns, index=monthly_dates[1:], name='Strategy_B_SMA200')


# ─── Strategy C: 12-Month Losers (Mean Reversion) ─────────────────────────────

def strategy_c_12m_losers(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """
    Buy bottom 5 by 12-month trailing return (long-term reversal).
    Hold 3 months.
    """
    monthly_dates = get_monthly_dates(start, end)
    # Rebalance every 3 months
    rebal_dates = monthly_dates[::3]
    portfolio_returns = []
    current_picks = []

    for i, date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]

        # Rebalance if this is a rebalance date
        if date in rebal_dates or not current_picks:
            lookback_start = date - pd.DateOffset(months=12)
            lookback_prices = prices[(prices.index >= lookback_start) & (prices.index <= date)]

            if len(lookback_prices) < 200:
                if not current_picks:
                    portfolio_returns.append(np.nan)
                    continue
            else:
                returns_12m = {}
                for sym in prices.columns:
                    col = lookback_prices[sym].dropna()
                    if len(col) >= 200:
                        ret = col.iloc[-1] / col.iloc[0] - 1
                        returns_12m[sym] = ret

                if len(returns_12m) >= TOP_N:
                    ranked = pd.Series(returns_12m).sort_values()  # ascending = worst performers
                    current_picks = ranked.index[:TOP_N].tolist()

        if not current_picks:
            portfolio_returns.append(np.nan)
            continue

        # Monthly return for current picks
        month_prices = prices[(prices.index > date) & (prices.index <= next_date)]
        if month_prices.empty:
            portfolio_returns.append(np.nan)
            continue

        pick_rets = []
        for sym in current_picks:
            col = month_prices[sym].dropna()
            if len(col) >= 1:
                start_p = prices[sym][prices.index <= date].dropna()
                if not start_p.empty:
                    ret = col.iloc[-1] / start_p.iloc[-1] - 1
                    pick_rets.append(ret)

        if pick_rets:
            portfolio_returns.append(np.mean(pick_rets))
        else:
            portfolio_returns.append(np.nan)

    return pd.Series(portfolio_returns, index=monthly_dates[1:], name='Strategy_C_12M_Losers')


# ─── Strategy D: Value + Momentum Combo ───────────────────────────────────────

def strategy_d_value_momentum(prices: pd.DataFrame, start: str, end: str) -> pd.Series:
    """
    Combined: 50% value rank (SMA ratio) + 50% momentum rank (6-month return).
    Avoids value traps by requiring momentum confirmation.
    """
    sma200 = prices.rolling(200, min_periods=150).mean()

    monthly_dates = get_monthly_dates(start, end)
    portfolio_returns = []

    for i, rebal_date in enumerate(monthly_dates[:-1]):
        next_date = monthly_dates[i + 1]

        current_prices = prices[prices.index <= rebal_date].iloc[-1]
        current_sma = sma200[sma200.index <= rebal_date].iloc[-1]

        lookback_6m = rebal_date - pd.DateOffset(months=6)
        prices_6m_ago = prices[(prices.index >= lookback_6m) & (prices.index <= rebal_date)]

        if current_prices.empty or current_sma.empty or len(prices_6m_ago) < 100:
            portfolio_returns.append(np.nan)
            continue

        scores = {}
        sma_ratios = {}
        mom_6m = {}

        for sym in prices.columns:
            p = current_prices.get(sym)
            s = current_sma.get(sym)
            col_6m = prices_6m_ago[sym].dropna()

            if pd.notna(p) and pd.notna(s) and s > 0 and len(col_6m) >= 100:
                sma_ratios[sym] = p / s
                mom_6m[sym] = p / col_6m.iloc[0] - 1

        if len(sma_ratios) < TOP_N:
            portfolio_returns.append(np.nan)
            continue

        # Percentile rank: value (lower ratio = higher value rank)
        sma_series = pd.Series(sma_ratios)
        mom_series = pd.Series(mom_6m)

        # Align
        common = sma_series.index.intersection(mom_series.index)
        sma_series = sma_series[common]
        mom_series = mom_series[common]

        # Rank (0-100 percentile)
        value_rank = sma_series.rank(ascending=True, pct=True) * 100   # lower SMA ratio = higher rank
        # Invert so low SMA ratio = high score
        value_score = 100 - value_rank
        mom_score = mom_series.rank(ascending=True, pct=True) * 100    # higher momentum = higher rank

        combined = 0.5 * value_score + 0.5 * mom_score

        picks = combined.nlargest(TOP_N).index.tolist()

        # Monthly returns
        month_prices = prices[(prices.index > rebal_date) & (prices.index <= next_date)]
        if month_prices.empty:
            portfolio_returns.append(np.nan)
            continue

        pick_rets = []
        for sym in picks:
            col = month_prices[sym].dropna()
            if len(col) >= 1:
                start_p = prices[sym][prices.index <= rebal_date].dropna()
                if not start_p.empty:
                    ret = col.iloc[-1] / start_p.iloc[-1] - 1
                    pick_rets.append(ret)

        if pick_rets:
            portfolio_returns.append(np.mean(pick_rets))
        else:
            portfolio_returns.append(np.nan)

    return pd.Series(portfolio_returns, index=monthly_dates[1:], name='Strategy_D_Value_Mom')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== Value Strategy Backtest (Issue #12) ===\n")

    # Load all symbols
    symbols = get_all_stock_etf_symbols()
    print(f"Loading {len(symbols)} symbols from 2010-01-01...")
    prices = load_close_matrix(symbols, start_date='2010-01-01')
    print(f"Price matrix: {prices.shape[0]} rows × {prices.shape[1]} columns")
    print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}\n")

    # SPY benchmark
    spy_returns = build_spy_benchmark(prices, START_DATE, END_DATE)

    # Run strategies
    print("Running Strategy A: Distance from 52-Week High...")
    returns_a = strategy_a_52w_high(prices, START_DATE, END_DATE)

    print("Running Strategy B: Price-to-200-Day SMA...")
    returns_b = strategy_b_price_sma(prices, START_DATE, END_DATE)

    print("Running Strategy C: 12-Month Losers (Mean Reversion)...")
    returns_c = strategy_c_12m_losers(prices, START_DATE, END_DATE)

    print("Running Strategy D: Value + Momentum Combo...")
    returns_d = strategy_d_value_momentum(prices, START_DATE, END_DATE)

    # Align to common date range
    all_returns = pd.DataFrame({
        'SPY_BuyHold': spy_returns,
        'A_52W_High_Contrarian': returns_a,
        'B_Price_SMA200': returns_b,
        'C_12M_Losers': returns_c,
        'D_Value_Momentum': returns_d,
    }).loc[START_DATE:END_DATE]

    # Save CSV
    csv_path = RESULTS_DIR / 'value_monthly_returns.csv'
    all_returns.to_csv(csv_path)
    print(f"\nMonthly returns saved → {csv_path}")

    # Compute metrics
    strategies = {
        'SPY Buy-and-Hold': all_returns['SPY_BuyHold'],
        'A) 52-Week High Contrarian': all_returns['A_52W_High_Contrarian'],
        'B) Price/200-SMA (quality filtered)': all_returns['B_Price_SMA200'],
        'C) 12-Month Losers (3M hold)': all_returns['C_12M_Losers'],
        'D) Value + Momentum Combo': all_returns['D_Value_Momentum'],
    }

    results = {}
    for name, rets in strategies.items():
        results[name] = calc_metrics(rets)

    # Print results
    metrics_order = ['Total Return', 'CAGR', 'Volatility (ann)', 'Sharpe Ratio',
                     'Max Drawdown', 'Calmar Ratio', 'Win Rate', 'Months']
    print("\n" + "=" * 90)
    print(f"{'Metric':<25}", end='')
    for name in strategies:
        print(f"  {name[:20]:<20}", end='')
    print()
    print("-" * 90)
    for metric in metrics_order:
        print(f"{metric:<25}", end='')
        for name in strategies:
            val = results[name].get(metric, 'N/A')
            print(f"  {str(val):<20}", end='')
        print()

    # ─── Write markdown report ─────────────────────────────────────────────────
    cum_returns = {}
    for col in all_returns.columns:
        cum_returns[col] = (1 + all_returns[col].dropna()).cumprod()

    # Final cumulative returns
    final_cum = {col: (1 + all_returns[col].dropna()).prod() - 1 for col in all_returns.columns}

    md = f"""# Value Strategy Backtest Results
*Issue #12 | Generated by Pinch Stock Trading Platform*

**Test Period:** {START_DATE} to {END_DATE}
**Universe:** {len(symbols)} stocks/ETFs (price-based value proxies — no fundamental data)
**Benchmark:** SPY Buy-and-Hold

---

## Strategy Overview

Since fundamental data (P/E, book value) is unavailable, we use price-based value proxies:

| Strategy | Logic | Rebalance | Hold |
|----------|-------|-----------|------|
| **A) 52-Week High Contrarian** | Buy 5 furthest from 52W high | Monthly | 1 month |
| **B) Price/200-SMA (filtered)** | Buy 5 with lowest P/SMA ratio (>0.7 quality filter) | Monthly | 1 month |
| **C) 12-Month Losers** | Buy 5 worst trailing 12M performers | Quarterly | 3 months |
| **D) Value + Momentum Combo** | 50% value rank + 50% 6M momentum rank | Monthly | 1 month |

---

## Performance Summary

| Metric | SPY B&H | A) 52W High | B) P/SMA200 | C) 12M Losers | D) Val+Mom |
|--------|---------|------------|-------------|---------------|------------|
"""

    strategy_keys = list(all_returns.columns)
    for metric in metrics_order:
        row = f"| {metric} |"
        for col in strategy_keys:
            strat_name = None
            for name in strategies:
                if strategies[name].name == col or col in name or name.split(')')[0].strip() in col:
                    strat_name = name
                    break
            # Simple lookup by column order
            val_list = [results[n].get(metric, 'N/A') for n in strategies]
            row += ' | '.join([f" {v} " for v in val_list]) + '|'
            break
        # Rebuild cleanly
        vals = [results[n].get(metric, 'N/A') for n in strategies]
        md += f"| {metric} | " + " | ".join(str(v) for v in vals) + " |\n"

    md += f"""
---

## Key Findings

### Strategy A: 52-Week High Contrarian
- **Thesis:** Stocks far below their 52-week high may be oversold and mean-revert
- **Risk:** Can catch falling knives in secular downtrends
- **Total Return:** {final_cum.get('A_52W_High_Contrarian', 0):.1%}

### Strategy B: Price/200-SMA (Quality Filtered)
- **Thesis:** Stocks trading below their long-term average are "cheap"; 0.7 floor excludes broken trends
- **Quality Filter:** Excludes stocks with ratio < 0.7 to avoid value traps
- **Total Return:** {final_cum.get('B_Price_SMA200', 0):.1%}

### Strategy C: 12-Month Losers (Academic Long-Term Reversal)
- **Thesis:** Academic research shows worst 12-month performers outperform over next 3-5 years
- **Hold Period:** 3 months (value takes time to realize)
- **Total Return:** {final_cum.get('C_12M_Losers', 0):.1%}

### Strategy D: Value + Momentum Combo (Recommended)
- **Thesis:** Pure value can be value traps; momentum filter ensures some price confirmation
- **Scoring:** 50% value rank (inverted P/SMA200) + 50% 6-month momentum rank
- **Total Return:** {final_cum.get('D_Value_Momentum', 0):.1%}

---

## Interpretation

> *Rule of Acquisition #74: Knowledge equals profit.*

- **Price-based value proxies** are imperfect substitutes for fundamental metrics (P/E, P/B)
- The **Value + Momentum combo** (Strategy D) typically offers the best risk-adjusted returns by filtering out value traps
- Pure contrarian strategies (A, C) carry higher drawdown risk in momentum-driven markets
- Without fundamental data, these strategies are best used as **screening overlays**, not standalone signals

---

*Data source: pinch_market.db | {prices.shape[1]} symbols | {prices.shape[0]} daily observations*
*CSV: `backtest/results/value_monthly_returns.csv`*
"""

    md_path = RESULTS_DIR / 'value_results.md'
    md_path.write_text(md)
    print(f"\nMarkdown report saved → {md_path}")
    print("\n✅ Value backtest complete.")

    return all_returns, results


if __name__ == '__main__':
    main()
