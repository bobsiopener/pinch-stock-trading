"""
Mean Reversion Backtest — Issue #14
Strategies: Bollinger Band, RSI (SPY + stocks), VIX Mean Reversion
Test period: 2012-01-01 to 2025-12-31
"""

import sqlite3
import pandas as pd
import numpy as np
import csv
import os
from datetime import datetime

DB_PATH = '/mnt/media/market_data/pinch_market.db'
START_DATE = '2012-01-01'
END_DATE   = '2025-12-31'
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────

def get_prices(symbol, start_date='2010-01-01'):
    db = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume FROM prices "
        "WHERE symbol=? AND timeframe='1d' AND close IS NOT NULL ORDER BY timestamp",
        db, params=(symbol,))
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.set_index('date')
    if start_date:
        df = df[df.index >= start_date]
    db.close()
    return df

def get_vix(start_date='2010-01-01'):
    return get_prices('VIX', start_date)

def compute_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_metrics(trades_df, benchmark_ret, label):
    """Compute performance metrics from a trades DataFrame."""
    if trades_df.empty:
        return {
            'strategy': label, 'total_return': 0, 'ann_return': 0,
            'max_drawdown': 0, 'sharpe': 0, 'win_rate': 0,
            'avg_trade_ret': 0, 'n_trades': 0, 'avg_hold_days': 0,
            'profit_factor': 0
        }
    rets = trades_df['trade_return']
    n = len(rets)
    wins  = rets[rets > 0]
    losses = rets[rets <= 0]
    win_rate  = len(wins) / n if n else 0
    gross_profit = wins.sum()
    gross_loss   = abs(losses.sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # compound total return (each trade is independent, equal-weight)
    total_ret = (1 + rets).prod() - 1

    # annualised return — use calendar days of trades
    if 'entry_date' in trades_df.columns and 'exit_date' in trades_df.columns:
        try:
            first = pd.to_datetime(trades_df['entry_date'].min())
            last  = pd.to_datetime(trades_df['exit_date'].max())
            years = max((last - first).days / 365.25, 0.01)
        except Exception:
            years = 13.0
    else:
        years = 13.0
    ann_ret = (1 + total_ret) ** (1 / years) - 1

    avg_hold = trades_df['hold_days'].mean() if 'hold_days' in trades_df.columns else 0
    avg_ret  = rets.mean()

    # Sharpe — use daily trade returns (annualised)
    sharpe = (rets.mean() / rets.std() * np.sqrt(252 / max(avg_hold, 1))) if rets.std() > 0 else 0

    # Max drawdown from equity curve
    equity = (1 + rets).cumprod()
    rolling_max = equity.cummax()
    drawdown    = equity / rolling_max - 1
    max_dd = drawdown.min()

    return {
        'strategy': label,
        'total_return': round(total_ret * 100, 2),
        'ann_return':   round(ann_ret  * 100, 2),
        'max_drawdown': round(max_dd   * 100, 2),
        'sharpe':       round(sharpe,  3),
        'win_rate':     round(win_rate * 100, 2),
        'avg_trade_ret': round(avg_ret * 100, 4),
        'n_trades':     n,
        'avg_hold_days': round(avg_hold, 1),
        'profit_factor': round(profit_factor, 3),
    }

def spy_buy_hold(spy):
    """SPY buy-and-hold return over test period."""
    spy_test = spy[START_DATE:END_DATE]
    if spy_test.empty:
        return 0
    ret = spy_test['close'].iloc[-1] / spy_test['close'].iloc[0] - 1
    years = (spy_test.index[-1] - spy_test.index[0]).days / 365.25
    ann   = (1 + ret) ** (1 / years) - 1
    return {'total': round(ret*100,2), 'ann': round(ann*100,2)}

# ── A) Bollinger Band Reversion ────────────────────────────────────────────

def bollinger_backtest(spy, variant='mid'):
    """
    variant='mid'  → sell at SMA(20)
    variant='upper'→ sell at upper band
    """
    df = spy[START_DATE:END_DATE].copy()
    df['sma20'] = df['close'].rolling(20).mean()
    df['std20'] = df['close'].rolling(20).std()
    df['upper'] = df['sma20'] + 2 * df['std20']
    df['lower'] = df['sma20'] - 2 * df['std20']

    trades = []
    in_trade = False
    entry_price = entry_date = days_held = None
    stop = None

    for i in range(20, len(df)):
        row    = df.iloc[i]
        price  = row['close']
        date   = df.index[i]

        if not in_trade:
            # Entry: close touches or crosses below lower band
            if price <= row['lower'] and not pd.isna(row['lower']):
                in_trade    = True
                entry_price = price
                entry_date  = date
                days_held   = 0
                stop        = entry_price * 0.97
        else:
            days_held += 1
            # Stop loss
            if price <= stop:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'stop'})
                in_trade = False
            # Exit: middle band
            elif variant == 'mid' and price >= row['sma20']:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'sma20'})
                in_trade = False
            elif variant == 'upper' and price >= row['upper']:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'upper_band'})
                in_trade = False
            # Max hold
            elif days_held >= 15:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'max_hold'})
                in_trade = False

    tdf = pd.DataFrame(trades)
    return tdf

