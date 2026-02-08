"""Bureau of Economic Analysis (BEA) REST API client."""

from typing import Any

import pandas as pd
import requests

from backend.config import settings

BEA_API_URL = "https://apps.bea.gov/api/data"


def get_table(
    table_name: str,
    frequency: str = "Q",
    year: str = "ALL",
) -> pd.DataFrame:
    """Fetch a NIPA table from the BEA API.

    Args:
        table_name: BEA table identifier (e.g. 'T10101' for GDP).
        frequency: Data frequency -- 'Q' (quarterly), 'M' (monthly), or 'A' (annual).
        year: Year(s) to retrieve. Use 'ALL' for all available years, or a
              comma-separated string like '2020,2021,2022'.

    Returns:
        DataFrame with columns: line_number, line_description, time_period, value.

    Raises:
        ValueError: If the BEA API key is not configured.
        RuntimeError: If the API returns an error.
    """
    if not settings.bea_api_key:
        raise ValueError(
            "BEA API key is not configured. Set BEA_API_KEY in your .env file."
        )

    params: dict[str, str] = {
        "UserID": settings.bea_api_key,
        "method": "GetData",
        "DataSetName": "NIPA",
        "TableName": table_name,
        "Frequency": frequency,
        "Year": year,
        "ResultFormat": "JSON",
    }

    response = requests.get(BEA_API_URL, params=params, timeout=30)
    response.raise_for_status()

    result = response.json()

    # Navigate the nested BEA response structure
    beaapi = result.get("BEAAPI", {})
    error = beaapi.get("Error")
    if error:
        raise RuntimeError(f"BEA API error: {error}")

    results_block = beaapi.get("Results", {})
    data_list: list[dict[str, Any]] = results_block.get("Data", [])

    if not data_list:
        return pd.DataFrame(columns=["line_number", "line_description", "time_period", "value"])

    rows: list[dict[str, Any]] = []
    for item in data_list:
        value_str = item.get("DataValue", "").replace(",", "")
        try:
            value = float(value_str)
        except (ValueError, TypeError):
            continue

        rows.append(
            {
                "line_number": item.get("LineNumber", ""),
                "line_description": item.get("LineDescription", ""),
                "time_period": item.get("TimePeriod", ""),
                "value": value,
            }
        )

    df = pd.DataFrame(rows)
    df.sort_values(["line_number", "time_period"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df
