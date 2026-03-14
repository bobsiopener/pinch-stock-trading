#!/usr/bin/env python3
"""
Pinch Stock Trading — Macro Regime Detection
Issue #28: Automated regime detection using FRED data and VIX.

Usage:
    python3 macro_regime.py current    — show current regime and signals
    python3 macro_regime.py history    — show regime timeline (2010-present)
    python3 macro_regime.py backtest   — show SPY returns by regime

Rule of Acquisition #34: War is good for business. (But know which regime you're in first.)
"""

import sqlite3
import argparse
import sys
import json
from datetime import datetime, date
from typing import Optional

# ─── Config ──────────────────────────────────────────────────────────────────

MARKET_DB = '/mnt/media/market_data/pinch_market.db'

# FRED series used for regime detection
INDICATORS = {
    'yield_curve':  'T10Y2Y',    # 10Y-2Y spread (positive = normal, negative = inverted)
    'fed_funds':    'FEDFUNDS',   # Fed Funds rate
    'cpi':          'CPIAUCSL',   # CPI index (we compute YoY change)
    'unemployment': 'UNRATE',     # Unemployment rate
    'vix':          'VIX',        # From prices table
}

# Regime thresholds
REGIME_RULES = {
    'EXPANSION': {
        'yield_curve_min': 0.0,       # positive yield curve
        'vix_max': 20.0,              # calm volatility
        'unemployment_trend': 'flat_or_falling',
    },
    'LATE_CYCLE': {
        'yield_curve_max': 0.5,       # flattening/near inversion
        'vix_min': 18.0,              # volatility rising
        'fed_funds_min': 3.0,         # high rates
    },
    'RECESSION': {
        'yield_curve_max': -0.1,      # deeply inverted (or normalizing from inversion)
        'vix_min': 25.0,              # elevated fear
        'unemployment_trend': 'rising',
    },
    'RECOVERY': {
        'yield_curve_min': -0.5,      # steepening from inversion
        'vix_max': 22.0,              # declining volatility
        'unemployment_trend': 'peaking_or_falling',
    },
}

# Allocation recommendations per regime
ALLOCATIONS = {
    'EXPANSION': {
        'equities': 0.70, 'bonds': 0.10, 'gold': 0.10, 'cash': 0.10,
        'notes': 'Full risk-on. Overweight growth, small cap.',
    },
    'LATE_CYCLE': {
        'equities': 0.50, 'bonds': 0.20, 'gold': 0.15, 'cash': 0.15,
        'notes': 'Reduce equities. Rotate to quality, gold, short duration.',
    },
    'RECESSION': {
        'equities': 0.25, 'bonds': 0.35, 'gold': 0.20, 'cash': 0.20,
        'notes': 'Defensive. Overweight bonds, gold, cash. Avoid cyclicals.',
    },
    'RECOVERY': {
        'equities': 0.60, 'bonds': 0.15, 'gold': 0.10, 'cash': 0.15,
        'notes': 'Early recovery. Add equities gradually, reduce cash.',
    },
}


# ─── Data Access ─────────────────────────────────────────────────────────────

def get_db():
    return sqlite3.connect(MARKET_DB)


