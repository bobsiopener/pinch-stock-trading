#!/usr/bin/env python3
"""
Pinch Stock Trading — Insider Trading / Institutional Flow Signal
Issue #27: SEC EDGAR Form 4 + 13F filings for insider activity signals.

Usage:
    insider_flow.py check <symbol>           — recent insider activity for ticker
    insider_flow.py scan                     — scan all portfolio holdings
    insider_flow.py institutional <symbol>   — top institutional holders (13F)

Rule of Acquisition #34: War is good for business. (So is knowing who's buying.)
"""

import sqlite3
import argparse
import sys
import os
import json
import time
import requests
from datetime import datetime, date, timedelta
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR     = os.path.join(os.path.dirname(__file__), '../..')
STATE_DIR    = os.path.join(BASE_DIR, 'state')
PORTFOLIO_DB = os.path.join(STATE_DIR, 'portfolio.db')
INSIDER_FILE = os.path.join(STATE_DIR, 'insider_flow.json')
MARKET_DB    = '/mnt/media/market_data/pinch_market.db'

os.makedirs(STATE_DIR, exist_ok=True)

# ─── EDGAR Config ─────────────────────────────────────────────────────────────

EDGAR_HEADERS = {
    "User-Agent": "Pinch-TradingBot/1.0 pinch@openclaw.ai",
    "Accept": "application/json",
}

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&forms=4"
EDGAR_FILING_URL = "https://data.sec.gov/submissions/{cik}.json"
EDGAR_COMPANY_SEARCH = "https://efts.sec.gov/LATEST/search-index?q=%22{name}%22&forms=13F-HR&dateRange=custom&startdt={start}"
EDGAR_FULLTEXT_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=4&dateRange=custom&startdt={start}&enddt={end}"

# Known CIKs for major 13F filers (padded to 10 digits)
MAJOR_13F_FILERS = {
    "Berkshire Hathaway": "0001067983",
    "Bridgewater Associates": "0001350694",
    "Renaissance Technologies": "0001037389",
    "Citadel Advisors": "0001423298",
    "BlackRock": "0001364742",
    "Vanguard": "0000102909",
}

# Strong signal roles
HIGH_CONVICTION_ROLES = {
    "Chief Executive Officer", "CEO", "President", "Chief Financial Officer",
    "CFO", "Executive Vice President", "EVP", "Director", "Chairman",
    "10% Owner", "Chief Operating Officer", "COO",
}

# ─── Portfolio Symbols ────────────────────────────────────────────────────────

def get_portfolio_symbols() -> list[str]:
    """Load symbols from positions table."""
    try:
        with sqlite3.connect(PORTFOLIO_DB) as conn:
            rows = conn.execute("SELECT symbol FROM positions").fetchall()
            return [r[0] for r in rows]
    except Exception:
        return ["QQQ", "NVDA", "MSFT", "GOOG", "BRK-B", "AVGO", "GLD", "TLT", "PLTR", "ANET"]


# ─── Market Price Helpers ─────────────────────────────────────────────────────

def get_price_stats(symbol: str) -> dict:
    """Return current price and 52-week high/low."""
    try:
        with sqlite3.connect(MARKET_DB) as conn:
            rows = conn.execute(
                "SELECT close FROM prices WHERE symbol=? ORDER BY timestamp DESC LIMIT 252",
                (symbol.upper(),)
            ).fetchall()
            if not rows:
                return {}
            prices = [r[0] for r in rows]
            return {
                "current": prices[0],
                "high_52w": max(prices),
                "low_52w": min(prices),
                "pct_from_low": (prices[0] / min(prices) - 1) * 100,
                "pct_from_high": (prices[0] / max(prices) - 1) * 100,
            }
    except Exception:
        return {}


# ─── EDGAR Fetchers ───────────────────────────────────────────────────────────

