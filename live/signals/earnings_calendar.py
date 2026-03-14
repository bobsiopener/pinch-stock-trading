#!/usr/bin/env python3
"""
Pinch Stock Trading — Earnings Calendar Integration
Issue #26: Track earnings dates, pre-earnings alerts, historical surprise analysis.

Usage:
    python3 earnings_calendar.py update             — refresh all earnings dates
    python3 earnings_calendar.py check              — show upcoming earnings for portfolio
    python3 earnings_calendar.py history <symbol>   — show historical earnings reactions

Rule of Acquisition #208: Sometimes the only thing more dangerous than a question is an answer.
(Know when earnings are before you sell covered calls.)
"""

import sqlite3
import json
import argparse
import sys
import os
from datetime import datetime, date, timedelta
from typing import Optional

# ─── Config ──────────────────────────────────────────────────────────────────

MARKET_DB = '/mnt/media/market_data/pinch_market.db'
PORTFOLIO_DB = os.path.join(os.path.dirname(__file__), '../../state/portfolio.db')
EARNINGS_FILE = os.path.join(os.path.dirname(__file__), '../../state/earnings_calendar.json')

# Default universe — used when portfolio is empty
DEFAULT_HOLDINGS = [
    'AAPL', 'AMD', 'AMZN', 'ANET', 'BRK-B', 'CSCO', 'GOOG', 'MSFT',
    'NVDA', 'PLTR', 'MSTR', 'META', 'TSLA', 'AVGO', 'ORCL', 'WFC',
]

# Equity-only symbols (crypto/ETFs don't have earnings)
EQUITY_ONLY = True

PRE_EARNINGS_WARN_DAYS = 5   # Don't sell covered calls within this window
PRE_EARNINGS_CRIT_DAYS = 1   # CRITICAL: earnings tomorrow

# Proxy for earnings reactions: single-day moves > this threshold
EARNINGS_MOVE_THRESHOLD = 0.03  # 3%


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_market_db():
    return sqlite3.connect(MARKET_DB)


def get_portfolio_symbols() -> list[str]:
    """Get symbols from portfolio DB; fallback to DEFAULT_HOLDINGS."""
    try:
        conn = sqlite3.connect(PORTFOLIO_DB)
        rows = conn.execute("SELECT symbol FROM holdings WHERE shares > 0").fetchall()
        conn.close()
        symbols = [r[0] for r in rows]
        if symbols:
            return symbols
    except Exception:
        pass
    return DEFAULT_HOLDINGS


def is_equity_symbol(symbol: str) -> bool:
    """Exclude crypto and pure ETFs from earnings tracking."""
    crypto = {'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT',
              'LINK', 'AVAX', 'MATIC', 'OP', 'ARB', 'AAVE', 'UNI', 'MKR',
              'PEPE', 'SHIB', 'WIF'}
    etfs = {'SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'SHY', 'HYG', 'LQD',
            'XLK', 'XLE', 'XLF', 'XLV', 'XBI', 'SMH', 'EEM', 'FXI',
            'EWJ', 'ARKK', 'COPX', 'SLV', 'USO', 'UNG'}
    indices = {'VIX', 'VIXCLS'}
    return symbol not in (crypto | etfs | indices)


def load_earnings_calendar() -> dict:
    """Load saved earnings calendar from JSON file."""
    if os.path.exists(EARNINGS_FILE):
        with open(EARNINGS_FILE) as f:
            return json.load(f)
    return {}


