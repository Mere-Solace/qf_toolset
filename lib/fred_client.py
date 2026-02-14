"""FRED (Federal Reserve Economic Data) API client."""

import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def _get_client() -> Fred:
    """Create a fredapi client using the FRED_API_KEY env var."""
    
    key = os.getenv("FRED_API_KEY")

    if not key:
        raise ValueError(
            "FRED API key is not configured. Set FRED_API_KEY in your .env file."
        )
    return Fred(api_key=key)


def get_series(
    series_id: str,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> pd.DataFrame:
    """Fetch a FRED data series as a DataFrame.

    Args:
        series_id: FRED series identifier (e.g. 'DGS10', 'UNRATE').
        start_date: Earliest observation date (inclusive).
        end_date: Latest observation date (inclusive).

    Returns:
        DataFrame with 'date' and 'value' columns.
    """
    client = _get_client()
    data: pd.Series = client.get_series(
        series_id,
        observation_start=start_date,
        observation_end=end_date,
    )
    df = data.reset_index()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df.dropna(subset=["value"], inplace=True)
    return df


def get_series_info(series_id: str) -> dict:
    """Fetch metadata for a FRED series.

    Args:
        series_id: FRED series identifier.

    Returns:
        Dictionary with series metadata (title, frequency, units, etc.).
    """
    client = _get_client()
    info = client.get_series_info(series_id)
    return info.to_dict()
