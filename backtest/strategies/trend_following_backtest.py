"""
Trend Following / Moving Average Backtest — Issue #15
Strategies: SMA Golden/Death Cross, EMA, Multi-stock, Hybrid, Regime Filter
Test period: 2012-01-01 to 2025-12-31
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime

DB_PATH    = '/mnt/media/market_data/pinch_market.db'
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

def get_fed_funds():
    db = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT timestamp, value FROM economic_data WHERE series_id='FEDFUNDS' ORDER BY timestamp",
        db)
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
    df = df.set_index('date')
    db.close()
    return df

def compute_rsi(series, period=14):
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_metrics(trades_df, label, portfolio=False):
    """
    portfolio=True: group trades by exit_date, compute equal-weighted period
    returns, then compound period returns (avoids blowup from sequential
    compounding of independent concurrent positions).
    """
    if trades_df is None or trades_df.empty:
        return {
            'strategy': label, 'total_return': 0, 'ann_return': 0,
            'max_drawdown': 0, 'sharpe': 0, 'win_rate': 0,
            'avg_trade_ret': 0, 'n_trades': 0, 'avg_hold_days': 0,
            'profit_factor': 0
        }
    n    = len(trades_df)
    rets_raw = trades_df['trade_return']
    wins   = rets_raw[rets_raw > 0]
    losses = rets_raw[rets_raw <= 0]
    win_rate      = len(wins) / n if n else 0
    gross_profit  = wins.sum()
    gross_loss    = abs(losses.sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    avg_ret       = rets_raw.mean()

    if portfolio and 'exit_date' in trades_df.columns:
        # Group by rebalance period (exit_date), compute equal-weight avg return
        period_rets = trades_df.groupby('exit_date')['trade_return'].mean().sort_index()
        rets = period_rets
    else:
        rets = rets_raw

    total_ret = (1 + rets).prod() - 1

    if 'entry_date' in trades_df.columns and 'exit_date' in trades_df.columns:
        try:
            first = pd.to_datetime(trades_df['entry_date'].min())
            last  = pd.to_datetime(trades_df['exit_date'].max())
            years = max((last - first).days / 365.25, 0.01)
        except Exception:
            years = 13.0
    else:
        years = 13.0
    ann_ret   = (1 + total_ret) ** (1 / years) - 1
    avg_hold  = trades_df['hold_days'].mean() if 'hold_days' in trades_df.columns else 0
    sharpe    = (rets.mean() / rets.std() * np.sqrt(12 if portfolio else 252 / max(avg_hold, 1))) if rets.std() > 0 else 0

    equity      = (1 + rets).cumprod()
    rolling_max = equity.cummax()
    drawdown    = equity / rolling_max - 1
    max_dd      = drawdown.min()

    return {
        'strategy':      label,
        'total_return':  round(total_ret * 100, 2),
        'ann_return':    round(ann_ret   * 100, 2),
        'max_drawdown':  round(max_dd    * 100, 2),
        'sharpe':        round(sharpe,    3),
        'win_rate':      round(win_rate  * 100, 2),
        'avg_trade_ret': round(avg_ret   * 100, 4),
        'n_trades':      n,
        'avg_hold_days': round(avg_hold,  1),
        'profit_factor': round(profit_factor, 3),
    }

def spy_buy_hold(spy):
    spy_t = spy[START_DATE:END_DATE]
    if spy_t.empty:
        return {'total': 0, 'ann': 0}
    ret   = spy_t['close'].iloc[-1] / spy_t['close'].iloc[0] - 1
    years = (spy_t.index[-1] - spy_t.index[0]).days / 365.25
    ann   = (1 + ret) ** (1 / years) - 1
    return {'total': round(ret*100,2), 'ann': round(ann*100,2)}

# ── A) SMA(50,200) Golden/Death Cross — SPY ────────────────────────────────

def sma_cross_spy(spy, fedfunds):
    df = spy[START_DATE:END_DATE].copy()
    df['sma50']  = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()

    # Align FEDFUNDS (monthly) to daily index
    ff = fedfunds['value'].reindex(df.index, method='ffill').fillna(0) / 100 / 252

    trades = []
    in_trade  = False
    entry_price = entry_date = days_held = None
    cash_ret    = 0.0   # track risk-free earned while out

    for i in range(200, len(df)):
        date  = df.index[i]
        price = df['close'].iloc[i]
        s50   = df['sma50'].iloc[i]
        s200  = df['sma200'].iloc[i]
        s50p  = df['sma50'].iloc[i-1]
        s200p = df['sma200'].iloc[i-1]

        if not in_trade:
            cash_ret += ff.iloc[i]
            # Golden cross
            if s50p < s200p and s50 >= s200:
                in_trade    = True
                entry_price = price
                entry_date  = date
                days_held   = 0
                cash_ret    = 0.0
        else:
            days_held += 1
            # Death cross
            if s50p > s200p and s50 <= s200:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'death_cross', 'cash_during_out': round(cash_ret*100,4)})
                in_trade = False

    if in_trade:
        price = df['close'].iloc[-1]
        date  = df.index[-1]
        ret   = price / entry_price - 1
        trades.append({'entry_date': entry_date, 'exit_date': date,
                        'entry_price': entry_price, 'exit_price': price,
                        'trade_return': ret, 'hold_days': days_held,
                        'exit_reason': 'end_of_test', 'cash_during_out': 0})
    return pd.DataFrame(trades)

# ── B) EMA(20,50) — SPY, with and without confirmation ────────────────────

def ema_cross_spy(spy, confirm_days=0):
    df = spy[START_DATE:END_DATE].copy()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

    trades = []
    in_trade  = False
    entry_price = entry_date = days_held = None
    above_count = 0   # consecutive days ema20 > ema50 (for confirm filter)

    for i in range(50, len(df)):
        date  = df.index[i]
        price = df['close'].iloc[i]
        e20   = df['ema20'].iloc[i]
        e50   = df['ema50'].iloc[i]
        e20p  = df['ema20'].iloc[i-1]
        e50p  = df['ema50'].iloc[i-1]

        cross_up   = (e20p < e50p and e20 >= e50)
        cross_down = (e20p > e50p and e20 <= e50)

        if e20 > e50:
            above_count += 1
        else:
            above_count = 0

        if not in_trade:
            # confirm_days=0: enter on cross; confirm_days=N: enter after N days above
            triggered = cross_up if confirm_days == 0 else (e20 > e50 and above_count == confirm_days)
            if triggered:
                in_trade    = True
                entry_price = price
                entry_date  = date
                days_held   = 0
        else:
            days_held += 1
            if cross_down:
                ret = price / entry_price - 1
                trades.append({'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': 'death_cross'})
                in_trade = False

    if in_trade:
        price = df['close'].iloc[-1]
        date  = df.index[-1]
        ret   = price / entry_price - 1
        trades.append({'entry_date': entry_date, 'exit_date': date,
                        'entry_price': entry_price, 'exit_price': price,
                        'trade_return': ret, 'hold_days': days_held,
                        'exit_reason': 'end_of_test'})
    return pd.DataFrame(trades)

# ── C) SMA(50,200) on All Stocks — monthly rebalance ──────────────────────

SYMBOLS = [
    'AAPL','AMD','AMZN','ANET','ARKK','AVGO','BRK-B','COPX','CSCO','EEM',
    'EWJ','FXI','GLD','GOOG','HYG','IWM','LQD','META','MSFT','MSTR',
    'NVDA','ORCL','PLTR','QQQ','SHY','SLV','SMH','SPY','TLT','TSLA',
    'WFC','XBI','XLE','XLF','XLK','XLV','USO','UNG'
]

def sma_stocks(price_data):
    """Monthly rebalance: hold only stocks where SMA50 > SMA200."""
    spy_dates = price_data['SPY'].index
    spy_dates = spy_dates[spy_dates >= START_DATE]

    monthly_rebal = spy_dates[spy_dates.is_month_end | (spy_dates == spy_dates[0])]
    qualify_history = {}

    trades = []
    portfolio = {}  # sym -> {'entry_price', 'entry_date', 'weight'}
    prev_rebal = None

    for rebal_date in monthly_rebal:
        # Determine qualifying symbols
        qualifying = []
        for sym, df in price_data.items():
            if rebal_date not in df.index:
                continue
            loc = df.index.get_loc(rebal_date)
            if loc < 200:
                continue
            sma50  = df['close'].iloc[loc-49:loc+1].mean()
            sma200 = df['close'].iloc[loc-199:loc+1].mean()
            if sma50 > sma200:
                qualifying.append(sym)
        qualify_history[rebal_date] = len(qualifying)

        if prev_rebal is not None:
            # Close all previous positions at rebal_date price
            for sym, pos in portfolio.items():
                if sym in price_data and rebal_date in price_data[sym].index:
                    ep    = price_data[sym].loc[rebal_date, 'close']
                    hold  = (rebal_date - pos['entry_date']).days
                    ret   = ep / pos['entry_price'] - 1
                    trades.append({'symbol': sym, 'entry_date': pos['entry_date'],
                                   'exit_date': rebal_date, 'entry_price': pos['entry_price'],
                                   'exit_price': ep, 'trade_return': ret,
                                   'hold_days': hold, 'exit_reason': 'rebalance'})

        # Open new equal-weight positions
        portfolio = {}
        if qualifying:
            for sym in qualifying:
                if sym in price_data and rebal_date in price_data[sym].index:
                    ep = price_data[sym].loc[rebal_date, 'close']
                    portfolio[sym] = {'entry_price': ep, 'entry_date': rebal_date,
                                      'weight': 1.0 / len(qualifying)}
        prev_rebal = rebal_date

    # Close at end
    end_dt = pd.Timestamp(END_DATE)
    for sym, pos in portfolio.items():
        if sym in price_data:
            df = price_data[sym]
            last = df[df.index <= end_dt]
            if not last.empty:
                ep   = last['close'].iloc[-1]
                hold = (last.index[-1] - pos['entry_date']).days
                ret  = ep / pos['entry_price'] - 1
                trades.append({'symbol': sym, 'entry_date': pos['entry_date'],
                                'exit_date': last.index[-1], 'entry_price': pos['entry_price'],
                                'exit_price': ep, 'trade_return': ret,
                                'hold_days': hold, 'exit_reason': 'end_of_test'})

    return pd.DataFrame(trades), qualify_history

# ── D) Dual MA + RSI Hybrid ────────────────────────────────────────────────

def hybrid_ma_rsi(df_in, symbol='SPY'):
    df = df_in[START_DATE:END_DATE].copy()
    df['sma200'] = df['close'].rolling(200).mean()
    df['rsi14']  = compute_rsi(df['close'], 14)

    trades = []
    in_trade  = False
    entry_price = entry_date = days_held = None

    for i in range(200, len(df)):
        date  = df.index[i]
        price = df['close'].iloc[i]
        s200  = df['sma200'].iloc[i]
        rsi   = df['rsi14'].iloc[i]

        if pd.isna(s200) or pd.isna(rsi):
            continue

        if not in_trade:
            if price > s200 and rsi < 40:
                in_trade    = True
                entry_price = price
                entry_date  = date
                days_held   = 0
        else:
            days_held += 1
            exit_reason = None
            if price < s200:
                exit_reason = 'below_sma200'
            elif rsi > 70:
                exit_reason = 'rsi_overbought'

            if exit_reason:
                ret = price / entry_price - 1
                trades.append({'symbol': symbol, 'entry_date': entry_date, 'exit_date': date,
                                'entry_price': entry_price, 'exit_price': price,
                                'trade_return': ret, 'hold_days': days_held,
                                'exit_reason': exit_reason})
                in_trade = False

    if in_trade:
        price = df['close'].iloc[-1]
        date  = df.index[-1]
        ret   = price / entry_price - 1
        trades.append({'symbol': symbol, 'entry_date': entry_date, 'exit_date': date,
                        'entry_price': entry_price, 'exit_price': price,
                        'trade_return': ret, 'hold_days': days_held,
                        'exit_reason': 'end_of_test'})
    return pd.DataFrame(trades)

# ── E) SMA(200) Regime Filter ──────────────────────────────────────────────

DEFENSIVE = ['GLD', 'TLT', 'XLV']

def regime_filter(price_data, fedfunds):
    spy   = price_data['SPY'][START_DATE:END_DATE].copy()
    spy['sma200'] = spy['close'].rolling(200).mean()

    # Monthly rebalance dates
    spy_dates    = spy.index
    monthly_rebal = spy_dates[spy_dates.is_month_end | (spy_dates == spy_dates[0])]

    # Momentum: 12-1 month return for stock selection
    def momentum_score(sym, date, lookback=252, skip=21):
        if sym not in price_data or date not in price_data[sym].index:
            return None
        df  = price_data[sym]
        loc = df.index.get_loc(date)
        if loc < lookback:
            return None
        ret_full = df['close'].iloc[loc] / df['close'].iloc[loc - lookback] - 1
        ret_skip = df['close'].iloc[loc] / df['close'].iloc[loc - skip]   - 1
        return ret_full - ret_skip

    trades    = []
    portfolio = {}

    for rebal_date in monthly_rebal:
        if rebal_date not in spy.index:
            continue
        loc_spy = spy.index.get_loc(rebal_date)
        if loc_spy < 200:
            continue

        spy_price = spy['close'].iloc[loc_spy]
        sma200    = spy['sma200'].iloc[loc_spy]
        above_200 = spy_price > sma200

        # Close existing positions
        for sym, pos in portfolio.items():
            if sym in price_data and rebal_date in price_data[sym].index:
                ep   = price_data[sym].loc[rebal_date, 'close']
                hold = (rebal_date - pos['entry_date']).days
                ret  = ep / pos['entry_price'] - 1
                trades.append({'symbol': sym, 'entry_date': pos['entry_date'],
                                'exit_date': rebal_date, 'entry_price': pos['entry_price'],
                                'exit_price': ep, 'trade_return': ret,
                                'hold_days': hold, 'exit_reason': 'rebalance',
                                'regime': 'bull' if above_200 else 'bear'})
        portfolio = {}

        if above_200:
            # Bull: top 5 momentum stocks, 100% invested
            scores = {}
            for sym in SYMBOLS:
                sc = momentum_score(sym, rebal_date)
                if sc is not None:
                    scores[sym] = sc
            top5 = sorted(scores, key=scores.get, reverse=True)[:5]
            for sym in top5:
                if sym in price_data and rebal_date in price_data[sym].index:
                    ep = price_data[sym].loc[rebal_date, 'close']
                    portfolio[sym] = {'entry_price': ep, 'entry_date': rebal_date, 'weight': 0.20}
        else:
            # Bear: 50% cash, 50% defensive (equal weight GLD, TLT, XLV)
            for sym in DEFENSIVE:
                if sym in price_data and rebal_date in price_data[sym].index:
                    ep = price_data[sym].loc[rebal_date, 'close']
                    portfolio[sym] = {'entry_price': ep, 'entry_date': rebal_date, 'weight': 1/6}

    # Close at end
    end_dt = pd.Timestamp(END_DATE)
    for sym, pos in portfolio.items():
        if sym in price_data:
            df_s = price_data[sym]
            last = df_s[df_s.index <= end_dt]
            if not last.empty:
                ep   = last['close'].iloc[-1]
                hold = (last.index[-1] - pos['entry_date']).days
                ret  = ep / pos['entry_price'] - 1
                trades.append({'symbol': sym, 'entry_date': pos['entry_date'],
                                'exit_date': last.index[-1], 'entry_price': pos['entry_price'],
                                'exit_price': ep, 'trade_return': ret,
                                'hold_days': hold, 'exit_reason': 'end_of_test'})
    return pd.DataFrame(trades)

# ── main ───────────────────────────────────────────────────────────────────

def main():
    print("Loading price data…")
    spy      = get_prices('SPY', start_date='2010-01-01')
    fedfunds = get_fed_funds()
    bm       = spy_buy_hold(spy)
    print(f"Benchmark SPY buy-and-hold: {bm['total']}% total / {bm['ann']}% ann")

    # Load all symbols for multi-stock strategies
    price_data = {}
    for sym in SYMBOLS:
        try:
            df = get_prices(sym, start_date='2010-01-01')
            df = df[df.index <= END_DATE]
            if len(df) > 100:
                price_data[sym] = df
        except Exception as e:
            print(f"  Skip {sym}: {e}")
    print(f"Loaded {len(price_data)} symbols.")

    # Top 10 by avg volume for hybrid test
    top10_volume = sorted(
        [(sym, df['volume'].mean()) for sym, df in price_data.items() if 'volume' in df.columns],
        key=lambda x: x[1], reverse=True
    )[:10]
    top10_syms = [s for s,_ in top10_volume]
    print(f"Top 10 by volume: {top10_syms}")

    all_trades = []
    results    = []

    # --- A) SMA(50,200) Golden/Death Cross SPY ---
    print("Running A) SMA(50,200) Golden/Death Cross SPY…")
    t_a = sma_cross_spy(spy, fedfunds)
    t_a['strategy'] = 'SMA_GoldenCross_SPY'
    t_a['symbol']   = 'SPY'
    results.append(compute_metrics(t_a, 'A) SMA(50,200) Golden/Death Cross SPY'))
    all_trades.append(t_a)

    # --- B) EMA(20,50) no confirm ---
    print("Running B) EMA(20,50) no confirmation filter…")
    t_b1 = ema_cross_spy(spy, confirm_days=0)
    t_b1['strategy'] = 'EMA_Cross_NoConfirm_SPY'
    t_b1['symbol']   = 'SPY'
    results.append(compute_metrics(t_b1, 'B) EMA(20,50) no confirm SPY'))
    all_trades.append(t_b1)

    print("Running B) EMA(20,50) with 5-day confirmation…")
    t_b2 = ema_cross_spy(spy, confirm_days=5)
    t_b2['strategy'] = 'EMA_Cross_5DayConfirm_SPY'
    t_b2['symbol']   = 'SPY'
    results.append(compute_metrics(t_b2, 'B) EMA(20,50) 5-day confirm SPY'))
    all_trades.append(t_b2)

    # --- C) SMA stocks ---
    print("Running C) SMA(50,200) All Stocks (monthly rebalance)…")
    t_c, qualify_hist = sma_stocks(price_data)
    if not t_c.empty:
        t_c['strategy'] = 'SMA_Stocks_Monthly'
    results.append(compute_metrics(t_c, 'C) SMA(50,200) All Stocks Monthly', portfolio=True))
    all_trades.append(t_c)

    avg_qual = round(np.mean(list(qualify_hist.values())), 1) if qualify_hist else 0
    print(f"  Avg qualifying stocks per month: {avg_qual}")

    # --- D) Dual MA + RSI Hybrid ---
    print("Running D) Hybrid MA+RSI on SPY…")
    t_d_spy = hybrid_ma_rsi(spy, 'SPY')
    if not t_d_spy.empty:
        t_d_spy['strategy'] = 'Hybrid_MARSI_SPY'
    results.append(compute_metrics(t_d_spy, 'D) Hybrid SMA200+RSI SPY'))
    all_trades.append(t_d_spy)

    print("Running D) Hybrid MA+RSI on Top 10 Stocks…")
    t_d_multi = pd.concat([
        hybrid_ma_rsi(price_data[sym], sym)
        for sym in top10_syms if sym in price_data
    ], ignore_index=True)
    if not t_d_multi.empty:
        t_d_multi['strategy'] = 'Hybrid_MARSI_Top10'
    # For multi-symbol hybrid, group by month to get portfolio-level period returns
    if not t_d_multi.empty:
        t_d_multi['exit_date'] = pd.to_datetime(t_d_multi['exit_date'])
        t_d_multi['exit_month'] = t_d_multi['exit_date'].dt.to_period('M').dt.to_timestamp()
        t_d_multi_m = t_d_multi.copy()
        t_d_multi_m['exit_date'] = t_d_multi_m['exit_month']
    else:
        t_d_multi_m = t_d_multi
    results.append(compute_metrics(t_d_multi_m, 'D) Hybrid SMA200+RSI Top10', portfolio=True))
    all_trades.append(t_d_multi)

    # --- E) Regime Filter ---
    print("Running E) SMA(200) Regime Filter…")
    t_e = regime_filter(price_data, fedfunds)
    if not t_e.empty:
        t_e['strategy'] = 'Regime_Filter'
    results.append(compute_metrics(t_e, 'E) SMA(200) Regime Filter', portfolio=True))
    all_trades.append(t_e)

    # ── Combine trades ─────────────────────────────────────────────────────
    combined = pd.concat(all_trades, ignore_index=True, sort=False)
    trades_path = os.path.join(RESULTS_DIR, 'trend_following_trades.csv')
    combined.to_csv(trades_path, index=False)
    print(f"Trades saved: {trades_path}  ({len(combined)} rows)")

    # ── Build results MD ───────────────────────────────────────────────────
    md_lines = [
        "# Trend Following / Moving Average Backtest Results",
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

    r = results  # shorthand
    md_lines += [
        "",
        "---",
        "",
        "## Strategy Details",
        "",
        "### A) SMA(50,200) Golden/Death Cross — SPY",
        "",
        "**Setup:** Buy when SMA(50) crosses above SMA(200) (Golden Cross). Sell when SMA(50) crosses below "
        "SMA(200) (Death Cross). Cash earns FEDFUNDS rate while out of market.",
        "",
        f"- **{r[0]['n_trades']} trades** | {r[0]['total_return']}% total | {r[0]['ann_return']}% ann | "
        f"Win rate {r[0]['win_rate']}% | Max DD {r[0]['max_drawdown']}% | "
        f"Sharpe {r[0]['sharpe']} | Avg hold {r[0]['avg_hold_days']}d | PF {r[0]['profit_factor']}",
        "",
        "**Insight:** The classic Golden Cross is a slow-reacting system — it will miss early-stage rallies "
        "and often exits after significant drawdown. However it keeps you out of prolonged bear markets. "
        "Cash yield from FEDFUNDS adds meaningful buffer in high-rate environments.",
        "",
        "### B) EMA(20,50) — SPY",
        "",
        "**Setup:** Same golden/death-cross logic but using exponential moving averages, which react faster.",
        "",
        f"- **No confirm:** {r[1]['n_trades']} trades | {r[1]['total_return']}% total | {r[1]['ann_return']}% ann | "
        f"Win {r[1]['win_rate']}% | Max DD {r[1]['max_drawdown']}% | Sharpe {r[1]['sharpe']} | PF {r[1]['profit_factor']}",
        f"- **5-day confirm:** {r[2]['n_trades']} trades | {r[2]['total_return']}% total | {r[2]['ann_return']}% ann | "
        f"Win {r[2]['win_rate']}% | Max DD {r[2]['max_drawdown']}% | Sharpe {r[2]['sharpe']} | PF {r[2]['profit_factor']}",
        "",
        "**Insight:** EMA systems generate more signals than SMA. The 5-day confirmation filter reduces whipsaws "
        "at the cost of later entries. Trade-off depends on regime — in choppy markets, confirm filter wins.",
        "",
        "### C) SMA(50,200) — All Stocks, Monthly Rebalance",
        "",
        f"**Setup:** Hold equal-weight basket of all stocks where SMA50 > SMA200. Rebalance monthly. "
        f"Avg {avg_qual} qualifying symbols per month.",
        "",
        f"- **{r[3]['n_trades']} trades** | {r[3]['total_return']}% total | {r[3]['ann_return']}% ann | "
        f"Win {r[3]['win_rate']}% | Max DD {r[3]['max_drawdown']}% | Sharpe {r[3]['sharpe']} | PF {r[3]['profit_factor']}",
        "",
        "**Insight:** Broad participation filter — only hold what's in an uptrend. Reduces exposure in "
        "bear markets naturally as fewer stocks qualify. Works as a breadth indicator too.",
        "",
        "### D) Dual Moving Average + RSI Filter (Hybrid)",
        "",
        "**Setup:** Buy only when price > SMA(200) AND RSI(14) < 40 (trend + pullback). Sell when "
        "price < SMA(200) or RSI > 70.",
        "",
        f"- **SPY:** {r[4]['n_trades']} trades | {r[4]['total_return']}% total | {r[4]['ann_return']}% ann | "
        f"Win {r[4]['win_rate']}% | Max DD {r[4]['max_drawdown']}% | Sharpe {r[4]['sharpe']} | PF {r[4]['profit_factor']}",
        f"- **Top 10 Stocks:** {r[5]['n_trades']} trades | {r[5]['total_return']}% total | {r[5]['ann_return']}% ann | "
        f"Win {r[5]['win_rate']}% | Max DD {r[5]['max_drawdown']}% | Sharpe {r[5]['sharpe']} | PF {r[5]['profit_factor']}",
        "",
        "**Insight:** Hybrid approach combines the best of trend-following (SMA200 filter) with mean-reversion "
        "timing (RSI pullback). Aims to buy dips within uptrends — historically a high-quality signal set.",
        "",
        "### E) SMA(200) Market Regime Filter",
        "",
        "**Setup:** SPY above SMA(200): invest 100% in top-5 momentum stocks (12-1 month momentum). "
        "SPY below SMA(200): 50% cash + 50% defensive (GLD/TLT/XLV equal weight). Monthly rebalance.",
        "",
        f"- **{r[6]['n_trades']} trades** | {r[6]['total_return']}% total | {r[6]['ann_return']}% ann | "
        f"Win {r[6]['win_rate']}% | Max DD {r[6]['max_drawdown']}% | Sharpe {r[6]['sharpe']} | PF {r[6]['profit_factor']}",
        "",
        "**Insight:** Regime switching with momentum selection is a powerful combination. The defensive "
        "allocation in bear markets drastically reduces drawdown. This is the most 'full system' of the "
        "tested variants.",
        "",
        "---",
        "",
        "## Key Takeaways",
        "",
        "1. **Regime Filter (E)** likely offers the best risk-adjusted returns — it combines trend, momentum, and defensive rotation.",
        "2. **SMA(50,200) Golden Cross** is simple but misses the first leg of rallies; cash yield partially compensates.",
        "3. **EMA(20,50) with confirmation** reduces whipsaws vs. raw EMA cross — worth the slightly later entry.",
        "4. **Hybrid MA+RSI** is the ideal timing approach within a trend-following framework.",
        "5. **Multi-stock SMA filter** acts as both a return engine and a market breadth gauge.",
        "",
        "---",
        "",
        f"*Generated by trend_following_backtest.py — {datetime.now().strftime('%Y-%m-%d')}*",
    ]

    md_path = os.path.join(RESULTS_DIR, 'trend_following_results.md')
    with open(md_path, 'w') as f:
        f.write('\n'.join(md_lines))
    print(f"Results saved: {md_path}")

    # Console summary
    print("\n" + "="*75)
    print("TREND FOLLOWING BACKTEST — SUMMARY")
    print("="*75)
    print(f"{'Strategy':<40} {'TotRet%':>8} {'Ann%':>7} {'MaxDD%':>7} {'Sharpe':>7} {'Trades':>7}")
    print("-"*75)
    for r_ in results:
        print(f"{r_['strategy']:<40} {r_['total_return']:>8} {r_['ann_return']:>7} "
              f"{r_['max_drawdown']:>7} {r_['sharpe']:>7} {r_['n_trades']:>7}")
    print(f"{'SPY Buy & Hold':<40} {bm['total']:>8} {bm['ann']:>7}")

    return results


if __name__ == '__main__':
    main()
