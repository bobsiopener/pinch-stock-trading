"""
Stock Trading Data Loader
Reads from shared market database at /mnt/media/market_data/pinch_market.db

Pinch Stock Trading Platform
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict

DB_PATH = '/mnt/media/market_data/pinch_market.db'

# Known sector ETFs in the database
SECTOR_ETFS = ['XLK', 'XLF', 'XLV', 'XLE', 'XLY', 'XLP', 'XLI', 'XLU', 'XLRE', 'XLB', 'XBI', 'SMH']
INDEX_ETFS = ['SPY', 'QQQ', 'IWM', 'DIA']
INTL_ETFS = ['EEM', 'FXI', 'EWJ']
COMMODITY_ETFS = ['GLD', 'SLV', 'USO']
BOND_ETFS = ['TLT', 'IEF', 'SHY']


def _get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)


def get_prices(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Get daily OHLCV for a stock/ETF symbol.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL', 'SPY')
        start_date: Start date as 'YYYY-MM-DD' (default: 2010-01-01)
        end_date: End date as 'YYYY-MM-DD' (default: today)

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
        Index: date (datetime)
    """
    if start_date is None:
        start_date = '2010-01-01'
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    query = """
        SELECT date, open, high, low, close, volume
        FROM prices
        WHERE symbol = ?
          AND date >= ?
          AND date <= ?
        ORDER BY date ASC
    """

    with _get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=(symbol.upper(), start_date, end_date))

    if df.empty:
        return df

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df


