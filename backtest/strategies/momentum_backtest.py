"""
Momentum Strategy Backtest — Issue #11
Universe: All stock/ETF symbols in DB (exclude VIX)
Signal: trailing N-day return (63, 126, 252 days)
Hold: top K equal-weight (K = 3, 5, 10)
Rebalance: monthly
Commission: 0.1% per trade (round trip)
Benchmark: SPY buy-and-hold
Test period: 2012-01-01 to 2025-12-31
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

DB_PATH = '/mnt/media/market_data/pinch_market.db'
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

START_DATE = '2012-01-01'
END_DATE   = '2025-12-31'
WARMUP_DATE = '2010-01-01'
COMMISSION = 0.001  # 0.1% one-way; round-trip = 2x

# ─── data loading ────────────────────────────────────────────────────────────

def load_all_prices(start_date=WARMUP_DATE, end_date=END_DATE):
    """Load close prices for all non-VIX symbols into a single DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT timestamp, symbol, close
        FROM prices
        WHERE timeframe = '1d'
          AND close IS NOT NULL
          AND symbol != 'VIX'
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp
    """
    start_ts = int(pd.Timestamp(start_date).timestamp())
    end_ts   = int(pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).timestamp())
    df = pd.read_sql_query(query, conn, params=(start_ts, end_ts))
    conn.close()

    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.drop_duplicates(subset=['date', 'symbol'])
    prices = df.pivot(index='date', columns='symbol', values='close')
    prices = prices.sort_index()
    return prices


def load_fedfunds():
    """Load Fed Funds rate from economic_data."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT timestamp, value FROM economic_data WHERE series_id = 'FEDFUNDS' ORDER BY timestamp",
        conn
    )
    conn.close()
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.set_index('date')['value'].dropna()
    return df


# ─── metrics ─────────────────────────────────────────────────────────────────

def calc_metrics(monthly_returns: pd.Series, name: str, rf_annual: float = 0.02) -> dict:
    """Calculate performance metrics from a series of monthly returns."""
    r = monthly_returns.dropna()
    if len(r) == 0:
        return {}

    total_return = (1 + r).prod() - 1
    n_years = len(r) / 12
    ann_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else np.nan

    # Max drawdown
    cum = (1 + r).cumprod()
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / rolling_max
    max_dd = drawdown.min()

    # Sharpe (monthly log returns)
    log_r = np.log(1 + r)
    rf_monthly = rf_annual / 12
    excess = log_r - rf_monthly
    sharpe = (excess.mean() / excess.std() * np.sqrt(12)) if excess.std() > 0 else np.nan

    # Calmar
    calmar = ann_return / abs(max_dd) if max_dd != 0 else np.nan

    # Win rate
    win_rate = (r > 0).mean()

    # Best / worst year
    yearly = r.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1)
    best_year  = yearly.max() if len(yearly) else np.nan
    worst_year = yearly.min() if len(yearly) else np.nan

    return {
        'Strategy': name,
        'Total Return': f"{total_return:.1%}",
        'Ann. Return': f"{ann_return:.1%}",
        'Max Drawdown': f"{max_dd:.1%}",
        'Sharpe Ratio': f"{sharpe:.2f}",
        'Calmar Ratio': f"{calmar:.2f}",
        'Win Rate': f"{win_rate:.1%}",
        'Best Year': f"{best_year:.1%}",
        'Worst Year': f"{worst_year:.1%}",
        '_total': total_return,
        '_ann': ann_return,
        '_maxdd': max_dd,
        '_sharpe': sharpe,
    }


# ─── backtest engine ──────────────────────────────────────────────────────────

