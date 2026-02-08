"""Yahoo Finance wrapper for market data retrieval."""

from typing import Any

import pandas as pd
import yfinance as yf


def get_quote(ticker: str) -> dict[str, Any]:
    """Fetch current price information for a ticker.

    Args:
        ticker: Stock/ETF/index ticker symbol (e.g. 'SPY', '^VIX').

    Returns:
        Dictionary with current price fields including regularMarketPrice,
        regularMarketChange, regularMarketVolume, and other fast-info fields.
    """
    t = yf.Ticker(ticker)
    info = t.fast_info
    return {
        "ticker": ticker,
        "last_price": info.get("lastPrice"),
        "previous_close": info.get("previousClose"),
        "open": info.get("open"),
        "day_high": info.get("dayHigh"),
        "day_low": info.get("dayLow"),
        "volume": info.get("lastVolume"),
        "market_cap": info.get("marketCap"),
        "fifty_day_average": info.get("fiftyDayAverage"),
        "two_hundred_day_average": info.get("twoHundredDayAverage"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
    }


def get_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch historical OHLCV data for a ticker.

    Args:
        ticker: Stock/ETF/index ticker symbol.
        period: Lookback period (e.g. '1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', 'max').
        interval: Bar size (e.g. '1m', '5m', '15m', '1h', '1d', '1wk', '1mo').

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume.
    """
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def get_financials(ticker: str) -> dict[str, dict[str, pd.DataFrame]]:
    """Fetch financial statements for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Nested dict with keys 'quarterly' and 'annual', each containing
        'balance_sheet', 'income_stmt', and 'cash_flow' DataFrames.
    """
    t = yf.Ticker(ticker)
    return {
        "quarterly": {
            "balance_sheet": t.quarterly_balance_sheet,
            "income_stmt": t.quarterly_income_stmt,
            "cash_flow": t.quarterly_cashflow,
        },
        "annual": {
            "balance_sheet": t.balance_sheet,
            "income_stmt": t.income_stmt,
            "cash_flow": t.cashflow,
        },
    }