def get_multiple(symbols: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Get prices for multiple symbols.

    Args:
        symbols: List of ticker symbols
        start_date: Start date as 'YYYY-MM-DD'
        end_date: End date as 'YYYY-MM-DD'

    Returns:
        Dict mapping symbol -> DataFrame of OHLCV data
    """
    result = {}
    for symbol in symbols:
        df = get_prices(symbol, start_date, end_date)
        if not df.empty:
            result[symbol.upper()] = df
    return result


def get_close_matrix(symbols: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Get a matrix of closing prices for multiple symbols.

    Args:
        symbols: List of ticker symbols
        start_date: Start date as 'YYYY-MM-DD'
        end_date: End date as 'YYYY-MM-DD'

    Returns:
        DataFrame with dates as index, symbols as columns
    """
    data = get_multiple(symbols, start_date, end_date)
    if not data:
        return pd.DataFrame()

    close_data = {sym: df['close'] for sym, df in data.items()}
    return pd.DataFrame(close_data)


def get_economic(series_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Get FRED economic series data.

    Args:
        series_id: FRED series ID (e.g. 'FEDFUNDS', 'CPIAUCSL', 'T10Y2Y', 'UNRATE')
        start_date: Start date as 'YYYY-MM-DD'
        end_date: End date as 'YYYY-MM-DD'

    Returns:
        DataFrame with columns: date, value
        Index: date (datetime)

    Common series:
        FEDFUNDS  - Federal Funds Rate
        CPIAUCSL  - CPI (all urban consumers)
        T10Y2Y    - 10Y-2Y Treasury yield spread (yield curve)
        T10YIE    - 10Y breakeven inflation
        UNRATE    - Unemployment rate
        GDP       - Gross Domestic Product
        DGS10     - 10-Year Treasury Constant Maturity Rate
        DGS2      - 2-Year Treasury Constant Maturity Rate
    """
    if start_date is None:
        start_date = '2000-01-01'
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # Try fred_data table first, fall back to economic_data
    with _get_connection() as conn:
        cursor = conn.cursor()
        tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        if 'fred_data' in tables:
            query = """
                SELECT date, value
                FROM fred_data
                WHERE series_id = ?
                  AND date >= ?
                  AND date <= ?
                ORDER BY date ASC
            """
        elif 'economic_data' in tables:
            query = """
                SELECT date, value
                FROM economic_data
                WHERE series_id = ?
                  AND date >= ?
                  AND date <= ?
                ORDER BY date ASC
            """
        else:
            print(f"[db_loader] Warning: No FRED/economic table found. Available: {tables}")
            return pd.DataFrame()

        df = pd.read_sql_query(query, conn, params=(series_id.upper(), start_date, end_date))

    if df.empty:
        return df

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df


def get_vix(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Get VIX data (fear index). Available since 1990.

    Returns:
        DataFrame with VIX close values
    """
    if start_date is None:
        start_date = '1990-01-01'

    with _get_connection() as conn:
        cursor = conn.cursor()
        tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        # Try vix table or prices table with VIX symbol
        if 'vix' in tables:
            query = f"""
                SELECT date, close
                FROM vix
                WHERE date >= '{start_date}'
                ORDER BY date ASC
            """
            if end_date:
                query = f"""
                    SELECT date, close
                    FROM vix
                    WHERE date >= '{start_date}' AND date <= '{end_date}'
                    ORDER BY date ASC
                """
            df = pd.read_sql_query(query, conn)
        else:
            # Fall back to prices table
            df = get_prices('^VIX', start_date, end_date)
            if df.empty:
                df = get_prices('VIX', start_date, end_date)
            return df[['close']] if not df.empty else df

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    return df


def get_returns(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.Series:
    """
    Get daily log returns for a symbol.

    Args:
        symbol: Ticker symbol
        start_date: Start date as 'YYYY-MM-DD'
        end_date: End date as 'YYYY-MM-DD'

    Returns:
        Series of daily returns, indexed by date
    """
    df = get_prices(symbol, start_date, end_date)
    if df.empty:
        return pd.Series(dtype=float)

    returns = df['close'].pct_change().dropna()
    return returns


def get_sector_etfs(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Get prices for all sector ETFs in the database.

    Returns:
        Dict mapping ETF symbol -> DataFrame
    """
    return get_multiple(SECTOR_ETFS, start_date, end_date)


def get_sector_close_matrix(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Get closing prices for all sector ETFs as a matrix.
    Useful for sector rotation backtesting.

    Returns:
        DataFrame with dates as index, sector ETF symbols as columns
    """
    return get_close_matrix(SECTOR_ETFS, start_date, end_date)


def available_symbols() -> pd.DataFrame:
    """
    List all available stock/ETF symbols with their date ranges and record counts.

    Returns:
        DataFrame with columns: symbol, first_date, last_date, records
    """
    query = """
        SELECT
            symbol,
            MIN(date) AS first_date,
            MAX(date) AS last_date,
            COUNT(*) AS records
        FROM prices
        GROUP BY symbol
        ORDER BY symbol ASC
    """
    with _get_connection() as conn:
        df = pd.read_sql_query(query, conn)

    return df


def available_economic_series() -> pd.DataFrame:
    """
    List all available FRED economic series in the database.

    Returns:
        DataFrame with columns: series_id, first_date, last_date, records
    """
    with _get_connection() as conn:
        cursor = conn.cursor()
        tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        table = 'fred_data' if 'fred_data' in tables else 'economic_data' if 'economic_data' in tables else None
        if table is None:
            return pd.DataFrame()

        query = f"""
            SELECT
                series_id,
                MIN(date) AS first_date,
                MAX(date) AS last_date,
                COUNT(*) AS records
            FROM {table}
            GROUP BY series_id
            ORDER BY series_id ASC
        """
        df = pd.read_sql_query(query, conn)

    return df


def momentum_score(symbol: str, lookback_months: int = 12, end_date: Optional[str] = None) -> Optional[float]:
    """
    Calculate price momentum score (simple return over lookback period).

    Args:
        symbol: Ticker symbol
        lookback_months: Lookback period in months (default: 12)
        end_date: End date (default: today)

    Returns:
        Momentum score (percentage return) or None if insufficient data
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_dt = end_dt - timedelta(days=lookback_months * 30)
    start_date = start_dt.strftime('%Y-%m-%d')

    df = get_prices(symbol, start_date, end_date)
    if len(df) < 10:
        return None

    return (df['close'].iloc[-1] / df['close'].iloc[0]) - 1


def relative_strength_rank(symbols: List[str], lookback_months: int = 6, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Rank symbols by momentum (relative strength).
    Used for momentum and sector rotation strategies.

    Args:
        symbols: List of symbols to rank
        lookback_months: Lookback period in months
        end_date: End date (default: today)

    Returns:
        DataFrame with columns: symbol, momentum, rank
        Sorted by momentum descending (rank 1 = strongest)
    """
    scores = []
    for symbol in symbols:
        score = momentum_score(symbol, lookback_months, end_date)
        if score is not None:
            scores.append({'symbol': symbol, 'momentum': score})

    if not scores:
        return pd.DataFrame()

    df = pd.DataFrame(scores)
    df = df.sort_values('momentum', ascending=False).reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)
    return df


# ─── CLI / debug ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Pinch Stock Trading — Data Loader ===\n")

    print("Available symbols:")
    syms = available_symbols()
    print(syms.to_string(index=False))

    print("\nEconomic series:")
    econ = available_economic_series()
    if not econ.empty:
        print(econ.to_string(index=False))
    else:
        print("  (none found)")

    print("\nSector ETF relative strength (6M):")
    rs = relative_strength_rank(SECTOR_ETFS, lookback_months=6)
    if not rs.empty:
        print(rs.to_string(index=False))
    else:
        print("  (no data)")