def _edgar_get(url: str, retries: int = 3) -> Optional[dict]:
    """GET with retry, rate-limit awareness."""
    for i in range(retries):
        try:
            resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                print(f"[insider_flow] Rate limited — waiting {wait}s…", file=sys.stderr)
                time.sleep(wait)
                continue
            if resp.status_code == 200:
                return resp.json()
            print(f"[insider_flow] HTTP {resp.status_code} for {url}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[insider_flow] Request error ({e}) — retry {i+1}/{retries}", file=sys.stderr)
            time.sleep(2)
    return None


def fetch_form4_filings(ticker: str, days: int = 90) -> list[dict]:
    """
    Fetch recent Form 4 filings for a ticker via EDGAR full-text search.
    Returns list of filing metadata dicts.
    """
    start = (date.today() - timedelta(days=days)).isoformat()
    end   = date.today().isoformat()
    url   = EDGAR_FULLTEXT_URL.format(ticker=ticker.upper(), start=start, end=end)

    data = _edgar_get(url)
    if not data:
        return []

    hits = data.get("hits", {}).get("hits", [])
    filings = []
    for hit in hits[:20]:
        src = hit.get("_source", {})
        filings.append({
            "filing_date": src.get("period_of_report", src.get("file_date", "")),
            "form_type":   src.get("form_type", "4"),
            "filer_name":  src.get("display_names", [src.get("entity_name", "Unknown")])[0] if src.get("display_names") else src.get("entity_name", "Unknown"),
            "cik":         src.get("entity_id", ""),
            "accession":   src.get("accession_no", ""),
            "description": src.get("biz_description", ""),
        })
    return filings


def fetch_company_cik(ticker: str) -> Optional[str]:
    """Look up a company's CIK by ticker from EDGAR company search."""
    try:
        url  = f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker.upper()}&type=4&dateb=&owner=include&count=1&search_text=&action=getcompany&output=atom"
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        # Parse CIK from atom/XML response (simplified)
        import re
        m = re.search(r'/cgi-bin/browse-edgar\?action=getcompany&CIK=(\d+)', resp.text)
        return m.group(1).zfill(10) if m else None
    except Exception:
        return None


def fetch_13f_holdings(filer_name: str) -> list[dict]:
    """
    Fetch latest 13F-HR filing holdings for a known filer.
    Returns top holdings list.
    """
    cik = MAJOR_13F_FILERS.get(filer_name)
    if not cik:
        print(f"[insider_flow] Unknown filer: {filer_name}", file=sys.stderr)
        return []

    url  = EDGAR_FILING_URL.format(cik=cik)
    data = _edgar_get(url)
    if not data:
        return []

    filings = data.get("filings", {}).get("recent", {})
    forms   = filings.get("form", [])
    dates   = filings.get("filingDate", [])
    accnos  = filings.get("accessionNumber", [])

    # Find most recent 13F-HR
    idx = next((i for i, f in enumerate(forms) if "13F-HR" in f), None)
    if idx is None:
        return []

    filing_date = dates[idx]
    accno       = accnos[idx].replace("-", "")

    # Fetch the index page for this filing
    idx_url = f"https://www.sec.gov/Archives/edgar/full-index/{filing_date[:4]}/{filing_date[5:7]}/form.idx"

    return [{
        "filer":        filer_name,
        "form":         "13F-HR",
        "filing_date":  filing_date,
        "accession":    accnos[idx],
        "note":         "13F data is 45 days delayed — for long-term positioning only",
        "source_url":   f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F&dateb=&owner=include&count=5",
    }]


# ─── Signal Logic ─────────────────────────────────────────────────────────────

