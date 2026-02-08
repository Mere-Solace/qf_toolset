"""Export Yahoo Finance financial statements to Excel workbooks."""

from pathlib import Path

import yfinance as yf
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows


def export_financials_to_excel(
    ticker: str,
    output_dir: str | Path = "output",
) -> Path:
    """Download all financial statements for a ticker and write them to an Excel file.

    Creates a workbook with six sheets:
        - Annual Balance Sheet
        - Quarterly Balance Sheet
        - Annual Income Statement
        - Quarterly Income Statement
        - Annual Cash Flow
        - Quarterly Cash Flow

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL').
        output_dir: Directory where the Excel file will be saved.

    Returns:
        Path to the created Excel file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    t = yf.Ticker(ticker)

    statements: dict[str, object] = {
        "Annual Balance Sheet": t.balance_sheet,
        "Quarterly Balance Sheet": t.quarterly_balance_sheet,
        "Annual Income Stmt": t.income_stmt,
        "Quarterly Income Stmt": t.quarterly_income_stmt,
        "Annual Cash Flow": t.cashflow,
        "Quarterly Cash Flow": t.quarterly_cashflow,
    }

    wb = Workbook()
    # Remove the default sheet created by openpyxl
    wb.remove(wb.active)

    for sheet_name, df in statements.items():
        ws = wb.create_sheet(title=sheet_name)

        if df is None or df.empty:
            ws.append([f"No data available for {sheet_name}"])
            continue

        # Reset index so the row labels become a column
        df_reset = df.reset_index()
        df_reset.rename(columns={"index": "Item"}, inplace=True)

        # Convert datetime column headers to date strings for readability
        df_reset.columns = [
            col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
            for col in df_reset.columns
        ]

        for row in dataframe_to_rows(df_reset, index=False, header=True):
            ws.append(row)

        # Auto-size the first column
        if ws.column_dimensions:
            ws.column_dimensions["A"].width = 40

    filepath = output_path / f"{ticker}_financials.xlsx"
    wb.save(str(filepath))
    return filepath
