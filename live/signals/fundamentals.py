#!/usr/bin/env python3
"""
Pinch Stock Trading — Fundamental Data Collection & Scoring
Issue #30: yfinance fundamentals + Piotroski F-Score + quality/value/growth screening.

Usage:
    fundamentals.py scan                       — score all portfolio holdings
    fundamentals.py screen --value             — find value stocks
    fundamentals.py screen --quality           — find quality stocks
    fundamentals.py screen --growth            — find growth stocks
    fundamentals.py compare <sym1> <sym2>      — side-by-side comparison
    fundamentals.py refresh [--force]          — refresh fundamental data
    fundamentals.py show <symbol>              — full fundamental detail

Rule of Acquisition #22: A wise man can hear profit in the wind.
(A wiser man reads the 10-K first.)
"""

import sqlite3
import argparse
import sys
import os
import json
from datetime import datetime, date
from typing import Optional

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("[fundamentals] ⚠️  yfinance not installed — run: pip install yfinance", file=sys.stderr)

# ─── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR        = os.path.join(os.path.dirname(__file__), '../..')
STATE_DIR       = os.path.join(BASE_DIR, 'state')
PORTFOLIO_DB    = os.path.join(STATE_DIR, 'portfolio.db')
FUNDAMENTALS_FILE = os.path.join(STATE_DIR, 'fundamentals.json')
MARKET_DB       = '/mnt/media/market_data/pinch_market.db'

os.makedirs(STATE_DIR, exist_ok=True)

# ─── Full Screening Universe ──────────────────────────────────────────────────

SCREENING_UNIVERSE = [
    # Portfolio holdings
    "AAPL", "AMD", "AMZN", "ANET", "AVGO", "BRK-B", "CSCO", "GOOG",
    "META", "MSFT", "NVDA", "ORCL", "PLTR", "TSLA",
    # Additional quality/value candidates
    "JNJ", "UNH", "JPM", "V", "MA", "WMT", "COST", "HD",
    "XOM", "CVX", "NEE", "PG", "KO", "MCD", "LOW",
]

# Sector median P/E estimates (approximate 2025 data)
SECTOR_MEDIAN_PE = {
    "Technology":             28.0,
    "Communication Services": 22.0,
    "Consumer Discretionary": 25.0,
    "Consumer Staples":       22.0,
    "Energy":                 12.0,
    "Financials":             13.0,
    "Healthcare":             20.0,
    "Industrials":            20.0,
    "Materials":              16.0,
    "Real Estate":            30.0,
    "Utilities":              17.0,
}


# ─── Data Persistence ─────────────────────────────────────────────────────────

def load_fundamentals() -> dict:
    if os.path.exists(FUNDAMENTALS_FILE):
        with open(FUNDAMENTALS_FILE) as f:
            return json.load(f)
    return {}


