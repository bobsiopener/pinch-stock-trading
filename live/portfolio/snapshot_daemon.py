#!/usr/bin/env python3
"""
Pinch Stock Trading Platform — Portfolio Snapshot Daemon
Captures portfolio state over time for performance tracking and alerting.

Usage:
    python3 snapshot_daemon.py take             — take one snapshot now
    python3 snapshot_daemon.py history          — show snapshot history
    python3 snapshot_daemon.py history --days 7 — last 7 days
    python3 snapshot_daemon.py chart            — ASCII chart of portfolio value
    python3 snapshot_daemon.py export           — CSV export of snapshots

Rule of Acquisition #22: A wise man can hear profit in the wind.
"""

import sqlite3
import argparse
import sys
import os
import csv
import json
from datetime import datetime, timedelta
from typing import Optional

# ─── Paths ───────────────────────────────────────────────────────────────────

PORTFOLIO_DB = os.path.join(os.path.dirname(__file__), '../../state/portfolio.db')
MARKET_DB    = '/mnt/media/market_data/pinch_market.db'
STARTING_CAPITAL = 500_000.00

# Sector mapping for concentration warnings
TECH_SYMBOLS = {'QQQ', 'NVDA', 'MSFT', 'AVGO', 'GOOG', 'ANET', 'PLTR', 'AMD', 'AAPL', 'META', 'AMZN', 'TSM', 'ASML', 'MU'}

# ─── Schema ──────────────────────────────────────────────────────────────────

SNAPSHOTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT NOT NULL DEFAULT (datetime('now')),
    total_value       REAL NOT NULL,
    cash              REAL NOT NULL,
    invested          REAL NOT NULL,
    num_positions     INTEGER NOT NULL DEFAULT 0,
    daily_return      REAL,
    cumulative_return REAL,
    max_drawdown      REAL,
    positions_json    TEXT
);
"""


# ─── DB Helpers ──────────────────────────────────────────────────────────────

def get_portfolio_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(PORTFOLIO_DB)), exist_ok=True)
    conn = sqlite3.connect(PORTFOLIO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_snapshots_table():
    with get_portfolio_conn() as conn:
        conn.executescript(SNAPSHOTS_SCHEMA)


def get_market_price(symbol: str) -> Optional[float]:
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            row = conn.execute(
                "SELECT close FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                (symbol.upper(),)
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"[snapshot] Warning: Could not fetch price for {symbol}: {e}", file=sys.stderr)
        return None


def get_cash() -> float:
    with get_portfolio_conn() as conn:
        row = conn.execute("SELECT value FROM portfolio_state WHERE key = 'cash'").fetchone()
        return float(row['value']) if row else STARTING_CAPITAL


def get_holdings() -> list[dict]:
    with get_portfolio_conn() as conn:
        rows = conn.execute("SELECT symbol, shares, avg_cost, sector FROM holdings ORDER BY symbol").fetchall()
        return [dict(r) for r in rows]


def get_previous_snapshot() -> Optional[dict]:
    with get_portfolio_conn() as conn:
        row = conn.execute(
            "SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_all_snapshots(days: Optional[int] = None) -> list[dict]:
    with get_portfolio_conn() as conn:
        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                "SELECT * FROM snapshots WHERE timestamp >= ? ORDER BY timestamp ASC",
                (cutoff,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM snapshots ORDER BY timestamp ASC"
            ).fetchall()
        return [dict(r) for r in rows]


# ─── Alerting ────────────────────────────────────────────────────────────────

def run_alerts(total_value: float, cash: float, daily_return: Optional[float],
               cumulative_return: float, max_drawdown: float,
               positions: dict, prev_snapshot: Optional[dict]):
    """Check thresholds and print warnings."""
    alerts = []

    # Daily drawdown alert (> 2%)
    if daily_return is not None and daily_return < -2.0:
        alerts.append(f"⚠️  WARNING: Daily drawdown {daily_return:.2f}% exceeds -2% threshold")

    # Total drawdown alert (> 10%)
    if max_drawdown < -10.0:
        alerts.append(f"🚨 CRITICAL: Max drawdown {max_drawdown:.2f}% exceeds -10% threshold")

    # Position concentration (> 15% weight)
    for symbol, pos in positions.items():
        if pos['weight'] > 15.0:
            alerts.append(f"⚠️  CONCENTRATION: {symbol} is {pos['weight']:.1f}% of portfolio (>15%)")

    # Tech sector concentration (> 40%)
    tech_weight = sum(
        pos['weight'] for sym, pos in positions.items()
        if sym.upper() in TECH_SYMBOLS
    )
    if tech_weight > 40.0:
        alerts.append(f"⚠️  SECTOR WARNING: Tech sector is {tech_weight:.1f}% of portfolio (>40%)")

    if alerts:
        print()
        for alert in alerts:
            print(f"  {alert}")
        print()

    return alerts


# ─── Core Snapshot Logic ─────────────────────────────────────────────────────

def take_snapshot(verbose: bool = True) -> dict:
    """Capture current portfolio state and store in snapshots table."""
    ensure_snapshots_table()

    cash = get_cash()
    holdings = get_holdings()
    prev = get_previous_snapshot()

    positions = {}
    invested = 0.0

    for h in holdings:
        symbol = h['symbol']
        shares = h['shares']
        avg_cost = h['avg_cost']
        current_price = get_market_price(symbol) or avg_cost
        value = shares * current_price
        invested += value

        positions[symbol] = {
            'shares': shares,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'value': value,
            'weight': 0.0,   # filled below
            'pnl': value - (shares * avg_cost),
            'pnl_pct': ((current_price / avg_cost) - 1) * 100 if avg_cost else 0.0,
        }

    total_value = cash + invested

    # Weights (as % of total portfolio including cash)
    for sym in positions:
        positions[sym]['weight'] = (positions[sym]['value'] / total_value * 100) if total_value else 0.0

    # Returns
    cumulative_return = ((total_value / STARTING_CAPITAL) - 1) * 100

    daily_return = None
    if prev:
        prev_value = prev['total_value']
        daily_return = ((total_value / prev_value) - 1) * 100 if prev_value else 0.0

    # Max drawdown: scan all historical snapshots
    all_snaps = get_all_snapshots()
    peak = STARTING_CAPITAL
    max_drawdown = 0.0
    for s in all_snaps:
        if s['total_value'] > peak:
            peak = s['total_value']
        dd = ((s['total_value'] / peak) - 1) * 100
        if dd < max_drawdown:
            max_drawdown = dd
    # Also check current value vs historical peak
    if total_value > peak:
        peak = total_value
    current_dd = ((total_value / peak) - 1) * 100
    if current_dd < max_drawdown:
        max_drawdown = current_dd

    ts = datetime.now().isoformat(timespec='seconds')
    positions_json = json.dumps(positions)

    with get_portfolio_conn() as conn:
        conn.execute(
            """INSERT INTO snapshots
               (timestamp, total_value, cash, invested, num_positions,
                daily_return, cumulative_return, max_drawdown, positions_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts, total_value, cash, invested, len(holdings),
             daily_return, cumulative_return, max_drawdown, positions_json)
        )

    snap = {
        'timestamp': ts,
        'total_value': total_value,
        'cash': cash,
        'invested': invested,
        'num_positions': len(holdings),
        'daily_return': daily_return,
        'cumulative_return': cumulative_return,
        'max_drawdown': max_drawdown,
        'positions': positions,
    }

    if verbose:
        dr_str = f"{daily_return:+.2f}%" if daily_return is not None else "N/A"
        print(f"\n📸 Snapshot taken: {ts}")
        print(f"   Total Value:    ${total_value:>13,.2f}")
        print(f"   Cash:           ${cash:>13,.2f}")
        print(f"   Invested:       ${invested:>13,.2f}")
        print(f"   Positions:      {len(holdings)}")
        print(f"   Daily Return:   {dr_str}")
        print(f"   Cumul. Return:  {cumulative_return:+.2f}%")
        print(f"   Max Drawdown:   {max_drawdown:.2f}%")

        run_alerts(total_value, cash, daily_return, cumulative_return, max_drawdown, positions, prev)

    return snap


# ─── History View ────────────────────────────────────────────────────────────

