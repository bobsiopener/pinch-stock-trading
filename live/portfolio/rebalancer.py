#!/usr/bin/env python3
"""
Pinch Stock Trading Platform — Rebalancing Engine
Compares current portfolio weights against targets and generates trade orders.

Usage:
    python3 rebalancer.py preview              — show current vs target, trades needed
    python3 rebalancer.py preview --regime     — auto-detect market regime, use regime targets
    python3 rebalancer.py execute              — run trades through portfolio manager
    python3 rebalancer.py set-target NVDA 0.12 — adjust a single target weight
    python3 rebalancer.py targets              — show current target allocation

Rule of Acquisition #22: A wise man can hear profit in the wind.
"""

import sqlite3
import argparse
import sys
import os
import json
from datetime import datetime
from typing import Optional

# ─── Paths ───────────────────────────────────────────────────────────────────

PORTFOLIO_DB = os.path.join(os.path.dirname(__file__), '../../state/portfolio.db')
MARKET_DB    = '/mnt/media/market_data/pinch_market.db'
TARGETS_KEY  = 'rebalancer_targets'

STARTING_CAPITAL = 500_000.00

# ─── Default Target Allocations ──────────────────────────────────────────────

BULL_TARGETS: dict[str, float] = {
    # Core (60%)
    'QQQ':   0.12,   # Broad tech/growth
    'NVDA':  0.10,   # AI leader
    'MSFT':  0.08,   # Quality tech
    'AVGO':  0.08,   # Semis
    'GOOG':  0.07,   # Mega cap
    'ANET':  0.05,   # AI networking
    'PLTR':  0.05,   # AI/defense
    'BRK-B': 0.05,   # Value anchor
    # Defensive (25%)
    'GLD':   0.10,   # Gold hedge
    'TLT':   0.08,   # Bond duration
    'XLV':   0.07,   # Healthcare defensive
    # Cash (15%)
    '_CASH': 0.15,
}

BEAR_TARGETS: dict[str, float] = {
    'QQQ':   0.05,
    'NVDA':  0.05,
    'MSFT':  0.05,
    'GLD':   0.15,
    'TLT':   0.12,
    'XLV':   0.10,
    'SHY':   0.08,
    'BRK-B': 0.05,
    '_CASH': 0.35,
}

MIN_TRADE_VALUE = 100.00   # Minimum notional per order
DRIFT_THRESHOLD = 0.03     # Default 3% drift threshold for "threshold" mode


# ─── DB Helpers ──────────────────────────────────────────────────────────────

