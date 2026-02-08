"""Utility for exporting DataFrames to Excel files."""

from pathlib import Path

import pandas as pd


def export_dataframe_to_excel(
    df: pd.DataFrame,
    filepath: str | Path,
    sheet_name: str = "Sheet1",
) -> Path:
    """Write a DataFrame to an Excel file.

    If the file already exists, the sheet will be added (or replaced) without
    removing other sheets.

    Args:
        df: DataFrame to export.
        filepath: Destination file path (.xlsx).
        sheet_name: Name of the worksheet.

    Returns:
        Path to the written Excel file.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if filepath.exists():
        with pd.ExcelWriter(
            str(filepath),
            engine="openpyxl",
            mode="a",
            if_sheet_exists="replace",
        ) as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=True)
    else:
        with pd.ExcelWriter(str(filepath), engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=True)

    return filepath
