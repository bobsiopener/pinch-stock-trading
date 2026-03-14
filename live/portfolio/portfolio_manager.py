#!/usr/bin/env python3
"""
Pinch Stock Trading Platform — Portfolio Manager (Production Grade)
Imaginary portfolio: real prices, no real money.

Usage:
    python3 portfolio_manager.py buy QQQ 10
    python3 portfolio_manager.py buy QQQ 10 --price 593.72
    python3 portfolio_manager.py sell QQQ 5
    python3 portfolio_manager.py status
    python3 portfolio_manager.py history [--symbol QQQ] [--date-from 2026-01-01] [--date-to 2026-03-14]
    python3 portfolio_manager.py performance
    python3 portfolio_manager.py snapshot
    python3 portfolio_manager.py rebalance --preview
    python3 portfolio_manager.py export [--format csv|json] [--out FILE]
    python3 portfolio_manager.py import-positions [--reset]
    python3 portfolio_manager.py signals
    python3 portfolio_manager.py risk

Rule of Acquisition #22: A wise man can hear profit in the wind.
"""

import sqlite3
import argparse
import sys
import os
import json
import csv
import io
import time
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────

PORTFOLIO_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../state/portfolio.db')
MARKET_DB    = '/mnt/media/market_data/pinch_market.db'

STARTING_CAPITAL = 500_000.00
COMMISSION       = 0.0          # imaginary portfolio, zero commission
PRICE_CACHE_TTL  = 300          # seconds (5 min)
PNL_METHOD       = 'avgcost'    # 'avgcost' | 'fifo'  (fifo not yet implemented)

# Sector map for holdings
SECTOR_MAP = {
    'QQQ':   'ETF-Tech',
    'NVDA':  'Semiconductors',
    'MSFT':  'Software',
    'GOOG':  'Communication',
    'BRK-B': 'Financials',
    'AVGO':  'Semiconductors',
    'GLD':   'Commodity',
    'TLT':   'Bonds',
    'PLTR':  'Software',
    'ANET':  'Networking',
    'SPY':   'ETF-Broad',
    'IWM':   'ETF-SmallCap',
    'AAPL':  'Technology',
    'AMZN':  'Consumer',
    'META':  'Communication',
    'TSLA':  'Auto',
}

INITIAL_POSITIONS = {
    'QQQ':   {'shares': 99,  'avg_cost': 604.90},
    'NVDA':  {'shares': 254, 'avg_cost': 177.19},
    'MSFT':  {'shares': 101, 'avg_cost': 392.74},
    'GOOG':  {'shares': 112, 'avg_cost': 311.43},
    'BRK-B': {'shares': 99,  'avg_cost': 502.67},
    'AVGO':  {'shares': 125, 'avg_cost': 319.55},
    'GLD':   {'shares': 124, 'avg_cost': 480.75},
    'TLT':   {'shares': 495, 'avg_cost':  90.80},
    'PLTR':  {'shares': 220, 'avg_cost': 135.94},
    'ANET':  {'shares': 191, 'avg_cost': 130.25},
}
# cash = 500000 - sum(shares * avg_cost) = 71530.11 (approx)

# In-process price cache: {symbol: (price, timestamp)}
_price_cache: Dict[str, Tuple[float, float]] = {}


# ─── Schema ──────────────────────────────────────────────────────────────────