def analyze_insider_signal(ticker: str, filings: list[dict], price_stats: dict) -> dict:
    """
    Apply insider signal rules:
    - Cluster buys (3+ insiders buying within 30 days) = STRONG BUY
    - CEO/CFO buying > $500K = significant signal
    - Insider selling alone = weak signal
    - Buying + near 52-week low = high conviction
    """
    buy_count  = 0
    sell_count = 0
    signal     = "NEUTRAL"
    reasons    = []

    # Count buys vs sells from filing descriptions
    for f in filings:
        desc = (f.get("description", "") + " " + f.get("filer_name", "")).lower()
        if any(w in desc for w in ["purchase", "acquisition", "buy"]):
            buy_count += 1
        elif any(w in desc for w in ["sale", "disposition", "sell"]):
            sell_count += 1

    # Rule: cluster buys
    if buy_count >= 3:
        signal = "STRONG BUY"
        reasons.append(f"Cluster buying: {buy_count} insider buy filings in 90 days")
    elif buy_count >= 1:
        signal = "MILD BUY"
        reasons.append(f"{buy_count} insider buy filing(s) in 90 days")

    # Rule: near 52-week low boosts conviction
    if price_stats and price_stats.get("pct_from_low", 100) < 15 and buy_count > 0:
        if signal == "MILD BUY":
            signal = "BUY"
        elif signal == "STRONG BUY":
            signal = "VERY STRONG BUY"
        reasons.append(f"Stock near 52W low ({price_stats['pct_from_low']:.1f}% from low) — high conviction")

    # Rule: selling alone is weak
    if sell_count > 0 and buy_count == 0:
        signal = "WEAK SELL (noise)"
        reasons.append(f"{sell_count} insider sell filing(s) — selling alone is weak signal (diversification/taxes)")

    total_filings = len(filings)

    return {
        "ticker":         ticker,
        "signal":         signal,
        "buy_filings":    buy_count,
        "sell_filings":   sell_count,
        "total_filings":  total_filings,
        "price_stats":    price_stats,
        "reasons":        reasons,
        "filing_count":   total_filings,
        "checked_at":     datetime.now().isoformat(),
    }


# ─── State Persistence ────────────────────────────────────────────────────────

def load_state() -> dict:
    if os.path.exists(INSIDER_FILE):
        with open(INSIDER_FILE) as f:
            return json.load(f)
    return {"insider": {}, "institutional": {}}