def get_portfolio_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(PORTFOLIO_DB)), exist_ok=True)
    conn = sqlite3.connect(PORTFOLIO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_market_price(symbol: str) -> Optional[float]:
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            row = conn.execute(
                "SELECT close FROM prices WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
                (symbol.upper(),)
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"[rebalancer] Warning: Could not fetch price for {symbol}: {e}", file=sys.stderr)
        return None


def get_cash() -> float:
    with get_portfolio_conn() as conn:
        row = conn.execute("SELECT value FROM portfolio_state WHERE key = 'cash'").fetchone()
        return float(row['value']) if row else STARTING_CAPITAL


def get_holdings() -> list[dict]:
    with get_portfolio_conn() as conn:
        # 'positions' is the active table; 'holdings' kept for legacy compat
        try:
            rows = conn.execute("SELECT symbol, shares, avg_cost, sector FROM positions").fetchall()
            if rows:
                return [dict(r) for r in rows]
        except Exception:
            pass
        rows = conn.execute("SELECT symbol, shares, avg_cost, sector FROM holdings").fetchall()
        return [dict(r) for r in rows]


def load_targets() -> dict[str, float]:
    """Load saved targets from portfolio_state, falling back to BULL_TARGETS."""
    with get_portfolio_conn() as conn:
        row = conn.execute(
            "SELECT value FROM portfolio_state WHERE key = ?", (TARGETS_KEY,)
        ).fetchone()
        if row:
            return json.loads(row['value'])
    return dict(BULL_TARGETS)


def save_targets(targets: dict[str, float]):
    """Persist targets to portfolio_state."""
    with get_portfolio_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO portfolio_state (key, value, updated_at)
               VALUES (?, ?, datetime('now'))""",
            (TARGETS_KEY, json.dumps(targets))
        )


# ─── Regime Detection ────────────────────────────────────────────────────────

def get_regime() -> str:
    """
    Determine market regime by comparing SPY's current price to its 200-day SMA.
    Returns 'BULL' or 'BEAR'.
    """
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            rows = conn.execute(
                "SELECT timestamp, close FROM prices WHERE symbol = 'SPY' ORDER BY timestamp DESC LIMIT 200"
            ).fetchall()

        if len(rows) < 200:
            print("[rebalancer] Warning: Fewer than 200 SPY data points; defaulting to BULL regime.")
            return 'BULL'

        current_price = rows[0][1]
        sma200 = sum(r[1] for r in rows) / 200

        regime = 'BULL' if current_price > sma200 else 'BEAR'
        print(f"[rebalancer] SPY ${current_price:.2f} vs SMA200 ${sma200:.2f} → {regime} regime")
        return regime

    except Exception as e:
        print(f"[rebalancer] Warning: Regime detection failed ({e}); defaulting to BULL.")
        return 'BULL'


# ─── Portfolio State ─────────────────────────────────────────────────────────

def build_portfolio_state() -> dict:
    """
    Returns:
      {
        'total_value': float,
        'cash': float,
        'positions': { symbol: { shares, avg_cost, price, value, weight, pnl, pnl_pct } }
      }
    """
    cash = get_cash()
    holdings = get_holdings()

    positions = {}
    invested = 0.0

    for h in holdings:
        symbol = h['symbol']
        shares = h['shares']
        avg_cost = h['avg_cost']
        price = get_market_price(symbol) or avg_cost
        value = shares * price
        invested += value
        pnl = value - shares * avg_cost
        positions[symbol] = {
            'shares': shares,
            'avg_cost': avg_cost,
            'price': price,
            'value': value,
            'weight': 0.0,
            'pnl': pnl,
            'pnl_pct': ((price / avg_cost) - 1) * 100 if avg_cost else 0.0,
        }

    total_value = cash + invested
    for sym in positions:
        positions[sym]['weight'] = positions[sym]['value'] / total_value if total_value else 0.0

    return {'total_value': total_value, 'cash': cash, 'positions': positions}


# ─── Trade Generation ────────────────────────────────────────────────────────

def generate_trades(
    state: dict,
    targets: dict[str, float],
    mode: str = 'preview',
    drift_threshold: float = DRIFT_THRESHOLD,
) -> list[dict]:
    """
    Compute rebalancing trades.

    Parameters
    ----------
    state           : output of build_portfolio_state()
    targets         : target weights (fractions, not %, _CASH excluded from trade gen)
    mode            : 'preview' | 'threshold' | 'full' | 'tax-aware'
    drift_threshold : used in 'threshold' mode only

    Returns list of trade dicts:
      { symbol, side, shares, price, estimated_value, reason }
    """
    total_value = state['total_value']
    cash        = state['cash']
    positions   = state['positions']

    trades = []

    equity_targets = {k: v for k, v in targets.items() if k != '_CASH'}

    for symbol, target_weight in equity_targets.items():
        target_value = target_weight * total_value
        price = get_market_price(symbol)
        if price is None:
            print(f"[rebalancer] Warning: no price for {symbol}, skipping.")
            continue

        current_value  = positions.get(symbol, {}).get('value', 0.0)
        current_weight = positions.get(symbol, {}).get('weight', 0.0)
        delta_value    = target_value - current_value
        drift          = abs(target_weight - current_weight)

        # threshold mode: skip if within tolerance
        if mode == 'threshold' and drift < drift_threshold:
            continue

        if abs(delta_value) < MIN_TRADE_VALUE:
            continue

        shares = abs(delta_value) / price
        side   = 'BUY' if delta_value > 0 else 'SELL'

        # tax-aware: prefer selling losers, skip selling winners
        if mode == 'tax-aware' and side == 'SELL':
            pnl = positions.get(symbol, {}).get('pnl', 0.0)
            if pnl > 0:
                continue  # defer winner; will accept a small drift

        reason = f"rebalance ({mode}) target={target_weight*100:.1f}% current={current_weight*100:.1f}%"
        trades.append({
            'symbol':          symbol,
            'side':            side,
            'shares':          shares,
            'price':           price,
            'estimated_value': abs(delta_value),
            'reason':          reason,
        })

    # Handle owned positions that are NOT in targets (close them out in full/tax-aware mode)
    if mode in ('full', 'tax-aware'):
        for symbol, pos in positions.items():
            if symbol not in equity_targets and pos['shares'] > 0:
                price = pos['price']
                shares = pos['shares']
                value  = pos['value']
                if value < MIN_TRADE_VALUE:
                    continue
                if mode == 'tax-aware' and pos['pnl'] > 0:
                    continue  # defer winner
                trades.append({
                    'symbol':          symbol,
                    'side':            'SELL',
                    'shares':          shares,
                    'price':           price,
                    'estimated_value': value,
                    'reason':          'not in target allocation — close position',
                })

    # Sort: sells first (free up cash), then buys
    trades.sort(key=lambda t: (0 if t['side'] == 'SELL' else 1, t['symbol']))
    return trades


# ─── Display Helpers ─────────────────────────────────────────────────────────

def print_preview(state: dict, targets: dict[str, float], trades: list[dict], regime: str = ''):
    total_value = state['total_value']
    positions   = state['positions']

    header = "REBALANCE PREVIEW"
    if regime:
        header += f"  [{regime} REGIME]"

    print(f"\n{'='*80}")
    print(f"  {header}")
    print(f"  Portfolio value: ${total_value:,.2f}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    print(f"  {'SYMBOL':<8} {'CURRENT $':>12} {'CURR %':>8} {'TARGET %':>9} {'DRIFT':>8} {'ACTION':>6}")
    print(f"  {'-'*60}")

    all_symbols = sorted(set(list(positions.keys()) + [k for k in targets if k != '_CASH']))
    for sym in all_symbols:
        cur_val = positions.get(sym, {}).get('value', 0.0)
        cur_wt  = positions.get(sym, {}).get('weight', 0.0) * 100
        tgt_wt  = targets.get(sym, 0.0) * 100
        drift   = tgt_wt - cur_wt
        action  = ""
        if abs(drift) > 0.5:
            action = "▲ BUY" if drift > 0 else "▼ SELL"
        drift_str = f"{drift:+.1f}%"
        print(f"  {sym:<8} ${cur_val:>11,.0f} {cur_wt:>7.1f}% {tgt_wt:>8.1f}% {drift_str:>8}  {action}")

    # Cash line
    cash_wt  = state['cash'] / total_value * 100
    cash_tgt = targets.get('_CASH', 0.0) * 100
    cash_drift = cash_tgt - cash_wt
    print(f"  {'_CASH':<8} ${state['cash']:>11,.0f} {cash_wt:>7.1f}% {cash_tgt:>8.1f}% {cash_drift:>+8.1f}%")

    print(f"{'='*80}")

    if not trades:
        print(f"  ✅ Portfolio is balanced — no trades required.\n")
        return

    total_buy  = sum(t['estimated_value'] for t in trades if t['side'] == 'BUY')
    total_sell = sum(t['estimated_value'] for t in trades if t['side'] == 'SELL')

    print(f"\n  TRADES REQUIRED  (sells: ${total_sell:,.0f}  |  buys: ${total_buy:,.0f})")
    print(f"  {'SIDE':<6} {'SYMBOL':<8} {'SHARES':>10} {'PRICE':>10} {'VALUE':>12}  REASON")
    print(f"  {'-'*72}")

    for t in trades:
        print(f"  {t['side']:<6} {t['symbol']:<8} {t['shares']:>10.2f} ${t['price']:>9.2f} ${t['estimated_value']:>11,.0f}  {t['reason']}")

    print(f"\n  Total trades: {len(trades)}  |  Net buy/sell: ${total_buy - total_sell:+,.0f}")
    print(f"{'='*80}\n")


def print_targets(targets: dict[str, float]):
    equity_total = sum(v for k, v in targets.items() if k != '_CASH')
    cash_pct     = targets.get('_CASH', 0.0) * 100

    print(f"\n{'='*50}")
    print(f"  CURRENT TARGET ALLOCATION")
    print(f"{'='*50}")
    print(f"  {'SYMBOL':<10} {'TARGET':>8}  BAR")
    print(f"  {'-'*45}")

    for sym, wt in sorted(targets.items(), key=lambda x: -x[1]):
        bar = '█' * int(wt * 100 / 2)
        print(f"  {sym:<10} {wt*100:>7.1f}%  {bar}")

    print(f"  {'-'*45}")
    print(f"  {'EQUITY':<10} {equity_total*100:>7.1f}%")
    print(f"  {'CASH':<10} {cash_pct:>7.1f}%")
    total_check = (equity_total + targets.get('_CASH', 0.0)) * 100
    print(f"  {'TOTAL':<10} {total_check:>7.1f}%")
    print(f"{'='*50}\n")


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_preview(use_regime: bool = False, mode: str = 'preview',
                drift_threshold: float = DRIFT_THRESHOLD):
    targets = load_targets()
    regime  = ''

    if use_regime:
        regime  = get_regime()
        if regime == 'BEAR':
            targets = dict(BEAR_TARGETS)
            print(f"[rebalancer] 🐻 BEAR regime detected — switching to defensive targets")
        else:
            print(f"[rebalancer] 🐂 BULL regime detected — using normal targets")

    state  = build_portfolio_state()
    trades = generate_trades(state, targets, mode=mode, drift_threshold=drift_threshold)
    print_preview(state, targets, trades, regime=regime)


def cmd_execute(use_regime: bool = False, mode: str = 'full',
                drift_threshold: float = DRIFT_THRESHOLD):
    """Execute rebalancing trades through the portfolio manager."""
    # Import portfolio manager from same directory
    sys.path.insert(0, os.path.dirname(__file__))
    from portfolio_manager import Portfolio

    targets = load_targets()
    regime  = ''

    if use_regime:
        regime = get_regime()
        if regime == 'BEAR':
            targets = dict(BEAR_TARGETS)
            print(f"[rebalancer] 🐻 BEAR regime — using defensive targets")

    state  = build_portfolio_state()
    trades = generate_trades(state, targets, mode=mode, drift_threshold=drift_threshold)

    if not trades:
        print("[rebalancer] ✅ No trades needed — portfolio is balanced.")
        return

    print(f"\n[rebalancer] Executing {len(trades)} trade(s)...\n")
    p = Portfolio()

    for trade in trades:
        symbol = trade['symbol']
        shares = trade['shares']
        price  = trade['price']
        reason = trade['reason']

        if trade['side'] == 'BUY':
            p.buy(symbol, shares, price=price, reason=reason, strategy='rebalance')
        else:
            p.sell(symbol, shares, price=price, reason=reason)

    print(f"\n[rebalancer] ✅ Rebalancing complete.")


def cmd_set_target(symbol: str, weight: float):
    symbol = symbol.upper()
    if weight < 0 or weight > 1:
        print(f"[rebalancer] ERROR: Weight must be between 0 and 1 (e.g. 0.10 for 10%).")
        sys.exit(1)

    targets = load_targets()
    old = targets.get(symbol, 0.0)
    targets[symbol] = weight

    # Warn if total > 1
    total = sum(targets.values())
    if total > 1.001:
        print(f"[rebalancer] ⚠️  Warning: Total allocation is {total*100:.1f}% — adjust other targets.")

    save_targets(targets)
    print(f"[rebalancer] ✅ {symbol}: {old*100:.1f}% → {weight*100:.1f}%  (total now {total*100:.1f}%)")


def cmd_targets():
    targets = load_targets()
    print_targets(targets)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Rebalancing Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  preview           Show current vs target allocations and trades needed
  execute           Execute trades via portfolio manager
  set-target        Adjust a single target weight
  targets           Display current target allocations

Rebalance modes (--mode):
  preview    — dry run, no execution (default for 'preview')
  threshold  — only trade positions drifting > --threshold (default 3%)
  full       — rebalance everything to exact targets (default for 'execute')
  tax-aware  — prefer selling losers, defer selling winners
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    # preview
    prev_p = subparsers.add_parser('preview', help='Show current vs target, trades needed')
    prev_p.add_argument('--regime', action='store_true', help='Auto-detect market regime')
    prev_p.add_argument('--mode', default='preview',
                        choices=['preview', 'threshold', 'full', 'tax-aware'],
                        help='Rebalance mode')
    prev_p.add_argument('--threshold', type=float, default=DRIFT_THRESHOLD,
                        help=f'Drift threshold for threshold mode (default {DRIFT_THRESHOLD})')

    # execute
    exec_p = subparsers.add_parser('execute', help='Execute rebalancing trades')
    exec_p.add_argument('--regime', action='store_true', help='Auto-detect market regime')
    exec_p.add_argument('--mode', default='full',
                        choices=['threshold', 'full', 'tax-aware'],
                        help='Rebalance mode (default: full)')
    exec_p.add_argument('--threshold', type=float, default=DRIFT_THRESHOLD,
                        help=f'Drift threshold for threshold mode (default {DRIFT_THRESHOLD})')

    # set-target
    set_p = subparsers.add_parser('set-target', help='Adjust a target weight')
    set_p.add_argument('symbol', type=str, help='Ticker symbol (or _CASH)')
    set_p.add_argument('weight', type=float, help='Target weight as decimal (e.g. 0.10)')

    # targets
    subparsers.add_parser('targets', help='Show current target allocation')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'preview':
        cmd_preview(use_regime=args.regime, mode=args.mode, drift_threshold=args.threshold)
    elif args.command == 'execute':
        cmd_execute(use_regime=args.regime, mode=args.mode, drift_threshold=args.threshold)
    elif args.command == 'set-target':
        cmd_set_target(args.symbol, args.weight)
    elif args.command == 'targets':
        cmd_targets()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