NEW_SCHEMA = """
-- Core positions
CREATE TABLE IF NOT EXISTS positions (
    symbol          TEXT PRIMARY KEY,
    shares          REAL NOT NULL DEFAULT 0,
    avg_cost        REAL NOT NULL DEFAULT 0,
    first_buy_date  TEXT,
    last_trade_date TEXT,
    strategy        TEXT,
    sector          TEXT,
    notes           TEXT
);

-- All trades (immutable log)
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,   -- BUY | SELL
    shares      REAL NOT NULL,
    price       REAL NOT NULL,
    commission  REAL NOT NULL DEFAULT 0,
    realized_pnl REAL,          -- only on SELL
    timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
    strategy    TEXT,
    notes       TEXT
);

-- Time-series portfolio snapshots
CREATE TABLE IF NOT EXISTS snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL UNIQUE,
    total_value     REAL NOT NULL,
    cash            REAL NOT NULL,
    invested_value  REAL NOT NULL,
    positions_json  TEXT,
    metrics_json    TEXT
);

-- Target weights for rebalancing
CREATE TABLE IF NOT EXISTS targets (
    symbol          TEXT PRIMARY KEY,
    target_weight   REAL NOT NULL,  -- 0..1
    strategy        TEXT,
    notes           TEXT
);

-- KV state (cash, inception date, etc.)
CREATE TABLE IF NOT EXISTS portfolio_state (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO portfolio_state (key, value) VALUES ('cash', '500000.00');
INSERT OR IGNORE INTO portfolio_state (key, value) VALUES ('inception_date', date('now'));
INSERT OR IGNORE INTO portfolio_state (key, value) VALUES ('starting_capital', '500000.00');
"""