def get_fred_series(series_id: str, limit: int = 60) -> list[tuple]:
    """Return [(date_str, value)] for a FRED series, most recent first."""
    conn = get_db()
    rows = conn.execute("""
        SELECT datetime(timestamp, 'unixepoch') as dt, value
        FROM economic_data
        WHERE series_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (series_id, limit)).fetchall()
    conn.close()
    return rows


def get_vix_series(limit: int = 60) -> list[tuple]:
    """Return [(date_str, value)] for VIX from prices table."""
    conn = get_db()
    rows = conn.execute("""
        SELECT datetime(timestamp, 'unixepoch') as dt, close
        FROM prices
        WHERE symbol = 'VIX' AND timeframe = '1d'
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def get_spy_monthly_returns() -> list[dict]:
    """Return monthly SPY returns for regime backtesting."""
    conn = get_db()
    rows = conn.execute("""
        SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as month,
               MIN(open) as open_price,
               MAX(close) as close_price,
               AVG(close) as avg_close
        FROM prices
        WHERE symbol = 'SPY' AND timeframe = '1d'
        GROUP BY month
        ORDER BY month ASC
    """).fetchall()
    conn.close()

    results = []
    for i in range(1, len(rows)):
        prev_close = rows[i-1][2]  # avg_close proxy
        curr_close = rows[i][2]
        if prev_close and prev_close > 0:
            ret = (curr_close - prev_close) / prev_close
            results.append({
                'month': rows[i][0],
                'spy_return': ret,
                'spy_close': curr_close,
            })
    return results


def latest_value(series: list[tuple]) -> Optional[float]:
    """Get the most recent value from a series."""
    if series:
        return series[0][1]
    return None


def trend_direction(series: list[tuple], lookback: int = 6) -> str:
    """Determine trend: rising, falling, flat."""
    if len(series) < lookback:
        return 'unknown'
    recent = [r[1] for r in series[:lookback] if r[1] is not None]
    if len(recent) < 2:
        return 'unknown'
    # Simple: compare first half avg vs second half avg
    mid = len(recent) // 2
    newer_avg = sum(recent[:mid]) / mid
    older_avg = sum(recent[mid:]) / (len(recent) - mid)
    diff = newer_avg - older_avg
    if abs(diff) < 0.05:
        return 'flat'
    return 'rising' if diff > 0 else 'falling'


def cpi_yoy(series: list[tuple]) -> Optional[float]:
    """Calculate CPI year-over-year change."""
    if len(series) < 13:
        return None
    current = series[0][1]
    year_ago = series[12][1]
    if year_ago and year_ago > 0:
        return (current - year_ago) / year_ago * 100
    return None


# ─── Regime Classification ───────────────────────────────────────────────────

def classify_regime(yc: float, ff: float, vix: float, unrate: float,
                    yc_trend: str, vix_trend: str, unrate_trend: str) -> tuple[str, float]:
    """
    Classify macro regime and return (regime_name, confidence).
    Returns the best-matching regime with a 0-1 confidence score.
    """
    scores = {}

    # ── EXPANSION ──
    exp_score = 0.0
    exp_factors = 0
    if yc is not None:
        if yc > 0.5:
            exp_score += 1.0
        elif yc > 0.0:
            exp_score += 0.5
        exp_factors += 1
    if vix is not None:
        if vix < 16:
            exp_score += 1.0
        elif vix < 20:
            exp_score += 0.5
        exp_factors += 1
    if unrate_trend in ('falling',):
        exp_score += 1.0
        exp_factors += 1
    elif unrate_trend == 'flat':
        exp_score += 0.5
        exp_factors += 1
    scores['EXPANSION'] = exp_score / max(exp_factors, 1)

    # ── LATE_CYCLE ──
    lc_score = 0.0
    lc_factors = 0
    if yc is not None:
        if yc < 0.3 and yc > -0.5:
            lc_score += 1.0
        elif yc < 0.7:
            lc_score += 0.5
        lc_factors += 1
    if ff is not None:
        if ff > 4.0:
            lc_score += 1.0
        elif ff > 2.5:
            lc_score += 0.5
        lc_factors += 1
    if vix is not None:
        if 18 <= vix <= 28:
            lc_score += 1.0
        elif vix > 15:
            lc_score += 0.5
        lc_factors += 1
    if vix_trend == 'rising':
        lc_score += 0.5
        lc_factors += 1
    scores['LATE_CYCLE'] = lc_score / max(lc_factors, 1)

    # ── RECESSION ──
    rec_score = 0.0
    rec_factors = 0
    if yc is not None:
        if yc < -0.3:
            rec_score += 1.0
        elif yc < 0:
            rec_score += 0.5
        rec_factors += 1
    if vix is not None:
        if vix > 28:
            rec_score += 1.0
        elif vix > 22:
            rec_score += 0.5
        rec_factors += 1
    if unrate_trend == 'rising':
        rec_score += 1.0
        rec_factors += 1
    scores['RECESSION'] = rec_score / max(rec_factors, 1)

    # ── RECOVERY ──
    rec2_score = 0.0
    rec2_factors = 0
    if yc_trend == 'rising':  # yield curve steepening
        rec2_score += 1.0
        rec2_factors += 1
    if vix is not None and vix < 22 and vix_trend == 'falling':
        rec2_score += 1.0
        rec2_factors += 1
    if ff is not None and ff < 3.0:
        rec2_score += 0.5
        rec2_factors += 1
    if unrate_trend in ('falling', 'flat'):
        rec2_score += 0.5
        rec2_factors += 1
    scores['RECOVERY'] = rec2_score / max(rec2_factors, 1)

    best_regime = max(scores, key=scores.get)
    confidence = scores[best_regime]
    return best_regime, round(confidence, 2)


def signal_label(indicator: str, value: float) -> str:
    """Human-readable signal label for an indicator value."""
    if indicator == 'yield_curve':
        if value > 1.0:   return 'STEEP'
        if value > 0.3:   return 'NORMAL'
        if value > 0.0:   return 'FLAT'
        if value > -0.5:  return 'INVERTED'
        return 'DEEPLY_INVERTED'

    if indicator == 'fed_funds':
        if value > 5.0:  return 'VERY_RESTRICTIVE'
        if value > 3.5:  return 'RESTRICTIVE'
        if value > 2.0:  return 'NEUTRAL'
        if value > 0.5:  return 'ACCOMMODATIVE'
        return 'VERY_ACCOMMODATIVE'

    if indicator == 'vix':
        if value > 35:  return 'PANIC'
        if value > 25:  return 'ELEVATED'
        if value > 20:  return 'CAUTIOUS'
        if value > 15:  return 'CALM'
        return 'VERY_CALM'

    if indicator == 'unemployment':
        if value > 7.0:  return 'HIGH'
        if value > 5.0:  return 'ELEVATED'
        if value > 4.0:  return 'STABLE'
        return 'LOW'

    if indicator == 'cpi_yoy':
        if value > 6.0:  return 'VERY_HIGH'
        if value > 3.5:  return 'HIGH'
        if value > 2.0:  return 'ABOVE_TARGET'
        if value > 1.0:  return 'AT_TARGET'
        return 'BELOW_TARGET'

    return 'N/A'


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_current(args):
    """Show current macro regime and all indicator signals."""
    print(f"\n{'═'*65}")
    print(f"  MACRO REGIME DETECTION  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═'*65}")

    # Fetch all indicators
    yc_data  = get_fred_series('T10Y2Y', 30)
    ff_data  = get_fred_series('FEDFUNDS', 30)
    cpi_data = get_fred_series('CPIAUCSL', 20)
    un_data  = get_fred_series('UNRATE', 30)
    vix_data = get_vix_series(30)

    yc_val   = latest_value(yc_data)
    ff_val   = latest_value(ff_data)
    cpi_val  = cpi_yoy(cpi_data) if len(cpi_data) >= 13 else None
    un_val   = latest_value(un_data)
    vix_val  = latest_value(vix_data)

    yc_trend    = trend_direction(yc_data, 6)
    vix_trend   = trend_direction(vix_data, 10)
    un_trend    = trend_direction(un_data, 6)

    if all(v is None for v in [yc_val, ff_val, un_val, vix_val]):
        print("  ERROR: No data found in database.")
        sys.exit(1)

    # Classify
    regime, confidence = classify_regime(
        yc=yc_val, ff=ff_val, vix=vix_val, unrate=un_val,
        yc_trend=yc_trend, vix_trend=vix_trend, unrate_trend=un_trend,
    )

    regime_emoji = {
        'EXPANSION': '🟢',
        'LATE_CYCLE': '🟡',
        'RECESSION': '🔴',
        'RECOVERY': '🔵',
    }.get(regime, '⚪')

    print(f"\n  {regime_emoji} REGIME:     {regime}")
    print(f"  CONFIDENCE:  {confidence*100:.0f}%")
    print()

    # Indicators table
    print(f"  {'INDICATOR':<18} {'VALUE':>8}  {'SIGNAL':<22} {'TREND'}")
    print(f"  {'-'*18} {'-'*8}  {'-'*22} {'-'*12}")

    if yc_val is not None:
        sig = signal_label('yield_curve', yc_val)
        print(f"  {'Yield Curve':<18} {yc_val:>7.2f}%  {sig:<22} {yc_trend}")

    if ff_val is not None:
        sig = signal_label('fed_funds', ff_val)
        print(f"  {'Fed Funds':<18} {ff_val:>7.2f}%  {sig:<22} {trend_direction(ff_data, 6)}")

    if vix_val is not None:
        sig = signal_label('vix', vix_val)
        print(f"  {'VIX':<18} {vix_val:>7.1f}   {sig:<22} {vix_trend}")

    if un_val is not None:
        sig = signal_label('unemployment', un_val)
        print(f"  {'Unemployment':<18} {un_val:>7.1f}%  {sig:<22} {un_trend}")

    if cpi_val is not None:
        sig = signal_label('cpi_yoy', cpi_val)
        print(f"  {'CPI (YoY)':<18} {cpi_val:>7.1f}%  {sig:<22} —")

    # Allocation recommendation
    alloc = ALLOCATIONS.get(regime, {})
    print()
    print(f"  ALLOCATION RECOMMENDATION:")
    if alloc:
        print(f"  Equities: {alloc.get('equities',0)*100:.0f}%  "
              f"Bonds: {alloc.get('bonds',0)*100:.0f}%  "
              f"Gold: {alloc.get('gold',0)*100:.0f}%  "
              f"Cash: {alloc.get('cash',0)*100:.0f}%")
        print(f"  → {alloc.get('notes','')}")

    # JSON output for programmatic use
    output = {
        'regime': regime,
        'confidence': confidence,
        'indicators': {
            'yield_curve': {
                'value': yc_val,
                'signal': signal_label('yield_curve', yc_val) if yc_val else None,
                'trend': yc_trend,
            },
            'fed_funds': {
                'value': ff_val,
                'signal': signal_label('fed_funds', ff_val) if ff_val else None,
                'trend': trend_direction(ff_data, 6),
            },
            'vix': {
                'value': vix_val,
                'signal': signal_label('vix', vix_val) if vix_val else None,
                'trend': vix_trend,
            },
            'unemployment': {
                'value': un_val,
                'signal': signal_label('unemployment', un_val) if un_val else None,
                'trend': un_trend,
            },
            'cpi_yoy': {
                'value': cpi_val,
                'signal': signal_label('cpi_yoy', cpi_val) if cpi_val else None,
            },
        },
        'allocation_recommendation': {
            'equities': alloc.get('equities', 0),
            'bonds': alloc.get('bonds', 0),
            'gold': alloc.get('gold', 0),
            'cash': alloc.get('cash', 0),
        },
        'timestamp': datetime.now().isoformat()[:19],
    }

    print()
    print(f"  Rule of Acquisition #34: War is good for business.")
    print(f"  (Know your regime. Trade accordingly.)")

    if getattr(args, 'json', False):
        print()
        print(json.dumps(output, indent=2))


def cmd_history(args):
    """Show monthly regime timeline from 2010 to present."""
    print(f"\n{'═'*70}")
    print(f"  MACRO REGIME TIMELINE  |  Monthly 2010–{date.today().year}")
    print(f"{'═'*70}")

    conn = get_db()

    # Get monthly data for all indicators
    def get_monthly_fred(series_id):
        rows = conn.execute("""
            SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as month,
                   AVG(value) as avg_val
            FROM economic_data
            WHERE series_id = ? AND timestamp >= strftime('%s', '2010-01-01')
            GROUP BY month
            ORDER BY month ASC
        """, (series_id,)).fetchall()
        return {r[0]: r[1] for r in rows}

    def get_monthly_vix():
        rows = conn.execute("""
            SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as month,
                   AVG(close) as avg_vix
            FROM prices
            WHERE symbol = 'VIX' AND timestamp >= strftime('%s', '2010-01-01')
            GROUP BY month
            ORDER BY month ASC
        """).fetchall()
        return {r[0]: r[1] for r in rows}

    yc_monthly = get_monthly_fred('T10Y2Y')
    ff_monthly = get_monthly_fred('FEDFUNDS')
    un_monthly = get_monthly_fred('UNRATE')
    vix_monthly = get_monthly_vix()
    conn.close()

    # Get all months
    all_months = sorted(set(list(yc_monthly.keys()) + list(vix_monthly.keys())))

    regimes_by_month = {}
    prev_regime = None

    print(f"\n  {'Month':<10} {'Regime':<14} {'YC':>7} {'VIX':>6} {'UNRATE':>8} {'FF':>6}")
    print(f"  {'-'*10} {'-'*14} {'-'*7} {'-'*6} {'-'*8} {'-'*6}")

    for month in all_months:
        yc  = yc_monthly.get(month)
        ff  = ff_monthly.get(month)
        vix = vix_monthly.get(month)
        un  = un_monthly.get(month)

        if not any([yc, vix]):
            continue

        regime, conf = classify_regime(
            yc=yc, ff=ff, vix=vix, unrate=un,
            yc_trend='flat', vix_trend='flat', unrate_trend='flat',
        )

        regimes_by_month[month] = regime

        # Mark transitions
        marker = '◄ NEW' if regime != prev_regime else ''
        if regime != prev_regime:
            print(f"  {'':10} {'─'*14}")

        emoji = {'EXPANSION': '🟢', 'LATE_CYCLE': '🟡', 'RECESSION': '🔴', 'RECOVERY': '🔵'}.get(regime, '⚪')
        yc_s  = f"{yc:+.2f}" if yc is not None else '  N/A'
        vix_s = f"{vix:.1f}" if vix is not None else ' N/A'
        un_s  = f"{un:.1f}%" if un is not None else '  N/A'
        ff_s  = f"{ff:.2f}" if ff is not None else ' N/A'

        print(f"  {month:<10} {emoji}{regime:<13} {yc_s:>7} {vix_s:>6} {un_s:>8} {ff_s:>6}  {marker}")
        prev_regime = regime

    # Count months per regime
    print(f"\n  REGIME DISTRIBUTION:")
    from collections import Counter
    counts = Counter(regimes_by_month.values())
    total = sum(counts.values())
    for r, n in sorted(counts.items(), key=lambda x: -x[1]):
        pct = n / total * 100
        bar = '█' * int(pct / 3)
        print(f"  {r:<14} {n:3d} months ({pct:.0f}%)  {bar}")


def cmd_backtest(args):
    """Show SPY returns by regime."""
    print(f"\n{'═'*65}")
    print(f"  SPY RETURNS BY MACRO REGIME")
    print(f"{'═'*65}")

    conn = get_db()

    # Monthly SPY returns
    spy_rows = conn.execute("""
        SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as month,
               MIN(open) as first_open,
               (SELECT close FROM prices p2
                WHERE p2.symbol = 'SPY'
                  AND strftime('%Y-%m', datetime(p2.timestamp, 'unixepoch')) = strftime('%Y-%m', datetime(p.timestamp, 'unixepoch'))
                  AND p2.timeframe = '1d'
                ORDER BY p2.timestamp DESC LIMIT 1) as last_close
        FROM prices p
        WHERE symbol = 'SPY' AND timeframe = '1d'
          AND timestamp >= strftime('%s', '2010-01-01')
        GROUP BY month
        ORDER BY month
    """).fetchall()

    def get_monthly_fred(series_id):
        rows = conn.execute("""
            SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as month,
                   AVG(value) as avg_val
            FROM economic_data
            WHERE series_id = ? AND timestamp >= strftime('%s', '2010-01-01')
            GROUP BY month ORDER BY month
        """, (series_id,)).fetchall()
        return {r[0]: r[1] for r in rows}

    def get_monthly_vix():
        rows = conn.execute("""
            SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as month,
                   AVG(close) as avg_vix
            FROM prices
            WHERE symbol = 'VIX' AND timestamp >= strftime('%s', '2010-01-01')
            GROUP BY month ORDER BY month
        """).fetchall()
        return {r[0]: r[1] for r in rows}

    yc_monthly  = get_monthly_fred('T10Y2Y')
    ff_monthly  = get_monthly_fred('FEDFUNDS')
    un_monthly  = get_monthly_fred('UNRATE')
    vix_monthly = get_monthly_vix()
    conn.close()

    # Group SPY returns by regime
    from collections import defaultdict
    regime_returns = defaultdict(list)

    for i in range(1, len(spy_rows)):
        month = spy_rows[i][0]
        prev_close = spy_rows[i-1][2]
        curr_close = spy_rows[i][2]
        if prev_close and curr_close and prev_close > 0:
            monthly_ret = (curr_close - prev_close) / prev_close

            yc  = yc_monthly.get(month)
            ff  = ff_monthly.get(month)
            vix = vix_monthly.get(month)
            un  = un_monthly.get(month)

            if yc is not None or vix is not None:
                regime, _ = classify_regime(
                    yc=yc, ff=ff, vix=vix, unrate=un,
                    yc_trend='flat', vix_trend='flat', unrate_trend='flat',
                )
                regime_returns[regime].append(monthly_ret)

    print()
    print(f"  {'REGIME':<14} {'N':>5} {'Avg Mo Ret':>12} {'Ann. Ret':>10} {'Win Rate':>10} {'Best Mo':>10} {'Worst Mo':>10}")
    print(f"  {'-'*14} {'-'*5} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    order = ['EXPANSION', 'LATE_CYCLE', 'RECOVERY', 'RECESSION']
    for regime in order:
        rets = regime_returns.get(regime, [])
        if not rets:
            continue
        n = len(rets)
        avg_mo = sum(rets) / n
        ann = (1 + avg_mo) ** 12 - 1
        win_rate = sum(1 for r in rets if r > 0) / n
        best = max(rets)
        worst = min(rets)

        emoji = {'EXPANSION': '🟢', 'LATE_CYCLE': '🟡', 'RECESSION': '🔴', 'RECOVERY': '🔵'}.get(regime, '⚪')
        print(f"  {emoji}{regime:<13} {n:>5} {avg_mo*100:>+11.2f}% {ann*100:>+9.1f}% {win_rate*100:>9.0f}% {best*100:>+9.1f}% {worst*100:>+9.1f}%")

    print()
    print(f"  NOTE: Monthly returns classified using contemporaneous macro data.")
    print(f"  Rule of Acquisition #74: Knowledge equals profit.")
    print(f"  (Know your regime before sizing your position.)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Macro Regime Detection — Signal Research',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  current     Show current regime, all indicators, and allocation recommendation
  history     Show monthly regime timeline (2010 to present)
  backtest    Show SPY returns by regime

Examples:
  python3 macro_regime.py current
  python3 macro_regime.py history
  python3 macro_regime.py backtest
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    cur = subparsers.add_parser('current', help='Current regime')
    cur.add_argument('--json', action='store_true', help='Output raw JSON')

    subparsers.add_parser('history', help='Regime timeline')
    subparsers.add_parser('backtest', help='SPY returns by regime')

    args = parser.parse_args()

    if args.command == 'current':
        cmd_current(args)
    elif args.command == 'history':
        cmd_history(args)
    elif args.command == 'backtest':
        cmd_backtest(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