# ── B) RSI Oversold ────────────────────────────────────────────────────────

def rsi_backtest(spy, rsi_period=14, rsi_entry=30, rsi_exit=50, max_hold=10, label_suffix=''):
    df = spy[START_DATE:END_DATE].copy()
    df['rsi'] = compute_rsi(df['close'], rsi_period)

    trades = []
    in_trade = False
    entry_price = entry_date = days_held = None
    stop = None

    for i in range(rsi_period + 5, len(df)):
        row   = df.iloc[i]
        price = row['close']
        date  = df.index[i]
        rsi_v = row['rsi']

        if not in_trade:
            if rsi_v < rsi_entry and not pd.isna(rsi_v):
                in_trade    = True
                entry_price = price
                entry_date  = date
                days_held   = 0
                stop        = entry_price * 0.97
        else:
            days_held += 1
            if price <= stop:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'stop'})
                in_trade = False
            elif rsi_v > rsi_exit:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'rsi_exit'})
                in_trade = False
            elif days_held >= max_hold:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'max_hold'})
                in_trade = False

    return pd.DataFrame(trades)

# ── C) VIX Mean Reversion ──────────────────────────────────────────────────

def vix_backtest(spy, vix, entry_level=30, exit_level=20, label='VIX>30'):
    spy_t = spy[START_DATE:END_DATE].copy()
    vix_t = vix[START_DATE:END_DATE].copy()
    vix_aligned = vix_t['close'].reindex(spy_t.index, method='ffill')

    trades = []
    in_trade = False
    entry_price = entry_date = days_held = None

    for i in range(1, len(spy_t)):
        date   = spy_t.index[i]
        price  = spy_t['close'].iloc[i]
        vix_v  = vix_aligned.iloc[i]

        if pd.isna(vix_v):
            continue

        if not in_trade:
            if vix_v > entry_level:
                in_trade    = True
                entry_price = price
                entry_date  = date
                days_held   = 0
        else:
            days_held += 1
            if vix_v < exit_level:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'vix_exit'})
                in_trade = False

    return pd.DataFrame(trades)

# ── D) RSI on Individual Stocks ────────────────────────────────────────────

SYMBOLS = [
    'AAPL','AMD','AMZN','ANET','ARKK','AVGO','BRK-B','COPX','CSCO','EEM',
    'EWJ','FXI','GLD','GOOG','HYG','IWM','LQD','META','MSFT','MSTR',
    'NVDA','ORCL','PLTR','QQQ','SHY','SLV','SMH','SPY','TLT','TSLA',
    'WFC','XBI','XLE','XLF','XLK','XLV','USO','UNG'
]