def run_momentum_backtest(prices: pd.DataFrame, lookback_days: int, top_k: int) -> tuple:
    """
    Run momentum backtest.
    Returns (monthly_returns Series, n_trades int, turnover float)
    """
    # Get month-end trading days in the test window
    test_prices = prices[prices.index >= START_DATE]
    month_ends = test_prices.resample('ME').last().index  # month-end dates

    monthly_returns = []
    dates = []
    current_holdings = set()
    n_trades = 0
    total_turnover = 0.0

    for i in range(len(month_ends) - 1):
        rebal_date = month_ends[i]
        next_date  = month_ends[i + 1]

        # Find the actual trading day on or before rebal_date
        avail = prices[prices.index <= rebal_date]
        if avail.empty:
            continue
        rebal_idx = avail.index[-1]

        # Lookback: need data from lookback_days before rebal_date
        lookback_start_idx = prices.index.searchsorted(rebal_idx) - lookback_days
        if lookback_start_idx < 0:
            continue

        lookback_start = prices.index[max(0, lookback_start_idx)]

        # Calculate lookback returns for each symbol
        snapshot = prices.loc[lookback_start:rebal_idx]
        # Use first valid close in lookback window vs last
        first_close = snapshot.iloc[0]
        last_close  = snapshot.iloc[-1]
        ret = (last_close / first_close) - 1

        # Remove NaN; need at least top_k valid
        ret = ret.dropna()
        if len(ret) < top_k:
            continue

        # Select top K by momentum
        new_holdings = set(ret.nlargest(top_k).index.tolist())

        # Trades = symbols leaving + entering
        sold = current_holdings - new_holdings
        bought = new_holdings - current_holdings
        trade_count = len(sold) + len(bought)
        n_trades += trade_count

        # Turnover: fraction of portfolio replaced
        if len(current_holdings) > 0:
            turnover = len(sold) / len(current_holdings)
        else:
            turnover = 1.0
        total_turnover += turnover

        # Commission cost (round-trip on changed positions)
        # Each sell + each buy = 2 * commission * (weight per position)
        weight = 1.0 / top_k
        commission_cost = trade_count * COMMISSION * weight

        # Calculate next-month return for the selected holdings
        # Return from rebal_date close to next_date close
        avail_next = prices[prices.index <= next_date]
        if avail_next.empty:
            continue
        next_idx = avail_next.index[-1]

        # For each holding, compute return from rebal_date to next month
        holding_returns = []
        for sym in new_holdings:
            if sym in prices.columns:
                p_start = prices.loc[rebal_idx, sym] if rebal_idx in prices.index else np.nan
                p_end   = prices.loc[next_idx, sym]  if next_idx  in prices.index else np.nan
                if pd.notna(p_start) and pd.notna(p_end) and p_start > 0:
                    holding_returns.append((p_end / p_start) - 1)

        if not holding_returns:
            continue

        port_return = np.mean(holding_returns) - commission_cost
        monthly_returns.append(port_return)
        dates.append(next_date)

        current_holdings = new_holdings

    if not monthly_returns:
        return pd.Series(dtype=float), 0, 0.0

    series = pd.Series(monthly_returns, index=pd.DatetimeIndex(dates))
    avg_turnover = total_turnover / max(len(month_ends) - 1, 1)
    return series, n_trades, avg_turnover


def run_spy_benchmark(prices: pd.DataFrame) -> pd.Series:
    """SPY buy-and-hold monthly returns."""
    spy = prices['SPY'].dropna()
    test_spy = spy[spy.index >= START_DATE]
    monthly = test_spy.resample('ME').last().pct_change().dropna()
    return monthly


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("MOMENTUM STRATEGY BACKTEST")
    print(f"Period: {START_DATE} to {END_DATE}")
    print("=" * 70)

    print("\nLoading price data...")
    prices = load_all_prices()
    print(f"  Loaded {len(prices.columns)} symbols, {len(prices)} trading days")

    # Risk-free rate
    ff = load_fedfunds()
    rf_annual = ff.mean() / 100  # FEDFUNDS is in percent
    print(f"  Avg Fed Funds rate: {rf_annual:.2%}")

    # SPY benchmark
    spy_monthly = run_spy_benchmark(prices)
    spy_metrics = calc_metrics(spy_monthly, 'SPY Buy & Hold', rf_annual)
    print(f"\n  SPY benchmark loaded: {len(spy_monthly)} months")

    # Variants to test
    lookbacks = [63, 126, 252]
    top_ks    = [3, 5, 10]

    all_results = []
    all_monthly = {}

    # Run all variants
    variants = []
    for lb in lookbacks:
        for k in top_ks:
            lb_label = {63: '3M', 126: '6M', 252: '12M'}[lb]
            label = f"Mom {lb_label} Top{k}"
            variants.append((lb, k, label))

    print(f"\nRunning {len(variants)} variants...")
    for lb, k, label in variants:
        print(f"  {label}...", end=' ', flush=True)
        monthly, n_trades, turnover = run_momentum_backtest(prices, lb, k)
        metrics = calc_metrics(monthly, label, rf_annual)
        metrics['N Trades'] = n_trades
        metrics['Turnover'] = f"{turnover:.1%}"
        metrics['Months'] = len(monthly)
        all_results.append(metrics)
        all_monthly[label] = monthly
        print(f"done ({len(monthly)} months, {n_trades} trades)")

    # Add SPY benchmark
    spy_metrics['N Trades'] = 0
    spy_metrics['Turnover'] = '0.0%'
    spy_metrics['Months'] = len(spy_monthly)
    all_results.append(spy_metrics)
    all_monthly['SPY Buy & Hold'] = spy_monthly

    # ─── print results table ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    display_cols = ['Strategy', 'Total Return', 'Ann. Return', 'Max Drawdown',
                    'Sharpe Ratio', 'Calmar Ratio', 'Win Rate', 'Best Year',
                    'Worst Year', 'N Trades', 'Turnover']
    df_results = pd.DataFrame(all_results)[display_cols]
    print(df_results.to_string(index=False))

    # ─── best variant highlight ───────────────────────────────────────────
    numeric_results = [(r['Strategy'], r['_sharpe']) for r in all_results if '_sharpe' in r and pd.notna(r['_sharpe'])]
    if numeric_results:
        best = max(numeric_results, key=lambda x: x[1])
        print(f"\n  Best variant by Sharpe: {best[0]} ({best[1]:.2f})")

    # ─── save monthly CSV ─────────────────────────────────────────────────
    csv_path = os.path.join(RESULTS_DIR, 'momentum_monthly.csv')
    monthly_df = pd.DataFrame(all_monthly)
    monthly_df.index.name = 'date'
    monthly_df.to_csv(csv_path)
    print(f"\n  Monthly returns saved: {csv_path}")

    # ─── save markdown report ─────────────────────────────────────────────
    md_path = os.path.join(RESULTS_DIR, 'momentum_results.md')
    write_markdown_report(df_results, all_monthly, all_results, rf_annual, md_path)
    print(f"  Markdown report saved: {md_path}")

    return df_results, all_monthly, all_results


