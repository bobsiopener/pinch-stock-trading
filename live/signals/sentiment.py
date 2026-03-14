#!/usr/bin/env python3
"""
Pinch Stock Trading — Sentiment / Alternative Data
Issue #29: VIX-based sentiment, market breadth, momentum, composite score.

Usage:
    python3 sentiment.py current              — show all sentiment indicators
    python3 sentiment.py history [--days 30]  — sentiment over time
    python3 sentiment.py signals              — actionable signals

Rule of Acquisition #62: The riskier the road, the greater the profit.
(But know when the crowd is wrong — and bet against them.)
"""

import sqlite3
import argparse
import sys
from datetime import datetime, date, timedelta
from typing import Optional

# ─── Config ──────────────────────────────────────────────────────────────────

MARKET_DB = '/mnt/media/market_data/pinch_market.db'

# Full universe from our DB (38 equity-like symbols including ETFs + stocks)
UNIVERSE = [
    # Stocks
    'AAPL', 'AMD', 'AMZN', 'ANET', 'AVGO', 'BRK-B', 'CSCO', 'GOOG',
    'META', 'MSFT', 'MSTR', 'NVDA', 'ORCL', 'PLTR', 'TSLA', 'WFC',
    # ETFs
    'SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'SHY', 'HYG', 'LQD',
    'XLK', 'XLE', 'XLF', 'XLV', 'XBI', 'SMH', 'EEM', 'FXI',
    'EWJ', 'ARKK', 'COPX', 'SLV', 'USO', 'UNG',
]

# VIX thresholds
VIX_EXTREME_FEAR  = 30.0   # Contrarian BUY zone
VIX_FEAR          = 25.0   # Elevated fear
VIX_CAUTION       = 20.0   # Cautious territory
VIX_CALM          = 15.0   # Calm market

# Breadth thresholds (% above 200d SMA)
BREADTH_BULL        = 0.70  # > 70% = healthy bull
BREADTH_BEAR        = 0.30  # < 30% = bear market
BREADTH_EXTREME_LOW = 0.20  # < 20% = extreme bearish (contrarian BUY!)

# Sentiment score thresholds
SCORE_BUY_ZONE     = -50   # Contrarian buy
SCORE_CAUTION_ZONE = +50   # Caution / trim


# ─── Data Access ─────────────────────────────────────────────────────────────

def get_db():
    return sqlite3.connect(MARKET_DB)


def get_prices(symbol: str, days: int = 260) -> list[tuple]:
    """Return [(timestamp, close)] for a symbol, most recent first."""
    conn = get_db()
    rows = conn.execute("""
        SELECT timestamp, close
        FROM prices
        WHERE symbol = ? AND timeframe = '1d'
        ORDER BY timestamp DESC
        LIMIT ?
    """, (symbol, days)).fetchall()
    conn.close()
    return rows


def get_all_prices_recent(symbols: list[str], days: int = 260) -> dict[str, list[tuple]]:
    """Batch fetch prices for multiple symbols."""
    conn = get_db()
    placeholders = ','.join('?' * len(symbols))
    rows = conn.execute(f"""
        SELECT symbol, timestamp, close
        FROM prices
        WHERE symbol IN ({placeholders}) AND timeframe = '1d'
        ORDER BY symbol, timestamp DESC
    """, symbols).fetchall()
    conn.close()

    result = {}
    for row in rows:
        sym, ts, close = row
        if sym not in result:
            result[sym] = []
        if len(result[sym]) < days:
            result[sym].append((ts, close))
    return result


def get_vix_series(days: int = 300) -> list[tuple]:
    """Return [(timestamp, close)] for VIX."""
    return get_prices('VIX', days)


def get_vix_term_structure() -> Optional[dict]:
    """Return latest VIX term structure (spot, 3m, 6m)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT expiry, vix_value, days_to_expiry
        FROM vix_term_structure
        WHERE timestamp = (SELECT MAX(timestamp) FROM vix_term_structure)
        ORDER BY days_to_expiry
    """).fetchall()
    conn.close()
    if not rows:
        return None
    return {r[0]: {'value': r[1], 'days': r[2]} for r in rows}


# ─── VIX Sentiment ───────────────────────────────────────────────────────────

