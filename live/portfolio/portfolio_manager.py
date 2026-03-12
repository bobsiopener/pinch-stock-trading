"""
Pinch Stock Trading Platform — Portfolio Manager
Imaginary portfolio: real prices, no real money.

Usage:
    python3 portfolio_manager.py buy AAPL 50
    python3 portfolio_manager.py buy AAPL 50 --price 195.50 --reason "Momentum entry"
    python3 portfolio_manager.py sell AAPL 25
    python3 portfolio_manager.py status
    python3 portfolio_manager.py history
    python3 portfolio_manager.py performance
    python3 portfolio_manager.py snapshot

Rule of Acquisition #22: A wise man can hear profit in the wind.
"""

import sqlite3
import argparse
import sys
import os
from datetime import datetime, date
from typing import Optional

# Portfolio database (separate from market data)
PORTFOLIO_DB = os.path.join(os.path.dirname(__file__), '../../state/portfolio.db')
MARKET_DB = '/mnt/media/market_data/pinch_market.db'

STARTING_CAPITAL = 500_000.00
BENCHMARKS = ['SPY', 'QQQ']
COMMISSION = 0.0  # Imaginary portfolio, zero commission


# ─── Database Setup ──────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL UNIQUE,
    shares      REAL NOT NULL DEFAULT 0,
    avg_cost    REAL NOT NULL DEFAULT 0,
    sector      TEXT,
    strategy    TEXT,  -- which strategy sourced this position
    notes       TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
    symbol      TEXT NOT NULL,
    action      TEXT NOT NULL,  -- BUY, SELL, DIVIDEND
    shares      REAL NOT NULL,
    price       REAL NOT NULL,
    commission  REAL NOT NULL DEFAULT 0,
    total_value REAL NOT NULL,
    reason      TEXT,
    strategy    TEXT
);

CREATE TABLE IF NOT EXISTS daily_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date   TEXT NOT NULL UNIQUE,
    portfolio_value REAL NOT NULL,
    cash            REAL NOT NULL,
    invested_value  REAL NOT NULL,
    daily_pnl       REAL,
    daily_return    REAL,
    cumulative_return REAL,
    spy_daily       REAL,
    qqq_daily       REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portfolio_state (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Initialize state if not exists
INSERT OR IGNORE INTO portfolio_state (key, value) VALUES ('cash', '500000.00');
INSERT OR IGNORE INTO portfolio_state (key, value) VALUES ('inception_date', date('now'));
INSERT OR IGNORE INTO portfolio_state (key, value) VALUES ('starting_capital', '500000.00');
"""


def get_portfolio_conn() -> sqlite3.Connection:
    """Get connection to portfolio database."""
    os.makedirs(os.path.dirname(os.path.abspath(PORTFOLIO_DB)), exist_ok=True)
    conn = sqlite3.connect(PORTFOLIO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the portfolio database schema."""
    with get_portfolio_conn() as conn:
        conn.executescript(SCHEMA)
    print(f"[portfolio] Database initialized at {PORTFOLIO_DB}")


def get_market_price(symbol: str) -> Optional[float]:
    """Look up the latest price from the market database."""
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            row = conn.execute(
                "SELECT close FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                (symbol.upper(),)
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"[portfolio] Warning: Could not fetch price for {symbol}: {e}")
        return None


def get_cash() -> float:
    """Get current cash balance."""
    with get_portfolio_conn() as conn:
        row = conn.execute("SELECT value FROM portfolio_state WHERE key = 'cash'").fetchone()
        return float(row['value']) if row else STARTING_CAPITAL


def set_cash(amount: float):
    """Update cash balance."""
    with get_portfolio_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO portfolio_state (key, value, updated_at) VALUES ('cash', ?, datetime('now'))",
            (str(amount),)
        )


# ─── Portfolio Operations ────────────────────────────────────────────────────

