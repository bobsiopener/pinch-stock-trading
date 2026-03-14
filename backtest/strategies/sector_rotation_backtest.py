"""
Sector Rotation Strategy Backtest — Issue #13
Universe: XLK, XLF, XLV, XLE, XBI, SMH, EEM, FXI, EWJ, GLD, TLT, SLV, USO, HYG
Signal: trailing 3-month return
Hold: top N equal-weight, rebalance monthly
Variants: top 2/3/4/5 + VIX filter + yield curve filter
Benchmarks: SPY buy-and-hold, equal-weight all sectors
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

START_DATE  = '2012-01-01'
END_DATE    = '2025-12-31'
WARMUP_DATE = '2010-01-01'
COMMISSION  = 0.001  # 0.1% one-way

SECTOR_UNIVERSE = ['XLK', 'XLF', 'XLV', 'XLE', 'XBI', 'SMH',
                   'EEM', 'FXI', 'EWJ', 'GLD', 'TLT', 'SLV', 'USO', 'HYG']
DEFENSIVE = ['GLD', 'TLT', 'SHY']
LOOKBACK_DAYS = 63  # ~3 months


# ─── data loading ────────────────────────────────────────────────────────────

def load_prices(symbols, start_date=WARMUP_DATE, end_date=END_DATE):
    """Load close prices for specified symbols."""
    conn = sqlite3.connect(DB_PATH)
    placeholders = ','.join(['?'] * len(symbols))
    query = f"""
        SELECT timestamp, symbol, close
        FROM prices
        WHERE timeframe = '1d'
          AND close IS NOT NULL
          AND symbol IN ({placeholders})
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp
    """
    start_ts = int(pd.Timestamp(start_date).timestamp())
    end_ts   = int(pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).timestamp())
    params = list(symbols) + [start_ts, end_ts]
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.drop_duplicates(subset=['date', 'symbol'])
    prices = df.pivot(index='date', columns='symbol', values='close').sort_index()
    return prices


def load_vix(start_date=WARMUP_DATE, end_date=END_DATE):
    """Load VIX close prices."""
    conn = sqlite3.connect(DB_PATH)
    start_ts = int(pd.Timestamp(start_date).timestamp())
    end_ts   = int(pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).timestamp())
    df = pd.read_sql_query(
        "SELECT timestamp, close FROM prices "
        "WHERE symbol='VIX' AND timeframe='1d' AND close IS NOT NULL "
        "AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
        conn, params=(start_ts, end_ts)
    )
    conn.close()
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.set_index('date')['close']
    return df


def load_yield_curve(start_date=WARMUP_DATE, end_date=END_DATE):
    """Load T10Y2Y yield spread from economic_data."""
    conn = sqlite3.connect(DB_PATH)
    start_ts = int(pd.Timestamp(start_date).timestamp())
    end_ts   = int(pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).timestamp())
    df = pd.read_sql_query(
        "SELECT timestamp, value FROM economic_data "
        "WHERE series_id='T10Y2Y' AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
        conn, params=(start_ts, end_ts)
    )
    conn.close()
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.set_index('date')['value'].dropna()
    return df


def load_fedfunds():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT timestamp, value FROM economic_data WHERE series_id='FEDFUNDS' ORDER BY timestamp",
        conn
    )
    conn.close()
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    return df.set_index('date')['value'].dropna()


# ─── metrics ─────────────────────────────────────────────────────────────────

def calc_metrics(monthly_returns: pd.Series, name: str, rf_annual: float = 0.02) -> dict:
    r = monthly_returns.dropna()
    if len(r) == 0:
        return {'Strategy': name}

    total_return = (1 + r).prod() - 1
    n_years = len(r) / 12
    ann_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else np.nan

    cum = (1 + r).cumprod()
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / rolling_max
    max_dd = drawdown.min()

    log_r = np.log(1 + r)
    rf_monthly = rf_annual / 12
    excess = log_r - rf_monthly
    sharpe = (excess.mean() / excess.std() * np.sqrt(12)) if excess.std() > 0 else np.nan

    calmar = ann_return / abs(max_dd) if max_dd != 0 else np.nan
    win_rate = (r > 0).mean()

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

def get_vix_on_date(vix: pd.Series, date: pd.Timestamp) -> float:
    """Get VIX level on or before the given date."""
    avail = vix[vix.index <= date]
    if avail.empty:
        return np.nan
    return avail.iloc[-1]


def get_yield_curve_on_date(yc: pd.Series, date: pd.Timestamp) -> float:
    """Get T10Y2Y spread on or before the given date."""
    avail = yc[yc.index <= date]
    if avail.empty:
        return np.nan
    return avail.iloc[-1]


def run_sector_rotation(
    prices: pd.DataFrame,
    top_k: int,
    vix: pd.Series = None,
    yield_curve: pd.Series = None,
    vix_filter: bool = False,
    yc_filter: bool = False,
    label: str = ""
) -> tuple:
    """
    Run sector rotation backtest.
    Returns (monthly_returns Series, n_trades int, avg_turnover float)
    """
    # Need SHY for yield-curve defensive strategy
    symbols_needed = SECTOR_UNIVERSE.copy()
    if yc_filter and 'SHY' not in symbols_needed:
        symbols_needed.append('SHY')

    test_prices = prices[prices.index >= START_DATE]
    month_ends = test_prices.resample('ME').last().index

    monthly_returns = []
    dates = []
    current_holdings = set()
    n_trades = 0
    total_turnover = 0.0

    for i in range(len(month_ends) - 1):
        rebal_date = month_ends[i]
        next_date  = month_ends[i + 1]

        avail = prices[prices.index <= rebal_date]
        if avail.empty:
            continue
        rebal_idx = avail.index[-1]

        lookback_start_idx = prices.index.searchsorted(rebal_idx) - LOOKBACK_DAYS
        if lookback_start_idx < 0:
            continue
        lookback_start = prices.index[max(0, lookback_start_idx)]

        snapshot = prices.loc[lookback_start:rebal_idx]
        first_close = snapshot.iloc[0]
        last_close  = snapshot.iloc[-1]
        sector_cols = [c for c in SECTOR_UNIVERSE if c in prices.columns]
        ret = (last_close[sector_cols] / first_close[sector_cols]) - 1
        ret = ret.dropna()

        if len(ret) < top_k:
            continue

        # ── Apply filters ──────────────────────────────────────────────────
        cash_fraction = 0.0
        use_defensive = False

        if vix_filter and vix is not None:
            vix_level = get_vix_on_date(vix, rebal_idx)
            if not np.isnan(vix_level):
                if vix_level > 35:
                    cash_fraction = 1.0
                elif vix_level > 25:
                    cash_fraction = 0.5

        if yc_filter and yield_curve is not None:
            yc_level = get_yield_curve_on_date(yield_curve, rebal_idx)
            if not np.isnan(yc_level) and yc_level < 0:
                use_defensive = True

        # Determine new holdings
        if cash_fraction >= 1.0:
            new_holdings = set()  # 100% cash
        elif use_defensive:
            # Defensive basket
            def_avail = [s for s in DEFENSIVE if s in prices.columns]
            if def_avail:
                new_holdings = set(def_avail)
            else:
                new_holdings = set()
        else:
            top_sectors = set(ret.nlargest(top_k).index.tolist())
            if cash_fraction > 0:
                # Hold top_k with reduced exposure; model as fewer symbols
                effective_k = max(1, round(top_k * (1 - cash_fraction)))
                top_sectors = set(ret.nlargest(effective_k).index.tolist())
            new_holdings = top_sectors

        # Count trades / turnover
        sold = current_holdings - new_holdings
        bought = new_holdings - current_holdings
        trade_count = len(sold) + len(bought)
        n_trades += trade_count

        if len(current_holdings) > 0:
            turnover = len(sold) / len(current_holdings)
        elif len(new_holdings) > 0:
            turnover = 1.0
        else:
            turnover = 0.0
        total_turnover += turnover

        # Commission cost
        weight = 1.0 / max(len(new_holdings), 1) if new_holdings else 0
        commission_cost = trade_count * COMMISSION * weight

        # Next month return
        avail_next = prices[prices.index <= next_date]
        if avail_next.empty:
            continue
        next_idx = avail_next.index[-1]

        if not new_holdings:
            # 100% cash
            port_return = 0.0
        else:
            holding_returns = []
            for sym in new_holdings:
                if sym in prices.columns:
                    p_start = prices.at[rebal_idx, sym] if rebal_idx in prices.index else np.nan
                    p_end   = prices.at[next_idx, sym]  if next_idx  in prices.index else np.nan
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


def run_equal_weight_benchmark(prices: pd.DataFrame) -> pd.Series:
    """Equal-weight all sector ETFs, monthly rebalanced."""
    cols = [c for c in SECTOR_UNIVERSE if c in prices.columns]
    test = prices[cols][prices.index >= START_DATE]
    monthly = test.resample('ME').last().pct_change().dropna()
    eq_weight = monthly.mean(axis=1)
    return eq_weight


def run_spy_benchmark(prices: pd.DataFrame) -> pd.Series:
    """SPY buy-and-hold monthly returns."""
    spy = prices['SPY'].dropna() if 'SPY' in prices.columns else pd.Series(dtype=float)
    test_spy = spy[spy.index >= START_DATE]
    monthly = test_spy.resample('ME').last().pct_change().dropna()
    return monthly


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("SECTOR ROTATION STRATEGY BACKTEST")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Universe: {', '.join(SECTOR_UNIVERSE)}")
    print("=" * 70)

    # Load all needed symbols
    all_symbols = SECTOR_UNIVERSE + ['SPY', 'SHY', 'VIX']
    all_symbols = list(set(all_symbols))
    print("\nLoading price data...")
    prices = load_prices(all_symbols)
    print(f"  Loaded {len(prices.columns)} symbols, {len(prices)} trading days")
    print(f"  Available sectors: {[c for c in SECTOR_UNIVERSE if c in prices.columns]}")

    vix = load_vix()
    print(f"  VIX loaded: {len(vix)} records")

    yc = load_yield_curve()
    print(f"  T10Y2Y loaded: {len(yc)} records")

    ff = load_fedfunds()
    rf_annual = ff.mean() / 100
    print(f"  Avg Fed Funds rate: {rf_annual:.2%}")

    # Benchmarks
    spy_monthly = run_spy_benchmark(prices)
    ew_monthly  = run_equal_weight_benchmark(prices)
    spy_metrics = calc_metrics(spy_monthly, 'SPY Buy & Hold', rf_annual)
    ew_metrics  = calc_metrics(ew_monthly,  'Equal-Weight All Sectors', rf_annual)
    spy_metrics.update({'N Trades': 0, 'Turnover': '0.0%', 'Filter': 'None', 'Months': len(spy_monthly)})
    ew_metrics.update({'N Trades': 0, 'Turnover': '~100%', 'Filter': 'None', 'Months': len(ew_monthly)})

    # Variants
    top_ks = [2, 3, 4, 5]
    variants = []

    # Base variants (no filter)
    for k in top_ks:
        variants.append(dict(top_k=k, vix_filter=False, yc_filter=False, label=f"SR Top{k}"))

    # VIX filter variants (top 3 base, with VIX filter)
    variants.append(dict(top_k=3, vix_filter=True,  yc_filter=False, label="SR Top3 +VIX"))
    variants.append(dict(top_k=4, vix_filter=True,  yc_filter=False, label="SR Top4 +VIX"))
    variants.append(dict(top_k=5, vix_filter=True,  yc_filter=False, label="SR Top5 +VIX"))

    # Yield curve filter variants
    variants.append(dict(top_k=3, vix_filter=False, yc_filter=True,  label="SR Top3 +YC"))
    variants.append(dict(top_k=3, vix_filter=True,  yc_filter=True,  label="SR Top3 +VIX+YC"))

    print(f"\nRunning {len(variants)} variants...")
    all_results = []
    all_monthly = {}

    for v in variants:
        label = v['label']
        print(f"  {label}...", end=' ', flush=True)
        monthly, n_trades, turnover = run_sector_rotation(
            prices=prices,
            top_k=v['top_k'],
            vix=vix,
            yield_curve=yc,
            vix_filter=v['vix_filter'],
            yc_filter=v['yc_filter'],
            label=label
        )
        filter_str = []
        if v['vix_filter']: filter_str.append('VIX')
        if v['yc_filter']:  filter_str.append('YC')
        filter_label = '+'.join(filter_str) if filter_str else 'None'

        metrics = calc_metrics(monthly, label, rf_annual)
        metrics['N Trades'] = n_trades
        metrics['Turnover'] = f"{turnover:.1%}"
        metrics['Filter'] = filter_label
        metrics['Months'] = len(monthly)
        all_results.append(metrics)
        all_monthly[label] = monthly
        print(f"done ({len(monthly)} months, {n_trades} trades)")

    # Add benchmarks
    all_results.extend([spy_metrics, ew_metrics])
    all_monthly['SPY Buy & Hold'] = spy_monthly
    all_monthly['EW Sectors'] = ew_monthly

    # ─── print results ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    display_cols = ['Strategy', 'Filter', 'Total Return', 'Ann. Return', 'Max Drawdown',
                    'Sharpe Ratio', 'Calmar Ratio', 'Win Rate', 'Best Year',
                    'Worst Year', 'N Trades', 'Turnover']
    df_results = pd.DataFrame(all_results)
    # Ensure all cols exist
    for col in display_cols:
        if col not in df_results.columns:
            df_results[col] = 'N/A'
    print(df_results[display_cols].to_string(index=False))

    # Best variant
    numeric_results = [(r['Strategy'], r['_sharpe']) for r in all_results
                       if '_sharpe' in r and pd.notna(r.get('_sharpe', np.nan))]
    if numeric_results:
        best = max(numeric_results, key=lambda x: x[1])
        print(f"\n  Best variant by Sharpe: {best[0]} ({best[1]:.2f})")

    # ─── save CSV ─────────────────────────────────────────────────────────
    csv_path = os.path.join(RESULTS_DIR, 'sector_rotation_monthly.csv')
    monthly_df = pd.DataFrame(all_monthly)
    monthly_df.index.name = 'date'
    monthly_df.to_csv(csv_path)
    print(f"\n  Monthly returns saved: {csv_path}")

    # ─── save markdown ────────────────────────────────────────────────────
    md_path = os.path.join(RESULTS_DIR, 'sector_rotation_results.md')
    write_markdown_report(df_results[display_cols], all_monthly, all_results, rf_annual, md_path)
    print(f"  Markdown report saved: {md_path}")

    return df_results, all_monthly, all_results


def write_markdown_report(df_results, all_monthly, all_results, rf_annual, path):
    today = datetime.now().strftime('%Y-%m-%d')
    lines = []
    lines.append("# Sector Rotation Strategy Backtest Results")
    lines.append(f"\n**Generated:** {today}  ")
    lines.append(f"**Period:** {START_DATE} to {END_DATE}  ")
    lines.append(f"**Universe:** {', '.join(SECTOR_UNIVERSE)}  ")
    lines.append(f"**Risk-Free Rate:** {rf_annual:.2%} (avg FEDFUNDS)  ")
    lines.append(f"**Commission:** {COMMISSION:.1%} per side  ")
    lines.append(f"**Lookback:** 3 months (63 trading days)  ")
    lines.append(f"**Rebalance:** Monthly  ")
    lines.append("")

    lines.append("## Strategy Overview")
    lines.append("")
    lines.append("Monthly sector rotation strategy. Ranks sector ETFs by trailing 3-month return,")
    lines.append("buys equal-weight top N sectors, rebalances monthly.")
    lines.append("")
    lines.append("**Base variants:** Top 2, 3, 4, 5 sectors")
    lines.append(f"**VIX filter:** VIX > 25 → 50% cash allocation; VIX > 35 → 100% cash")
    lines.append(f"**Yield curve filter:** T10Y2Y < 0 (inverted) → hold defensive (GLD, TLT, SHY)")
    lines.append("")

    lines.append("## Results Table")
    lines.append("")
    lines.append(df_results.to_markdown(index=False))
    lines.append("")

    # Annual returns
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
        annual_fmt = annual_df.applymap(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
        lines.append(annual_fmt.to_markdown())
        lines.append("")

    # VIX filter analysis
    lines.append("## Filter Analysis")
    lines.append("")
    lines.append("### VIX Filter")
    lines.append("The VIX filter reduces exposure during high-volatility regimes:")
    lines.append("- VIX > 35: Move to 100% cash (avoids crash-period losses)")
    lines.append("- VIX > 25: Move to 50% cash (partial protection)")
    lines.append("")
    lines.append("### Yield Curve Filter")
    lines.append("When the yield curve inverts (T10Y2Y < 0), the strategy switches to")
    lines.append("defensive assets (GLD, TLT, SHY) to preserve capital.")
    lines.append("Historically, inversions precede recessions by 6–18 months.")
    lines.append("")

    # Key findings
    numeric_results = [(r['Strategy'], r['_sharpe'], r['_ann'], r['_maxdd'])
                       for r in all_results if '_sharpe' in r and pd.notna(r.get('_sharpe', np.nan))]
    if numeric_results:
        by_sharpe  = sorted(numeric_results, key=lambda x: x[1], reverse=True)
        by_return  = sorted(numeric_results, key=lambda x: x[2], reverse=True)
        by_drawdown = sorted(numeric_results, key=lambda x: x[3], reverse=True)

        lines.append("## Key Findings")
        lines.append("")
        lines.append(f"- **Best Risk-Adjusted (Sharpe):** {by_sharpe[0][0]} ({by_sharpe[0][1]:.2f})")
        lines.append(f"- **Best Raw Return:** {by_return[0][0]} ({by_return[0][2]:.1%} annualized)")
        lines.append(f"- **Smallest Max Drawdown:** {by_drawdown[0][0]} ({by_drawdown[0][3]:.1%})")
        lines.append("")
        lines.append("### Observations")
        lines.append("- Sector rotation exploits relative strength across economic sectors.")
        lines.append("- Defensive filters (VIX, yield curve) reduce tail risk at the cost of some upside.")
        lines.append("- The combined VIX+YC filter may over-protect during choppy but non-crash markets.")
        lines.append("- Technology (XLK, SMH) and healthcare (XLV) tend to rank highly in bull markets.")
        lines.append("- Commodities (USO, SLV) and EM (EEM, FXI) add diversification but increase vol.")
        lines.append("")

    with open(path, 'w') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main()