# ─── Database helpers ─────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    """Return a connection to the portfolio DB (row_factory enabled)."""
    os.makedirs(os.path.dirname(os.path.abspath(PORTFOLIO_DB)), exist_ok=True)
    conn = sqlite3.connect(PORTFOLIO_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Apply schema (idempotent)."""
    with get_conn() as conn:
        conn.executescript(NEW_SCHEMA)


def get_cash() -> float:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM portfolio_state WHERE key='cash'").fetchone()
        return float(row['value']) if row else STARTING_CAPITAL


def set_cash(amount: float):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO portfolio_state(key,value,updated_at) VALUES('cash',?,datetime('now'))",
            (str(round(amount, 4)),)
        )


# ─── Price fetching ───────────────────────────────────────────────────────────

def get_price_from_db(symbol: str) -> Optional[float]:
    """Fetch latest daily close from market DB."""
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            row = conn.execute(
                "SELECT close FROM prices WHERE symbol=? AND timeframe='1d' ORDER BY timestamp DESC LIMIT 1",
                (symbol.upper(),)
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def get_price_from_yfinance(symbol: str) -> Optional[float]:
    """Fallback: fetch latest price from Yahoo Finance."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='2d')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass
    return None


def get_price(symbol: str) -> Optional[float]:
    """
    Get latest price for symbol.
    Strategy:
      1. In-process cache (5 min TTL)
      2. Market DB (local SQLite)
      3. Yahoo Finance fallback
    """
    sym = symbol.upper()
    now = time.time()

    # Check cache
    if sym in _price_cache:
        price, ts = _price_cache[sym]
        if now - ts < PRICE_CACHE_TTL:
            return price

    # Try market DB
    price = get_price_from_db(sym)
    if price is not None:
        _price_cache[sym] = (price, now)
        return price

    # Fallback to yfinance
    print(f"  [price] {sym}: market DB miss, fetching from Yahoo Finance…")
    price = get_price_from_yfinance(sym)
    if price is not None:
        _price_cache[sym] = (price, now)
        return price

    return None


def get_prices_batch(symbols: List[str]) -> Dict[str, Optional[float]]:
    """Fetch prices for multiple symbols efficiently."""
    result = {}
    need_yf = []

    # Pull all from market DB in one query
    try:
        placeholders = ','.join('?' * len(symbols))
        with sqlite3.connect(MARKET_DB) as mconn:
            rows = mconn.execute(
                f"""SELECT symbol, close FROM prices
                    WHERE symbol IN ({placeholders}) AND timeframe='1d'
                    GROUP BY symbol HAVING timestamp=MAX(timestamp)""",
                [s.upper() for s in symbols]
            ).fetchall()
        db_prices = {r[0]: r[1] for r in rows}
    except Exception:
        db_prices = {}

    for sym in symbols:
        sym = sym.upper()
        if sym in _price_cache and time.time() - _price_cache[sym][1] < PRICE_CACHE_TTL:
            result[sym] = _price_cache[sym][0]
        elif sym in db_prices:
            result[sym] = db_prices[sym]
            _price_cache[sym] = (db_prices[sym], time.time())
        else:
            need_yf.append(sym)
            result[sym] = None

    # Batch yfinance fetch for misses
    if need_yf:
        try:
            import yfinance as yf
            tickers = yf.download(' '.join(need_yf), period='2d', progress=False, auto_adjust=True)
            if not tickers.empty:
                for sym in need_yf:
                    try:
                        if len(need_yf) == 1:
                            p = float(tickers['Close'].iloc[-1])
                        else:
                            p = float(tickers['Close'][sym].dropna().iloc[-1])
                        result[sym] = p
                        _price_cache[sym] = (p, time.time())
                    except Exception:
                        pass
        except Exception as e:
            print(f"  [price] yfinance batch failed: {e}")

    return result


# ─── Portfolio class ──────────────────────────────────────────────────────────

class Portfolio:
    def __init__(self):
        init_db()

    # ── Positions ─────────────────────────────────────────────────────────────

    def get_positions(self) -> List[sqlite3.Row]:
        with get_conn() as conn:
            return conn.execute("SELECT * FROM positions WHERE shares > 0 ORDER BY symbol").fetchall()

    def get_position(self, symbol: str) -> Optional[sqlite3.Row]:
        with get_conn() as conn:
            return conn.execute("SELECT * FROM positions WHERE symbol=?", (symbol.upper(),)).fetchone()

    # ── Buy ───────────────────────────────────────────────────────────────────

    def buy(self, symbol: str, shares: float, price: Optional[float] = None,
            strategy: str = '', notes: str = '', silent: bool = False) -> bool:
        symbol = symbol.upper()

        if price is None:
            price = get_price(symbol)
            if price is None:
                print(f"  ERROR: Cannot find price for {symbol}. Use --price to specify.")
                return False

        total_cost = shares * price + COMMISSION
        cash = get_cash()

        if total_cost > cash + 0.01:
            print(f"  ERROR: Insufficient cash. Need ${total_cost:,.2f}, have ${cash:,.2f}")
            return False

        now = datetime.now().isoformat(timespec='seconds')
        today = date.today().isoformat()

        with get_conn() as conn:
            existing = conn.execute("SELECT shares, avg_cost FROM positions WHERE symbol=?", (symbol,)).fetchone()

            if existing:
                old_shares = existing['shares']
                old_cost   = existing['avg_cost']
                new_shares  = old_shares + shares
                new_avg     = ((old_shares * old_cost) + (shares * price)) / new_shares
                conn.execute(
                    "UPDATE positions SET shares=?, avg_cost=?, last_trade_date=? WHERE symbol=?",
                    (new_shares, round(new_avg, 4), today, symbol)
                )
            else:
                sector = SECTOR_MAP.get(symbol, '')
                conn.execute(
                    """INSERT INTO positions(symbol, shares, avg_cost, first_buy_date, last_trade_date, strategy, sector)
                       VALUES(?,?,?,?,?,?,?)""",
                    (symbol, shares, round(price, 4), today, today, strategy, sector)
                )

            conn.execute(
                """INSERT INTO trades(symbol, side, shares, price, commission, timestamp, strategy, notes)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (symbol, 'BUY', shares, price, COMMISSION, now, strategy, notes)
            )

        set_cash(cash - total_cost)

        if not silent:
            print(f"  ✅ BUY  {shares:.4g} {symbol} @ ${price:.2f} = ${total_cost:,.2f}")
            print(f"     Cash remaining: ${cash - total_cost:,.2f}")
        return True

    # ── Sell ──────────────────────────────────────────────────────────────────

    def sell(self, symbol: str, shares: float, price: Optional[float] = None,
             strategy: str = '', notes: str = '') -> bool:
        symbol = symbol.upper()

        existing = self.get_position(symbol)
        if not existing:
            print(f"  ERROR: No position in {symbol}")
            return False
        if existing['shares'] < shares - 0.001:
            print(f"  ERROR: Cannot sell {shares} {symbol}; holding {existing['shares']:.4g}")
            return False

        if price is None:
            price = get_price(symbol)
            if price is None:
                print(f"  ERROR: Cannot find price for {symbol}. Use --price to specify.")
                return False

        proceeds     = shares * price - COMMISSION
        avg_cost     = existing['avg_cost']
        realized_pnl = (price - avg_cost) * shares
        pnl_pct      = ((price / avg_cost) - 1) * 100
        now          = datetime.now().isoformat(timespec='seconds')
        today        = date.today().isoformat()

        with get_conn() as conn:
            new_shares = existing['shares'] - shares
            if new_shares < 1e-6:
                conn.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
            else:
                conn.execute(
                    "UPDATE positions SET shares=?, last_trade_date=? WHERE symbol=?",
                    (round(new_shares, 6), today, symbol)
                )

            conn.execute(
                """INSERT INTO trades(symbol, side, shares, price, commission, realized_pnl, timestamp, strategy, notes)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (symbol, 'SELL', shares, price, COMMISSION, round(realized_pnl, 4), now, strategy, notes)
            )

        cash = get_cash()
        set_cash(cash + proceeds)

        sign = '+' if realized_pnl >= 0 else ''
        print(f"  ✅ SELL {shares:.4g} {symbol} @ ${price:.2f} = ${proceeds:,.2f}")
        print(f"     Realized P&L: {sign}${realized_pnl:,.2f} ({sign}{pnl_pct:.1f}%)  |  Cash: ${cash + proceeds:,.2f}")
        return True

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self, as_json: bool = False):
        """Full portfolio view with live prices, P&L, weights."""
        cash = get_cash()
        positions = self.get_positions()

        if not positions:
            if as_json:
                print(json.dumps({'cash': cash, 'positions': [], 'total_value': cash}))
                return
            print(f"\n{'═'*74}")
            print(f"  💰 PINCH PORTFOLIO  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print(f"  No positions. Cash: ${cash:,.2f}")
            print(f"{'═'*74}\n")
            return

        symbols = [p['symbol'] for p in positions]
        prices  = get_prices_batch(symbols)

        rows = []
        total_market = cash
        total_cost   = 0.0

        for p in positions:
            sym        = p['symbol']
            shares     = p['shares']
            avg_cost   = p['avg_cost']
            cur_price  = prices.get(sym) or avg_cost
            mkt_val    = shares * cur_price
            cost_basis = shares * avg_cost
            unreal_pnl = mkt_val - cost_basis
            pnl_pct    = ((cur_price / avg_cost) - 1) * 100
            total_market += mkt_val
            total_cost   += cost_basis
            rows.append({
                'symbol': sym, 'shares': shares, 'avg_cost': avg_cost,
                'price': cur_price, 'mkt_val': mkt_val,
                'unreal_pnl': unreal_pnl, 'pnl_pct': pnl_pct,
                'sector': p['sector'] or '',
            })

        # Add weight column
        for r in rows:
            r['weight'] = r['mkt_val'] / total_market * 100 if total_market else 0

        invested   = total_market - cash
        total_pnl  = total_market - STARTING_CAPITAL
        total_ret  = (total_market / STARTING_CAPITAL - 1) * 100

        if as_json:
            data = {
                'as_of': datetime.now().isoformat(timespec='seconds'),
                'total_value': round(total_market, 2),
                'cash': round(cash, 2),
                'invested': round(invested, 2),
                'total_pnl': round(total_pnl, 2),
                'total_return_pct': round(total_ret, 4),
                'positions': [
                    {
                        'symbol': r['symbol'], 'shares': r['shares'],
                        'avg_cost': r['avg_cost'], 'current_price': r['price'],
                        'market_value': round(r['mkt_val'], 2),
                        'unrealized_pnl': round(r['unreal_pnl'], 2),
                        'pnl_pct': round(r['pnl_pct'], 4),
                        'weight_pct': round(r['weight'], 4),
                        'sector': r['sector'],
                    }
                    for r in rows
                ]
            }
            print(json.dumps(data, indent=2))
            return

        W = 82
        print(f"\n{'═'*W}")
        print(f"  💰 PINCH PORTFOLIO  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═'*W}")
        print(f"  {'SYMBOL':<7} {'SHR':>7} {'AVG COST':>9} {'PRICE':>9} {'MKT VAL':>11} {'UNREAL P&L':>12} {'%':>7} {'WT%':>6}  SECTOR")
        print(f"  {'─'*77}")

        for r in rows:
            pnl_sign = '+' if r['unreal_pnl'] >= 0 else ''
            print(
                f"  {r['symbol']:<7} {r['shares']:>7.4g} {r['avg_cost']:>9.2f} {r['price']:>9.2f}"
                f" ${r['mkt_val']:>10,.0f} {pnl_sign}${r['unreal_pnl']:>10,.0f}"
                f" {r['pnl_pct']:>+6.1f}%  {r['weight']:>5.1f}%  {r['sector']}"
            )

        print(f"  {'─'*77}")
        cash_wt = cash / total_market * 100
        print(f"  {'CASH':<7} {'':>7} {'':>9} {'':>9} ${cash:>10,.0f} {'':>13} {'':>7}  {cash_wt:.1f}%")
        print(f"  {'TOTAL':<7} {'':>7} {'':>9} {'':>9} ${total_market:>10,.0f}")
        print(f"{'═'*W}")
        sign = '+' if total_pnl >= 0 else ''
        print(f"  Invested: ${invested:,.2f}  |  Cash: ${cash:,.2f}  |  Total P&L: {sign}${total_pnl:,.2f} ({sign}{total_ret:.2f}%)")
        print(f"{'═'*W}\n")

    # ── History ───────────────────────────────────────────────────────────────

    def history(self, symbol: Optional[str] = None, date_from: Optional[str] = None,
                date_to: Optional[str] = None, limit: int = 50, as_json: bool = False):
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        if symbol:
            query += " AND symbol=?"
            params.append(symbol.upper())
        if date_from:
            query += " AND timestamp >= ?"
            params.append(date_from)
        if date_to:
            query += " AND timestamp <= ?"
            params.append(date_to + ' 23:59:59')
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()

        if as_json:
            print(json.dumps([dict(r) for r in rows], indent=2))
            return

        if not rows:
            print("  No trades found matching filters.")
            return

        print(f"\n{'═'*80}")
        print(f"  📋 TRADE HISTORY  ({len(rows)} records)")
        print(f"{'═'*80}")
        print(f"  {'DATE':<19} {'SIDE':<5} {'SYMBOL':<7} {'SHARES':>8} {'PRICE':>9} {'TOTAL':>11} {'REALIZED P&L':>13}  NOTES")
        print(f"  {'─'*74}")

        for r in rows:
            pnl_str = ''
            if r['realized_pnl'] is not None:
                pnl_str = f"${r['realized_pnl']:+,.2f}"
            print(f"  {r['timestamp'][:19]:<19} {r['side']:<5} {r['symbol']:<7}"
                  f" {r['shares']:>8.4g} {r['price']:>9.2f}"
                  f" ${r['shares']*r['price']:>10,.2f} {pnl_str:>13}"
                  + (f"  {r['notes']}" if r['notes'] else ''))

        print(f"{'═'*80}\n")

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self, label: Optional[str] = None):
        """Save current portfolio state to snapshots table."""
        cash      = get_cash()
        positions = self.get_positions()
        symbols   = [p['symbol'] for p in positions]
        prices    = get_prices_batch(symbols) if symbols else {}

        invested = 0.0
        pos_data = {}
        for p in positions:
            sym       = p['symbol']
            cur_price = prices.get(sym) or p['avg_cost']
            mkt_val   = p['shares'] * cur_price
            invested += mkt_val
            pos_data[sym] = {
                'shares': p['shares'], 'avg_cost': p['avg_cost'],
                'price': cur_price, 'value': round(mkt_val, 2)
            }

        total   = cash + invested
        ret_pct = (total / STARTING_CAPITAL - 1) * 100

        metrics = {
            'total_return_pct': round(ret_pct, 4),
            'total_pnl': round(total - STARTING_CAPITAL, 2),
            'num_positions': len(positions),
        }

        ts = label or datetime.now().isoformat(timespec='seconds')
        with get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO snapshots(timestamp, total_value, cash, invested_value, positions_json, metrics_json)
                   VALUES(?,?,?,?,?,?)""",
                (ts, round(total, 2), round(cash, 2), round(invested, 2),
                 json.dumps(pos_data), json.dumps(metrics))
            )

        print(f"  📸 Snapshot saved: {ts}  |  ${total:,.2f} ({ret_pct:+.2f}%)")

    # ── Performance ───────────────────────────────────────────────────────────

    def performance(self, as_json: bool = False):
        """Delegate to analytics module for detailed metrics."""
        try:
            from analytics import PortfolioAnalytics
            pa = PortfolioAnalytics()
            pa.print_performance(as_json=as_json)
        except ImportError:
            # Fallback: basic performance
            cash      = get_cash()
            positions = self.get_positions()
            symbols   = [p['symbol'] for p in positions]
            prices    = get_prices_batch(symbols) if symbols else {}

            total = cash
            for p in positions:
                total += p['shares'] * (prices.get(p['symbol']) or p['avg_cost'])

            pnl     = total - STARTING_CAPITAL
            ret_pct = (total / STARTING_CAPITAL - 1) * 100

            with get_conn() as conn:
                state = dict(conn.execute("SELECT key, value FROM portfolio_state").fetchall())

            data = {
                'inception_date':   state.get('inception_date', '?'),
                'starting_capital': STARTING_CAPITAL,
                'current_value':    round(total, 2),
                'total_pnl':        round(pnl, 2),
                'total_return_pct': round(ret_pct, 4),
            }

            if as_json:
                print(json.dumps(data, indent=2))
                return

            print(f"\n{'═'*55}")
            print(f"  📊 PERFORMANCE SUMMARY")
            print(f"{'═'*55}")
            print(f"  Inception date:    {data['inception_date']}")
            print(f"  Starting capital:  ${STARTING_CAPITAL:>14,.2f}")
            print(f"  Current value:     ${total:>14,.2f}")
            sign = '+' if pnl >= 0 else ''
            print(f"  Total P&L:         {sign}${pnl:>13,.2f}")
            print(f"  Total return:      {sign}{ret_pct:.2f}%")
            print(f"{'═'*55}\n")
            print("  (Run analytics.py for full metrics)")

    # ── Signals ───────────────────────────────────────────────────────────────

    def signals(self, as_json: bool = False):
        """Show signal dashboard (delegates to analytics)."""
        try:
            from analytics import PortfolioAnalytics
            pa = PortfolioAnalytics()
            pa.print_signals(as_json=as_json)
        except ImportError as e:
            print(f"  analytics.py required for signals: {e}")

    # ── Risk ──────────────────────────────────────────────────────────────────

    def risk(self, as_json: bool = False):
        """Show risk analysis (delegates to analytics)."""
        try:
            from analytics import PortfolioAnalytics
            pa = PortfolioAnalytics()
            pa.print_risk(as_json=as_json)
        except ImportError as e:
            print(f"  analytics.py required for risk: {e}")

    # ── Rebalance ─────────────────────────────────────────────────────────────

    def rebalance(self, preview: bool = True):
        """Show what trades are needed to reach target weights."""
        with get_conn() as conn:
            targets = conn.execute("SELECT * FROM targets").fetchall()

        if not targets:
            print("  No target weights set. Use `targets` table to define them.")
            return

        cash      = get_cash()
        positions = self.get_positions()
        symbols   = list(set([p['symbol'] for p in positions] + [t['symbol'] for t in targets]))
        prices    = get_prices_batch(symbols)

        total = cash
        for p in positions:
            total += p['shares'] * (prices.get(p['symbol']) or p['avg_cost'])

        pos_map = {p['symbol']: p for p in positions}

        print(f"\n{'═'*72}")
        print(f"  ⚖️  REBALANCE PREVIEW  |  Portfolio: ${total:,.2f}")
        print(f"{'═'*72}")
        print(f"  {'SYMBOL':<8} {'CUR VAL':>10} {'CUR WT%':>8} {'TGT WT%':>8} {'DIFF':>10} {'ACTION'}")
        print(f"  {'─'*66}")

        for t in sorted(targets, key=lambda x: x['symbol']):
            sym    = t['symbol']
            tgt_wt = t['target_weight']
            price  = prices.get(sym) or 0
            p      = pos_map.get(sym)
            cur_val = (p['shares'] * price) if p and price else 0
            cur_wt  = cur_val / total if total else 0
            tgt_val = tgt_wt * total
            diff    = tgt_val - cur_val

            if price and abs(diff) > 1:
                shares_delta = diff / price
                action = f"BUY {shares_delta:+.1f} shrs" if diff > 0 else f"SELL {-shares_delta:.1f} shrs"
            else:
                action = 'HOLD'

            print(f"  {sym:<8} ${cur_val:>9,.0f} {cur_wt*100:>7.1f}% {tgt_wt*100:>7.1f}%"
                  f" ${diff:>+9,.0f}  {action}")

        print(f"{'═'*72}")
        if preview:
            print("  [Preview only — no trades executed]")
        print()

    # ── Export ────────────────────────────────────────────────────────────────

    def export(self, fmt: str = 'json', out: Optional[str] = None):
        """Export portfolio state and trade history."""
        cash      = get_cash()
        positions = self.get_positions()
        symbols   = [p['symbol'] for p in positions]
        prices    = get_prices_batch(symbols) if symbols else {}

        with get_conn() as conn:
            trades = conn.execute("SELECT * FROM trades ORDER BY timestamp").fetchall()

        pos_data = []
        for p in positions:
            price   = prices.get(p['symbol']) or p['avg_cost']
            mkt_val = p['shares'] * price
            pos_data.append({
                'symbol':         p['symbol'],
                'shares':         p['shares'],
                'avg_cost':       p['avg_cost'],
                'current_price':  price,
                'market_value':   round(mkt_val, 2),
                'unrealized_pnl': round(mkt_val - p['shares'] * p['avg_cost'], 2),
                'first_buy_date': p['first_buy_date'],
                'sector':         p['sector'],
                'strategy':       p['strategy'],
            })

        trade_data = [dict(t) for t in trades]

        if fmt == 'json':
            data = {
                'as_of': datetime.now().isoformat(timespec='seconds'),
                'cash': round(cash, 2),
                'positions': pos_data,
                'trades': trade_data,
            }
            out_str = json.dumps(data, indent=2)
        else:
            # CSV — positions sheet
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=pos_data[0].keys() if pos_data else [])
            writer.writeheader()
            writer.writerows(pos_data)
            out_str = buf.getvalue()

        if out:
            Path(out).write_text(out_str)
            print(f"  Exported to {out}")
        else:
            print(out_str)

    # ── Import positions ──────────────────────────────────────────────────────

    def import_positions(self, positions_dict: Optional[Dict] = None,
                         cash_override: Optional[float] = None,
                         reset: bool = False, silent: bool = False):
        """
        Import a set of positions (e.g. INITIAL_POSITIONS) directly into the DB.
        Does NOT deduct cash — sets cash explicitly via cash_override.
        """
        if positions_dict is None:
            positions_dict = INITIAL_POSITIONS

        if reset:
            with get_conn() as conn:
                conn.execute("DELETE FROM positions")
                conn.execute("DELETE FROM trades")
                conn.execute("DELETE FROM snapshots")
            set_cash(STARTING_CAPITAL)
            if not silent:
                print("  ⚠️  Portfolio reset to empty.")

        today = date.today().isoformat()
        now   = datetime.now().isoformat(timespec='seconds')
        imported = []

        with get_conn() as conn:
            for sym, info in positions_dict.items():
                sym    = sym.upper()
                shares = info['shares']
                cost   = info['avg_cost']
                sector = SECTOR_MAP.get(sym, '')

                conn.execute(
                    """INSERT OR REPLACE INTO positions
                       (symbol, shares, avg_cost, first_buy_date, last_trade_date, sector, notes)
                       VALUES(?,?,?,?,?,?,'imported')""",
                    (sym, shares, cost, today, today, sector)
                )
                conn.execute(
                    """INSERT INTO trades(symbol, side, shares, price, commission, timestamp, notes)
                       VALUES(?,?,?,?,?,?,'import')""",
                    (sym, 'BUY', shares, cost, 0.0, now)
                )
                imported.append((sym, shares, cost))

        # Compute cash from initial capital minus cost of all imports
        if cash_override is not None:
            set_cash(cash_override)
        else:
            total_cost = sum(s * c for _, s, c in imported)
            set_cash(STARTING_CAPITAL - total_cost)

        if not silent:
            print(f"  ✅ Imported {len(imported)} positions:")
            for sym, shares, cost in imported:
                print(f"     {sym:<8} {shares:>6.0f} shares @ ${cost:.2f}")
            cash = get_cash()
            print(f"  💵 Cash set to: ${cash:,.2f}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='💰 Pinch Portfolio Manager — Rule #22: A wise man can hear profit in the wind.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    sub = parser.add_subparsers(dest='cmd', metavar='COMMAND')

    # buy
    p = sub.add_parser('buy', help='Buy shares')
    p.add_argument('symbol'); p.add_argument('shares', type=float)
    p.add_argument('--price', type=float); p.add_argument('--strategy', default='')
    p.add_argument('--notes', default='')

    # sell
    p = sub.add_parser('sell', help='Sell shares')
    p.add_argument('symbol'); p.add_argument('shares', type=float)
    p.add_argument('--price', type=float); p.add_argument('--strategy', default='')
    p.add_argument('--notes', default='')

    # status
    sub.add_parser('status', help='Full portfolio view with live prices and P&L')

    # history
    p = sub.add_parser('history', help='Trade history')
    p.add_argument('--symbol'); p.add_argument('--date-from'); p.add_argument('--date-to')
    p.add_argument('--limit', type=int, default=50)

    # performance
    sub.add_parser('performance', help='Performance metrics')

    # snapshot
    p = sub.add_parser('snapshot', help='Save portfolio snapshot')
    p.add_argument('--label', default=None)

    # rebalance
    p = sub.add_parser('rebalance', help='Rebalance preview')
    p.add_argument('--preview', action='store_true', default=True)

    # export
    p = sub.add_parser('export', help='Export portfolio to CSV or JSON')
    p.add_argument('--format', choices=['json', 'csv'], default='json')
    p.add_argument('--out', default=None)

    # import-positions
    p = sub.add_parser('import-positions', help='Import initial positions')
    p.add_argument('--reset', action='store_true', help='Clear existing data first')
    p.add_argument('--cash', type=float, default=None, help='Override cash balance')

    # signals
    sub.add_parser('signals', help='Strategy signal dashboard')

    # risk
    sub.add_parser('risk', help='Risk analysis')

    # init
    sub.add_parser('init', help='Initialize / migrate database')

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    portfolio = Portfolio()
    as_json   = args.json

    if args.cmd == 'buy':
        portfolio.buy(args.symbol, args.shares, args.price, args.strategy, args.notes)

    elif args.cmd == 'sell':
        portfolio.sell(args.symbol, args.shares, args.price, args.strategy, args.notes)

    elif args.cmd == 'status':
        portfolio.status(as_json=as_json)

    elif args.cmd == 'history':
        portfolio.history(args.symbol, args.date_from, args.date_to, args.limit, as_json=as_json)

    elif args.cmd == 'performance':
        portfolio.performance(as_json=as_json)

    elif args.cmd == 'snapshot':
        portfolio.snapshot(args.label)

    elif args.cmd == 'rebalance':
        portfolio.rebalance(preview=True)

    elif args.cmd == 'export':
        portfolio.export(fmt=args.format, out=args.out)

    elif args.cmd == 'import-positions':
        portfolio.import_positions(reset=args.reset, cash_override=args.cash)

    elif args.cmd == 'signals':
        portfolio.signals(as_json=as_json)

    elif args.cmd == 'risk':
        portfolio.risk(as_json=as_json)

    elif args.cmd == 'init':
        print("  Database initialized/migrated.")


if __name__ == '__main__':
    main()