def calc_vix_sentiment(vix_series: list[tuple]) -> dict:
    """Calculate VIX-based sentiment metrics."""
    if not vix_series:
        return {}

    current_vix = vix_series[0][1]

    # VIX percentile vs last 252 trading days
    lookback = min(252, len(vix_series))
    past_vix = [v[1] for v in vix_series[:lookback] if v[1] is not None]
    below = sum(1 for v in past_vix if v < current_vix)
    percentile = below / len(past_vix) * 100 if past_vix else 50.0

    # Signal classification
    if current_vix > VIX_EXTREME_FEAR:
        signal = 'EXTREME_FEAR'
        note = 'Contrarian BUY signal — historically high win rate!'
    elif current_vix > VIX_FEAR:
        signal = 'FEAR'
        note = 'Elevated fear. Start watching for entries.'
    elif current_vix > VIX_CAUTION:
        signal = 'CAUTION'
        note = 'Cautious. Moderate hedging advised.'
    elif current_vix > VIX_CALM:
        signal = 'NEUTRAL'
        note = 'Normal volatility. No special action.'
    else:
        signal = 'COMPLACENCY'
        note = 'Very low VIX — potential complacency. Reduce risk.'

    # Put/call proxy score: VIX-based (-50 to +50 contribution)
    # High VIX = fear = contrarian bullish = positive score contribution
    if current_vix > 30:
        pc_score = +40   # extreme fear = very bullish contrarian
    elif current_vix > 25:
        pc_score = +20
    elif current_vix > 20:
        pc_score = 0
    elif current_vix > 15:
        pc_score = -10
    else:
        pc_score = -20   # complacency = bearish for future returns

    return {
        'current_vix': current_vix,
        'percentile': round(percentile, 1),
        'signal': signal,
        'note': note,
        'pc_proxy_score': pc_score,
        'lookback_days': lookback,
    }


def calc_term_structure(ts: Optional[dict]) -> dict:
    """Analyze VIX term structure."""
    if not ts:
        return {'available': False}

    spot = ts.get('spot', {}).get('value')
    m3   = ts.get('3m', {}).get('value')
    m6   = ts.get('6m', {}).get('value')

    if not spot or not m3:
        return {'available': False, 'spot': spot}

    spread = m3 - spot
    if spread > 1.5:
        structure = 'CONTANGO'
        note = 'Calm market — futures pricing in normalization'
    elif spread > 0:
        structure = 'SLIGHT_CONTANGO'
        note = 'Near-normal. Mild complacency.'
    elif spread > -1.5:
        structure = 'BACKWARDATION'
        note = 'Stress! Near-term fear elevated vs future'
    else:
        structure = 'STEEP_BACKWARDATION'
        note = 'Severe near-term stress. Market in crisis mode.'

    return {
        'available': True,
        'spot': spot,
        '3m': m3,
        '6m': m6,
        'spread_3m': round(spread, 2),
        'structure': structure,
        'note': note,
    }


# ─── Market Breadth ──────────────────────────────────────────────────────────

def calc_breadth(all_prices: dict) -> dict:
    """Calculate % of universe above 200-day SMA and advance/decline."""
    above_200 = 0
    below_200 = 0
    advances = 0
    declines = 0
    valid = 0
    sma_detail = {}

    for symbol in UNIVERSE:
        prices = all_prices.get(symbol, [])
        closes = [p[1] for p in prices if p[1] is not None]

        if len(closes) < 5:
            continue

        current = closes[0]
        valid += 1

        # 200-day SMA
        if len(closes) >= 200:
            sma200 = sum(closes[:200]) / 200
            above = current > sma200
            sma_detail[symbol] = {
                'above': above,
                'sma200': round(sma200, 2),
                'current': round(current, 2),
                'pct_from_sma': round((current - sma200) / sma200 * 100, 1),
            }
            if above:
                above_200 += 1
            else:
                below_200 += 1

        # Advance/Decline: today vs yesterday
        if len(closes) >= 2:
            if closes[0] > closes[1]:
                advances += 1
            else:
                declines += 1

    total_sma = above_200 + below_200
    pct_above = above_200 / total_sma if total_sma > 0 else 0.5

    total_ad = advances + declines
    ad_ratio = advances / total_ad if total_ad > 0 else 0.5

    # Breadth signal
    if pct_above > BREADTH_BULL:
        breadth_signal = 'HEALTHY_BULL'
        note = 'Strong participation. Bull market well-supported.'
    elif pct_above > BREADTH_BEAR:
        breadth_signal = 'MIXED'
        note = 'Mixed market. Some sectors leading, others lagging.'
    elif pct_above > BREADTH_EXTREME_LOW:
        breadth_signal = 'BEAR'
        note = 'Bear market conditions. Defensive positioning recommended.'
    else:
        breadth_signal = 'EXTREME_BEARISH'
        note = 'Extreme bearish breadth — contrarian BUY zone!'

    # Breadth score contribution (-50 to +50)
    if pct_above < 0.20:
        breadth_score = +40   # extreme low = contrarian buy
    elif pct_above < 0.30:
        breadth_score = +15
    elif pct_above < 0.50:
        breadth_score = -10
    elif pct_above < 0.70:
        breadth_score = +10
    else:
        breadth_score = +20   # very healthy breadth

    return {
        'pct_above_200d': round(pct_above, 3),
        'above_200d': above_200,
        'below_200d': below_200,
        'total_valid': total_sma,
        'signal': breadth_signal,
        'note': note,
        'breadth_score': breadth_score,
        'ad_ratio': round(ad_ratio, 3),
        'advances': advances,
        'declines': declines,
        'detail': sma_detail,
    }


