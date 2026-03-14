#!/usr/bin/env python3
"""
Pinch Stock Trading Platform — Portfolio Analytics (Issue #19)

Provides:
  - Performance metrics: total return, CAGR, Sharpe, Sortino, max drawdown, beta, alpha, IR
  - Risk analysis: sector allocation, HHI, correlation matrix, VaR, CVaR, portfolio beta
  - Signal dashboard: RSI(14), distance from 200-SMA, 6-month momentum, flags

Usage (as standalone CLI):
    python3 analytics.py performance
    python3 analytics.py signals
    python3 analytics.py risk
    python3 analytics.py all

Or imported by portfolio_manager.py:
    from analytics import PortfolioAnalytics
    pa = PortfolioAnalytics()
    pa.print_performance()
"""

import sqlite3
import json
import os
import sys
import argparse
import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PORTFOLIO_DB     = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../state/portfolio.db')
MARKET_DB        = '/mnt/media/market_data/pinch_market.db'
STARTING_CAPITAL = 500_000.00
RISK_FREE_RATE   = 0.045   # ~4.5% annualized (T-bill proxy)
TRADING_DAYS     = 252


# ─── Data access ─────────────────────────────────────────────────────────────

def _pconn() -> sqlite3.Connection:
    conn = sqlite3.connect(PORTFOLIO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _mconn() -> sqlite3.Connection:
    conn = sqlite3.connect(MARKET_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_cash_bal() -> float:
    with _pconn() as conn:
        row = conn.execute("SELECT value FROM portfolio_state WHERE key='cash'").fetchone()
        return float(row['value']) if row else STARTING_CAPITAL


def load_positions() -> List[Dict]:
    with _pconn() as conn:
        rows = conn.execute("SELECT * FROM positions WHERE shares > 0 ORDER BY symbol").fetchall()
    return [dict(r) for r in rows]


def load_snapshots() -> pd.DataFrame:
    """Load portfolio snapshots as a time-series DataFrame."""
    with _pconn() as conn:
        rows = conn.execute(
            "SELECT timestamp, total_value, cash, invested_value FROM snapshots ORDER BY timestamp"
        ).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.set_index('timestamp')


def load_price_history(symbols: List[str], days: int = 365) -> pd.DataFrame:
    """
    Load daily OHLCV from market DB for the given symbols.
    Returns a DataFrame indexed by date, one column per symbol.
    """
    if not symbols:
        return pd.DataFrame()
    cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
    placeholders = ','.join('?' * len(symbols))
    with _mconn() as conn:
        rows = conn.execute(
            f"""SELECT symbol, timestamp, close FROM prices
                WHERE symbol IN ({placeholders}) AND timeframe='1d' AND timestamp >= ?
                ORDER BY timestamp""",
            [s.upper() for s in symbols] + [cutoff]
        ).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=['symbol', 'timestamp', 'close'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.date
    df = df.drop_duplicates(['symbol', 'date'])
    pivot = df.pivot(index='date', columns='symbol', values='close')
    pivot.index = pd.to_datetime(pivot.index)
    return pivot


def get_latest_prices(symbols: List[str]) -> Dict[str, Optional[float]]:
    """Fetch most-recent price for each symbol (DB first, yfinance fallback)."""
    if not symbols:
        return {}
    placeholders = ','.join('?' * len(symbols))
    with _mconn() as conn:
        rows = conn.execute(
            f"""SELECT symbol, close FROM prices
                WHERE symbol IN ({placeholders}) AND timeframe='1d'
                GROUP BY symbol HAVING timestamp=MAX(timestamp)""",
            [s.upper() for s in symbols]
        ).fetchall()
    prices = {r['symbol']: r['close'] for r in rows}

    misses = [s for s in symbols if s.upper() not in prices]
    if misses:
        try:
            import yfinance as yf
            tickers = yf.download(' '.join(misses), period='2d', progress=False, auto_adjust=True)
            if not tickers.empty:
                for sym in misses:
                    try:
                        p = float(tickers['Close'].iloc[-1]) if len(misses) == 1 \
                            else float(tickers['Close'][sym].dropna().iloc[-1])
                        prices[sym.upper()] = p
                    except Exception:
                        pass
        except Exception:
            pass

    return {s: prices.get(s.upper()) for s in symbols}


# ─── Technical indicators ─────────────────────────────────────────────────────

def calc_rsi(series: pd.Series, period: int = 14) -> Optional[float]:
    if len(series) < period + 1:
        return None
    delta    = series.diff().dropna()
    gain     = delta.clip(lower=0).rolling(period).mean()
    loss     = (-delta).clip(lower=0).rolling(period).mean()
    last_gain = gain.iloc[-1]
    last_loss = loss.iloc[-1]
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return round(100 - 100 / (1 + rs), 2)


def calc_sma(series: pd.Series, period: int = 200) -> Optional[float]:
    if len(series) < period:
        return None
    return round(float(series.rolling(period).mean().iloc[-1]), 4)


def calc_momentum_6m(series: pd.Series) -> Optional[float]:
    """Total return over last ~126 trading days."""
    if len(series) < 126:
        return None
    return round((float(series.iloc[-1]) / float(series.iloc[-126]) - 1) * 100, 4)


# ─── Stat helpers ─────────────────────────────────────────────────────────────

def _daily_rf(annual: float = RISK_FREE_RATE) -> float:
    return (1 + annual) ** (1 / TRADING_DAYS) - 1


def sharpe_ratio(returns: pd.Series) -> float:
    excess = returns - _daily_rf()
    if excess.std() == 0:
        return 0.0
    return round(excess.mean() / excess.std() * math.sqrt(TRADING_DAYS), 4)


def sortino_ratio(returns: pd.Series) -> float:
    excess   = returns - _daily_rf()
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    return round(excess.mean() / downside.std() * math.sqrt(TRADING_DAYS), 4)


def max_drawdown(values: pd.Series) -> float:
    peak = values.cummax()
    dd   = (values - peak) / peak
    return float(dd.min())


def calc_cagr(start: float, end: float, years: float) -> float:
    if years <= 0 or start <= 0:
        return 0.0
    return round((end / start) ** (1 / years) - 1, 6)


def calc_beta(port: pd.Series, bench: pd.Series) -> float:
    aligned = pd.concat([port, bench], axis=1).dropna()
    if len(aligned) < 10:
        return float('nan')
    cov = float(aligned.cov().iloc[0, 1])
    var = float(aligned.iloc[:, 1].var())
    return round(cov / var, 4) if var != 0 else float('nan')


def calc_alpha(port: pd.Series, bench: pd.Series, beta: float) -> float:
    """Jensen's alpha (annualized)."""
    if math.isnan(beta):
        return float('nan')
    rf        = _daily_rf() * TRADING_DAYS
    port_ann  = float(port.mean()) * TRADING_DAYS
    bench_ann = float(bench.mean()) * TRADING_DAYS
    return round(port_ann - (rf + beta * (bench_ann - rf)), 6)


def tracking_error(port: pd.Series, bench: pd.Series) -> float:
    aligned = pd.concat([port, bench], axis=1).dropna()
    if len(aligned) < 2:
        return float('nan')
    diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return round(float(diff.std()) * math.sqrt(TRADING_DAYS), 6)


def information_ratio(port: pd.Series, bench: pd.Series) -> float:
    te = tracking_error(port, bench)
    if math.isnan(te) or te == 0:
        return float('nan')
    aligned = pd.concat([port, bench], axis=1).dropna()
    diff    = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return round((float(diff.mean()) * TRADING_DAYS) / te, 4)


def var_hist(returns: pd.Series, confidence: float = 0.95, notional: float = 1.0) -> float:
    if len(returns) < 20:
        return float('nan')
    return round(float(returns.quantile(1 - confidence)) * notional, 2)


def cvar_hist(returns: pd.Series, confidence: float = 0.95, notional: float = 1.0) -> float:
    if len(returns) < 20:
        return float('nan')
    cutoff = returns.quantile(1 - confidence)
    return round(float(returns[returns <= cutoff].mean()) * notional, 2)


def var_parametric(returns: pd.Series, confidence: float = 0.95, notional: float = 1.0) -> float:
    from scipy import stats
    z = stats.norm.ppf(1 - confidence)
    return round((float(returns.mean()) + z * float(returns.std())) * notional, 2)


def hhi(weights: Dict[str, float]) -> float:
    return round(sum(w ** 2 for w in weights.values()), 6)


# ─── Analytics class ──────────────────────────────────────────────────────────

class PortfolioAnalytics:
    def __init__(self):
        self.positions = load_positions()
        self.symbols   = [p['symbol'] for p in self.positions]

    def _portfolio_returns(self, days: int = 365) -> Tuple[pd.Series, pd.Series]:
        """Weighted daily portfolio returns and SPY returns."""
        if not self.symbols:
            return pd.Series(dtype=float), pd.Series(dtype=float)

        all_syms = list(set(self.symbols + ['SPY']))
        hist     = load_price_history(all_syms, days=days)
        if hist.empty:
            return pd.Series(dtype=float), pd.Series(dtype=float)
        hist = hist.ffill().dropna(how='all')

        latest = get_latest_prices(self.symbols)
        total  = sum(p['shares'] * (latest.get(p['symbol']) or p['avg_cost'])
                     for p in self.positions)
        weights = {
            p['symbol']: (p['shares'] * (latest.get(p['symbol']) or p['avg_cost'])) / total
            for p in self.positions
        } if total else {}

        port_r = pd.Series(0.0, index=hist.index)
        for sym, wt in weights.items():
            if sym in hist.columns:
                port_r += hist[sym].pct_change().fillna(0) * wt
        port_r = port_r.dropna()

        spy_r = hist['SPY'].pct_change().dropna() if 'SPY' in hist.columns else pd.Series(dtype=float)
        return port_r, spy_r

    # ── Performance metrics ────────────────────────────────────────────────────

    def get_performance_metrics(self) -> Dict:
        with _pconn() as conn:
            state = dict(conn.execute("SELECT key, value FROM portfolio_state").fetchall())

        inception_date = state.get('inception_date', date.today().isoformat())
        inception_dt   = datetime.strptime(inception_date, '%Y-%m-%d')
        years_held     = max((datetime.now() - inception_dt).days / 365.25, 1 / 365.25)

        latest     = get_latest_prices(self.symbols)
        cash       = get_cash_bal()
        total_val  = cash
        cost_basis = 0.0
        for p in self.positions:
            price     = latest.get(p['symbol']) or p['avg_cost']
            total_val += p['shares'] * price
            cost_basis += p['shares'] * p['avg_cost']

        total_pnl = total_val - STARTING_CAPITAL
        total_ret = total_val / STARTING_CAPITAL - 1
        ann       = calc_cagr(STARTING_CAPITAL, total_val, years_held)

        port_r, spy_r = self._portfolio_returns(days=max(int(years_held * 365) + 30, 252))

        # Use snapshot series for MDD if available
        snap_df = load_snapshots()
        if len(snap_df) >= 5:
            val_series = snap_df['total_value']
            daily_rets = val_series.pct_change().dropna()
            mdd        = max_drawdown(val_series)
        else:
            daily_rets = port_r
            cum        = (1 + port_r).cumprod()
            mdd        = max_drawdown(cum) if len(cum) > 1 else float('nan')

        beta  = calc_beta(port_r, spy_r) if len(port_r) > 10 and len(spy_r) > 10 else float('nan')
        alpha = calc_alpha(port_r, spy_r, beta)
        te    = tracking_error(port_r, spy_r)
        ir    = information_ratio(port_r, spy_r)
        shp   = sharpe_ratio(daily_rets) if len(daily_rets) > 5 else float('nan')
        srt   = sortino_ratio(daily_rets) if len(daily_rets) > 5 else float('nan')

        def period_ret(n):
            if len(port_r) >= n:
                return round(float((port_r.iloc[-n:] + 1).prod() - 1), 6)
            return None

        return {
            'inception_date':    inception_date,
            'years_held':        round(years_held, 4),
            'starting_capital':  STARTING_CAPITAL,
            'current_value':     round(total_val, 2),
            'cash':              round(cash, 2),
            'cost_basis':        round(cost_basis, 2),
            'total_pnl':         round(total_pnl, 2),
            'total_return_pct':  round(total_ret * 100, 4),
            'cagr_pct':          round(ann * 100, 4),
            'daily_return':      period_ret(1),
            'weekly_return':     period_ret(5),
            'monthly_return':    period_ret(21),
            'sharpe':            shp if not math.isnan(shp) else None,
            'sortino':           srt if not math.isnan(srt) else None,
            'max_drawdown_pct':  round(mdd * 100, 4) if not math.isnan(mdd) else None,
            'beta_vs_spy':       beta if not math.isnan(beta) else None,
            'alpha_vs_spy_pct':  round(alpha * 100, 4) if not math.isnan(alpha) else None,
            'tracking_error_pct': round(te * 100, 4) if not math.isnan(te) else None,
            'information_ratio': ir if not math.isnan(ir) else None,
        }

    def print_performance(self, as_json: bool = False):
        m = self.get_performance_metrics()
        if as_json:
            print(json.dumps(m, indent=2))
            return

        def f(v, suf='', pre=''):
            if v is None:
                return 'N/A'
            return f"{pre}{v:,.4g}{suf}"

        W = 62
        print(f"\n{'═'*W}")
        print(f"  📊 PERFORMANCE SUMMARY")
        print(f"{'═'*W}")
        print(f"  Inception:           {m['inception_date']}  ({m['years_held']:.2f} yrs)")
        print(f"  Starting capital:    ${m['starting_capital']:>14,.2f}")
        print(f"  Current value:       ${m['current_value']:>14,.2f}")
        print(f"  Cost basis:          ${m['cost_basis']:>14,.2f}")
        print(f"  Cash:                ${m['cash']:>14,.2f}")
        pnl_s = '+' if m['total_pnl'] >= 0 else ''
        print(f"  Total P&L:           {pnl_s}${m['total_pnl']:>13,.2f}")
        ret_s = '+' if m['total_return_pct'] >= 0 else ''
        print(f"  Total return:        {ret_s}{m['total_return_pct']:>+13.2f}%")
        print(f"  CAGR:                {f(m['cagr_pct'], '%'):>15}")
        print(f"{'─'*W}")
        print(f"  Period Returns")
        def pret(v): return f"{v*100:>+13.4f}%" if v is not None else '         N/A'
        print(f"    Daily  (1d):       {pret(m['daily_return'])}")
        print(f"    Weekly (5d):       {pret(m['weekly_return'])}")
        print(f"    Monthly (21d):     {pret(m['monthly_return'])}")
        print(f"{'─'*W}")
        print(f"  Risk Metrics")
        print(f"    Sharpe ratio:      {f(m['sharpe']):>15}")
        print(f"    Sortino ratio:     {f(m['sortino']):>15}")
        print(f"    Max drawdown:      {f(m['max_drawdown_pct'], '%'):>15}")
        print(f"    Beta (vs SPY):     {f(m['beta_vs_spy']):>15}")
        print(f"    Alpha (vs SPY):    {f(m['alpha_vs_spy_pct'], '%'):>15}")
        print(f"    Tracking error:    {f(m['tracking_error_pct'], '%'):>15}")
        print(f"    Info ratio:        {f(m['information_ratio']):>15}")
        print(f"{'═'*W}\n")

    # ── Risk analysis ──────────────────────────────────────────────────────────

    def get_risk_metrics(self) -> Dict:
        latest    = get_latest_prices(self.symbols)
        cash      = get_cash_bal()
        total_val = cash
        pos_vals: Dict[str, float] = {}

        for p in self.positions:
            price = latest.get(p['symbol']) or p['avg_cost']
            val   = p['shares'] * price
            pos_vals[p['symbol']] = val
            total_val += val

        weights = {sym: val / total_val for sym, val in pos_vals.items()} if total_val else {}

        # Sector allocation
        sector_alloc: Dict[str, float] = {}
        for p in self.positions:
            sec = p.get('sector') or 'Unknown'
            sector_alloc[sec] = sector_alloc.get(sec, 0) + weights.get(p['symbol'], 0)

        hhi_val = hhi(weights)

        # Price history for correlations + VaR
        all_syms = list(set(self.symbols + ['SPY']))
        hist     = load_price_history(all_syms, days=252)
        hist     = hist.ffill().dropna(how='all') if not hist.empty else hist

        corr_data  = None
        var_95     = cvar_95 = var_99 = None
        port_beta  = None

        if not hist.empty:
            sym_hist = hist[[s for s in self.symbols if s in hist.columns]]
            if len(sym_hist.columns) > 1:
                corr_data = sym_hist.pct_change().dropna().corr().round(4).to_dict()

            port_r = pd.Series(0.0, index=hist.index)
            for sym, wt in weights.items():
                if sym in hist.columns:
                    port_r += hist[sym].pct_change().fillna(0) * wt
            port_r = port_r.dropna()

            var_95  = var_hist(port_r, 0.95, total_val)
            cvar_95 = cvar_hist(port_r, 0.95, total_val)
            var_99  = var_hist(port_r, 0.99, total_val)

            if 'SPY' in hist.columns:
                spy_r = hist['SPY'].pct_change().dropna()
                b     = calc_beta(port_r, spy_r)
                port_beta = b if not math.isnan(b) else None

        return {
            'total_value':    round(total_val, 2),
            'weights_pct':    {k: round(v * 100, 3) for k, v in weights.items()},
            'sector_pct':     {k: round(v * 100, 3) for k, v in sector_alloc.items()},
            'hhi':            hhi_val,
            'var_95_1d':      var_95,
            'cvar_95_1d':     cvar_95,
            'var_99_1d':      var_99,
            'portfolio_beta': port_beta,
            'correlation':    corr_data,
        }

    def print_risk(self, as_json: bool = False):
        m = self.get_risk_metrics()
        if as_json:
            print(json.dumps(m, indent=2))
            return

        W = 62
        print(f"\n{'═'*W}")
        print(f"  ⚠️  RISK ANALYSIS")
        print(f"{'═'*W}")
        print(f"  Portfolio value:  ${m['total_value']:>14,.2f}")
        print(f"  Portfolio beta:   {m['portfolio_beta'] if m['portfolio_beta'] is not None else 'N/A':>15}")
        print(f"  HHI (concentration): {m['hhi']:.4f}  {'(High)' if m['hhi'] > 0.15 else '(Moderate)' if m['hhi'] > 0.08 else '(Low)'}")
        print(f"{'─'*W}")
        print(f"  Value at Risk (1-day, 95% confidence)")
        print(f"    Historical VaR:    ${m['var_95_1d']:>10,.0f}" if m['var_95_1d'] is not None else "    Historical VaR:    N/A")
        print(f"    Expected Shortfall: ${m['cvar_95_1d']:>9,.0f}" if m['cvar_95_1d'] is not None else "    Expected Shortfall: N/A")
        print(f"    VaR 99%:           ${m['var_99_1d']:>10,.0f}" if m['var_99_1d'] is not None else "    VaR 99%:           N/A")
        print(f"{'─'*W}")
        print(f"  Sector Allocation")
        for sec, pct in sorted(m['sector_pct'].items(), key=lambda x: -x[1]):
            bar = '█' * int(pct / 3) if pct > 0 else ''
            print(f"    {sec:<18} {pct:>6.1f}%  {bar}")
        print(f"{'─'*W}")
        print(f"  Position Weights")
        for sym, pct in sorted(m['weights_pct'].items(), key=lambda x: -x[1]):
            bar = '█' * int(pct / 2)
            print(f"    {sym:<8} {pct:>6.1f}%  {bar}")
        print(f"{'─'*W}")
        if m['correlation']:
            syms = list(m['correlation'].keys())
            print(f"  Correlation Matrix")
            header = ''.join(f"{s:>8}" for s in syms)
            print(f"    {'':>8}{header}")
            for s1 in syms:
                row_str = ''.join(f"{m['correlation'][s1].get(s2, float('nan')):>8.2f}" for s2 in syms)
                print(f"    {s1:>8}{row_str}")
        print(f"{'═'*W}\n")

    # ── Signal dashboard ───────────────────────────────────────────────────────

    def get_signals(self) -> List[Dict]:
        if not self.symbols:
            return []

        hist = load_price_history(self.symbols, days=400)
        if hist.empty:
            return []
        hist = hist.ffill().dropna(how='all')

        latest = get_latest_prices(self.symbols)
        cash   = get_cash_bal()
        total  = cash + sum(
            p['shares'] * (latest.get(p['symbol']) or p['avg_cost'])
            for p in self.positions
        )

        signals = []
        for p in self.positions:
            sym    = p['symbol']
            price  = latest.get(sym) or p['avg_cost']
            weight = (p['shares'] * price / total * 100) if total else 0

            if sym not in hist.columns:
                signals.append({'symbol': sym, 'price': price, 'weight_pct': round(weight, 2),
                                 'error': 'no price history'})
                continue

            series  = hist[sym].dropna()
            rsi     = calc_rsi(series, 14)
            sma200  = calc_sma(series, 200)
            sma50   = calc_sma(series, 50)
            mom6m   = calc_momentum_6m(series)

            # Distance from 200-SMA
            dist_200 = round((price / sma200 - 1) * 100, 2) if sma200 else None

            # Flags
            flags = []
            if rsi is not None:
                if rsi > 70:
                    flags.append('OVERBOUGHT (RSI>70)')
                elif rsi < 30:
                    flags.append('OVERSOLD (RSI<30)')
            if sma200 and price < sma200:
                flags.append('BELOW 200-SMA ⚠️')
            if sma50 and sma200 and sma50 < sma200:
                flags.append('DEATH CROSS')

            signals.append({
                'symbol':       sym,
                'price':        round(price, 2),
                'weight_pct':   round(weight, 2),
                'rsi_14':       rsi,
                'sma_200':      round(sma200, 2) if sma200 else None,
                'sma_50':       round(sma50, 2) if sma50 else None,
                'dist_200_pct': dist_200,
                'mom_6m_pct':   mom6m,
                'flags':        flags,
            })

        # Rank by 6-month momentum
        ranked = sorted(
            [s for s in signals if s.get('mom_6m_pct') is not None],
            key=lambda x: x['mom_6m_pct'], reverse=True
        )
        for i, s in enumerate(ranked, 1):
            s['momentum_rank'] = i

        return signals

    def print_signals(self, as_json: bool = False):
        signals = self.get_signals()
        if as_json:
            print(json.dumps(signals, indent=2))
            return

        print(f"\n{'═'*88}")
        print(f"  📡 SIGNAL DASHBOARD  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═'*88}")
        print(f"  {'SYMBOL':<8} {'PRICE':>8} {'WT%':>5} {'RSI14':>6} {'SMA200':>8} {'DIST%':>7} {'MOM6M%':>8} {'MR':>3}  FLAGS")
        print(f"  {'─'*82}")

        all_signals = sorted(signals, key=lambda x: x.get('momentum_rank', 999))
        for s in all_signals:
            rsi_s    = f"{s['rsi_14']:.1f}" if s.get('rsi_14') is not None else 'N/A'
            sma_s    = f"{s['sma_200']:,.2f}" if s.get('sma_200') else 'N/A'
            dist_s   = f"{s['dist_200_pct']:+.1f}%" if s.get('dist_200_pct') is not None else 'N/A'
            mom_s    = f"{s['mom_6m_pct']:+.1f}%" if s.get('mom_6m_pct') is not None else 'N/A'
            rank_s   = str(s.get('momentum_rank', '-'))
            flags_s  = ', '.join(s.get('flags', [])) or '—'

            # RSI coloring cue
            rsi_mark = ''
            if s.get('rsi_14') is not None:
                rsi_mark = '▲' if s['rsi_14'] > 70 else ('▼' if s['rsi_14'] < 30 else ' ')

            print(f"  {s['symbol']:<8} {s['price']:>8,.2f} {s['weight_pct']:>5.1f}"
                  f" {rsi_s:>5}{rsi_mark} {sma_s:>8} {dist_s:>7} {mom_s:>8} {rank_s:>3}  {flags_s}")

        print(f"{'─'*88}")
        flags_count = sum(len(s.get('flags', [])) for s in signals)
        print(f"  {flags_count} active flag(s)  |  RSI: ▲=overbought >70  ▼=oversold <30")
        print(f"{'═'*88}\n")

    # ── Combined output ────────────────────────────────────────────────────────

    def print_all(self, as_json: bool = False):
        self.print_performance(as_json=as_json)
        self.print_risk(as_json=as_json)
        self.print_signals(as_json=as_json)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Pinch Portfolio Analytics')
    parser.add_argument('command', choices=['performance', 'risk', 'signals', 'all'])
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    pa = PortfolioAnalytics()
    if args.command == 'performance':
        pa.print_performance(as_json=args.json)
    elif args.command == 'risk':
        pa.print_risk(as_json=args.json)
    elif args.command == 'signals':
        pa.print_signals(as_json=args.json)
    elif args.command == 'all':
        pa.print_all(as_json=args.json)


if __name__ == '__main__':
    main()
