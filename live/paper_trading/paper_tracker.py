#!/usr/bin/env python3
"""
Pinch Stock Trading — Paper Trade Tracker
Issue #23: Log paper trades, generate daily/weekly reports, track P&L.

Usage:
    paper_tracker.py log-trade NVDA buy 10 180.25 [--strategy momentum] [--reason "regime shift"]
    paper_tracker.py status                   — current positions, unrealized P&L, cash
    paper_tracker.py daily-report             — daily report vs SPY benchmark
    paper_tracker.py weekly-summary           — weekly P&L and strategy attribution
    paper_tracker.py history [--symbol NVDA]  — trade log

Rule of Acquisition #74: Knowledge equals profit.
"""

import sqlite3
import argparse
import sys
import os
import json
from datetime import datetime, date, timedelta
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR      = os.path.join(os.path.dirname(__file__), '../..')
STATE_DIR     = os.path.join(BASE_DIR, 'state')
REPORTS_DIR   = os.path.join(os.path.dirname(__file__), 'reports')
TRADES_FILE   = os.path.join(STATE_DIR, 'paper_trades.json')
PORTFOLIO_DB  = os.path.join(STATE_DIR, 'portfolio.db')
MARKET_DB     = '/mnt/media/market_data/pinch_market.db'

STARTING_CASH = 500_000.00

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)


# ─── Data Helpers ─────────────────────────────────────────────────────────────

def load_trades() -> dict:
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE) as f:
            return json.load(f)
    return {"cash": STARTING_CASH, "trades": [], "positions": {}}


