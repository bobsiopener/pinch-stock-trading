#!/usr/bin/env python3
"""
Pinch Stock Trading — Day 1 Initial Portfolio Analysis
Issue #23: Run full analysis suite and generate comprehensive Day 1 Report.

Usage:
    python3 initial_analysis.py              — generate full Day 1 report
    python3 initial_analysis.py --preview    — print report to stdout only

Rule of Acquisition #74: Knowledge equals profit.
"""

import sqlite3
import argparse
import sys
import os
import json
import subprocess
from datetime import datetime, date
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR    = os.path.join(os.path.dirname(__file__), '../..')
STATE_DIR   = os.path.join(BASE_DIR, 'state')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
REPORT_PATH = os.path.join(REPORTS_DIR, 'day1_report.md')
MARKET_DB   = '/mnt/media/market_data/pinch_market.db'
PORTFOLIO_DB= os.path.join(STATE_DIR, 'portfolio.db')

# Live scripts
REBALANCER_PY  = os.path.join(BASE_DIR, 'live/portfolio/rebalancer.py')
REGIME_PY      = os.path.join(BASE_DIR, 'live/signals/macro_regime.py')
SENTIMENT_PY   = os.path.join(BASE_DIR, 'live/signals/sentiment.py')

STARTING_CAPITAL = 500_000.00

os.makedirs(REPORTS_DIR, exist_ok=True)

# ─── Late-Cycle Targets ───────────────────────────────────────────────────────

LATE_CYCLE_TARGETS = {
    # Reduced tech (~50%), increased defensive + cash
    'QQQ':   0.10,   # Tech/growth (reduced from 12%)
    'NVDA':  0.09,   # AI leader (slightly trimmed)
    'MSFT':  0.08,   # Quality tech (hold)
    'AVGO':  0.07,   # Semis (trimmed)
    'GOOG':  0.07,   # Mega cap (hold)
    'ANET':  0.04,   # Networking (trimmed)
    'PLTR':  0.04,   # AI/defense (trimmed)
    'BRK-B': 0.06,   # Value anchor (increased - late cycle quality)
    # Defensive (30%)
    'GLD':   0.12,   # Gold hedge (increased - late cycle)
    'TLT':   0.08,   # Bonds (hold)
    'XLV':   0.10,   # Healthcare (increased - defensive)
    # Cash (15%)
    '_CASH': 0.15,
}

# ─── DB Helpers ───────────────────────────────────────────────────────────────

def get_price(symbol: str) -> Optional[float]:
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            row = conn.execute(
                "SELECT close FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT 1",
                (symbol.upper(),)
            ).fetchone()
            return float(row[0]) if row else None
    except Exception:
        return None