def save_earnings_calendar(data: dict):
    """Save earnings calendar to JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(EARNINGS_FILE)), exist_ok=True)
    with open(EARNINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def get_trading_days_until(target_date_str: str) -> Optional[int]:
    """Count trading days (Mon-Fri, no holiday check) until target date."""
    if not target_date_str or target_date_str == 'N/A':
        return None
    try:
        target = datetime.strptime(target_date_str[:10], '%Y-%m-%d').date()
        today = date.today()
        if target < today:
            return -1
        count = 0
        d = today
        while d < target:
            if d.weekday() < 5:  # Mon=0 ... Fri=4
                count += 1
            d += timedelta(days=1)
        return count
    except Exception:
        return None


# ─── Update: Fetch Earnings Dates ────────────────────────────────────────────

def cmd_update(args):
    """Refresh all earnings dates via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance")
        sys.exit(1)

    symbols = get_portfolio_symbols()
    equity_symbols = [s for s in symbols if is_equity_symbol(s)]

    print(f"[earnings] Fetching earnings dates for {len(equity_symbols)} equity symbols...")

    calendar = load_earnings_calendar()
    updated = 0
    errors = 0

    for symbol in sorted(equity_symbols):
        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar

            next_earnings = None
            confirmed = False
            timing = None

            if cal is not None and not (hasattr(cal, 'empty') and cal.empty):
                # calendar can be a dict or DataFrame depending on yfinance version
                if isinstance(cal, dict):
                    earnings_date = cal.get('Earnings Date')
                    if earnings_date:
                        if hasattr(earnings_date, '__iter__') and not isinstance(earnings_date, str):
                            earnings_date = list(earnings_date)[0]
                        next_earnings = str(earnings_date)[:10]
                        confirmed = True
                elif hasattr(cal, 'loc'):
                    try:
                        ed = cal.loc['Earnings Date']
                        if hasattr(ed, '__iter__'):
                            ed = list(ed)[0]
                        next_earnings = str(ed)[:10]
                        confirmed = True
                    except Exception:
                        pass

            # Fallback: check earnings_dates attribute
            if not next_earnings:
                try:
                    ed = ticker.earnings_dates
                    if ed is not None and not ed.empty:
                        future = ed[ed.index > datetime.now()]
                        if not future.empty:
                            next_earnings = str(future.index[0])[:10]
                            confirmed = False
                except Exception:
                    pass

            calendar[symbol] = {
                'next_earnings': next_earnings or 'N/A',
                'confirmed': confirmed,
                'time': timing or 'TBD',
                'updated_at': datetime.now().isoformat()[:16],
            }
            status = f"{next_earnings or 'N/A'} {'(confirmed)' if confirmed else '(est.)'}"
            print(f"  {symbol:10s} → {status}")
            updated += 1

        except Exception as e:
            print(f"  {symbol:10s} → ERROR: {e}")
            errors += 1

    save_earnings_calendar(calendar)
    print(f"\n[earnings] Done. Updated: {updated}, Errors: {errors}")
    print(f"[earnings] Saved to: {EARNINGS_FILE}")


# ─── Check: Upcoming Earnings Alerts ─────────────────────────────────────────

def cmd_check(args):
    """Show upcoming earnings for portfolio holdings with alerts."""
    calendar = load_earnings_calendar()

    if not calendar:
        print("[earnings] No earnings data found. Run: earnings_calendar.py update")
        sys.exit(1)

    symbols = get_portfolio_symbols()
    equity_symbols = [s for s in symbols if is_equity_symbol(s)]

    today = date.today()

    critical = []   # within 1 trading day
    warning = []    # within 5 trading days
    upcoming = []   # within 30 days
    later = []

    for symbol in sorted(equity_symbols):
        data = calendar.get(symbol)
        if not data:
            continue

        next_e = data.get('next_earnings', 'N/A')
        if next_e == 'N/A':
            continue

        days = get_trading_days_until(next_e)
        if days is None:
            continue

        entry = {
            'symbol': symbol,
            'date': next_e,
            'days': days,
            'confirmed': data.get('confirmed', False),
            'time': data.get('time', 'TBD'),
        }

        if 0 <= days <= PRE_EARNINGS_CRIT_DAYS:
            critical.append(entry)
        elif days <= PRE_EARNINGS_WARN_DAYS:
            warning.append(entry)
        elif days <= 30:
            upcoming.append(entry)
        else:
            later.append(entry)

    print(f"\n{'═'*60}")
    print(f"  EARNINGS CALENDAR CHECK  |  {today.strftime('%Y-%m-%d')}")
    print(f"{'═'*60}")

    if critical:
        print(f"\n🚨 CRITICAL — Earnings within {PRE_EARNINGS_CRIT_DAYS} trading day:")
        for e in critical:
            conf = '✓' if e['confirmed'] else '~'
            print(f"  {e['symbol']:8s} → {e['date']} [{e['time']}] ({e['days']}d)  {conf}")
        print("  ⚠️  DO NOT trade options on these names!")

    if warning:
        print(f"\n⚠️  WARNING — Earnings within {PRE_EARNINGS_WARN_DAYS} trading days (no covered calls):")
        for e in warning:
            conf = '✓' if e['confirmed'] else '~'
            print(f"  {e['symbol']:8s} → {e['date']} [{e['time']}] ({e['days']}d)  {conf}")

    if upcoming:
        print(f"\n📅 UPCOMING — Earnings within 30 days:")
        for e in sorted(upcoming, key=lambda x: x['days']):
            conf = '✓' if e['confirmed'] else '~'
            print(f"  {e['symbol']:8s} → {e['date']} [{e['time']}] ({e['days']}d)  {conf}")

    if not critical and not warning and not upcoming:
        print("\n  ✅ No earnings in the next 30 days for your holdings.")
    else:
        print(f"\n  Legend: ✓=confirmed  ~=estimated  AMC=after close  BMO=before open")

    if later:
        print(f"\n  Further out ({len(later)} symbols): {', '.join(e['symbol'] for e in sorted(later, key=lambda x: x['days']))}")


# ─── History: Earnings Reaction Analysis ─────────────────────────────────────