def save_trades(data: dict):
    with open(TRADES_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def get_price(symbol: str) -> Optional[float]:
    """Fetch latest close price from market DB."""
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            row = conn.execute(
                "SELECT close FROM prices WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
                (symbol.upper(),)
            ).fetchone()
            return float(row[0]) if row else None
    except Exception:
        return None


def get_spy_return(since_date: str) -> float:
    """Return SPY % gain from since_date to today."""
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            # price at or after since_date
            ts_start = int(datetime.strptime(since_date, '%Y-%m-%d').timestamp())
            row_start = conn.execute(
                "SELECT close FROM prices WHERE symbol='SPY' AND timestamp >= ? ORDER BY timestamp ASC LIMIT 1",
                (ts_start,)
            ).fetchone()
            row_end = conn.execute(
                "SELECT close FROM prices WHERE symbol='SPY' ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if row_start and row_end:
                return (row_end[0] / row_start[0] - 1) * 100
    except Exception:
        pass
    return 0.0


# ─── Core Logic ───────────────────────────────────────────────────────────────

def apply_trade(data: dict, symbol: str, side: str, shares: float, price: float,
                strategy: str = 'manual', reason: str = '') -> dict:
    """Apply a trade to data dict; returns updated dict."""
    symbol = symbol.upper()
    side   = side.lower()
    notional = shares * price

    trade_record = {
        "id":        len(data["trades"]) + 1,
        "timestamp": datetime.now().isoformat(),
        "date":      date.today().isoformat(),
        "symbol":    symbol,
        "side":      side,
        "shares":    shares,
        "price":     price,
        "notional":  notional,
        "strategy":  strategy,
        "reason":    reason,
    }

    if side == "buy":
        if data["cash"] < notional:
            print(f"[paper_tracker] ⚠️  Insufficient cash: need ${notional:,.0f}, have ${data['cash']:,.0f}")
            # Allow anyway for paper trading (margin sim)
        data["cash"] -= notional
        pos = data["positions"].get(symbol, {"shares": 0.0, "avg_cost": 0.0, "strategy": strategy})
        old_shares = pos["shares"]
        old_cost   = pos["avg_cost"]
        new_shares = old_shares + shares
        pos["avg_cost"] = ((old_shares * old_cost) + notional) / new_shares if new_shares else price
        pos["shares"]   = new_shares
        pos["strategy"] = strategy
        data["positions"][symbol] = pos

    elif side == "sell":
        pos = data["positions"].get(symbol)
        if not pos or pos["shares"] < shares:
            available = pos["shares"] if pos else 0
            print(f"[paper_tracker] ⚠️  Only {available:.2f} shares of {symbol} available — adjusting")
            shares = min(shares, available) if pos else 0
            if shares == 0:
                print(f"[paper_tracker] Skipping sell — no shares.")
                return data
            trade_record["shares"]   = shares
            trade_record["notional"] = shares * price
        data["cash"] += shares * price
        pos["shares"] -= shares
        if pos["shares"] <= 0.001:
            del data["positions"][symbol]
        else:
            data["positions"][symbol] = pos

    data["trades"].append(trade_record)
    return data


def compute_portfolio_value(data: dict) -> dict:
    """Return full portfolio value breakdown with live prices."""
    positions = {}
    total_invested = 0.0

    for symbol, pos in data["positions"].items():
        price = get_price(symbol) or pos.get("avg_cost", 0)
        value = pos["shares"] * price
        cost  = pos["shares"] * pos["avg_cost"]
        pnl   = value - cost
        positions[symbol] = {
            "shares":    pos["shares"],
            "avg_cost":  pos["avg_cost"],
            "price":     price,
            "value":     value,
            "cost_basis":cost,
            "pnl":       pnl,
            "pnl_pct":   (pnl / cost * 100) if cost else 0.0,
            "strategy":  pos.get("strategy", "manual"),
        }
        total_invested += value

    total_value = data["cash"] + total_invested
    start_value = STARTING_CASH
    total_pnl   = total_value - start_value

    return {
        "cash":          data["cash"],
        "invested":      total_invested,
        "total_value":   total_value,
        "total_pnl":     total_pnl,
        "total_pnl_pct": (total_pnl / start_value * 100) if start_value else 0.0,
        "positions":     positions,
    }


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_log_trade(args):
    symbol   = args.symbol.upper()
    side     = args.side.lower()
    shares   = float(args.shares)
    price    = float(args.price)
    strategy = args.strategy or "manual"
    reason   = args.reason or ""

    data = load_trades()
    data = apply_trade(data, symbol, side, shares, price, strategy, reason)
    save_trades(data)

    notional = shares * price
    print(f"[paper_tracker] ✅ {side.upper()} {shares:.4f} {symbol} @ ${price:.2f} = ${notional:,.0f}")
    print(f"  Strategy: {strategy}  |  Cash remaining: ${data['cash']:,.0f}")
    if reason:
        print(f"  Reason: {reason}")


def cmd_status(args):
    data  = load_trades()
    pf    = compute_portfolio_value(data)
    now   = datetime.now().strftime('%Y-%m-%d %H:%M')

    print(f"\n{'='*70}")
    print(f"  PAPER PORTFOLIO STATUS  |  {now}")
    print(f"{'='*70}")
    print(f"  Total Value:   ${pf['total_value']:>12,.2f}")
    print(f"  Cash:          ${pf['cash']:>12,.2f}  ({pf['cash']/pf['total_value']*100:.1f}%)")
    print(f"  Invested:      ${pf['invested']:>12,.2f}  ({pf['invested']/pf['total_value']*100:.1f}%)")
    sign = '+' if pf['total_pnl'] >= 0 else ''
    print(f"  Total P&L:    {sign}${pf['total_pnl']:>11,.2f}  ({sign}{pf['total_pnl_pct']:.2f}%)")
    print(f"\n  {'SYMBOL':<8} {'SHARES':>8} {'AVG COST':>10} {'PRICE':>10} {'VALUE':>12} {'P&L':>10} {'%':>7}  STRATEGY")
    print(f"  {'-'*78}")

    for sym, pos in sorted(pf["positions"].items()):
        pnl_str = f"{'+' if pos['pnl'] >= 0 else ''}{pos['pnl']:,.0f}"
        pct_str = f"{'+' if pos['pnl_pct'] >= 0 else ''}{pos['pnl_pct']:.1f}%"
        print(f"  {sym:<8} {pos['shares']:>8.2f} ${pos['avg_cost']:>9.2f} ${pos['price']:>9.2f} ${pos['value']:>11,.0f} {pnl_str:>10}  {pct_str:>7}  {pos['strategy']}")

    print(f"{'='*70}\n")


def cmd_daily_report(args):
    data  = load_trades()
    pf    = compute_portfolio_value(data)
    today = date.today().isoformat()

    # Determine start date (inception or 30 days ago)
    if data["trades"]:
        start_date = data["trades"][0]["date"]
    else:
        start_date = today

    spy_ret   = get_spy_return(start_date)
    port_ret  = pf["total_pnl_pct"]
    alpha     = port_ret - spy_ret

    # Trades today
    today_trades = [t for t in data["trades"] if t["date"] == today]

    lines = [
        f"# Daily Paper Trading Report — {today}",
        f"",
        f"## Portfolio Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Value | ${pf['total_value']:,.2f} |",
        f"| Cash | ${pf['cash']:,.2f} ({pf['cash']/pf['total_value']*100:.1f}%) |",
        f"| Total P&L | {'+'if pf['total_pnl']>=0 else ''}{pf['total_pnl']:,.2f} ({pf['total_pnl_pct']:+.2f}%) |",
        f"| SPY Return (since inception) | {spy_ret:+.2f}% |",
        f"| Alpha vs SPY | {alpha:+.2f}% |",
        f"",
        f"## Current Positions",
        f"| Symbol | Shares | Avg Cost | Price | Value | P&L | % | Strategy |",
        f"|--------|--------|----------|-------|-------|-----|---|----------|",
    ]

    for sym, pos in sorted(pf["positions"].items()):
        lines.append(
            f"| {sym} | {pos['shares']:.2f} | ${pos['avg_cost']:.2f} | ${pos['price']:.2f} "
            f"| ${pos['value']:,.0f} | {'+' if pos['pnl']>=0 else ''}{pos['pnl']:,.0f} "
            f"| {pos['pnl_pct']:+.1f}% | {pos['strategy']} |"
        )

    lines += [
        f"",
        f"## Today's Trades ({len(today_trades)})",
    ]
    if today_trades:
        lines.append(f"| # | Side | Symbol | Shares | Price | Notional | Strategy | Reason |")
        lines.append(f"|---|------|--------|--------|-------|----------|----------|--------|")
        for t in today_trades:
            lines.append(
                f"| {t['id']} | {t['side'].upper()} | {t['symbol']} | {t['shares']:.2f} "
                f"| ${t['price']:.2f} | ${t['notional']:,.0f} | {t['strategy']} | {t['reason']} |"
            )
    else:
        lines.append("_No trades today._")

    lines += [
        f"",
        f"## Strategy Attribution",
    ]

    # Strategy breakdown
    strategy_pnl: dict[str, float] = {}
    for sym, pos in pf["positions"].items():
        strat = pos["strategy"]
        strategy_pnl[strat] = strategy_pnl.get(strat, 0.0) + pos["pnl"]

    lines.append(f"| Strategy | P&L |")
    lines.append(f"|----------|-----|")
    for strat, pnl in sorted(strategy_pnl.items(), key=lambda x: -abs(x[1])):
        lines.append(f"| {strat} | {'+' if pnl>=0 else ''}{pnl:,.2f} |")

    report = "\n".join(lines)
    report_path = os.path.join(REPORTS_DIR, f"daily_{today}.md")
    with open(report_path, 'w') as f:
        f.write(report)

    print(report)
    print(f"\n[paper_tracker] Report saved → {report_path}")


def cmd_weekly_summary(args):
    data  = load_trades()
    pf    = compute_portfolio_value(data)
    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()

    # Trades this week
    week_trades = [t for t in data["trades"] if t["date"] >= week_ago]
    port_ret    = pf["total_pnl_pct"]
    spy_ret     = get_spy_return(week_ago)

    # Best/worst positions
    sorted_pos = sorted(pf["positions"].items(), key=lambda x: x[1]["pnl_pct"])
    worst = sorted_pos[:3]
    best  = sorted_pos[-3:][::-1]

    # Strategy P&L
    strategy_stats: dict[str, dict] = {}
    for t in data["trades"]:
        s = t.get("strategy", "manual")
        if s not in strategy_stats:
            strategy_stats[s] = {"trades": 0, "buy_notional": 0.0, "sell_notional": 0.0}
        strategy_stats[s]["trades"] += 1
        if t["side"] == "buy":
            strategy_stats[s]["buy_notional"] += t["notional"]
        else:
            strategy_stats[s]["sell_notional"] += t["notional"]

    lines = [
        f"# Weekly Paper Trading Summary — {week_ago} to {today.isoformat()}",
        f"",
        f"## Performance",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Portfolio Return | {port_ret:+.2f}% |",
        f"| SPY Return (week) | {spy_ret:+.2f}% |",
        f"| Alpha | {port_ret - spy_ret:+.2f}% |",
        f"| Trades This Week | {len(week_trades)} |",
        f"| Total Value | ${pf['total_value']:,.2f} |",
        f"",
        f"## Top Performers",
        f"| Symbol | P&L | % |",
        f"|--------|-----|---|",
    ]
    for sym, pos in best:
        lines.append(f"| {sym} | {'+' if pos['pnl']>=0 else ''}{pos['pnl']:,.0f} | {pos['pnl_pct']:+.1f}% |")

    lines += [
        f"",
        f"## Worst Performers",
        f"| Symbol | P&L | % |",
        f"|--------|-----|---|",
    ]
    for sym, pos in worst:
        lines.append(f"| {sym} | {'+' if pos['pnl']>=0 else ''}{pos['pnl']:,.0f} | {pos['pnl_pct']:+.1f}% |")

    lines += [
        f"",
        f"## Strategy Attribution",
        f"| Strategy | Trades | Buy Volume | Sell Volume |",
        f"|----------|--------|------------|-------------|",
    ]
    for strat, stats in sorted(strategy_stats.items()):
        lines.append(
            f"| {strat} | {stats['trades']} | ${stats['buy_notional']:,.0f} | ${stats['sell_notional']:,.0f} |"
        )

    lines += [
        f"",
        f"## This Week's Trades",
    ]
    if week_trades:
        lines.append("| Date | Side | Symbol | Shares | Price | Strategy |")
        lines.append("|------|------|--------|--------|-------|----------|")
        for t in week_trades:
            lines.append(
                f"| {t['date']} | {t['side'].upper()} | {t['symbol']} | "
                f"{t['shares']:.2f} | ${t['price']:.2f} | {t['strategy']} |"
            )
    else:
        lines.append("_No trades this week._")

    report = "\n".join(lines)
    report_path = os.path.join(REPORTS_DIR, f"weekly_{today.isoformat()}.md")
    with open(report_path, 'w') as f:
        f.write(report)

    print(report)
    print(f"\n[paper_tracker] Weekly summary saved → {report_path}")


def cmd_history(args):
    data   = load_trades()
    trades = data["trades"]
    symbol = args.symbol.upper() if args.symbol else None

    if symbol:
        trades = [t for t in trades if t["symbol"] == symbol]
        print(f"\nTrade history for {symbol} ({len(trades)} trades):\n")
    else:
        print(f"\nFull trade history ({len(trades)} trades):\n")

    print(f"  {'#':>4}  {'DATE':<12} {'SIDE':<5} {'SYMBOL':<8} {'SHARES':>8} {'PRICE':>10} {'NOTIONAL':>12}  STRATEGY")
    print(f"  {'-'*72}")
    for t in trades[-50:]:
        print(
            f"  {t['id']:>4}  {t['date']:<12} {t['side'].upper():<5} {t['symbol']:<8} "
            f"{t['shares']:>8.2f} ${t['price']:>9.2f} ${t['notional']:>11,.0f}  {t['strategy']}"
        )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Paper Trade Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  paper_tracker.py log-trade NVDA buy 10 180.25 --strategy momentum --reason "AI breakout"
  paper_tracker.py status
  paper_tracker.py daily-report
  paper_tracker.py weekly-summary
  paper_tracker.py history --symbol NVDA
        """
    )
    sub = parser.add_subparsers(dest='command')

    # log-trade
    lt = sub.add_parser('log-trade', help='Log a paper trade')
    lt.add_argument('symbol')
    lt.add_argument('side', choices=['buy', 'sell', 'BUY', 'SELL'])
    lt.add_argument('shares', type=float)
    lt.add_argument('price', type=float)
    lt.add_argument('--strategy', default='manual', help='Strategy attribution')
    lt.add_argument('--reason', default='', help='Trade rationale')

    # status
    sub.add_parser('status', help='Current positions and P&L')

    # daily-report
    sub.add_parser('daily-report', help='Generate daily report vs SPY')

    # weekly-summary
    sub.add_parser('weekly-summary', help='Weekly P&L and strategy attribution')

    # history
    hist = sub.add_parser('history', help='Trade log')
    hist.add_argument('--symbol', default=None, help='Filter by symbol')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'log-trade':
        cmd_log_trade(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'daily-report':
        cmd_daily_report(args)
    elif args.command == 'weekly-summary':
        cmd_weekly_summary(args)
    elif args.command == 'history':
        cmd_history(args)


if __name__ == '__main__':
    main()