def write_markdown_report(df_results, all_monthly, all_results, rf_annual, path):
    today = datetime.now().strftime('%Y-%m-%d')
    lines = []
    lines.append("# Momentum Strategy Backtest Results")
    lines.append(f"\n**Generated:** {today}  ")
    lines.append(f"**Period:** {START_DATE} to {END_DATE}  ")
    lines.append(f"**Risk-Free Rate:** {rf_annual:.2%} (avg FEDFUNDS)  ")
    lines.append(f"**Commission:** {COMMISSION:.1%} per side  ")
    lines.append(f"**Rebalance:** Monthly  ")
    lines.append("")

    lines.append("## Strategy Overview")
    lines.append("")
    lines.append("Monthly momentum strategy ranking all DB symbols by trailing return.")
    lines.append("Equal-weight top K holdings, rebalanced monthly.")
    lines.append("")
    lines.append("**Lookback variants:** 3M (63d), 6M (126d), 12M (252d)")
    lines.append("**Top-K variants:** 3, 5, 10")
    lines.append("")

    lines.append("## Results Table")
    lines.append("")
    lines.append(df_results.to_markdown(index=False))
    lines.append("")

    # Annual returns table
    lines.append("## Annual Returns by Variant")
    lines.append("")
    annual_data = {}
    for col, series in all_monthly.items():
        if len(series) == 0:
            continue
        yearly = series.groupby(series.index.year).apply(lambda x: (1 + x).prod() - 1)
        annual_data[col] = yearly
    if annual_data:
        annual_df = pd.DataFrame(annual_data)
        annual_df.index.name = 'Year'
        # Format as percent
        annual_fmt = annual_df.applymap(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
        lines.append(annual_fmt.to_markdown())
        lines.append("")

    # Best variant
    numeric_results = [(r['Strategy'], r['_sharpe'], r['_ann']) for r in all_results
                       if '_sharpe' in r and pd.notna(r.get('_sharpe', np.nan))]
    if numeric_results:
        by_sharpe = sorted(numeric_results, key=lambda x: x[1], reverse=True)
        lines.append("## Key Findings")
        lines.append("")
        lines.append(f"- **Best Sharpe:** {by_sharpe[0][0]} (Sharpe: {by_sharpe[0][1]:.2f})")
        by_return = sorted(numeric_results, key=lambda x: x[2], reverse=True)
        lines.append(f"- **Best Ann. Return:** {by_return[0][0]} ({by_return[0][2]:.1%})")
        lines.append("")
        lines.append("### Observations")
        lines.append("- Momentum strategies exploit price persistence over 3–12 month horizons.")
        lines.append("- The universe includes equities, ETFs, and crypto — high-momentum crypto")
        lines.append("  names can dominate top slots, boosting returns but increasing drawdowns.")
        lines.append("- Shorter lookbacks (3M) react faster but incur more turnover.")
        lines.append("- Longer lookbacks (12M) are more stable but slower to adapt.")
        lines.append("")

    with open(path, 'w') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main()