# ─── Momentum Breadth ────────────────────────────────────────────────────────

def calc_momentum(all_prices: dict) -> dict:
    """Calculate momentum breadth metrics."""
    pos_3m = 0
    neg_3m = 0
    returns_6m = []
    valid = 0

    TRADING_DAYS_3M = 63
    TRADING_DAYS_6M = 126

    for symbol in UNIVERSE:
        prices = all_prices.get(symbol, [])
        closes = [p[1] for p in prices if p[1] is not None]

        if len(closes) < TRADING_DAYS_3M:
            continue

        valid += 1
        current = closes[0]

        # 3-month return
        close_3m_ago = closes[min(TRADING_DAYS_3M, len(closes)-1)]
        ret_3m = (current - close_3m_ago) / close_3m_ago
        if ret_3m > 0:
            pos_3m += 1
        else:
            neg_3m += 1

        # 6-month return
        if len(closes) >= TRADING_DAYS_6M:
            close_6m_ago = closes[min(TRADING_DAYS_6M, len(closes)-1)]
            ret_6m = (current - close_6m_ago) / close_6m_ago
            returns_6m.append(ret_6m)

    total_3m = pos_3m + neg_3m
    pct_pos_3m = pos_3m / total_3m if total_3m > 0 else 0.5
    avg_6m = sum(returns_6m) / len(returns_6m) if returns_6m else 0

    # Check for divergence: SPY 3m return vs breadth
    spy_prices = all_prices.get('SPY', [])
    spy_closes = [p[1] for p in spy_prices if p[1] is not None]
    spy_3m_ret = None
    divergence = False
    divergence_note = ''

    if len(spy_closes) >= TRADING_DAYS_3M:
        spy_3m_ret = (spy_closes[0] - spy_closes[TRADING_DAYS_3M]) / spy_closes[TRADING_DAYS_3M]
        # Divergence: SPY up but breadth < 50%
        if spy_3m_ret > 0.02 and pct_pos_3m < 0.50:
            divergence = True
            divergence_note = '⚠️  INDEX UP but BREADTH DECLINING — potential warning!'
        elif spy_3m_ret < -0.02 and pct_pos_3m > 0.60:
            divergence = True
            divergence_note = '💡 INDEX DOWN but BREADTH STRONG — potential recovery signal!'

    # Momentum score contribution (-50 to +50)
    if pct_pos_3m > 0.70:
        mom_score = +25
    elif pct_pos_3m > 0.50:
        mom_score = +10
    elif pct_pos_3m > 0.30:
        mom_score = -10
    else:
        mom_score = -25

    return {
        'pct_positive_3m': round(pct_pos_3m, 3),
        'positive_3m': pos_3m,
        'negative_3m': neg_3m,
        'avg_6m_return': round(avg_6m * 100, 2),
        'spy_3m_return': round(spy_3m_ret * 100, 2) if spy_3m_ret is not None else None,
        'divergence': divergence,
        'divergence_note': divergence_note,
        'momentum_score': mom_score,
        'valid_symbols': valid,
    }


# ─── Composite Score ─────────────────────────────────────────────────────────