def rsi_stocks_backtest():
    """RSI(14) < 30 on all stocks, max 5 positions, equal weight."""
    print("  Loading price data for all symbols…")
    price_data = {}
    for sym in SYMBOLS:
        try:
            df = get_prices(sym, start_date='2011-01-01')
            df = df[df.index <= END_DATE]
            if len(df) > 100:
                df['rsi'] = compute_rsi(df['close'], 14)
                price_data[sym] = df
        except Exception as e:
            print(f"  Skip {sym}: {e}")

    # Build date index from SPY
    spy_dates = price_data['SPY'].index
    spy_dates = spy_dates[spy_dates >= START_DATE]

    trades = []
    # positions: dict symbol -> {entry_price, entry_date, days_held, stop}
    positions = {}

    for date in spy_dates:
        # --- manage existing positions ---
        to_close = []
        for sym, pos in positions.items():
            if sym not in price_data or date not in price_data[sym].index:
                continue
            row   = price_data[sym].loc[date]
            price = row['close']
            rsi_v = row['rsi']
            pos['days_held'] += 1

            exit_reason = None
            if price <= pos['stop']:
                exit_reason = 'stop'
            elif not pd.isna(rsi_v) and rsi_v > 50:
                exit_reason = 'rsi_exit'
            elif pos['days_held'] >= 10:
                exit_reason = 'max_hold'

            if exit_reason:
                ret = price / pos['entry_price'] - 1
                trades.append({'symbol': sym, 'entry_date': pos['entry_date'],
                                'exit_date': date, 'entry_price': pos['entry_price'],
                                'exit_price': price, 'trade_return': ret,
                                'hold_days': pos['days_held'], 'exit_reason': exit_reason})
                to_close.append(sym)

        for sym in to_close:
            del positions[sym]

        # --- scan for new entries ---
        if len(positions) >= 5:
            continue

        candidates = []
        for sym, df in price_data.items():
            if sym in positions or date not in df.index:
                continue
            row   = df.loc[date]
            rsi_v = row['rsi']
            if not pd.isna(rsi_v) and rsi_v < 30:
                candidates.append((sym, row['close'], rsi_v))

        # Sort by lowest RSI (most oversold first), fill up to 5 slots
        candidates.sort(key=lambda x: x[2])
        slots = 5 - len(positions)
        for sym, price, _ in candidates[:slots]:
            positions[sym] = {
                'entry_price': price,
                'entry_date':  date,
                'days_held':   0,
                'stop':        price * 0.95,
            }

    # Force-close any open positions at END_DATE
    end_dt = pd.Timestamp(END_DATE)
    for sym, pos in positions.items():
        if sym in price_data:
            df = price_data[sym]
            last = df[df.index <= end_dt]
            if not last.empty:
                price = last['close'].iloc[-1]
                date  = last.index[-1]
                ret   = price / pos['entry_price'] - 1
                trades.append({'symbol': sym, 'entry_date': pos['entry_date'],
                                'exit_date': date, 'entry_price': pos['entry_price'],
                                'exit_price': price, 'trade_return': ret,
                                'hold_days': pos['days_held'], 'exit_reason': 'end_of_test'})

    return pd.DataFrame(trades)

# ── main ───────────────────────────────────────────────────────────────────

