"""CSV storage layer for time-series data.

Provides read/write/diff utilities for per-series CSV files stored under
``data/raw/{source}/{series_code}.csv``.  Each CSV contains two columns:
``date`` (YYYY-MM-DD) and ``value`` (float), sorted by date ascending.
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


def _csv_path(series_code: str, data_dir: Path | None = None, source: str = "fred") -> Path:
    """Return the path to the CSV file for the given series."""
    base = data_dir or DEFAULT_DATA_DIR
    return base / "raw" / source / f"{series_code}.csv"


def load_series_csv(
    series_code: str,
    data_dir: Path | None = None,
    source: str = "fred",
) -> pd.DataFrame:
    """Read the CSV for *series_code* and return a DataFrame.

    Returns an empty DataFrame with ``date`` and ``value`` columns if the file
    does not exist.
    """
    path = _csv_path(series_code, data_dir, source)
    if not path.exists():
        return pd.DataFrame(columns=["date", "value"])
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = df["date"].dt.date
    return df


def save_series_csv(
    series_code: str,
    df: pd.DataFrame,
    data_dir: Path | None = None,
    source: str = "fred",
) -> Path:
    """Write *df* (with ``date`` and ``value`` columns) to CSV, sorted by date.

    Creates parent directories as needed.  Returns the file path.
    """
    path = _csv_path(series_code, data_dir, source)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df[["date", "value"]].copy()
    out = out.sort_values("date").reset_index(drop=True)
    out.to_csv(path, index=False)
    return path


def get_last_date(
    series_code: str,
    data_dir: Path | None = None,
    source: str = "fred",
) -> date | None:
    """Return the latest observation date in the CSV, or ``None`` if no file."""
    df = load_series_csv(series_code, data_dir, source)
    if df.empty:
        return None
    return max(df["date"])


def append_rows(
    series_code: str,
    new_df: pd.DataFrame,
    data_dir: Path | None = None,
    source: str = "fred",
) -> int:
    """Append only *new* rows to the CSV (by date), keeping it sorted and
    duplicate-free.

    Returns the number of rows actually appended.
    """
    existing = load_series_csv(series_code, data_dir, source)
    if existing.empty:
        save_series_csv(series_code, new_df, data_dir, source)
        return len(new_df)

    existing_dates = set(existing["date"])
    novel = new_df[~new_df["date"].isin(existing_dates)]
    if novel.empty:
        return 0

    combined = pd.concat([existing, novel[["date", "value"]]], ignore_index=True)
    save_series_csv(series_code, combined, data_dir, source)
    return len(novel)