def calc_composite(vix_sent: dict, breadth: dict, momentum: dict) -> dict:
    """Calculate composite sentiment score (-100 to +100)."""
    # Component scores (each -50 to +50)
    vix_score     = vix_sent.get('pc_proxy_score', 0)
    breadth_score = breadth.get('breadth_score', 0)
    mom_score     = momentum.get('momentum_score', 0)

    # Weighted average: VIX 40%, breadth 35%, momentum 25%
    raw = (vix_score * 0.40) + (breadth_score * 0.35) + (mom_score * 0.25)
    # Scale to -100 to +100
    score = max(-100, min(100, raw * 2))

    if score < SCORE_BUY_ZONE:
        zone = 'EXTREME_FEAR'
        action = '🟢 CONTRARIAN BUY ZONE — accumulate quality'
    elif score < -20:
        zone = 'FEAR'
        action = '🔵 FEAR — watch for entries, not panic'
    elif score < +20:
        zone = 'NEUTRAL'
        action = '⚪ NEUTRAL — normal allocation, no special action'
    elif score < SCORE_CAUTION_ZONE:
        zone = 'GREED'
        action = '🟡 GREED — start trimming winners, raise cash'
    else:
        zone = 'EXTREME_GREED'
        action = '🔴 EXTREME GREED — defensive posture, reduce exposure'

    return {
        'score': round(score, 1),
        'zone': zone,
        'action': action,
        'components': {
            'vix_score': vix_score,
            'breadth_score': breadth_score,
            'momentum_score': mom_score,
        },
    }


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_current(args):
    """Show all current sentiment indicators."""
    print(f"\n{'═'*65}")
    print(f"  SENTIMENT DASHBOARD  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═'*65}")

    # Fetch data
    vix_series = get_vix_series(300)
    ts_data    = get_vix_term_structure()
    all_prices = get_all_prices_recent(UNIVERSE, 260)

    # Calculate indicators
    vix_sent  = calc_vix_sentiment(vix_series)
    term_str  = calc_term_structure(ts_data)
    breadth   = calc_breadth(all_prices)
    momentum  = calc_momentum(all_prices)
    composite = calc_composite(vix_sent, breadth, momentum)

    # ── Composite Score ──
    score = composite['score']
    bar_len = int((score + 100) / 200 * 40)
    bar = '─' * bar_len + '◉' + '─' * (40 - bar_len)
    print(f"\n  COMPOSITE SENTIMENT SCORE: {score:+.0f} / 100")
    print(f"  [-100 FEAR  {bar}  GREED +100]")
    print(f"  {composite['action']}")

    # ── VIX Section ──
    print(f"\n  {'─'*60}")
    print(f"  VIX SENTIMENT")
    if vix_sent:
        print(f"  VIX Level:    {vix_sent['current_vix']:.1f}  →  {vix_sent['signal']}")
        print(f"  Percentile:   {vix_sent['percentile']:.0f}th (vs last {vix_sent['lookback_days']} days)")
        print(f"  Note:         {vix_sent['note']}")

    if term_str.get('available'):
        print(f"\n  VIX Term Structure:")
        print(f"  Spot: {term_str['spot']:.1f}  |  3M: {term_str['3m']:.1f}  |  6M: {term_str.get('6m', 'N/A')}")
        print(f"  Structure: {term_str['structure']}  (3M spread: {term_str['spread_3m']:+.2f})")
        print(f"  → {term_str['note']}")

    # ── Market Breadth ──
    print(f"\n  {'─'*60}")
    print(f"  MARKET BREADTH")
    if breadth:
        pct = breadth['pct_above_200d'] * 100
        bar_b = '█' * int(pct / 3.33) + '░' * (30 - int(pct / 3.33))
        print(f"  Above 200d SMA: {pct:.0f}%  [{bar_b}]  ({breadth['above_200d']}/{breadth['total_valid']} symbols)")
        print(f"  Signal:         {breadth['signal']}")
        print(f"  Note:           {breadth['note']}")
        ad = breadth['ad_ratio'] * 100
        print(f"  Adv/Decl:       {breadth['advances']}↑  {breadth['declines']}↓  (ratio: {ad:.0f}% advancing)")

    # ── Momentum Breadth ──
    print(f"\n  {'─'*60}")
    print(f"  MOMENTUM BREADTH")
    if momentum:
        pct_3m = momentum['pct_positive_3m'] * 100
        bar_m = '█' * int(pct_3m / 3.33) + '░' * (30 - int(pct_3m / 3.33))
        print(f"  Positive 3M:    {pct_3m:.0f}%  [{bar_m}]  ({momentum['positive_3m']}/{momentum['positive_3m']+momentum['negative_3m']} symbols)")
        print(f"  Avg 6M Return:  {momentum['avg_6m_return']:+.1f}%")
        if momentum.get('spy_3m_return') is not None:
            print(f"  SPY 3M Return:  {momentum['spy_3m_return']:+.1f}%")
        if momentum.get('divergence'):
            print(f"  {momentum['divergence_note']}")

    # ── Score Breakdown ──
    print(f"\n  {'─'*60}")
    print(f"  SCORE BREAKDOWN:")
    c = composite['components']
    print(f"  VIX/P-C proxy:  {c['vix_score']:+d}  (weight 40%)")
    print(f"  Breadth:        {c['breadth_score']:+d}  (weight 35%)")
    print(f"  Momentum:       {c['momentum_score']:+d}  (weight 25%)")
    print(f"  Composite:      {composite['score']:+.0f}")

    print(f"\n  Rule of Acquisition #62: The riskier the road, the greater the profit.")


