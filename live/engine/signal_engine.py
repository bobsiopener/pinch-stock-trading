#!/usr/bin/env python3
"""
Pinch Stock Signal Engine — Daily automated signal generation
Runs at 4:35 PM ET (after data collection) and 9:35 AM ET (pre-market)
Rule of Acquisition #22: A wise man can hear profit in the wind.
"""

import sqlite3
import numpy as np
import json
import os
import sys
import subprocess
import time
from datetime import datetime, timezone, timedelta

DB_PATH = '/mnt/media/market_data/pinch_market.db'
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'state')
SIGNALS_FILE = os.path.join(STATE_DIR, 'daily_signals.json')
CONNORS_FILE = os.path.join(STATE_DIR, 'connors_positions.json')

# All tracked symbols
STOCK_SYMBOLS = [
    'SPY', 'QQQ', 'IWM', 'AAPL', 'NVDA', 'MSFT', 'GOOG', 'AMZN', 'TSLA',
    'AMD', 'PLTR', 'ANET', 'META', 'AVGO', 'BRK-B', 'CSCO', 'WFC', 'ORCL',
    'GLD', 'TLT', 'XLE', 'MSTR',
    'XLK', 'XLF', 'XLV', 'XBI', 'ARKK', 'SMH',
    'EEM', 'FXI', 'EWJ', 'HYG', 'LQD', 'SHY', 'SLV', 'USO', 'UNG', 'COPX',
]

# Imaginary portfolio holdings
PORTFOLIO = {
    'QQQ':   {'shares': 99,  'entry': 604.90},
    'NVDA':  {'shares': 254, 'entry': 177.19},
    'MSFT':  {'shares': 101, 'entry': 392.74},
    'GOOG':  {'shares': 112, 'entry': 311.43},
    'BRK-B': {'shares': 99,  'entry': 502.67},
    'AVGO':  {'shares': 125, 'entry': 319.55},
    'GLD':   {'shares': 124, 'entry': 480.75},
    'TLT':   {'shares': 495, 'entry': 90.80},
    'PLTR':  {'shares': 220, 'entry': 135.94},
    'ANET':  {'shares': 191, 'entry': 130.25},
}
CASH = 71530.11

# Regime target allocations
REGIME_TARGETS = {
    'EXPANSION': {
        'equities': 0.70, 'bonds': 0.10, 'gold': 0.10, 'cash': 0.10,
        'note': 'Risk-on: overweight growth equities',
    },
    'LATE_CYCLE': {
        'equities': 0.55, 'bonds': 0.15, 'gold': 0.15, 'cash': 0.15,
        'note': 'Rotate to defensive sectors, add gold',
    },
    'RECESSION': {
        'equities': 0.30, 'bonds': 0.35, 'gold': 0.20, 'cash': 0.15,
        'note': 'Risk-off: bonds, gold, cash; avoid cyclicals',
    },
    'RECOVERY': {
        'equities': 0.60, 'bonds': 0.20, 'gold': 0.10, 'cash': 0.10,
        'note': 'Begin rebuilding equity exposure',
    },
}


# ─── DB Helpers ───────────────────────────────────────────────────────────────

def load_json(path):
    """Load JSON file safely, return None if missing or corrupt."""
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def table_exists(db, table_name):
    """Check if a table exists in the DB."""
    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


def get_prices(db, symbol, days=252):
    """Get last N daily closes for a symbol. Returns list of floats (oldest first)."""
    try:
        rows = db.execute(
            """SELECT close FROM prices
               WHERE symbol=? AND timeframe='1d' AND close IS NOT NULL
               ORDER BY timestamp DESC LIMIT ?""",
            (symbol, days)
        ).fetchall()
        if not rows:
            return []
        # Reverse so oldest is first
        return [r[0] for r in reversed(rows)]
    except Exception as e:
        print(f"  [warn] get_prices({symbol}): {e}")
        return []


# ─── Technical Indicators ─────────────────────────────────────────────────────