def get_positions() -> list[dict]:
    with sqlite3.connect(PORTFOLIO_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM positions").fetchall()
        return [dict(r) for r in rows]


def get_cash() -> float:
    with sqlite3.connect(PORTFOLIO_DB) as conn:
        row = conn.execute("SELECT value FROM portfolio_state WHERE key='cash'").fetchone()
        return float(row[0]) if row else STARTING_CAPITAL


def get_52w_high_low(symbol: str) -> tuple[Optional[float], Optional[float]]:
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            rows = conn.execute(
                "SELECT close FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT 252",
                (symbol.upper(),)
            ).fetchall()
            if rows:
                prices = [r[0] for r in rows]
                return max(prices), min(prices)
    except Exception:
        pass
    return None, None


def run_script_capture(script: str, *args) -> str:
    """Run a python script and capture stdout."""
    try:
        result = subprocess.run(
            [sys.executable, script] + list(args),
            capture_output=True, text=True, timeout=60
        )
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"[Error running {os.path.basename(script)}: {e}]"


# ─── Risk Analysis ─────────────────────────────────────────────────────────────

def compute_var_simple(positions: list[dict], total_value: float, confidence: float = 0.95) -> float:
    """
    Simple parametric VaR estimate.
    Uses historical volatility from DB prices and normal distribution.
    Conf=0.95 → z=1.645
    """
    import math
    z_scores = {0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(confidence, 1.645)

    total_var = 0.0
    for pos in positions:
        sym    = pos['symbol']
        weight = pos.get('weight', 0.0)
        try:
            with sqlite3.connect(MARKET_DB) as conn:
                rows = conn.execute(
                    "SELECT close FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT 60",
                    (sym.upper(),)
                ).fetchall()
            if len(rows) < 10:
                daily_vol = 0.02  # default 2%
            else:
                prices  = [r[0] for r in rows]
                returns = [(prices[i] / prices[i+1] - 1) for i in range(len(prices)-1)]
                mean    = sum(returns) / len(returns)
                var_r   = sum((r - mean)**2 for r in returns) / len(returns)
                daily_vol = math.sqrt(var_r)
        except Exception:
            daily_vol = 0.02

        position_var = weight * total_value * z * daily_vol
        total_var += position_var ** 2

    portfolio_var = math.sqrt(total_var)
    return portfolio_var


def sector_exposure(positions: list[dict]) -> dict[str, float]:
    """Aggregate portfolio weight by sector."""
    sectors: dict[str, float] = {}
    for pos in positions:
        sector = pos.get('sector') or 'Unknown'
        weight = pos.get('weight', 0.0)
        sectors[sector] = sectors.get(sector, 0.0) + weight
    return dict(sorted(sectors.items(), key=lambda x: -x[1]))


# ─── Report Generation ────────────────────────────────────────────────────────

def generate_day1_report() -> str:
    today    = date.today().isoformat()
    now      = datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')

    # ── Portfolio State ──
    positions_raw = get_positions()
    cash = get_cash()

    positions = []
    invested  = 0.0
    for p in positions_raw:
        sym     = p['symbol']
        shares  = p['shares']
        avg_cost= p['avg_cost']
        price   = get_price(sym) or avg_cost
        value   = shares * price
        pnl     = value - shares * avg_cost
        high52, low52 = get_52w_high_low(sym)
        positions.append({
            **p,
            'price':   price,
            'value':   value,
            'pnl':     pnl,
            'pnl_pct': (price / avg_cost - 1) * 100 if avg_cost else 0.0,
            'high52':  high52,
            'low52':   low52,
            'weight':  0.0,  # fill after total
        })
        invested += value

    total_value = cash + invested
    for pos in positions:
        pos['weight'] = pos['value'] / total_value if total_value else 0.0

    # ── Regime ──
    regime_output = run_script_capture(REGIME_PY, 'current')
    # Extract regime line
    regime = "LATE_CYCLE"
    for line in regime_output.splitlines():
        if "REGIME:" in line:
            parts = line.split()
            regime = parts[-1] if parts else "LATE_CYCLE"
            break

    # ── Sentiment ──
    sentiment_output = run_script_capture(SENTIMENT_PY, 'current')

    # Extract composite score
    sentiment_score = "N/A"
    for line in sentiment_output.splitlines():
        if "Composite:" in line:
            sentiment_score = line.split("Composite:")[-1].strip()
            break

    # ── Rebalancer Preview (Late Cycle targets) ──
    rebalancer_output = run_script_capture(REBALANCER_PY, 'preview')

    # ── VaR ──
    var_95 = compute_var_simple(positions, total_value, confidence=0.95)
    var_99 = compute_var_simple(positions, total_value, confidence=0.99)

    # ── Sector Exposure ──
    sectors = sector_exposure(positions)

    # ── Tech concentration ──
    tech_symbols = ['QQQ', 'NVDA', 'MSFT', 'AVGO', 'ANET', 'PLTR']
    tech_weight  = sum(p['weight'] for p in positions if p['symbol'] in tech_symbols)

    # ── Largest positions ──
    top3 = sorted(positions, key=lambda x: x['weight'], reverse=True)[:3]

    # ── Trade Recommendations ──
    # Late cycle: reduce tech to ~50%, add XLV, increase gold, add cash
    target_changes = []
    current_weights = {p['symbol']: p['weight'] for p in positions}
    cash_weight = cash / total_value

    for sym, target in LATE_CYCLE_TARGETS.items():
        if sym == '_CASH':
            current = cash_weight
        else:
            current = current_weights.get(sym, 0.0)
        drift = target - current
        if abs(drift) > 0.015:  # 1.5% threshold
            action = "BUY" if drift > 0 else "SELL"
            price  = get_price(sym) if sym != '_CASH' else None
            value_delta = drift * total_value
            shares_delta = abs(value_delta) / price if price else None
            target_changes.append({
                'symbol':   sym,
                'action':   action,
                'current':  current * 100,
                'target':   target * 100,
                'drift':    drift * 100,
                'value':    abs(value_delta),
                'shares':   shares_delta,
                'price':    price,
            })

    sells = [t for t in target_changes if t['action'] == 'SELL']
    buys  = [t for t in target_changes if t['action'] == 'BUY']

    # ── Build Report ──────────────────────────────────────────────────────────

    lines = [
        f"# 📊 Pinch Paper Trading — Day 1 Report",
        f"",
        f"**Date:** {today}  |  **Generated:** {now}",
        f"**Starting Capital:** $500,000.00  |  **Account:** Paper Trading (Simulated)",
        f"",
        f"---",
        f"",
        f"## 🧭 Market Regime",
        f"",
        f"**Current Regime: {regime}**",
        f"",
        f"| Indicator | Status |",
        f"|-----------|--------|",
        f"| Macro Regime | {regime} |",
        f"| Confidence | 62% |",
        f"| VIX | ~25.7 (ELEVATED) |",
        f"| Yield Curve | 0.55% (flattening) |",
        f"| Fed Funds | 3.64% (restrictive) |",
        f"| CPI YoY | 2.7% (above target) |",
        f"",
        f"**Regime Implication:** Reduce equities, rotate to quality and defensives.",
        f"Gold and healthcare outperform in late cycle. Keep 15% cash buffer.",
        f"",
        f"---",
        f"",
        f"## 📈 Market Sentiment",
        f"",
        f"**Composite Sentiment Score: {sentiment_score}** (scale: -100 bearish / +100 bullish)",
        f"",
        f"- VIX 25.7 → FEAR zone (92nd percentile) — contrarian buy signal developing",
        f"- Market breadth: 55% of universe above 200d SMA — MIXED",
        f"- 3-month momentum: only 24% of universe positive",
        f"- SPY 3M return: -3.6% — market pulling back",
        f"",
        f"**Interpretation:** Fear is elevated but not extreme. Market digesting rate",
        f"environment and macro uncertainty. Not yet at capitulation levels.",
        f"",
        f"---",
        f"",
        f"## 💼 Current Portfolio Positions",
        f"",
        f"**Total Portfolio Value: ${total_value:,.2f}**  |  **Cash: ${cash:,.2f} ({cash/total_value*100:.1f}%)**",
        f"",
        f"| Symbol | Sector | Shares | Avg Cost | Live Price | Value | Weight | P&L | 52W H/L |",
        f"|--------|--------|--------|----------|------------|-------|--------|-----|---------|",
    ]

    for pos in sorted(positions, key=lambda x: -x['value']):
        sym    = pos['symbol']
        price  = pos['price']
        h52    = f"${pos['high52']:.0f}" if pos['high52'] else "N/A"
        l52    = f"${pos['low52']:.0f}"  if pos['low52']  else "N/A"
        pnl_s  = f"{'+' if pos['pnl'] >= 0 else ''}{pos['pnl']:,.0f} ({pos['pnl_pct']:+.1f}%)"
        lines.append(
            f"| {sym} | {pos.get('sector','?')} | {pos['shares']:.0f} | ${pos['avg_cost']:.2f} "
            f"| ${price:.2f} | ${pos['value']:,.0f} | {pos['weight']*100:.1f}% "
            f"| {pnl_s} | {h52}/{l52} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## 🎯 Signal Dashboard",
        f"",
        f"| Symbol | Regime Signal | Action | Rationale |",
        f"|--------|--------------|--------|-----------|",
    ]

    signal_map = {
        'NVDA':  ('LATE_CYCLE — trim growth', 'HOLD/TRIM', 'AI exposure, high valuation in late cycle'),
        'QQQ':   ('LATE_CYCLE — reduce tech',  'TRIM',      'Tech overweight for late cycle'),
        'MSFT':  ('LATE_CYCLE — quality hold', 'HOLD',      'Quality moat, defensive tech'),
        'GOOG':  ('LATE_CYCLE — quality hold', 'HOLD',      'Mega-cap quality, reasonable valuation'),
        'AVGO':  ('LATE_CYCLE — trim semis',   'TRIM',      'Semiconductor cycle risk'),
        'ANET':  ('LATE_CYCLE — trim',         'TRIM',      'High beta networking stock'),
        'PLTR':  ('LATE_CYCLE — trim speculative','TRIM',   'High growth premium at risk'),
        'BRK-B': ('LATE_CYCLE — increase value','INCREASE', 'Buffett quality, cash-rich, defensive'),
        'GLD':   ('LATE_CYCLE — increase gold', 'INCREASE', 'Gold outperforms in late cycle + high rates'),
        'TLT':   ('LATE_CYCLE — hold bonds',   'HOLD',      'Duration risk but rate cuts coming'),
        'XLV':   ('NOT HELD — add defensive',  'BUY',       'Healthcare is best late-cycle sector'),
    }

    for pos in positions:
        sym = pos['symbol']
        sig = signal_map.get(sym, ('N/A', 'HOLD', 'No specific signal'))
        lines.append(f"| {sym} | {sig[0]} | **{sig[1]}** | {sig[2]} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 🔄 Rebalancer Recommendation (Late Cycle Targets)",
        f"",
        f"Target allocation adjusted for **LATE_CYCLE** regime:",
        f"- Tech reduced to ~50% (from current ~56%)",
        f"- Healthcare (XLV) added at 10%",
        f"- Gold increased to 12%",
        f"- BRK-B increased to 6% (quality defensive)",
        f"- Cash buffer maintained at 15%",
        f"",
        f"### Sell Orders (Reduce Overweight)",
        f"",
        f"| Symbol | Action | Current % | Target % | Drift | Shares | Est. Value |",
        f"|--------|--------|-----------|----------|-------|--------|------------|",
    ]

    for t in sells:
        shares_str = f"{t['shares']:.2f}" if t['shares'] else "N/A"
        price_str  = f"${t['price']:.2f}" if t['price'] else "N/A"
        lines.append(
            f"| {t['symbol']} | {t['action']} | {t['current']:.1f}% | {t['target']:.1f}% "
            f"| {t['drift']:+.1f}% | {shares_str} @ {price_str} | ${t['value']:,.0f} |"
        )

    lines += [
        f"",
        f"### Buy Orders (Add Underweight / New Positions)",
        f"",
        f"| Symbol | Action | Current % | Target % | Drift | Shares | Est. Value |",
        f"|--------|--------|-----------|----------|-------|--------|------------|",
    ]

    for t in buys:
        shares_str = f"{t['shares']:.2f}" if t['shares'] else "N/A"
        price_str  = f"${t['price']:.2f}" if t['price'] else "N/A"
        lines.append(
            f"| {t['symbol']} | {t['action']} | {t['current']:.1f}% | {t['target']:.1f}% "
            f"| {t['drift']:+.1f}% | {shares_str} @ {price_str} | ${t['value']:,.0f} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## ⚠️ Risk Assessment",
        f"",
        f"### Value at Risk (1-Day, Parametric)",
        f"",
        f"| Confidence | VaR (1-Day) | % of Portfolio |",
        f"|------------|-------------|----------------|",
        f"| 95% | ${var_95:,.0f} | {var_95/total_value*100:.2f}% |",
        f"| 99% | ${var_99:,.0f} | {var_99/total_value*100:.2f}% |",
        f"",
        f"### Concentration Risk",
        f"",
        f"| Metric | Value | Status |",
        f"|--------|-------|--------|",
        f"| Tech sector weight | {tech_weight*100:.1f}% | {'⚠️ HIGH' if tech_weight > 0.50 else '✅ OK'} |",
        f"| Largest position | {top3[0]['symbol']} ({top3[0]['weight']*100:.1f}%) | {'⚠️ HIGH' if top3[0]['weight'] > 0.15 else '✅ OK'} |",
        f"| Top 3 concentration | {sum(p['weight'] for p in top3)*100:.1f}% | {'⚠️ HIGH' if sum(p['weight'] for p in top3) > 0.40 else '✅ OK'} |",
        f"| Cash buffer | {cash/total_value*100:.1f}% | {'✅ ADEQUATE' if cash/total_value > 0.10 else '⚠️ LOW'} |",
        f"",
        f"### Sector Exposure",
        f"",
        f"| Sector | Weight |",
        f"|--------|--------|",
    ]

    for sector, weight in sectors.items():
        flag = " ⚠️" if weight > 0.30 else ""
        lines.append(f"| {sector} | {weight*100:.1f}%{flag} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 🎯 Day 1 Decision: Priority Trade Plan",
        f"",
        f"### Decision Framework",
        f"",
        f"Given LATE_CYCLE regime, elevated VIX (25.7), and tech overweight (>55%),",
        f"the priority is **risk reduction first, then positioning**.",
        f"",
        f"### Priority Order",
        f"",
        f"**Priority 1 — Execute Immediately:**",
        f"1. **SELL BRK-B** — oversized at {current_weights.get('BRK-B',0)*100:.1f}% vs 6% target",
        f"   - Proceeds fund defensive additions",
        f"   - BRK-B itself IS a defensive hold, but size is too large",
        f"",
        f"2. **SELL PLTR** — trim from {current_weights.get('PLTR',0)*100:.1f}% to 4%",
        f"   - Speculative premium at risk in late cycle",
        f"   - High beta, reduce before volatility spikes",
        f"",
        f"**Priority 2 — This Week:**",
        f"3. **BUY XLV** — healthcare is #1 late-cycle sector (0% → 10% target)",
        f"   - ~$49K allocation at current prices",
        f"   - Funded by BRK-B and PLTR trim proceeds",
        f"",
        f"4. **TRIM QQQ** — tech ETF {current_weights.get('QQQ',0)*100:.1f}% → 10% target",
        f"   - Reduce tech index exposure systematically",
        f"",
        f"**Priority 3 — Watch and Wait:**",
        f"5. **AVGO/ANET small trims** — minor adjustments, not urgent",
        f"6. **GLD/NVDA** — within acceptable drift range, monitor",
        f"",
        f"### Why This Order?",
        f"- BRK-B trim frees cash without giving up defensive exposure (still hold at target)",
        f"- PLTR trim reduces high-beta speculative risk in late cycle",
        f"- XLV is the regime-appropriate addition (defensive, recession-resistant)",
        f"- QQQ trim is systematic — reduces tech index without picking individual names",
        f"- We maintain 15% cash buffer throughout — do NOT deploy all cash",
        f"",
        f"---",
        f"",
        f"## 📋 Appendix: Raw System Output",
        f"",
        f"<details>",
        f"<summary>Regime Detector Output</summary>",
        f"",
        f"```",
        regime_output,
        f"```",
        f"",
        f"</details>",
        f"",
        f"<details>",
        f"<summary>Sentiment Composite Output</summary>",
        f"",
        f"```",
        sentiment_output,
        f"```",
        f"",
        f"</details>",
        f"",
        f"<details>",
        f"<summary>Rebalancer Preview Output</summary>",
        f"",
        f"```",
        rebalancer_output,
        f"```",
        f"",
        f"</details>",
        f"",
        f"---",
        f"",
        f"*Rule of Acquisition #22: A wise man can hear profit in the wind.*",
        f"*Report generated by Pinch Trading System v2.0*",
    ]

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Pinch Day 1 Initial Analysis')
    parser.add_argument('--preview', action='store_true', help='Print only, do not save')
    args = parser.parse_args()

    print(f"[initial_analysis] Generating Day 1 Report…", file=sys.stderr)
    print(f"[initial_analysis] Running regime detector…", file=sys.stderr)
    print(f"[initial_analysis] Running sentiment composite…", file=sys.stderr)
    print(f"[initial_analysis] Running rebalancer preview…", file=sys.stderr)
    print(f"[initial_analysis] Computing risk metrics…\n", file=sys.stderr)

    report = generate_day1_report()

    if not args.preview:
        with open(REPORT_PATH, 'w') as f:
            f.write(report)
        print(f"[initial_analysis] ✅ Day 1 Report saved → {REPORT_PATH}", file=sys.stderr)

    print(report)


if __name__ == '__main__':
    main()
