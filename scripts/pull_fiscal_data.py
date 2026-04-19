"""Pull US Treasury Fiscal Data API → Excel workbook.

Fetches the last 7 years of data from 11 datasets and writes each to a
separate sheet in output/fiscal_data.xlsx.

Usage:
    python scripts/pull_fiscal_data.py

Datasets pulled:
  - avg_interest_rates      Treasury average interest rates by security
  - debt_outstanding        Total federal debt outstanding (monthly)
  - schedules_fed_debt      Federal debt by holder type and security class
  - balance_sheets          Federal govt balance sheet line items
  - statement_net_cost      Agency-level gross cost / net cost
  - mts_table_1             Monthly receipts, outlays, deficit/surplus summary
  - mts_table_3             Receipts and outlays by detailed category
  - rates_of_exchange       USD exchange rates for ~170 currencies (quarterly)
  - slgs_statistics         State & Local Govt Series outstanding
  - title_xii               Unemployment fund advances by state
  - savings_bonds_pcs       Savings bonds outstanding by series/type
"""

import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.excel import NotebookWorkbook

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
CUTOFF = (date.today() - timedelta(days=7 * 365)).isoformat()  # ~7 years ago
PAGE_SIZE = 10_000

# ---------------------------------------------------------------------------
# Dataset definitions
# Each entry: (sheet_name, endpoint, fields, date_field, extra_filters)
# date_field=None means no date filter (small/static tables)
# ---------------------------------------------------------------------------
DATASETS = [
    (
        "Avg Interest Rates",
        "v2/accounting/od/avg_interest_rates",
        "record_date,security_type_desc,security_desc,avg_interest_rate_amt",
        "record_date",
        None,
    ),
    (
        "Debt Outstanding",
        "v2/accounting/od/debt_outstanding",
        "record_date,debt_outstanding_amt",
        "record_date",
        None,
    ),
    (
        "Federal Debt Schedule",
        "v1/accounting/od/schedules_fed_debt",
        "record_date,debt_holder_type,security_class1_desc,security_class2_desc,"
        "principal_mil_amt,accrued_int_payable_mil_amt,net_unamortized_mil_amt",
        "record_date",
        None,
    ),
    (
        "Balance Sheet",
        "v2/accounting/od/balance_sheets",
        "record_date,stmt_fiscal_year,account_desc,line_item_desc,position_bil_amt",
        "record_date",
        None,
    ),
    (
        "Agency Net Cost",
        "v2/accounting/od/statement_net_cost",
        "record_date,agency_nm,gross_cost_bil_amt,earned_revenue_bil_amt,net_cost_bil_amt",
        "record_date",
        None,
    ),
    (
        "MTS Summary",
        "v1/accounting/mts/mts_table_1",
        "record_date,classification_desc,current_month_gross_rcpt_amt,"
        "current_month_gross_outly_amt,current_month_dfct_sur_amt",
        "record_date",
        None,
    ),
    (
        "MTS Receipts & Outlays",
        "v1/accounting/mts/mts_table_3",
        "record_date,classification_desc,current_month_rcpt_outly_amt,"
        "current_fytd_rcpt_outly_amt,prior_fytd_rcpt_outly_amt",
        "record_date",
        None,
    ),
    (
        "FX Rates",
        "v1/accounting/od/rates_of_exchange",
        "record_date,country,currency,country_currency_desc,exchange_rate,effective_date",
        "record_date",
        None,
    ),
    (
        "SLGS Statistics",
        "v2/accounting/od/slgs_statistics",
        "record_date,security_type_desc,securities_outstanding_cnt,principal_outstanding_amt",
        "record_date",
        None,
    ),
    (
        "Title XII Advances",
        "v2/accounting/od/title_xii",
        "record_date,state_nm,interest_rate_pct,outstanding_advance_bal,"
        "advance_auth_month_amt,gross_advance_draws_month_amt",
        "record_date",
        None,
    ),
    (
        "Savings Bonds",
        "v1/accounting/od/savings_bonds_pcs",
        "record_date,series_cd,type_cd,total_pcs_cnt",
        "record_date",
        None,
    ),
]


def fetch_all(endpoint: str, params: dict) -> list[dict]:
    """Paginate through all pages and return combined records."""
    url = BASE_URL + endpoint
    all_rows: list[dict] = []
    page = 1
    total_pages = None

    while True:
        paged_params = {**params, "page[number]": page}
        try:
            resp = requests.get(url, params=paged_params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.error("  Request failed: %s", exc)
            break

        payload = resp.json()
        batch = payload.get("data", [])
        all_rows.extend(batch)

        if total_pages is None:
            total_pages = payload.get("meta", {}).get("total-pages", 1)

        if page % 5 == 0:
            log.info("    ... page %d/%d, %d rows so far", page, total_pages, len(all_rows))

        if page >= total_pages:
            break

        page += 1
        time.sleep(0.1)  # be polite

    return all_rows


def build_params(fields: str, date_field: str | None, extra_filters: str | None) -> dict:
    filters = []
    if date_field:
        filters.append(f"{date_field}:gte:{CUTOFF}")
    if extra_filters:
        filters.append(extra_filters)

    params: dict = {
        "fields": fields,
        "sort": f"{date_field}" if date_field else "src_line_nbr",
        "page[size]": PAGE_SIZE,
        "format": "json",
    }
    if filters:
        params["filter"] = ",".join(filters)
    return params


def main() -> None:
    output_path = PROJECT_ROOT / "output" / "fiscal_data.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = NotebookWorkbook(output_path)

    log.info("Cutoff date: %s (7-year window)", CUTOFF)
    log.info("Output: %s", output_path)

    for sheet_name, endpoint, fields, date_field, extra_filters in DATASETS:
        log.info("[%s] fetching %s ...", sheet_name, endpoint)
        params = build_params(fields, date_field, extra_filters)
        rows = fetch_all(endpoint, params)

        if not rows:
            log.warning("  No data returned — skipping sheet")
            continue

        df = pd.DataFrame(rows)

        # Parse dates
        if date_field and date_field in df.columns:
            df[date_field] = pd.to_datetime(df[date_field])

        # Parse numeric columns (everything that isn't a date or text descriptor)
        skip_cols = {date_field, "effective_date", "country", "currency",
                     "country_currency_desc", "security_type_desc", "security_desc",
                     "account_desc", "line_item_desc", "agency_nm", "classification_desc",
                     "debt_holder_type", "security_class1_desc", "security_class2_desc",
                     "state_nm", "series_cd", "type_cd", "stmt_fiscal_year"}
        for col in df.columns:
            if col not in skip_cols:
                converted = pd.to_numeric(df[col], errors="coerce")
                # Only replace if most values parsed (avoid mangling text columns)
                if converted.notna().mean() > 0.5:
                    df[col] = converted

        wb.write(sheet_name, df)
        log.info("  -> %d rows, %d cols written to sheet '%s'", len(df), len(df.columns), sheet_name)

    saved = wb.save()
    log.info("Saved: %s", saved)


if __name__ == "__main__":
    main()