def calc_rsi(prices, period=14):
    """Standard RSI calculation. Returns float or 50 if insufficient data."""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calc_rsi2(prices):
    """Connors RSI(2) — 2-period RSI for mean reversion."""
    return calc_rsi(prices, period=2)


# ─── Regime Detection ─────────────────────────────────────────────────────────

def detect_regime(db):
    """Detect current market regime from FRED + VIX data."""
    yc = db.execute(
        "SELECT value FROM economic_data WHERE series_id='T10Y2Y' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    vix = db.execute(
        "SELECT close FROM prices WHERE symbol='VIX' AND timeframe='1d' AND close IS NOT NULL ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    ff = db.execute(
        "SELECT value FROM economic_data WHERE series_id='FEDFUNDS' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    ur = db.execute(
        "SELECT value FROM economic_data WHERE series_id='UNRATE' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()

    spy_prices = get_prices(db, 'SPY', 252)
    spy_above_200 = spy_prices[-1] > np.mean(spy_prices[-200:]) if len(spy_prices) >= 200 else True

    vix_val = vix[0] if vix else 20
    yc_val = yc[0] if yc else 0

    if vix_val < 18 and yc_val > 0.5 and spy_above_200:
        regime = 'EXPANSION'
        confidence = 70
    elif vix_val > 30 and yc_val < 0:
        regime = 'RECESSION'
        confidence = 75
    elif vix_val > 22 or not spy_above_200:
        regime = 'LATE_CYCLE'
        confidence = 62
    else:
        regime = 'RECOVERY'
        confidence = 55

    return {
        'regime': regime,
        'confidence': confidence,
        'vix': round(vix_val, 2),
        'yield_curve': round(yc_val, 3),
        'fed_funds': round(ff[0], 2) if ff and ff[0] is not None else None,
        'unemployment': round(ur[0], 1) if ur and ur[0] is not None else None,
        'spy_above_200sma': bool(spy_above_200),
    }


# ─── Scans ────────────────────────────────────────────────────────────────────

def scan_connors_rsi(db, regime):
    """Scan for Connors RSI(2) < 10 entries and > 90 exits."""
    connors_positions = load_json(CONNORS_FILE) or {'positions': [], 'closed': []}
    signals = []

    for sym in STOCK_SYMBOLS:
        prices = get_prices(db, sym, 20)
        if len(prices) < 15:
            continue

        rsi2 = calc_rsi2(prices)
        rsi14 = calc_rsi(prices, 14)

        prices_long = get_prices(db, sym, 252)
        sma200 = np.mean(prices_long[-200:]) if len(prices_long) >= 200 else np.mean(prices_long)
        above_sma200 = prices[-1] > sma200

        # Entry: RSI(2) < 10, above 200 SMA, max 5 positions
        if rsi2 < 10 and above_sma200 and len(connors_positions['positions']) < 5:
            existing = [p for p in connors_positions['positions'] if p['symbol'] == sym]
            if not existing:
                signals.append({
                    'type': 'ENTRY',
                    'strategy': 'CONNORS_RSI2',
                    'symbol': sym,
                    'rsi2': round(rsi2, 1),
                    'rsi14': round(rsi14, 1),
                    'price': round(prices[-1], 2),
                    'reason': f'RSI(2)={rsi2:.1f} < 10, above 200 SMA, trend confirmed',
                })

        # Exit: RSI(2) > 90 or held > 5 days
        for pos in connors_positions['positions']:
            if pos['symbol'] == sym:
                if rsi2 > 90:
                    signals.append({
                        'type': 'EXIT',
                        'strategy': 'CONNORS_RSI2',
                        'symbol': sym,
                        'rsi2': round(rsi2, 1),
                        'entry_price': pos['entry_price'],
                        'current_price': round(prices[-1], 2),
                        'pnl_pct': round(((prices[-1] / pos['entry_price']) - 1) * 100, 2),
                        'reason': f'RSI(2)={rsi2:.1f} > 90, take profit',
                    })
                elif pos.get('days_held', 0) >= 5:
                    signals.append({
                        'type': 'EXIT',
                        'strategy': 'CONNORS_RSI2',
                        'symbol': sym,
                        'rsi2': round(rsi2, 1),
                        'entry_price': pos['entry_price'],
                        'current_price': round(prices[-1], 2),
                        'pnl_pct': round(((prices[-1] / pos['entry_price']) - 1) * 100, 2),
                        'reason': 'Max hold period (5 days) reached',
                    })

    return signals, connors_positions


def scan_vix_crisis(db):
    """Check for VIX crisis buy signal — 100% win rate historically."""
    vix_prices = get_prices(db, 'VIX', 252)
    if not vix_prices:
        return {'active': False, 'current': None, 'percentile': None,
                'crisis_buy': False, 'elevated': False, 'complacent': False,
                'signal': 'NO_DATA'}

    current_vix = vix_prices[-1]
    percentile = sum(1 for v in vix_prices if v <= current_vix) / len(vix_prices) * 100

    return {
        'current': round(current_vix, 2),
        'percentile': round(percentile, 1),
        'crisis_buy': current_vix > 30,
        'elevated': current_vix > 25,
        'complacent': current_vix < 15,
        'signal': ('BUY_SPY_AGGRESSIVELY' if current_vix > 30 else
                   'CAUTION' if current_vix > 25 else
                   'NORMAL' if current_vix >= 15 else 'REDUCE_RISK'),
    }


def scan_oversold_overbought(db):
    """Scan all symbols for RSI(14) < 30 (oversold) and > 70 (overbought)."""
    oversold = []
    overbought = []

    for sym in STOCK_SYMBOLS:
        prices = get_prices(db, sym, 30)
        if len(prices) < 15:
            continue
        rsi = calc_rsi(prices, 14)
        if rsi < 30:
            oversold.append({'symbol': sym, 'rsi14': round(rsi, 1), 'price': round(prices[-1], 2)})
        elif rsi > 70:
            overbought.append({'symbol': sym, 'rsi14': round(rsi, 1), 'price': round(prices[-1], 2)})

    # Sort by extremity
    oversold.sort(key=lambda x: x['rsi14'])
    overbought.sort(key=lambda x: x['rsi14'], reverse=True)

    return {'oversold': oversold, 'overbought': overbought}


def scan_trend_breaks(db):
    """Find symbols that just crossed below their 200-day SMA (within last 3 days)."""
    breaks = []

    for sym in STOCK_SYMBOLS:
        prices = get_prices(db, sym, 205)
        if len(prices) < 202:
            continue

        sma200_today = np.mean(prices[-200:])
        sma200_prev = np.mean(prices[-201:-1])

        current = prices[-1]
        prev = prices[-2]

        # Just crossed below: prev was above, current is below
        if prev >= sma200_prev and current < sma200_today:
            pct_below = ((current / sma200_today) - 1) * 100
            breaks.append({
                'symbol': sym,
                'price': round(current, 2),
                'sma200': round(sma200_today, 2),
                'pct_from_sma': round(pct_below, 2),
                'signal': 'BREAKDOWN',
            })
        # Also flag symbols already well below (>5%)
        elif current < sma200_today * 0.95:
            pct_below = ((current / sma200_today) - 1) * 100
            breaks.append({
                'symbol': sym,
                'price': round(current, 2),
                'sma200': round(sma200_today, 2),
                'pct_from_sma': round(pct_below, 2),
                'signal': 'BELOW_SMA200',
            })

    breaks.sort(key=lambda x: x['pct_from_sma'])
    return breaks


def calc_multi_factor_ranking(db):
    """Multi-factor ranking: 40% momentum + 30% value + 20% low-vol + 10% trend."""
    rankings = []
    has_fundamentals = table_exists(db, 'fundamentals')

    for sym in STOCK_SYMBOLS:
        prices = get_prices(db, sym, 252)
        if len(prices) < 126:
            continue

        # Momentum (6-month return)
        mom_6m = (prices[-1] / prices[-126] - 1) * 100 if len(prices) >= 126 else 0

        # Value (price / 200-SMA ratio — lower = cheaper)
        sma200 = np.mean(prices[-200:]) if len(prices) >= 200 else np.mean(prices)
        value_ratio = prices[-1] / sma200

        # Low volatility (60-day annualized vol — lower = better)
        if len(prices) >= 61:
            rets = np.diff(np.log(prices[-61:]))
            vol_60d = np.std(rets) * np.sqrt(252) * 100
        else:
            vol_60d = 50.0

        # Trend (above 200 SMA = 1, below = 0)
        trend = 1 if prices[-1] > sma200 else 0

        # Fundamentals (if table exists and data available)
        fund = None
        if has_fundamentals:
            try:
                fund = db.execute(
                    "SELECT pe_trailing, roe, profit_margin FROM fundamentals WHERE symbol=? ORDER BY timestamp DESC LIMIT 1",
                    (sym,)
                ).fetchone()
            except Exception:
                pass

        rankings.append({
            'symbol': sym,
            'price': round(prices[-1], 2),
            'mom_6m': mom_6m,
            'value_ratio': value_ratio,
            'vol_60d': vol_60d,
            'trend': trend,
            'pe': fund[0] if fund and fund[0] else None,
            'roe': fund[1] if fund and fund[1] else None,
        })

    if not rankings:
        return []

    n = len(rankings)

    # Percentile rank: Momentum (higher = better)
    mom_sorted = sorted(rankings, key=lambda x: x['mom_6m'])
    for i, r in enumerate(mom_sorted):
        r['mom_rank'] = (i / (n - 1)) * 100 if n > 1 else 50

    # Value: lower ratio = cheaper = better (invert rank)
    val_sorted = sorted(rankings, key=lambda x: x['value_ratio'], reverse=True)
    for i, r in enumerate(val_sorted):
        r['val_rank'] = (i / (n - 1)) * 100 if n > 1 else 50

    # Low vol: lower = better (invert rank)
    vol_sorted = sorted(rankings, key=lambda x: x['vol_60d'], reverse=True)
    for i, r in enumerate(vol_sorted):
        r['vol_rank'] = (i / (n - 1)) * 100 if n > 1 else 50

    # Composite: 40% mom + 30% value + 20% low-vol + 10% trend
    for r in rankings:
        r['composite'] = (
            0.40 * r['mom_rank'] +
            0.30 * r['val_rank'] +
            0.20 * r['vol_rank'] +
            0.10 * (r['trend'] * 100)
        )

    return sorted(rankings, key=lambda x: x['composite'], reverse=True)


def scan_covered_call_candidates(db):
    """Find covered call opportunities on 100+ share positions."""
    CC_CANDIDATES = {
        'CSCO': 872,   # 8 contracts possible
        'CVX':  100,
        'SPY':  100,
        'IWM':  202,   # 2 contracts
        'ANET': 200,   # 2 contracts
        'AVAV': 100,
        'QQQ':  207,   # Jaclyn IRA — 2 contracts
        'TSLA': 100,   # Jaclyn IRA
        'MO':   275,   # IRA — 2 contracts
        'BRK-B': 100,  # IRA
    }

    candidates = []
    for sym, shares in CC_CANDIDATES.items():
        prices = get_prices(db, sym, 60)
        if len(prices) < 30:
            continue

        current = prices[-1]
        contracts = shares // 100

        # IV proxy: 30-day historical vol
        rets = np.diff(np.log(prices[-31:]))
        hv30 = np.std(rets) * np.sqrt(252)

        # IV rank proxy: current 30d vol vs rolling 252-day window
        prices_long = get_prices(db, sym, 252)
        if len(prices_long) >= 60:
            all_hvs = []
            for i in range(30, len(prices_long)):
                r = np.diff(np.log(prices_long[i - 30:i + 1]))
                all_hvs.append(np.std(r) * np.sqrt(252))
            iv_rank = sum(1 for h in all_hvs if h <= hv30) / len(all_hvs) * 100 if all_hvs else 50
        else:
            iv_rank = 50

        # Estimated premium (simplified Black-Scholes approximation)
        # 2% OTM, 30 DTE
        strike = round(current * 1.02, 2)
        est_premium = current * hv30 * (30 / 365) ** 0.5 * 0.4  # delta-approximated
        monthly_income = est_premium * contracts * 100
        annual_yield = (est_premium / current) * 12 * 100

        candidates.append({
            'symbol': sym,
            'shares': shares,
            'contracts': contracts,
            'price': round(current, 2),
            'strike': strike,
            'hv30': round(hv30 * 100, 1),
            'iv_rank': round(iv_rank, 1),
            'est_premium': round(est_premium, 2),
            'monthly_income': round(monthly_income, 2),
            'annual_yield': round(annual_yield, 1),
            'recommend': iv_rank > 40,  # Only sell premium when IV elevated
        })

    return sorted(candidates, key=lambda x: x['monthly_income'], reverse=True)


def generate_portfolio_analysis(db, regime):
    """Check imaginary portfolio vs regime targets, generate rebalance recommendations."""
    targets = REGIME_TARGETS.get(regime['regime'], REGIME_TARGETS['RECOVERY'])

    positions = []
    total_value = CASH

    for sym, info in PORTFOLIO.items():
        prices = get_prices(db, sym, 5)
        current_price = prices[-1] if prices else info['entry']
        market_value = current_price * info['shares']
        pnl = (current_price - info['entry']) * info['shares']
        pnl_pct = ((current_price / info['entry']) - 1) * 100
        total_value += market_value

        positions.append({
            'symbol': sym,
            'shares': info['shares'],
            'entry': info['entry'],
            'current': round(current_price, 2),
            'market_value': round(market_value, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
        })

    # Classify positions
    equity_syms = {'QQQ', 'NVDA', 'MSFT', 'GOOG', 'AVGO', 'PLTR', 'ANET'}
    bond_syms = {'TLT'}
    gold_syms = {'GLD'}
    other_syms = {'BRK-B'}

    equity_val = sum(p['market_value'] for p in positions if p['symbol'] in equity_syms)
    bond_val = sum(p['market_value'] for p in positions if p['symbol'] in bond_syms)
    gold_val = sum(p['market_value'] for p in positions if p['symbol'] in gold_syms)

    current_alloc = {
        'equities': round(equity_val / total_value, 3),
        'bonds': round(bond_val / total_value, 3),
        'gold': round(gold_val / total_value, 3),
        'cash': round(CASH / total_value, 3),
    }

    # Generate rebalance suggestions
    suggestions = []
    for asset, target_pct in targets.items():
        if asset == 'note':
            continue
        current_pct = current_alloc.get(asset, 0)
        diff = current_pct - target_pct
        if abs(diff) > 0.05:  # >5% deviation
            if diff > 0:
                suggestions.append(f'TRIM {asset.upper()} ({current_pct*100:.0f}% → {target_pct*100:.0f}%)')
            else:
                suggestions.append(f'ADD {asset.upper()} ({current_pct*100:.0f}% → {target_pct*100:.0f}%)')

    # Sort positions by P&L
    positions.sort(key=lambda x: x['pnl_pct'], reverse=True)

    return {
        'total_value': round(total_value, 2),
        'cash': CASH,
        'cash_pct': round(CASH / total_value * 100, 1),
        'regime': regime['regime'],
        'target_allocation': targets,
        'current_allocation': current_alloc,
        'rebalance_suggestions': suggestions,
        'positions': positions,
        'best_performer': positions[0]['symbol'] if positions else None,
        'worst_performer': positions[-1]['symbol'] if positions else None,
    }


# ─── Discord ──────────────────────────────────────────────────────────────────

def send_discord(message):
    """Send alert to Discord #investments channel."""
    try:
        result = subprocess.run(
            [
                '/home/bob/.npm-global/bin/openclaw', 'message', 'send',
                '--channel', 'discord', '--account', 'pinch',
                '--target', '1476110474377429124',
                '-m', message,
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"  [warn] Discord send returned code {result.returncode}: {result.stderr.decode()[:200]}")
    except Exception as e:
        print(f"  [warn] Discord send failed: {e}")


def format_discord_message(signals):
    """Format signals into a Discord-friendly message."""
    regime = signals['regime']
    vix = signals['vix']

    lines = [
        f"📊 **PINCH DAILY SIGNALS** — {signals['timestamp'][:10]}",
        "",
        f"🏛️ **REGIME:** {regime['regime']} ({regime['confidence']}%)",
    ]

    if vix.get('current') is not None:
        lines.append(f"📊 **VIX:** {vix['current']} ({vix['percentile']}th pctl) — {vix['signal']}")
    else:
        lines.append("📊 **VIX:** No data")

    # Trade ideas
    ideas = []

    # VIX crisis
    if vix.get('crisis_buy'):
        ideas.append("🚨 **VIX CRISIS BUY:** VIX > 30 — BUY SPY aggressively (100% historical win rate)")

    # Connors entries/exits
    for s in signals.get('connors', []):
        if s['type'] == 'ENTRY':
            ideas.append(f"⚡ **BUY {s['symbol']}** — RSI(2)={s['rsi2']}, above 200 SMA [{s['strategy']}]")
        elif s['type'] == 'EXIT':
            ideas.append(f"💰 **SELL {s['symbol']}** — RSI(2)={s['rsi2']}, P&L {s['pnl_pct']:+.1f}% [{s['strategy']}]")

    # Covered calls (top 3 by monthly income)
    for cc in signals.get('covered_calls', [])[:3]:
        ideas.append(
            f"📝 **SELL {cc['symbol']} ${cc['strike']} call** — "
            f"{cc['contracts']}x, est ${cc['monthly_income']:.0f}/mo "
            f"({cc['annual_yield']:.1f}%/yr), IV rank {cc['iv_rank']:.0f}%"
        )

    if ideas:
        lines.append("")
        lines.append("⚔️ **TRADE IDEAS:**")
        for i, idea in enumerate(ideas[:5], 1):
            lines.append(f"{i}. {idea}")

    # Multi-factor top 5
    top5 = signals.get('multi_factor_top10', [])[:5]
    if top5:
        lines.append("")
        mf_str = " | ".join([f"{r['symbol']} ({r['score']:.0f})" for r in top5])
        lines.append(f"📈 **TOP 5:** {mf_str}")

    # Alerts (oversold, overbought, trend breaks)
    alerts = []
    for item in signals.get('oversold', [])[:3]:
        sym = item['symbol'] if isinstance(item, dict) else item
        alerts.append(f"🟢 {sym} OVERSOLD (RSI<30)")
    for item in signals.get('overbought', [])[:3]:
        sym = item['symbol'] if isinstance(item, dict) else item
        alerts.append(f"🔴 {sym} OVERBOUGHT (RSI>70)")
    for item in signals.get('trend_breaks', [])[:3]:
        sym = item['symbol'] if isinstance(item, dict) else item
        sig = item.get('signal', 'BELOW_SMA200') if isinstance(item, dict) else 'BELOW_SMA200'
        alerts.append(f"⚠️ {sym} {sig}")

    if alerts:
        lines.append("")
        lines.append(f"⚠️ **ALERTS:** {' | '.join(alerts[:5])}")

    # Portfolio summary
    port = signals.get('portfolio', {})
    if port:
        total = port.get('total_value', 0)
        lines.append("")
        lines.append(f"💼 **PORTFOLIO:** ${total:,.0f} | Cash {port.get('cash_pct', 0):.1f}%")
        if port.get('rebalance_suggestions'):
            lines.append(f"   ↳ Rebalance: {' | '.join(port['rebalance_suggestions'][:3])}")

    lines.append("")
    lines.append("_Rule of Acquisition #22: A wise man can hear profit in the wind._")

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Run full signal scan."""
    print(f"📊 Pinch Signal Engine — {datetime.now().strftime('%Y-%m-%d %H:%M')} ET")
    print(f"   DB: {DB_PATH}")
    print(f"   State: {STATE_DIR}")
    print()

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")

    # 1. Regime detection
    print("🏛️  Detecting regime...")
    regime = detect_regime(db)
    print(f"   Regime: {regime['regime']} ({regime['confidence']}%) | VIX={regime['vix']} | YC={regime['yield_curve']}")

    # 2. VIX crisis check
    print("📊 Scanning VIX...")
    vix = scan_vix_crisis(db)
    if vix.get('current'):
        print(f"   VIX: {vix['current']} ({vix['percentile']}th pctl) — {vix['signal']}")
    else:
        print("   VIX: No data available")

    # 3. Connors RSI(2)
    print("⚡ Running Connors RSI(2) scan...")
    connors_signals, connors_state = scan_connors_rsi(db, regime)
    print(f"   Found {len(connors_signals)} Connors signals")

    # 4. Oversold/overbought
    print("🔍 Scanning oversold/overbought...")
    oversold_ob = scan_oversold_overbought(db)
    print(f"   Oversold: {len(oversold_ob.get('oversold', []))} | Overbought: {len(oversold_ob.get('overbought', []))}")

    # 5. Trend breaks
    print("📉 Scanning trend breaks (200-day SMA)...")
    trend_breaks = scan_trend_breaks(db)
    print(f"   Found {len(trend_breaks)} trend breaks/warnings")

    # 6. Multi-factor ranking
    print("📈 Running multi-factor ranking...")
    mf_ranking = calc_multi_factor_ranking(db)
    if mf_ranking:
        top3 = [f"{r['symbol']}({r['composite']:.0f})" for r in mf_ranking[:3]]
        print(f"   Top 3: {', '.join(top3)}")

    # 7. Covered call candidates
    print("📝 Scanning covered call candidates...")
    cc_candidates = scan_covered_call_candidates(db)
    recommended_cc = [c for c in cc_candidates if c['recommend']]
    print(f"   {len(recommended_cc)} candidates (IV rank > 40%)")

    # 8. Portfolio analysis
    print("💼 Running portfolio analysis...")
    portfolio = generate_portfolio_analysis(db, regime)
    print(f"   Total value: ${portfolio['total_value']:,.0f} | Cash: {portfolio['cash_pct']}%")

    # Assemble signals dict
    signals = {
        'timestamp': datetime.now().isoformat(),
        'regime': regime,
        'vix': vix,
        'connors': connors_signals,
        'oversold': oversold_ob.get('oversold', []),
        'overbought': oversold_ob.get('overbought', []),
        'trend_breaks': trend_breaks,
        'multi_factor_top10': [
            {
                'symbol': r['symbol'],
                'score': round(r['composite'], 1),
                'mom': round(r['mom_6m'], 1),
                'vol': round(r['vol_60d'], 1),
            }
            for r in mf_ranking[:10]
        ],
        'multi_factor_bottom5': [
            {'symbol': r['symbol'], 'score': round(r['composite'], 1)}
            for r in mf_ranking[-5:]
        ],
        'covered_calls': recommended_cc,
        'portfolio': portfolio,
    }

    # Save signals JSON
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(SIGNALS_FILE, 'w') as f:
        json.dump(signals, f, indent=2)
    print(f"\n✅ Signals saved to {SIGNALS_FILE}")

    # Send Discord message
    print("📨 Sending Discord alert...")
    msg = format_discord_message(signals)
    send_discord(msg)

    # Save Connors positions state
    with open(CONNORS_FILE, 'w') as f:
        json.dump(connors_state, f, indent=2)

    db.close()
    print("✅ Done.")


if __name__ == '__main__':
    main()