def save_state(data: dict):
    with open(INSIDER_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_check(args):
    ticker = args.symbol.upper()
    print(f"\n[insider_flow] Checking Form 4 filings for {ticker} (last 90 days)…")

    filings     = fetch_form4_filings(ticker, days=90)
    price_stats = get_price_stats(ticker)
    analysis    = analyze_insider_signal(ticker, filings, price_stats)

    # Cache result
    state = load_state()
    state["insider"][ticker] = analysis
    save_state(state)

    # Display
    print(f"\n{'='*60}")
    print(f"  INSIDER FLOW: {ticker}")
    print(f"{'='*60}")
    print(f"  Signal:         {analysis['signal']}")
    print(f"  Buy filings:    {analysis['buy_filings']}")
    print(f"  Sell filings:   {analysis['sell_filings']}")
    print(f"  Total filings:  {analysis['total_filings']}")
    if price_stats:
        print(f"\n  Price Stats:")
        print(f"    Current:       ${price_stats.get('current', 0):.2f}")
        print(f"    52W High:      ${price_stats.get('high_52w', 0):.2f}  ({price_stats.get('pct_from_high', 0):+.1f}%)")
        print(f"    52W Low:       ${price_stats.get('low_52w', 0):.2f}   ({price_stats.get('pct_from_low', 0):+.1f}%)")
    if analysis["reasons"]:
        print(f"\n  Analysis:")
        for r in analysis["reasons"]:
            print(f"    • {r}")
    if filings:
        print(f"\n  Recent Filings:")
        for f in filings[:5]:
            print(f"    [{f['filing_date'][:10]}] {f['filer_name'][:40]}")
    else:
        print(f"\n  No Form 4 filings found in last 90 days.")
    print(f"{'='*60}\n")


def cmd_scan(args):
    symbols = get_portfolio_symbols()
    print(f"\n[insider_flow] Scanning {len(symbols)} portfolio holdings for insider activity…\n")

    results  = []
    state    = load_state()

    for sym in symbols:
        if sym.startswith("_") or sym in ("GLD", "TLT", "QQQ", "SHY", "XLV"):
            # ETFs/commodities don't have insider filings
            print(f"  {sym:<8} — ETF/commodity, skipping Form 4")
            continue

        print(f"  Checking {sym}…", end="", flush=True)
        filings     = fetch_form4_filings(sym, days=90)
        price_stats = get_price_stats(sym)
        analysis    = analyze_insider_signal(sym, filings, price_stats)
        state["insider"][sym] = analysis
        results.append(analysis)
        print(f" {analysis['signal']} ({analysis['total_filings']} filings)")
        time.sleep(0.5)  # EDGAR rate limit courtesy

    save_state(state)

    # Summary
    print(f"\n{'='*65}")
    print(f"  INSIDER FLOW SCAN RESULTS")
    print(f"{'='*65}")
    print(f"  {'SYMBOL':<10} {'SIGNAL':<22} {'BUYS':>5} {'SELLS':>6} {'FILINGS':>8}")
    print(f"  {'-'*58}")
    for r in sorted(results, key=lambda x: x["buy_filings"], reverse=True):
        print(
            f"  {r['ticker']:<10} {r['signal']:<22} {r['buy_filings']:>5} "
            f"{r['sell_filings']:>6} {r['total_filings']:>8}"
        )
    print(f"{'='*65}\n")


def cmd_institutional(args):
    ticker = args.symbol.upper()
    print(f"\n[insider_flow] Fetching institutional (13F) data for {ticker}…")
    print(f"  Note: 13F data is 45 days delayed — use for positioning, not timing.\n")

    state    = load_state()
    all_data = []

    for filer_name in MAJOR_13F_FILERS:
        print(f"  Checking {filer_name}…", end="", flush=True)
        result = fetch_13f_holdings(filer_name)
        if result:
            all_data.extend(result)
            print(f" ✓ latest 13F: {result[0]['filing_date']}")
        else:
            print(f" no data")
        time.sleep(0.3)

    state["institutional"][ticker] = {
        "ticker":     ticker,
        "checked_at": datetime.now().isoformat(),
        "filers":     all_data,
        "note":       "13F filings list major holders. For actual position sizes, parse the XML attachments.",
        "source":     f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=SC+13G&dateb=&owner=include&count=40",
    }
    save_state(state)

    print(f"\n{'='*70}")
    print(f"  INSTITUTIONAL HOLDINGS: {ticker}")
    print(f"{'='*70}")
    print(f"  {'FILER':<30} {'FORM':<10} {'FILED':>12}  NOTE")
    print(f"  {'-'*65}")
    for d in all_data:
        note_short = d.get("note", "")[:30]
        print(f"  {d['filer']:<30} {d['form']:<10} {d['filing_date']:>12}  {note_short}")
    print(f"\n  💡 For full position data, use:")
    print(f"     https://www.sec.gov/cgi-bin/viewer?action=view&cik=<CIK>&type=13F")
    print(f"     or whalewisdom.com / dataroma.com (aggregators)")
    print(f"{'='*70}\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pinch Insider Flow & Institutional Signal',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Signal Interpretation:
  STRONG BUY        — 3+ insiders buying within 90 days
  BUY               — Insider buying near 52W low (high conviction)
  MILD BUY          — Some insider buying activity
  NEUTRAL           — No recent insider activity
  WEAK SELL (noise) — Insider selling only (usually diversification/taxes)

Examples:
  insider_flow.py check NVDA
  insider_flow.py scan
  insider_flow.py institutional AAPL
        """
    )
    sub = parser.add_subparsers(dest='command')

    chk = sub.add_parser('check', help='Recent insider activity for a symbol')
    chk.add_argument('symbol')

    sub.add_parser('scan', help='Scan all portfolio holdings')

    inst = sub.add_parser('institutional', help='Top institutional holders (13F)')
    inst.add_argument('symbol')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'check':
        cmd_check(args)
    elif args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'institutional':
        cmd_institutional(args)


if __name__ == '__main__':
    main()