def cmd_history(days: Optional[int] = None):
    ensure_snapshots_table()
    snaps = get_all_snapshots(days)

    if not snaps:
        print("[snapshot] No snapshots found.")
        return

    label = f"last {days} days" if days else "all time"
    print(f"\n{'='*78}")
    print(f"  PORTFOLIO SNAPSHOT HISTORY ({label})")
    print(f"{'='*78}")
    print(f"  {'TIMESTAMP':<22} {'TOTAL VALUE':>13} {'CASH':>12} {'INVESTED':>12} {'DAILY':>8} {'CUMUL':>8} {'MAX DD':>8}")
    print(f"  {'-'*73}")

    for s in reversed(snaps):
        dr = f"{s['daily_return']:+.2f}%" if s['daily_return'] is not None else "   N/A"
        cr = f"{s['cumulative_return']:+.2f}%" if s['cumulative_return'] is not None else "   N/A"
        dd = f"{s['max_drawdown']:.2f}%" if s['max_drawdown'] is not None else "   N/A"
        print(f"  {s['timestamp'][:22]:<22} ${s['total_value']:>12,.2f} ${s['cash']:>11,.2f} "
              f"${s['invested']:>11,.2f} {dr:>8} {cr:>8} {dd:>8}")

    print(f"{'='*78}\n")


# ─── ASCII Chart ─────────────────────────────────────────────────────────────

def cmd_chart():
    ensure_snapshots_table()
    snaps = get_all_snapshots()

    if len(snaps) < 2:
        print("[snapshot] Not enough data to chart (need at least 2 snapshots).")
        return

    values = [s['total_value'] for s in snaps]
    labels = [s['timestamp'][:10] for s in snaps]

    chart_height = 20
    chart_width  = min(len(values), 80)

    # Down-sample if too many points
    if len(values) > chart_width:
        step = len(values) / chart_width
        sampled_values = [values[int(i * step)] for i in range(chart_width)]
        sampled_labels = [labels[int(i * step)] for i in range(chart_width)]
    else:
        sampled_values = values
        sampled_labels = labels

    min_val = min(sampled_values)
    max_val = max(sampled_values)
    val_range = max_val - min_val or 1.0

    # Normalise to chart_height rows
    def to_row(v):
        return chart_height - 1 - int((v - min_val) / val_range * (chart_height - 1))

    rows = [to_row(v) for v in sampled_values]

    print(f"\n  PORTFOLIO VALUE OVER TIME")
    print(f"  {'─'*60}")

    for row in range(chart_height):
        line_val = min_val + (1 - row / (chart_height - 1)) * val_range
        label = f"${line_val/1_000:.0f}k"
        bar_line = ""
        for col, r in enumerate(rows):
            if r == row:
                bar_line += "●"
            elif row > 0 and row < chart_height - 1 and r < row and rows[max(0, col-1)] > row:
                bar_line += "│"
            else:
                bar_line += " "
        print(f"  {label:>8}  │{bar_line}")

    print(f"  {'':>8}  └{'─' * len(sampled_values)}")

    # Print first/last date labels
    if sampled_labels:
        start = sampled_labels[0]
        end   = sampled_labels[-1]
        gap   = len(sampled_values) - len(start) - len(end) - 2
        gap   = max(gap, 1)
        print(f"  {'':>9}  {start}{' '*gap}{end}")

    start_val = values[0]
    end_val   = values[-1]
    total_ret = ((end_val / start_val) - 1) * 100
    print(f"\n  Snapshots: {len(snaps)} | Start: ${start_val:,.0f} → Current: ${end_val:,.0f} ({total_ret:+.2f}%)\n")


# ─── CSV Export ──────────────────────────────────────────────────────────────

def cmd_export():
    ensure_snapshots_table()
    snaps = get_all_snapshots()

    if not snaps:
        print("[snapshot] No snapshots to export.")
        return

    filename = f"portfolio_snapshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    fieldnames = ['timestamp', 'total_value', 'cash', 'invested', 'num_positions',
                  'daily_return', 'cumulative_return', 'max_drawdown']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in snaps:
            writer.writerow({k: s.get(k, '') for k in fieldnames})

    print(f"[snapshot] ✅ Exported {len(snaps)} snapshots to {filename}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Portfolio Snapshot Daemon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  take                  Take a snapshot right now
  history [--days N]    Show snapshot history
  chart                 ASCII chart of portfolio value over time
  export                Export snapshots to CSV
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('take', help='Take one snapshot now')

    hist_p = subparsers.add_parser('history', help='Show snapshot history')
    hist_p.add_argument('--days', type=int, default=None,
                        help='Limit to last N days (default: all)')

    subparsers.add_parser('chart', help='ASCII chart of portfolio value over time')
    subparsers.add_parser('export', help='CSV export of snapshots')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'take':
        take_snapshot(verbose=True)
    elif args.command == 'history':
        cmd_history(days=args.days)
    elif args.command == 'chart':
        cmd_chart()
    elif args.command == 'export':
        cmd_export()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
