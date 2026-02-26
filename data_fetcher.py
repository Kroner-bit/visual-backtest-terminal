"""
Yahoo Finance data fetcher module.
Wraps yfinance to download OHLCV data for backtesting.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def fetch_data(
    ticker: str,
    start: str = None,
    end: str = None,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Download OHLCV data from Yahoo Finance.

    Args:
        ticker: Stock/instrument ticker symbol (e.g. 'AAPL', 'EURUSD=X')
        start: Start date string 'YYYY-MM-DD' (optional, overrides period)
        end: End date string 'YYYY-MM-DD' (optional)
        period: Data period if start/end not given (e.g. '1y', '6mo', '5y')
        interval: Bar interval ('1m','5m','15m','1h','1d','1wk','1mo')

    Returns:
        pd.DataFrame with columns: Open, High, Low, Close, Volume
        Index is DatetimeIndex.

    Raises:
        ValueError: If ticker is invalid or no data returned.
    """
    try:
        if start:
            if not end:
                end = datetime.now().strftime("%Y-%m-%d")
            df = yf.download(
                ticker, start=start, end=end, interval=interval, progress=False
            )
        else:
            df = yf.download(ticker, period=period, interval=interval, progress=False)

        if df is None or df.empty:
            raise ValueError(
                f"No data returned for ticker '{ticker}'. "
                "Check the symbol and date range."
            )

        # Flatten multi-level columns if present (yfinance sometimes returns them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Ensure required columns exist
        required = ["Open", "High", "Low", "Close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Keep only what we need
        cols = ["Open", "High", "Low", "Close"]
        if "Volume" in df.columns:
            cols.append("Volume")
        df = df[cols].copy()

        # Drop any rows with NaN
        df.dropna(inplace=True)

        if df.empty:
            raise ValueError(f"All data rows were NaN for ticker '{ticker}'.")

        return df

    except Exception as e:
        if "No data" in str(e) or "Missing" in str(e) or "All data" in str(e):
            raise
        raise ValueError(f"Error fetching data for '{ticker}': {e}")


def get_available_intervals():
    """Return list of available intervals for the UI."""
    return [
        ("1 Minute", "1m"),
        ("5 Minutes", "5m"),
        ("15 Minutes", "15m"),
        ("30 Minutes", "30m"),
        ("1 Hour", "1h"),
        ("1 Day", "1d"),
        ("1 Week", "1wk"),
        ("1 Month", "1mo"),
    ]


def get_available_periods():
    """Return list of available periods for the UI."""
    return [
        ("1 Month", "1mo"),
        ("3 Months", "3mo"),
        ("6 Months", "6mo"),
        ("1 Year", "1y"),
        ("2 Years", "2y"),
        ("5 Years", "5y"),
        ("10 Years", "10y"),
        ("Max", "max"),
    ]