class Portfolio:
    """Imaginary stock portfolio backed by SQLite."""

    def __init__(self):
        init_db()

    def buy(self, symbol: str, shares: float, price: Optional[float] = None,
            reason: str = '', strategy: str = '', sector: str = ''):
        """
        Buy shares of a stock.

        Args:
            symbol: Ticker symbol
            shares: Number of shares to buy
            price: Price per share (auto-lookup if None)
            reason: Trade rationale
            strategy: Source strategy (momentum, value, etc.)
            sector: Sector classification
        """
        symbol = symbol.upper()

        if price is None:
            price = get_market_price(symbol)
            if price is None:
                print(f"[portfolio] ERROR: Could not find price for {symbol}. Use --price to specify.")
                return

        total_cost = shares * price + COMMISSION
        cash = get_cash()

        if total_cost > cash:
            print(f"[portfolio] ERROR: Insufficient cash. Need ${total_cost:,.2f}, have ${cash:,.2f}")
            return

        with get_portfolio_conn() as conn:
            # Check existing position
            existing = conn.execute(
                "SELECT shares, avg_cost FROM holdings WHERE symbol = ?", (symbol,)
            ).fetchone()

            if existing:
                # Average down/up
                old_shares = existing['shares']
                old_cost = existing['avg_cost']
                new_shares = old_shares + shares
                new_avg_cost = ((old_shares * old_cost) + (shares * price)) / new_shares
                conn.execute(
                    """UPDATE holdings SET shares = ?, avg_cost = ?, updated_at = datetime('now')
                       WHERE symbol = ?""",
                    (new_shares, new_avg_cost, symbol)
                )
            else:
                conn.execute(
                    """INSERT INTO holdings (symbol, shares, avg_cost, sector, strategy)
                       VALUES (?, ?, ?, ?, ?)""",
                    (symbol, shares, price, sector, strategy)
                )

            # Log transaction
            conn.execute(
                """INSERT INTO transactions (symbol, action, shares, price, commission, total_value, reason, strategy)
                   VALUES (?, 'BUY', ?, ?, ?, ?, ?, ?)""",
                (symbol, shares, price, COMMISSION, total_cost, reason, strategy)
            )

        # Update cash
        set_cash(cash - total_cost)

        print(f"[portfolio] ✅ BUY  {shares:.0f} {symbol} @ ${price:.2f} = ${total_cost:,.2f}")
        print(f"[portfolio]    Cash remaining: ${cash - total_cost:,.2f}")

    def sell(self, symbol: str, shares: float, price: Optional[float] = None,
             reason: str = '', strategy: str = ''):
        """
        Sell shares of a stock.

        Args:
            symbol: Ticker symbol
            shares: Number of shares to sell (use 'all' logic via shares=-1)
            price: Price per share (auto-lookup if None)
            reason: Trade rationale
        """
        symbol = symbol.upper()

        with get_portfolio_conn() as conn:
            existing = conn.execute(
                "SELECT shares, avg_cost FROM holdings WHERE symbol = ?", (symbol,)
            ).fetchone()

            if not existing or existing['shares'] < shares:
                held = existing['shares'] if existing else 0
                print(f"[portfolio] ERROR: Cannot sell {shares} {symbol}, only holding {held:.0f} shares")
                return

            if price is None:
                price = get_market_price(symbol)
                if price is None:
                    print(f"[portfolio] ERROR: Could not find price for {symbol}. Use --price to specify.")
                    return

            proceeds = shares * price - COMMISSION
            avg_cost = existing['avg_cost']
            pnl = (price - avg_cost) * shares
            pnl_pct = ((price / avg_cost) - 1) * 100

            new_shares = existing['shares'] - shares
            if new_shares < 0.001:
                conn.execute("DELETE FROM holdings WHERE symbol = ?", (symbol,))
            else:
                conn.execute(
                    "UPDATE holdings SET shares = ?, updated_at = datetime('now') WHERE symbol = ?",
                    (new_shares, symbol)
                )

            conn.execute(
                """INSERT INTO transactions (symbol, action, shares, price, commission, total_value, reason, strategy)
                   VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?)""",
                (symbol, shares, price, COMMISSION, proceeds, reason, strategy)
            )

        cash = get_cash()
        set_cash(cash + proceeds)

        pnl_sign = "+" if pnl >= 0 else ""
        print(f"[portfolio] ✅ SELL {shares:.0f} {symbol} @ ${price:.2f} = ${proceeds:,.2f}")
        print(f"[portfolio]    P&L: {pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.1f}%) | Cash: ${cash + proceeds:,.2f}")

    def status(self):
        """Print current portfolio status."""
        cash = get_cash()

        with get_portfolio_conn() as conn:
            holdings = conn.execute("SELECT * FROM holdings ORDER BY symbol").fetchall()

        if not holdings:
            print(f"\n{'='*60}")
            print(f"  PINCH STOCK PORTFOLIO — No positions")
            print(f"  Cash: ${cash:,.2f}")
            print(f"{'='*60}\n")
            return

        total_value = cash
        rows = []

        for h in holdings:
            symbol = h['symbol']
            shares = h['shares']
            avg_cost = h['avg_cost']
            current_price = get_market_price(symbol) or avg_cost
            market_value = shares * current_price
            pnl = market_value - (shares * avg_cost)
            pnl_pct = ((current_price / avg_cost) - 1) * 100
            total_value += market_value
            rows.append({
                'symbol': symbol,
                'shares': shares,
                'avg_cost': avg_cost,
                'price': current_price,
                'value': market_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
            })

        invested = total_value - cash
        inception_return = ((total_value / STARTING_CAPITAL) - 1) * 100

        print(f"\n{'='*72}")
        print(f"  PINCH STOCK PORTFOLIO  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*72}")
        print(f"  {'SYMBOL':<8} {'SHARES':>8} {'AVG COST':>10} {'PRICE':>10} {'VALUE':>12} {'P&L':>12} {'%':>7}")
        print(f"  {'-'*68}")

        for r in rows:
            pnl_str = f"${r['pnl']:+,.0f}"
            pct_str = f"{r['pnl_pct']:+.1f}%"
            weight = (r['value'] / total_value) * 100
            print(f"  {r['symbol']:<8} {r['shares']:>8.0f} {r['avg_cost']:>10.2f} {r['price']:>10.2f} "
                  f"${r['value']:>11,.0f} {pnl_str:>12} {pct_str:>7}  ({weight:.1f}%)")

        print(f"  {'-'*68}")
        print(f"  {'CASH':<8} {'':>8} {'':>10} {'':>10} ${cash:>11,.0f}")
        print(f"  {'TOTAL':<8} {'':>8} {'':>10} {'':>10} ${total_value:>11,.0f}")
        print(f"{'='*72}")
        print(f"  Invested: ${invested:,.2f}  |  Cash: ${cash:,.2f}  |  Inception: {inception_return:+.2f}%")
        print(f"{'='*72}\n")

    def history(self, limit: int = 20):
        """Print recent transaction history."""
        with get_portfolio_conn() as conn:
            txns = conn.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()

        print(f"\n{'='*72}")
        print(f"  TRANSACTION HISTORY (last {limit})")
        print(f"{'='*72}")
        print(f"  {'DATE':<20} {'ACTION':<6} {'SYMBOL':<8} {'SHARES':>8} {'PRICE':>10} {'TOTAL':>12}")
        print(f"  {'-'*68}")

        for t in txns:
            print(f"  {t['timestamp'][:19]:<20} {t['action']:<6} {t['symbol']:<8} "
                  f"{t['shares']:>8.0f} {t['price']:>10.2f} ${t['total_value']:>11,.2f}"
                  + (f"  [{t['reason']}]" if t['reason'] else ""))

        print(f"{'='*72}\n")

    def performance(self):
        """Print performance summary."""
        cash = get_cash()

        with get_portfolio_conn() as conn:
            holdings = conn.execute("SELECT * FROM holdings").fetchall()
            state = conn.execute("SELECT key, value FROM portfolio_state").fetchall()
            snapshots = conn.execute(
                "SELECT * FROM daily_snapshots ORDER BY snapshot_date DESC LIMIT 30"
            ).fetchall()

        state_dict = {r['key']: r['value'] for r in state}
        inception_date = state_dict.get('inception_date', 'Unknown')

        total_invested = 0
        total_value = cash
        for h in holdings:
            price = get_market_price(h['symbol']) or h['avg_cost']
            market_val = h['shares'] * price
            total_value += market_val
            total_invested += h['shares'] * h['avg_cost']

        total_pnl = total_value - STARTING_CAPITAL
        total_return = ((total_value / STARTING_CAPITAL) - 1) * 100

        print(f"\n{'='*60}")
        print(f"  PORTFOLIO PERFORMANCE")
        print(f"{'='*60}")
        print(f"  Inception:       {inception_date}")
        print(f"  Starting Capital: ${STARTING_CAPITAL:>12,.2f}")
        print(f"  Current Value:    ${total_value:>12,.2f}")
        print(f"  Total P&L:        ${total_pnl:>+12,.2f}")
        print(f"  Total Return:     {total_return:>+12.2f}%")
        print(f"{'='*60}\n")

    def snapshot(self):
        """Take a daily portfolio snapshot (called by systemd timer)."""
        today = date.today().isoformat()
        cash = get_cash()

        with get_portfolio_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM daily_snapshots WHERE snapshot_date = ?", (today,)
            ).fetchone()
            if existing:
                print(f"[portfolio] Snapshot already exists for {today}")
                return

            holdings = conn.execute("SELECT * FROM holdings").fetchall()

        invested_value = 0
        for h in holdings:
            price = get_market_price(h['symbol']) or h['avg_cost']
            invested_value += h['shares'] * price

        portfolio_value = cash + invested_value
        cumulative_return = ((portfolio_value / STARTING_CAPITAL) - 1) * 100

        with get_portfolio_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO daily_snapshots
                   (snapshot_date, portfolio_value, cash, invested_value, cumulative_return)
                   VALUES (?, ?, ?, ?, ?)""",
                (today, portfolio_value, cash, invested_value, cumulative_return)
            )

        print(f"[portfolio] 📸 Snapshot {today}: ${portfolio_value:,.2f} ({cumulative_return:+.2f}%)")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Pinch Stock Portfolio Manager')
    subparsers = parser.add_subparsers(dest='command')

    # buy
    buy_p = subparsers.add_parser('buy', help='Buy shares')
    buy_p.add_argument('symbol', type=str)
    buy_p.add_argument('shares', type=float)
    buy_p.add_argument('--price', type=float, default=None)
    buy_p.add_argument('--reason', type=str, default='')
    buy_p.add_argument('--strategy', type=str, default='')
    buy_p.add_argument('--sector', type=str, default='')

    # sell
    sell_p = subparsers.add_parser('sell', help='Sell shares')
    sell_p.add_argument('symbol', type=str)
    sell_p.add_argument('shares', type=float)
    sell_p.add_argument('--price', type=float, default=None)
    sell_p.add_argument('--reason', type=str, default='')

    # status
    subparsers.add_parser('status', help='Show current positions')

    # history
    hist_p = subparsers.add_parser('history', help='Show transaction history')
    hist_p.add_argument('--limit', type=int, default=20)

    # performance
    subparsers.add_parser('performance', help='Show performance summary')

    # snapshot
    subparsers.add_parser('snapshot', help='Take daily snapshot')

    # init
    subparsers.add_parser('init', help='Initialize portfolio database')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    p = Portfolio()

    if args.command == 'buy':
        p.buy(args.symbol, args.shares, args.price, args.reason, args.strategy, args.sector)
    elif args.command == 'sell':
        p.sell(args.symbol, args.shares, args.price, args.reason)
    elif args.command == 'status':
        p.status()
    elif args.command == 'history':
        p.history(args.limit)
    elif args.command == 'performance':
        p.performance()
    elif args.command == 'snapshot':
        p.snapshot()
    elif args.command == 'init':
        print("[portfolio] Database initialized.")


if __name__ == '__main__':
    main()
