"""Bureau of Labor Statistics (BLS) REST API v2 client."""

import json
from typing import Any

import pandas as pd
import requests

from backend.config import settings

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def get_series(
    series_ids: list[str],
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """Fetch one or more BLS time series.

    Args:
        series_ids: List of BLS series identifiers (e.g. ['CES0000000001']).
        start_year: First year of data to retrieve.
        end_year: Last year of data to retrieve.

    Returns:
        DataFrame with columns: series_id, date, value.

    Raises:
        RuntimeError: If the BLS API returns an error status.
    """
    payload: dict[str, Any] = {
        "seriesid": series_ids,
        "registrationkey": settings.bls_api_key,
    }
    if start_year is not None:
        payload["startyear"] = str(start_year)
    if end_year is not None:
        payload["endyear"] = str(end_year)

    headers = {"Content-type": "application/json"}
    response = requests.post(
        BLS_API_URL,
        data=json.dumps(payload),
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()

    if result.get("status") != "REQUEST_SUCCEEDED":
        msg = result.get("message", ["Unknown error"])
        raise RuntimeError(f"BLS API error: {msg}")

    rows: list[dict[str, Any]] = []
    for series_block in result.get("Results", {}).get("series", []):
        sid = series_block["seriesID"]
        for obs in series_block.get("data", []):
            year = int(obs["year"])
            period = obs["period"]

            # Monthly data: period is 'M01' through 'M12'
            if period.startswith("M") and period != "M13":
                month = int(period[1:])
                obs_date = pd.Timestamp(year=year, month=month, day=1).date()
            else:
                # Annual or special periods -- use Jan 1 of that year
                obs_date = pd.Timestamp(year=year, month=1, day=1).date()

            value_str = obs.get("value", "")
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                continue

            rows.append({"series_id": sid, "date": obs_date, "value": value})

    df = pd.DataFrame(rows)
    if not df.empty:
        df.sort_values(["series_id", "date"], inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df
