"""
Migrate Existing Imaginary Portfolio
Reads current positions from memory/portfolios.md and documents what will be imported.

This script does NOT execute trades — it just documents the import plan.
Run portfolio_manager.py to actually import.
"""

import os
import re
from pathlib import Path

MEMORY_FILE = Path('/home/bob/.openclaw/workspace-pinch/memory/portfolios.md')
PORTFOLIO_MANAGER = Path(__file__).parent / 'portfolio_manager.py'


def read_portfolio_file():
    """Read the current imaginary portfolio from memory."""
    if not MEMORY_FILE.exists():
        print(f"[migrate] Memory file not found: {MEMORY_FILE}")
        return None

    with open(MEMORY_FILE, 'r') as f:
        content = f.read()

    return content


def parse_stock_positions(content: str):
    """
    Parse stock/ETF positions from the portfolio markdown.
    Returns list of dicts with symbol, shares, avg_cost.

    NOTE: This is a best-effort parser — review output before importing.
    """
    positions = []

    # Look for table rows with stock data
    # Pattern: | SYMBOL | shares | price | value | ...
    lines = content.split('\n')
    in_table = False

    for line in lines:
        line = line.strip()
        if '|' not in line:
            in_table = False
            continue

        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) < 3:
            continue

        # Skip header and separator lines
        if parts[0] in ('Symbol', 'Ticker', '---', ':-:') or '---' in parts[0]:
            continue

        # Try to extract symbol and numeric values
        symbol = parts[0].upper().replace('$', '').strip()
        if not re.match(r'^[A-Z]{1,5}(-[A-Z])?$', symbol):
            continue

        # Try to find share count and price
        nums = []
        for p in parts[1:]:
            cleaned = re.sub(r'[$,]', '', p)
            try:
                nums.append(float(cleaned))
            except ValueError:
                pass

        if len(nums) >= 2:
            positions.append({
                'symbol': symbol,
                'shares': nums[0],
                'avg_cost': nums[1],
                'source': 'memory/portfolios.md'
            })

    return positions


def generate_import_commands(positions):
    """Generate the CLI commands to import positions."""
    if not positions:
        print("[migrate] No positions found to import.")
        return

    print("\n" + "="*60)
    print("  MIGRATION PLAN — Review before executing")
    print("="*60)
    print(f"\n  Found {len(positions)} stock/ETF positions:\n")

    for p in positions:
        cmd = f"python3 live/portfolio/portfolio_manager.py buy {p['symbol']} {p['shares']:.0f} --price {p['avg_cost']:.2f} --reason 'Migrated from imaginary portfolio'"
        print(f"  {cmd}")

    print("\n" + "="*60)
    print("  NOTE: Prices are approximate (avg cost, not current market)")
    print("  Review each position before executing.")
    print("  Current cash balance will be adjusted automatically.")
    print("="*60 + "\n")


def main():
    print("[migrate] Reading existing portfolio from memory...")
    content = read_portfolio_file()

    if content is None:
        print("[migrate] Could not read portfolio file. Manual import required.")
        print(f"\n  Portfolio file expected at: {MEMORY_FILE}")
        print("  Use: python3 live/portfolio/portfolio_manager.py buy SYMBOL SHARES --price PRICE")
        return

    print("[migrate] Parsing stock positions...")
    positions = parse_stock_positions(content)

    if not positions:
        print("[migrate] No parseable positions found.")
        print("  The portfolio file may use a different format.")
        print("  Manual import commands:")
        print("  python3 live/portfolio/portfolio_manager.py buy AAPL 100 --price 190.00")
    else:
        generate_import_commands(positions)


if __name__ == '__main__':
    main()