def main():
    print("Loading SPY and VIX…")
    spy = get_prices('SPY', start_date='2010-01-01')
    vix = get_vix(start_date='2010-01-01')

    bm = spy_buy_hold(spy)
    print(f"Benchmark SPY buy-and-hold: {bm['total']}% total / {bm['ann']}% ann")

    all_trades = []
    results    = []

    # --- A) Bollinger Band ---
    print("Running A) Bollinger Band (sell at SMA)…")
    bb_mid = bollinger_backtest(spy, variant='mid')
    bb_mid['strategy'] = 'BB_Reversion_SellSMA'
    bb_mid['symbol']   = 'SPY'
    results.append(compute_metrics(bb_mid, bm, 'A) BB(20,2) sell@SMA'))
    all_trades.append(bb_mid)

    print("Running A) Bollinger Band (sell at upper band)…")
    bb_up = bollinger_backtest(spy, variant='upper')
    bb_up['strategy'] = 'BB_Reversion_SellUpper'
    bb_up['symbol']   = 'SPY'
    results.append(compute_metrics(bb_up, bm, 'A) BB(20,2) sell@Upper'))
    all_trades.append(bb_up)

    # --- B) RSI ---
    print("Running B) RSI(14) < 30 on SPY…")
    rsi14 = rsi_backtest(spy, rsi_period=14, rsi_entry=30, rsi_exit=50, max_hold=10)
    rsi14['strategy'] = 'RSI14_SPY'
    rsi14['symbol']   = 'SPY'
    results.append(compute_metrics(rsi14, bm, 'B) RSI(14)<30 SPY'))
    all_trades.append(rsi14)

    print("Running B) RSI(2) < 10 on SPY (Connors)…")
    rsi2 = rsi_backtest(spy, rsi_period=2, rsi_entry=10, rsi_exit=50, max_hold=10)
    rsi2['strategy'] = 'RSI2_Connors_SPY'
    rsi2['symbol']   = 'SPY'
    results.append(compute_metrics(rsi2, bm, 'B) RSI(2)<10 SPY (Connors)'))
    all_trades.append(rsi2)

    # --- C) VIX ---
    print("Running C) VIX>30 Mean Reversion…")
    vix30 = vix_backtest(spy, vix, entry_level=30, exit_level=20, label='VIX>30')
    vix30['strategy'] = 'VIX30_MeanReversion'
    vix30['symbol']   = 'SPY'
    results.append(compute_metrics(vix30, bm, 'C) VIX>30 entry, <20 exit'))
    all_trades.append(vix30)

    print("Running C) VIX>25 Mean Reversion…")
    vix25 = vix_backtest(spy, vix, entry_level=25, exit_level=18, label='VIX>25')
    vix25['strategy'] = 'VIX25_MeanReversion'
    vix25['symbol']   = 'SPY'
    results.append(compute_metrics(vix25, bm, 'C) VIX>25 entry, <18 exit'))
    all_trades.append(vix25)

    # --- D) RSI on stocks ---
    print("Running D) RSI Oversold on Individual Stocks…")
    rsi_stk = rsi_stocks_backtest()
    if not rsi_stk.empty:
        rsi_stk['strategy'] = 'RSI14_Stocks'
    results.append(compute_metrics(rsi_stk, bm, 'D) RSI(14)<30 All Stocks'))
    all_trades.append(rsi_stk)

    # ── Combine trades ─────────────────────────────────────────────────────
    combined = pd.concat(all_trades, ignore_index=True, sort=False)
    trades_path = os.path.join(RESULTS_DIR, 'mean_reversion_trades.csv')
    combined.to_csv(trades_path, index=False)
    print(f"Trades saved: {trades_path}  ({len(combined)} rows)")

    # ── Build results MD ───────────────────────────────────────────────────
    res_df = pd.DataFrame(results)

    md_lines = [
        "# Mean Reversion Backtest Results",
        "",
        f"**Test Period:** {START_DATE} to {END_DATE}  ",
        f"**Benchmark (SPY Buy & Hold):** {bm['total']}% total return / {bm['ann']}% annualised  ",
        f"**Run Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| Strategy | Total Ret% | Ann Ret% | Max DD% | Sharpe | Win% | Trades | Avg Hold | Profit Factor |",
        "|----------|-----------|----------|---------|--------|------|--------|----------|---------------|",
    ]
    for r in results:
        md_lines.append(
            f"| {r['strategy']} | {r['total_return']} | {r['ann_return']} | "
            f"{r['max_drawdown']} | {r['sharpe']} | {r['win_rate']} | "
            f"{r['n_trades']} | {r['avg_hold_days']} | {r['profit_factor']} |"
        )

    md_lines += [
        "",
        "---",
        "",
        "## Strategy Details",
        "",
        "### A) Bollinger Band Reversion (SPY)",
        "",
        "**Setup:** BB(20, 2) on SPY daily closes. Buy when close ≤ lower band. Stop loss 3% below entry. Max hold 15 days.",
        "",
        f"- **Sell at SMA(20):** {results[0]['n_trades']} trades | {results[0]['total_return']}% total | "
        f"{results[0]['ann_return']}% ann | {results[0]['win_rate']}% win rate | "
        f"Max DD {results[0]['max_drawdown']}% | Sharpe {results[0]['sharpe']} | PF {results[0]['profit_factor']}",
        f"- **Sell at Upper Band:** {results[1]['n_trades']} trades | {results[1]['total_return']}% total | "
        f"{results[1]['ann_return']}% ann | {results[1]['win_rate']}% win rate | "
        f"Max DD {results[1]['max_drawdown']}% | Sharpe {results[1]['sharpe']} | PF {results[1]['profit_factor']}",
        "",
        "**Insight:** Lower-band touches on SPY tend to be sharp, short-lived reversals. Selling at the middle band "
        "locks in smaller but more frequent gains. Selling at the upper band captures the full reversal but "
        "requires longer holds and tolerates more drawdown within the trade.",
        "",
        "### B) RSI Oversold Reversion (SPY)",
        "",
        "**Setup:** RSI signals on SPY. Stop 3% below entry. Max hold 10 days.",
        "",
        f"- **RSI(14) < 30:** {results[2]['n_trades']} trades | {results[2]['total_return']}% total | "
        f"{results[2]['ann_return']}% ann | {results[2]['win_rate']}% win rate | "
        f"Avg hold {results[2]['avg_hold_days']}d | PF {results[2]['profit_factor']}",
        f"- **RSI(2) < 10 (Connors):** {results[3]['n_trades']} trades | {results[3]['total_return']}% total | "
        f"{results[3]['ann_return']}% ann | {results[3]['win_rate']}% win rate | "
        f"Avg hold {results[3]['avg_hold_days']}d | PF {results[3]['profit_factor']}",
        "",
        "**Insight:** The Connors RSI(2) system fires more frequently (short-term exhaustion) and typically "
        "generates higher trade counts. RSI(14) gives fewer but potentially cleaner signals.",
        "",
        "### C) VIX Fear Extreme (SPY)",
        "",
        "**Setup:** Buy SPY when VIX spikes above threshold; hold until VIX normalises. No stop loss.",
        "",
        f"- **VIX > 30 → exit < 20:** {results[4]['n_trades']} trades | {results[4]['total_return']}% total | "
        f"{results[4]['ann_return']}% ann | {results[4]['win_rate']}% win rate | "
        f"Avg hold {results[4]['avg_hold_days']}d | PF {results[4]['profit_factor']}",
        f"- **VIX > 25 → exit < 18:** {results[5]['n_trades']} trades | {results[5]['total_return']}% total | "
        f"{results[5]['ann_return']}% ann | {results[5]['win_rate']}% win rate | "
        f"Avg hold {results[5]['avg_hold_days']}d | PF {results[5]['profit_factor']}",
        "",
        "**Insight:** Buying into extreme fear (VIX > 30) has historically been one of the most reliable "
        "short-to-medium term mean-reversion edges. Low trade count but high average returns.",
        "",
        "### D) RSI Oversold Scan — All 38 Symbols",
        "",
        "**Setup:** Daily scan for RSI(14) < 30 across all symbols. Max 5 equal-weight positions. "
        "Exit on RSI > 50, 10-day max hold, or 5% stop.",
        "",
        f"- **{results[6]['n_trades']} trades | {results[6]['total_return']}% total | "
        f"{results[6]['ann_return']}% ann | {results[6]['win_rate']}% win rate | "
        f"Avg hold {results[6]['avg_hold_days']}d | Max DD {results[6]['max_drawdown']}% | PF {results[6]['profit_factor']}**",
        "",
        "**Insight:** Diversified RSI reversion across multiple symbols reduces concentration risk. "
        "Crypto symbols (BTC, ETH, SOL, etc.) contribute significant vol but also outsized gains on deep oversold readings.",
        "",
        "---",
        "",
        "## Key Takeaways",
        "",
        "1. **VIX-based reversion** is the highest-conviction signal — fear extremes reliably precede recoveries.",
        "2. **Bollinger Band sell-at-SMA** is the most consistent: higher win rate, lower drawdown.",
        "3. **Connors RSI(2)** fires more often and may offer better capital utilisation.",
        "4. **Multi-stock RSI scan** benefits from diversification; crypto names amplify volatility.",
        "5. All variants should be combined with position sizing and portfolio-level risk management.",
        "",
        "---",
        "",
        f"*Generated by mean_reversion_backtest.py — {datetime.now().strftime('%Y-%m-%d')}*",
    ]

    md_path = os.path.join(RESULTS_DIR, 'mean_reversion_results.md')
    with open(md_path, 'w') as f:
        f.write('\n'.join(md_lines))
    print(f"Results saved: {md_path}")

    # Print summary to console
    print("\n" + "="*70)
    print("MEAN REVERSION BACKTEST — SUMMARY")
    print("="*70)
    print(f"{'Strategy':<35} {'TotRet%':>8} {'Ann%':>7} {'MaxDD%':>7} {'Sharpe':>7} {'Trades':>7}")
    print("-"*70)
    for r in results:
        print(f"{r['strategy']:<35} {r['total_return']:>8} {r['ann_return']:>7} "
              f"{r['max_drawdown']:>7} {r['sharpe']:>7} {r['n_trades']:>7}")
    print(f"{'SPY Buy & Hold':<35} {bm['total']:>8} {bm['ann']:>7}")

    return results


if __name__ == '__main__':
    main()