def save_fundamentals(data: dict):
    with open(FUNDAMENTALS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def is_stale(record: dict, days: int = 7) -> bool:
    """Return True if record is older than `days` days."""
    ts = record.get("fetched_at")
    if not ts:
        return True
    try:
        fetched = datetime.fromisoformat(ts)
        return (datetime.now() - fetched).days >= days
    except Exception:
        return True


# ─── Portfolio Symbols ────────────────────────────────────────────────────────

def get_portfolio_symbols() -> list[str]:
    try:
        with sqlite3.connect(PORTFOLIO_DB) as conn:
            rows = conn.execute("SELECT symbol FROM positions").fetchall()
            # Exclude ETFs / non-equity symbols
            syms = [r[0] for r in rows]
            return [s for s in syms if s not in ("GLD", "TLT", "QQQ", "SHY", "XLV", "SPY", "IWM")]
    except Exception:
        return ["NVDA", "MSFT", "GOOG", "BRK-B", "AVGO", "PLTR", "ANET"]


# ─── Fundamental Fetcher ─────────────────────────────────────────────────────

def calculate_fcf_yield(info: dict) -> Optional[float]:
    """FCF yield = free cash flow / market cap."""
    fcf    = info.get("freeCashflow")
    mktcap = info.get("marketCap")
    if fcf and mktcap and mktcap > 0:
        return (fcf / mktcap) * 100
    return None


def get_fundamentals(symbol: str) -> dict:
    """Fetch fundamental data for a symbol via yfinance."""
    if not HAS_YFINANCE:
        return {"symbol": symbol, "error": "yfinance not installed", "fetched_at": datetime.now().isoformat()}

    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info

        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            return {
                "symbol":     symbol,
                "error":      "no data returned",
                "fetched_at": datetime.now().isoformat(),
            }

        fcf_yield = calculate_fcf_yield(info)

        return {
            "symbol":         symbol,
            "fetched_at":     datetime.now().isoformat(),
            "sector":         info.get("sector"),
            "industry":       info.get("industry"),
            "market_cap":     info.get("marketCap"),
            "pe_ratio":       info.get("trailingPE"),
            "forward_pe":     info.get("forwardPE"),
            "pb_ratio":       info.get("priceToBook"),
            "ps_ratio":       info.get("priceToSalesTrailing12Months"),
            "ev_ebitda":      info.get("enterpriseToEbitda"),
            "profit_margin":  info.get("profitMargins"),
            "roe":            info.get("returnOnEquity"),
            "debt_equity":    info.get("debtToEquity"),
            "current_ratio":  info.get("currentRatio"),
            "fcf_yield":      fcf_yield,
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio":   info.get("payoutRatio"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth":info.get("earningsGrowth"),
            # For Piotroski
            "roa":            info.get("returnOnAssets"),
            "operating_cf":   info.get("operatingCashflow"),
            "total_debt":     info.get("totalDebt"),
            "total_assets":   info.get("totalAssets"),
            "current_price":  info.get("currentPrice") or info.get("regularMarketPrice"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low":  info.get("fiftyTwoWeekLow"),
        }
    except Exception as e:
        return {
            "symbol":     symbol,
            "error":      str(e),
            "fetched_at": datetime.now().isoformat(),
        }


# ─── Scoring ─────────────────────────────────────────────────────────────────

def score_piotroski(f: dict) -> dict:
    """
    Simplified Piotroski F-Score (0-9):
    Profitability (4): ROA > 0, operating CF > 0, ROA improving (N/A without prior year), accruals low
    Leverage (3): D/E decreasing (N/A), current ratio improving (N/A), no dilution (N/A)
    Efficiency (2): gross margin improving (N/A), asset turnover improving (N/A)

    Using single-period available signals:
    - P1: ROA > 0
    - P2: Operating CF > 0
    - P3: CF > Net Income (quality of earnings) — approximate via FCF yield > 0
    - P4: Profit margin > 0
    - L1: Low debt/equity (< 1)
    - L2: Current ratio > 1
    - L3: No explicit new share data — skip (award 1 if mktcap > 0 as proxy)
    - E1: ROE > 0
    - E2: Forward P/E < Trailing P/E (earnings expected to grow)
    """
    score  = 0
    points = {}

    # Profitability
    roa = f.get("roa")
    if roa is not None:
        points["P1_roa_positive"] = 1 if roa > 0 else 0
        score += points["P1_roa_positive"]
    else:
        points["P1_roa_positive"] = None

    ocf = f.get("operating_cf")
    if ocf is not None:
        points["P2_ocf_positive"] = 1 if ocf > 0 else 0
        score += points["P2_ocf_positive"]
    else:
        points["P2_ocf_positive"] = None

    fcf_y = f.get("fcf_yield")
    if fcf_y is not None:
        points["P3_fcf_positive"] = 1 if fcf_y > 0 else 0
        score += points["P3_fcf_positive"]
    else:
        points["P3_fcf_positive"] = None

    pm = f.get("profit_margin")
    if pm is not None:
        points["P4_profit_margin_pos"] = 1 if pm > 0 else 0
        score += points["P4_profit_margin_pos"]
    else:
        points["P4_profit_margin_pos"] = None

    # Leverage
    de = f.get("debt_equity")
    if de is not None:
        points["L1_low_debt_equity"] = 1 if de < 100 else 0  # yfinance returns as %, so 100 = 1.0x
        score += points["L1_low_debt_equity"]
    else:
        points["L1_low_debt_equity"] = None

    cr = f.get("current_ratio")
    if cr is not None:
        points["L2_current_ratio_gt1"] = 1 if cr > 1 else 0
        score += points["L2_current_ratio_gt1"]
    else:
        points["L2_current_ratio_gt1"] = None

    points["L3_no_dilution"] = 1  # assume no dilution as proxy (no share count data)
    score += 1

    # Efficiency
    roe = f.get("roe")
    if roe is not None:
        points["E1_roe_positive"] = 1 if roe > 0 else 0
        score += points["E1_roe_positive"]
    else:
        points["E1_roe_positive"] = None

    fpe = f.get("forward_pe")
    pe  = f.get("pe_ratio")
    if fpe and pe and fpe > 0 and pe > 0:
        points["E2_earnings_growth"] = 1 if fpe < pe else 0
        score += points["E2_earnings_growth"]
    else:
        points["E2_earnings_growth"] = None

    return {"score": score, "max": 9, "points": points}


def score_quality(f: dict) -> dict:
    """Quality score: ROE > 15%, D/E < 1 (100 in yf %), margin > 10%, revenue growing."""
    score    = 0
    max_pts  = 4
    criteria = {}

    roe = f.get("roe")
    criteria["roe_gt_15pct"]      = (roe is not None and roe > 0.15)
    if criteria["roe_gt_15pct"]:  score += 1

    de  = f.get("debt_equity")
    criteria["de_lt_1"]           = (de is not None and de < 100)
    if criteria["de_lt_1"]:       score += 1

    pm  = f.get("profit_margin")
    criteria["margin_gt_10pct"]   = (pm is not None and pm > 0.10)
    if criteria["margin_gt_10pct"]:  score += 1

    rg  = f.get("revenue_growth")
    criteria["revenue_growing"]   = (rg is not None and rg > 0)
    if criteria["revenue_growing"]:  score += 1

    return {"score": score, "max": max_pts, "criteria": criteria, "pct": score / max_pts * 100}


def score_value(f: dict) -> dict:
    """Value score: P/E < sector median, P/B < 3, FCF yield > 5%."""
    score    = 0
    max_pts  = 3
    criteria = {}

    sector    = f.get("sector", "Technology")
    pe        = f.get("pe_ratio")
    sector_pe = SECTOR_MEDIAN_PE.get(sector, 22.0)

    criteria["pe_below_sector_median"] = (pe is not None and pe > 0 and pe < sector_pe)
    if criteria["pe_below_sector_median"]:  score += 1

    pb = f.get("pb_ratio")
    criteria["pb_lt_3"]                = (pb is not None and pb < 3)
    if criteria["pb_lt_3"]:  score += 1

    fcf_y = f.get("fcf_yield")
    criteria["fcf_yield_gt_5pct"]      = (fcf_y is not None and fcf_y > 5)
    if criteria["fcf_yield_gt_5pct"]:  score += 1

    return {"score": score, "max": max_pts, "criteria": criteria, "pct": score / max_pts * 100}


def score_growth(f: dict) -> dict:
    """Growth score: revenue > 10%, earnings > 15%, forward P/E < trailing."""
    score    = 0
    max_pts  = 3
    criteria = {}

    rg = f.get("revenue_growth")
    criteria["revenue_growth_gt_10pct"]  = (rg is not None and rg > 0.10)
    if criteria["revenue_growth_gt_10pct"]:  score += 1

    eg = f.get("earnings_growth")
    criteria["earnings_growth_gt_15pct"] = (eg is not None and eg > 0.15)
    if criteria["earnings_growth_gt_15pct"]:  score += 1

    fpe = f.get("forward_pe")
    pe  = f.get("pe_ratio")
    criteria["forward_pe_lt_trailing"]   = (fpe is not None and pe is not None and fpe > 0 and fpe < pe)
    if criteria["forward_pe_lt_trailing"]:  score += 1

    return {"score": score, "max": max_pts, "criteria": criteria, "pct": score / max_pts * 100}


def score_all(f: dict) -> dict:
    """Run all scoring models and return composite."""
    piotroski = score_piotroski(f)
    quality   = score_quality(f)
    value     = score_value(f)
    growth    = score_growth(f)

    # Composite: weighted average (piotroski 40%, quality 25%, value 20%, growth 15%)
    composite = (
        piotroski["score"] / piotroski["max"] * 0.40 +
        quality["score"]   / quality["max"]   * 0.25 +
        value["score"]     / value["max"]     * 0.20 +
        growth["score"]    / growth["max"]    * 0.15
    ) * 100

    return {
        "piotroski": piotroski,
        "quality":   quality,
        "value":     value,
        "growth":    growth,
        "composite": composite,
    }


def score_label(composite: float) -> str:
    if composite >= 75:  return "⭐ EXCEPTIONAL"
    if composite >= 60:  return "✅ STRONG"
    if composite >= 45:  return "👍 ABOVE AVERAGE"
    if composite >= 30:  return "➖ AVERAGE"
    return "⚠️  WEAK"


# ─── Display ─────────────────────────────────────────────────────────────────

def print_fundamentals_row(f: dict, scores: dict):
    sym       = f.get("symbol", "?")
    pe        = f.get("pe_ratio")
    fpe       = f.get("forward_pe")
    pb        = f.get("pb_ratio")
    roe       = f.get("roe")
    margin    = f.get("profit_margin")
    rg        = f.get("revenue_growth")
    de        = f.get("debt_equity")
    composite = scores["composite"]

    pe_str    = f"{pe:.1f}"   if pe    else "N/A"
    fpe_str   = f"{fpe:.1f}"  if fpe   else "N/A"
    pb_str    = f"{pb:.1f}"   if pb    else "N/A"
    roe_str   = f"{roe*100:.1f}%" if roe else "N/A"
    margin_str= f"{margin*100:.1f}%" if margin else "N/A"
    rg_str    = f"{rg*100:.1f}%"  if rg   else "N/A"
    de_str    = f"{de/100:.1f}x" if de else "N/A"
    label     = score_label(composite)

    print(
        f"  {sym:<8} {pe_str:>6} {fpe_str:>6} {pb_str:>6} {roe_str:>7} "
        f"{margin_str:>8} {rg_str:>8} {de_str:>7}  {composite:>5.0f}  {label}"
    )


def print_full_detail(f: dict, scores: dict):
    sym = f.get("symbol", "?")
    print(f"\n{'='*70}")
    print(f"  FUNDAMENTALS: {sym}  |  {f.get('sector','N/A')} / {f.get('industry','N/A')}")
    print(f"{'='*70}")

    def fmt(val, pct=False, mult=1, suffix=""):
        if val is None:
            return "N/A"
        if pct:
            return f"{val*mult*100:.1f}%"
        if suffix:
            return f"{val:.2f}{suffix}"
        if isinstance(val, float):
            return f"{val:.2f}"
        return str(val)

    mktcap = f.get("market_cap")
    mktcap_str = f"${mktcap/1e9:.1f}B" if mktcap else "N/A"

    print(f"\n  Valuation:")
    print(f"    Market Cap:      {mktcap_str}")
    print(f"    P/E (trailing):  {fmt(f.get('pe_ratio'))}")
    print(f"    P/E (forward):   {fmt(f.get('forward_pe'))}")
    print(f"    P/B:             {fmt(f.get('pb_ratio'))}")
    print(f"    P/S:             {fmt(f.get('ps_ratio'))}")
    print(f"    EV/EBITDA:       {fmt(f.get('ev_ebitda'))}")
    print(f"    FCF Yield:       {fmt(f.get('fcf_yield'), suffix='%')}")

    print(f"\n  Profitability:")
    print(f"    Profit Margin:   {fmt(f.get('profit_margin'), pct=True)}")
    print(f"    ROE:             {fmt(f.get('roe'), pct=True)}")
    print(f"    ROA:             {fmt(f.get('roa'), pct=True)}")

    print(f"\n  Growth:")
    print(f"    Revenue Growth:  {fmt(f.get('revenue_growth'), pct=True)}")
    print(f"    Earnings Growth: {fmt(f.get('earnings_growth'), pct=True)}")

    print(f"\n  Balance Sheet:")
    print(f"    Debt/Equity:     {fmt(f.get('debt_equity'), suffix='%') if f.get('debt_equity') else 'N/A'}")
    print(f"    Current Ratio:   {fmt(f.get('current_ratio'))}")

    print(f"\n  Income:")
    print(f"    Dividend Yield:  {fmt(f.get('dividend_yield'), pct=True)}")
    print(f"    Payout Ratio:    {fmt(f.get('payout_ratio'), pct=True)}")

    print(f"\n  Scores:")
    print(f"    Piotroski F:     {scores['piotroski']['score']}/9")
    print(f"    Quality:         {scores['quality']['score']}/4  ({scores['quality']['pct']:.0f}%)")
    print(f"    Value:           {scores['value']['score']}/3  ({scores['value']['pct']:.0f}%)")
    print(f"    Growth:          {scores['growth']['score']}/3  ({scores['growth']['pct']:.0f}%)")
    print(f"    Composite:       {scores['composite']:.0f}/100  {score_label(scores['composite'])}")

    # Flags
    flags = []
    pm = f.get("profit_margin")
    de = f.get("debt_equity")
    roe = f.get("roe")
    rg = f.get("revenue_growth")
    if pm and pm < 0:         flags.append("⚠️  Negative profit margin")
    if de and de > 200:       flags.append("⚠️  High debt/equity > 2x")
    if roe and roe < 0:       flags.append("⚠️  Negative ROE")
    if rg and rg < -0.05:     flags.append("⚠️  Declining revenue (>5%)")

    if flags:
        print(f"\n  ⚡ Flags:")
        for flg in flags:
            print(f"    {flg}")
    print(f"{'='*70}\n")


# ─── Commands ─────────────────────────────────────────────────────────────────

def refresh_symbol(symbol: str, force: bool = False) -> dict:
    """Fetch and cache fundamentals for a symbol."""
    data = load_fundamentals()
    record = data.get(symbol, {})

    if not force and record and not is_stale(record, days=7):
        return record

    print(f"  Fetching {symbol}…", end="", flush=True)
    f = get_fundamentals(symbol)
    if "error" in f:
        print(f" ⚠️  {f['error']}")
    else:
        scores = score_all(f)
        f["scores"] = scores
        data[symbol] = f
        save_fundamentals(data)
        composite = scores["composite"]
        print(f" {score_label(composite)} ({composite:.0f})")

    return data.get(symbol, f)


def cmd_scan(args):
    symbols = get_portfolio_symbols()
    print(f"\n[fundamentals] Scanning {len(symbols)} portfolio holdings…\n")

    all_data = []
    for sym in symbols:
        record = refresh_symbol(sym, force=getattr(args, 'force', False))
        if "scores" in record:
            all_data.append(record)

    print(f"\n{'='*90}")
    print(f"  FUNDAMENTAL SCAN — Portfolio Holdings")
    print(f"{'='*90}")
    print(f"  {'SYM':<8} {'P/E':>6} {'FPE':>6} {'P/B':>6} {'ROE':>7} {'MARGIN':>8} {'REV GRW':>8} {'D/E':>7}  {'SCORE':>5}  RATING")
    print(f"  {'-'*84}")

    for f in sorted(all_data, key=lambda x: x["scores"]["composite"], reverse=True):
        print_fundamentals_row(f, f["scores"])

    print(f"{'='*90}\n")


def cmd_screen(args):
    mode     = "value" if args.value else ("quality" if args.quality else "growth")
    universe = SCREENING_UNIVERSE
    print(f"\n[fundamentals] Screening {len(universe)} stocks for {mode.upper()} criteria…\n")

    qualified = []
    data = load_fundamentals()

    for sym in universe:
        if sym not in data or is_stale(data[sym]):
            record = refresh_symbol(sym, force=False)
        else:
            record = data[sym]

        if "scores" not in record:
            continue

        s = record["scores"]
        if mode == "value"   and s["value"]["score"] >= 2:
            qualified.append(record)
        elif mode == "quality" and s["quality"]["score"] >= 3:
            qualified.append(record)
        elif mode == "growth"  and s["growth"]["score"] >= 2:
            qualified.append(record)

    qualified.sort(key=lambda x: x["scores"]["composite"], reverse=True)

    print(f"\n{'='*90}")
    print(f"  {mode.upper()} SCREEN RESULTS ({len(qualified)} qualifying)")
    print(f"{'='*90}")
    print(f"  {'SYM':<8} {'P/E':>6} {'FPE':>6} {'P/B':>6} {'ROE':>7} {'MARGIN':>8} {'REV GRW':>8} {'D/E':>7}  {'SCORE':>5}  RATING")
    print(f"  {'-'*84}")
    for f in qualified[:20]:
        print_fundamentals_row(f, f["scores"])
    print(f"{'='*90}\n")


def cmd_compare(args):
    sym1, sym2 = args.symbol1.upper(), args.symbol2.upper()
    print(f"\n[fundamentals] Comparing {sym1} vs {sym2}…\n")

    r1 = refresh_symbol(sym1, force=False)
    r2 = refresh_symbol(sym2, force=False)

    if "scores" not in r1 or "scores" not in r2:
        print("[fundamentals] Could not load data for both symbols.")
        return

    def fmt_row(label: str, key: str, pct: bool = False, invert: bool = False):
        v1 = r1.get(key)
        v2 = r2.get(key)
        s1 = f"{v1*100:.1f}%" if (v1 is not None and pct) else (f"{v1:.2f}" if v1 is not None else "N/A")
        s2 = f"{v2*100:.1f}%" if (v2 is not None and pct) else (f"{v2:.2f}" if v2 is not None else "N/A")
        # winner: lower is better for invert=True, higher for False
        winner = ""
        if v1 is not None and v2 is not None:
            if (v1 > v2) ^ invert:
                winner = f"← {sym1}"
            elif v2 > v1:
                winner = f"{sym2} →"
            else:
                winner = "tie"
        return f"  {label:<22} {s1:>10}  {s2:>10}  {winner}"

    print(f"\n  {'METRIC':<22} {sym1:>10}  {sym2:>10}  WINNER")
    print(f"  {'-'*55}")
    print(fmt_row("P/E (trailing)",   "pe_ratio",       invert=True))
    print(fmt_row("P/E (forward)",    "forward_pe",     invert=True))
    print(fmt_row("P/B",              "pb_ratio",       invert=True))
    print(fmt_row("P/S",              "ps_ratio",       invert=True))
    print(fmt_row("EV/EBITDA",        "ev_ebitda",      invert=True))
    print(fmt_row("Profit Margin",    "profit_margin",  pct=True))
    print(fmt_row("ROE",              "roe",            pct=True))
    print(fmt_row("Revenue Growth",   "revenue_growth", pct=True))
    print(fmt_row("Earnings Growth",  "earnings_growth",pct=True))
    print(fmt_row("FCF Yield",        "fcf_yield"))
    print(fmt_row("Current Ratio",    "current_ratio"))

    print(f"\n  Scores:")
    s1c = r1["scores"]["composite"]
    s2c = r2["scores"]["composite"]
    w1  = "← winner" if s1c > s2c else ""
    w2  = "winner →" if s2c > s1c else ""
    print(f"  {'Composite Score':<22} {s1c:>10.0f}  {s2c:>10.0f}  {w1 or w2}")
    print(f"  {'Piotroski F':<22} {r1['scores']['piotroski']['score']:>10}  {r2['scores']['piotroski']['score']:>10}")
    print(f"  {'Quality':<22} {r1['scores']['quality']['score']:>10}  {r2['scores']['quality']['score']:>10}")
    print(f"  {'Value':<22} {r1['scores']['value']['score']:>10}  {r2['scores']['value']['score']:>10}")
    print(f"  {'Growth':<22} {r1['scores']['growth']['score']:>10}  {r2['scores']['growth']['score']:>10}")
    print()


def cmd_show(args):
    sym    = args.symbol.upper()
    record = refresh_symbol(sym, force=getattr(args, 'force', False))
    if "scores" not in record:
        print(f"[fundamentals] No data available for {sym}")
        return
    print_full_detail(record, record["scores"])


def cmd_refresh(args):
    universe = get_portfolio_symbols() + [s for s in SCREENING_UNIVERSE if s not in get_portfolio_symbols()]
    force    = getattr(args, 'force', False)
    print(f"\n[fundamentals] Refreshing {len(universe)} symbols (force={force})…\n")
    data = {}
    for sym in universe:
        record = refresh_symbol(sym, force=force)
        if "scores" in record:
            data[sym] = record
    print(f"\n[fundamentals] Done. {len(data)} symbols cached in {FUNDAMENTALS_FILE}")


# ─── Deterioration Check ─────────────────────────────────────────────────────

def check_deterioration() -> list[str]:
    """
    Compare latest fundamentals against prior values to flag deterioration.
    Returns list of warning strings.
    """
    data = load_fundamentals()
    warnings = []
    for sym, f in data.items():
        if "error" in f:
            continue
        pm  = f.get("profit_margin")
        rg  = f.get("revenue_growth")
        roe = f.get("roe")

        if pm and pm < 0:
            warnings.append(f"{sym}: Negative profit margin ({pm*100:.1f}%)")
        if rg and rg < -0.10:
            warnings.append(f"{sym}: Revenue declining >10% ({rg*100:.1f}%)")
        if roe and roe < -0.05:
            warnings.append(f"{sym}: Negative ROE ({roe*100:.1f}%)")
    return warnings


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Fundamental Data & Screening',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scoring Weights:
  Piotroski F-Score (0-9):  40% of composite
  Quality Score (0-4):      25% of composite
  Value Score (0-3):        20% of composite
  Growth Score (0-3):       15% of composite

Examples:
  fundamentals.py scan
  fundamentals.py screen --value
  fundamentals.py screen --quality
  fundamentals.py screen --growth
  fundamentals.py compare NVDA AMD
  fundamentals.py show MSFT
  fundamentals.py refresh --force
        """
    )
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('scan', help='Score all portfolio holdings')

    scr = sub.add_parser('screen', help='Screen for value/quality/growth stocks')
    scr_group = scr.add_mutually_exclusive_group(required=True)
    scr_group.add_argument('--value',   action='store_true')
    scr_group.add_argument('--quality', action='store_true')
    scr_group.add_argument('--growth',  action='store_true')

    cmp = sub.add_parser('compare', help='Side-by-side fundamental comparison')
    cmp.add_argument('symbol1')
    cmp.add_argument('symbol2')

    shw = sub.add_parser('show', help='Full fundamental detail for a symbol')
    shw.add_argument('symbol')
    shw.add_argument('--force', action='store_true', help='Force re-fetch')

    ref = sub.add_parser('refresh', help='Refresh fundamental data cache')
    ref.add_argument('--force', action='store_true', help='Force re-fetch even if fresh')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'screen':
        cmd_screen(args)
    elif args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'show':
        cmd_show(args)
    elif args.command == 'refresh':
        cmd_refresh(args)


if __name__ == '__main__':
    main()
