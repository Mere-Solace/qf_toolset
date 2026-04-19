"""Unified data loading for notebooks.

Wraps FRED and yfinance into a consistent interface:
each loader returns a DataFrame with a DatetimeIndex and a 'value' column
(or multiple named columns for multi-ticker yfinance calls).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_fred(
    series_id: str,
    start: date | str | None = None,
    end: date | str | None = None,
    use_cache: bool = True,
) -> pd.Series:
    """Load a FRED series, checking the local CSV cache first.

    Returns a pandas Series indexed by date with the series ID as the name.
    Falls back to a live API call if the cache is missing or *use_cache* is False.
    """
    cache_path = PROJECT_ROOT / "data" / "raw" / "fred" / f"{series_id}.csv"

    if use_cache and cache_path.exists():
        df = pd.read_csv(cache_path, parse_dates=["date"], index_col="date")
        s = df["value"].rename(series_id)
        if start:
            s = s[s.index >= pd.Timestamp(start)]
        if end:
            s = s[s.index <= pd.Timestamp(end)]
        return s

    from tools.fred import get_series as _fred_get
    df = _fred_get(series_id, start_date=start, end_date=end)
    s = df.set_index("date")["value"]
    s.index = pd.to_datetime(s.index)
    return s.rename(series_id)


def load_yfinance(
    tickers: str | list[str],
    start: date | str | None = None,
    end: date | str | None = None,
    field: str = "Close",
) -> pd.DataFrame:
    """Download price data from yfinance.

    Returns a DataFrame with a DatetimeIndex.  Single ticker returns one column
    named after the ticker; multiple tickers return one column each.
    """
    import yfinance as yf

    if isinstance(tickers, str):
        tickers = [tickers]

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)

    if len(tickers) == 1:
        df = raw[[field]].rename(columns={field: tickers[0]})
    else:
        df = raw[field] if field in raw.columns.get_level_values(0) else raw

    df.index = pd.to_datetime(df.index)
    return df


def load_master(
    sheet: str,
    series: str,
    rows_start: int = 0,
    start: date | str | None = None,
    stop: date | str | None = None,
) -> pd.DataFrame:
    """Read a single series column from the master workbook.

    Parameters
    ----------
    sheet : str
        Sheet name (e.g. "Treasury Rates", "All Data").
    series : str
        Column header to extract.
    rows_start : int
        Skip this many data rows from the top (0 = all rows).
    start : date | str | None
        Earliest date to include (inclusive).
    stop : date | str | None
        Latest date to include (inclusive). Defaults to today.

    Returns a two-column DataFrame with a DatetimeIndex (date) and the
    requested series column.
    """
    from datetime import date as _date
    _stop = pd.Timestamp(stop) if stop is not None else pd.Timestamp(_date.today())

    workbook_path = PROJECT_ROOT / "data" / "master_workbook.xlsx"
    df = pd.read_excel(workbook_path, sheet_name=sheet, index_col=0, header=1)
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"

    if series not in df.columns:
        raise KeyError(f"{series!r} not found in sheet {sheet!r}. Available: {list(df.columns)}")

    result = df[[series]].dropna()
    if rows_start:
        result = result.iloc[rows_start:]
    if start is not None:
        result = result[result.index >= pd.Timestamp(start)]
    result = result[result.index <= _stop]
    return result


def align(*series: pd.Series, method: str = "ffill") -> pd.DataFrame:
    """Outer-join multiple Series on date and forward-fill gaps.

    Useful for aligning series with different frequencies before modeling.
    """
    df = pd.concat(series, axis=1)
    df = df.sort_index()
    if method:
        df = df.fillna(method=method) if method == "bfill" else df.ffill()
    return df