def cmd_history(args):
    """Show sentiment over time."""
    days = args.days
    print(f"\n{'═'*65}")
    print(f"  SENTIMENT HISTORY  |  Last {days} days")
    print(f"{'═'*65}\n")

    vix_series = get_vix_series(days + 30)

    if not vix_series:
        print("  No VIX data available.")
        return

    print(f"  {'Date':<12} {'VIX':>6} {'Pct':>6} {'Signal':<20} {'Score':>7}")
    print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*20} {'-'*7}")

    all_prices = get_all_prices_recent(UNIVERSE, days + 50)

    # Show last N days
    shown = 0
    for i in range(min(days, len(vix_series))):
        row = vix_series[i]
        vix_val = row[1]
        dt_str = datetime.fromtimestamp(row[0]).strftime('%Y-%m-%d')

        if vix_val is None:
            continue

        # VIX percentile vs prior 252 days from this point
        window = vix_series[i:i+252]
        vals = [v[1] for v in window if v[1] is not None]
        pct = sum(1 for v in vals if v < vix_val) / len(vals) * 100 if vals else 50

        if vix_val > VIX_EXTREME_FEAR:
            sig = 'EXTREME_FEAR'
            vix_score = +40
        elif vix_val > VIX_FEAR:
            sig = 'FEAR'
            vix_score = +20
        elif vix_val > VIX_CAUTION:
            sig = 'CAUTION'
            vix_score = 0
        elif vix_val > VIX_CALM:
            sig = 'NEUTRAL'
            vix_score = -10
        else:
            sig = 'COMPLACENCY'
            vix_score = -20

        print(f"  {dt_str:<12} {vix_val:>6.1f} {pct:>5.0f}%  {sig:<20} {vix_score:>+7d}")
        shown += 1
        if shown >= days:
            break

    print(f"\n  (Showing VIX-based sentiment — run 'current' for full multi-factor score)")