def cmd_history(args):
    """Show historical earnings reactions for a symbol using price data."""
    symbol = args.symbol.upper()

    conn = get_market_db()

    rows = conn.execute("""
        SELECT datetime(timestamp, 'unixepoch') as dt, open, high, low, close, volume
        FROM prices
        WHERE symbol = ? AND timeframe = '1d'
        ORDER BY timestamp ASC
    """, (symbol,)).fetchall()
    conn.close()

    if not rows:
        print(f"[earnings] No price data found for {symbol}")
        sys.exit(1)

    print(f"\n{'═'*65}")
    print(f"  HISTORICAL EARNINGS REACTIONS — {symbol}")
    print(f"{'═'*65}")
    print(f"  Proxy method: single-day moves > {EARNINGS_MOVE_THRESHOLD*100:.0f}% = likely earnings reaction")
    print(f"  Data: {rows[0][0][:10]} → {rows[-1][0][:10]} ({len(rows)} days)")
    print()

    # Build list of (date, daily_return, open, close)
    moves = []
    for i in range(1, len(rows)):
        prev_close = rows[i-1][4]  # close
        curr_open  = rows[i][1]    # open
        curr_close = rows[i][4]    # close
        curr_date  = rows[i][0][:10]

        if prev_close and prev_close > 0:
            gap_pct = (curr_open - prev_close) / prev_close
            day_pct = (curr_close - prev_close) / prev_close

            if abs(day_pct) >= EARNINGS_MOVE_THRESHOLD:
                moves.append({
                    'date': curr_date,
                    'gap_pct': gap_pct,
                    'day_pct': day_pct,
                    'open': curr_open,
                    'close': curr_close,
                    'prev_close': prev_close,
                })

    if not moves:
        print(f"  No single-day moves > {EARNINGS_MOVE_THRESHOLD*100:.0f}% found for {symbol}")
        return

    # Separate gaps up vs gaps down
    gaps_up   = [m for m in moves if m['day_pct'] > 0]
    gaps_down = [m for m in moves if m['day_pct'] <= 0]

    avg_pos = sum(m['day_pct'] for m in gaps_up) / len(gaps_up) if gaps_up else 0
    avg_neg = sum(m['day_pct'] for m in gaps_down) / len(gaps_down) if gaps_down else 0

    print(f"  Significant moves (>{EARNINGS_MOVE_THRESHOLD*100:.0f}%): {len(moves)} events")
    print(f"  ↑ Gap ups:   {len(gaps_up):2d} events  (avg +{avg_pos*100:.1f}%)")
    print(f"  ↓ Gap downs: {len(gaps_down):2d} events  (avg {avg_neg*100:.1f}%)")
    print()

    # Calculate post-earnings drift: next 5 days after event
    print(f"  {'Date':<12} {'Day Move':>10} {'Gap':>8} {'Verdict':<12}")
    print(f"  {'-'*12} {'-'*10} {'-'*8} {'-'*12}")

    for m in moves[-30:]:  # Show last 30 events
        verdict = "GAP UP ↑" if m['day_pct'] > 0 else "GAP DOWN ↓"
        day_str = f"{m['day_pct']*100:+.1f}%"
        gap_str = f"{m['gap_pct']*100:+.1f}%"
        print(f"  {m['date']:<12} {day_str:>10} {gap_str:>8} {verdict:<12}")

    # Summary stats
    print()
    total = len(moves)
    pct_up = len(gaps_up) / total * 100 if total else 0
    avg_move = sum(abs(m['day_pct']) for m in moves) / total if total else 0

    print(f"  SUMMARY:")
    print(f"  → {symbol} gaps UP  {pct_up:.0f}% of the time on big moves")
    print(f"  → {symbol} gaps DOWN {100-pct_up:.0f}% of the time on big moves")
    print(f"  → Average absolute move: {avg_move*100:.1f}%")

    if pct_up > 60:
        print(f"  → Tendency: BULLISH reaction — consider holding through earnings")
    elif pct_up < 40:
        print(f"  → Tendency: BEARISH reaction — consider reducing before earnings")
    else:
        print(f"  → Tendency: MIXED — unpredictable; avoid large options positions")

    print()
    # Drift analysis: do moves continue or reverse?
    print(f"  [Note] For post-earnings drift analysis, run with more price history.")
    print(f"  Rule of Acquisition #208: Know the risk before you sell the premium.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Earnings Calendar — Signal Research',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  update              Refresh all earnings dates via yfinance
  check               Show upcoming earnings alerts for portfolio
  history <symbol>    Show historical earnings reactions for a symbol

Examples:
  python3 earnings_calendar.py update
  python3 earnings_calendar.py check
  python3 earnings_calendar.py history AAPL
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('update', help='Refresh earnings dates')
    subparsers.add_parser('check', help='Show upcoming earnings')
    hist = subparsers.add_parser('history', help='Historical earnings reactions')
    hist.add_argument('symbol', help='Stock symbol (e.g. AAPL)')

    args = parser.parse_args()

    if args.command == 'update':
        cmd_update(args)
    elif args.command == 'check':
        cmd_check(args)
    elif args.command == 'history':
        cmd_history(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