def cmd_signals(args):
    """Show actionable signals from sentiment data."""
    print(f"\n{'═'*65}")
    print(f"  ACTIONABLE SIGNALS  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═'*65}")

    vix_series = get_vix_series(300)
    ts_data    = get_vix_term_structure()
    all_prices = get_all_prices_recent(UNIVERSE, 260)

    vix_sent  = calc_vix_sentiment(vix_series)
    term_str  = calc_term_structure(ts_data)
    breadth   = calc_breadth(all_prices)
    momentum  = calc_momentum(all_prices)
    composite = calc_composite(vix_sent, breadth, momentum)

    signals = []

    # VIX signals
    if vix_sent:
        vix = vix_sent['current_vix']
        if vix > VIX_EXTREME_FEAR:
            signals.append({
                'priority': 1,
                'type': 'BUY',
                'signal': f'VIX EXTREME FEAR ({vix:.1f} > {VIX_EXTREME_FEAR})',
                'action': 'Contrarian buy signal. Historically > 80% win rate. Deploy cash, buy dips.',
                'source': 'VIX'
            })
        elif vix > VIX_FEAR:
            signals.append({
                'priority': 2,
                'type': 'WATCH',
                'signal': f'VIX ELEVATED ({vix:.1f} > {VIX_FEAR})',
                'action': 'Fear elevated. Start watching for entries. Avoid panic selling.',
                'source': 'VIX'
            })
        elif vix < VIX_CALM:
            signals.append({
                'priority': 3,
                'type': 'CAUTION',
                'signal': f'VIX VERY LOW ({vix:.1f} < {VIX_CALM})',
                'action': 'Complacency warning. Consider buying puts or trimming longs.',
                'source': 'VIX'
            })

    # Term structure
    if term_str.get('available') and term_str.get('structure') == 'STEEP_BACKWARDATION':
        signals.append({
            'priority': 1,
            'type': 'ALERT',
            'signal': 'VIX TERM STRUCTURE: STEEP BACKWARDATION',
            'action': 'Crisis mode. Near-term fear >> future. Reduce risk immediately.',
            'source': 'VIX Term'
        })

    # Breadth signals
    if breadth:
        pct = breadth['pct_above_200d']
        if pct < BREADTH_EXTREME_LOW:
            signals.append({
                'priority': 1,
                'type': 'BUY',
                'signal': f'BREADTH EXTREME LOW ({pct*100:.0f}% above 200d)',
                'action': 'Extreme bearish breadth = contrarian BUY. Historical win rate very high.',
                'source': 'Breadth'
            })
        elif pct < BREADTH_BEAR:
            signals.append({
                'priority': 2,
                'type': 'DEFENSIVE',
                'signal': f'BEAR MARKET BREADTH ({pct*100:.0f}% above 200d)',
                'action': 'Bear market conditions. Stay defensive. Wait for breadth recovery.',
                'source': 'Breadth'
            })

    # Divergence
    if momentum.get('divergence'):
        signals.append({
            'priority': 2,
            'type': 'WARNING',
            'signal': 'BREADTH DIVERGENCE DETECTED',
            'action': momentum.get('divergence_note', ''),
            'source': 'Momentum'
        })

    # Composite score signals
    score = composite['score']
    if score < SCORE_BUY_ZONE:
        signals.append({
            'priority': 1,
            'type': 'BUY',
            'signal': f'COMPOSITE SCORE: {score:+.0f} (EXTREME FEAR)',
            'action': composite['action'],
            'source': 'Composite'
        })
    elif score > SCORE_CAUTION_ZONE:
        signals.append({
            'priority': 2,
            'type': 'TRIM',
            'signal': f'COMPOSITE SCORE: {score:+.0f} (EXTREME GREED)',
            'action': composite['action'],
            'source': 'Composite'
        })

    if not signals:
        signals.append({
            'priority': 5,
            'type': 'NEUTRAL',
            'signal': 'No extreme signals detected',
            'action': f'Composite score: {score:+.0f}. Normal market conditions. Maintain allocation.',
            'source': 'All'
        })

    # Print signals sorted by priority
    print()
    for s in sorted(signals, key=lambda x: x['priority']):
        type_emoji = {
            'BUY': '🟢', 'SELL': '🔴', 'TRIM': '🟡',
            'ALERT': '🚨', 'WARNING': '⚠️ ', 'CAUTION': '🟡',
            'DEFENSIVE': '🔵', 'WATCH': '👀', 'NEUTRAL': '⚪',
        }.get(s['type'], '⚪')
        print(f"  {type_emoji} [{s['type']:9s}] {s['signal']}")
        print(f"     → {s['action']}")
        print(f"     Source: {s['source']}")
        print()

    print(f"  Rule of Acquisition #62: The riskier the road, the greater the profit.")
    print(f"  (But only take the risk when the signals are with you.)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Sentiment / Alternative Data — Signal Research',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  current              Show all sentiment indicators
  history [--days N]   Sentiment over time (default: 30 days)
  signals              Actionable signals from sentiment data

Examples:
  python3 sentiment.py current
  python3 sentiment.py history --days 60
  python3 sentiment.py signals
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('current', help='All current indicators')
    hist = subparsers.add_parser('history', help='Sentiment over time')
    hist.add_argument('--days', type=int, default=30, help='Number of days (default: 30)')
    subparsers.add_parser('signals', help='Actionable signals')

    args = parser.parse_args()

    if args.command == 'current':
        cmd_current(args)
    elif args.command == 'history':
        cmd_history(args)
    elif args.command == 'signals':
        cmd_signals(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
