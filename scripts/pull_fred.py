"""Fetch all configured FRED series to CSV files.

Usage:
    python scripts/pull_fred.py           # Incremental (only new data)
    python scripts/pull_fred.py --full    # Full re-sync from scratch

After fetching, automatically rebuilds the master Excel workbook.
"""

import argparse
import json
import logging
import sys
from datetime import timedelta
from pathlib import Path

# Allow running from project root: `python scripts/pull_fred.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.csv_store import append_rows, get_last_date, save_series_csv
from lib.fred_client import get_series

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

SERIES_CONFIG = PROJECT_ROOT / "config" / "series.json"


def load_fred_series() -> list[dict]:
    """Read the FRED series list from config/series.json."""
    with open(SERIES_CONFIG) as f:
        seed = json.load(f)

    raw = seed.get("fred", {})
    series_list: list[dict] = []
    for _category, items in raw.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    series_list.append(item)
    return series_list


def pull_fred(full_sync: bool = False) -> int:
    """Fetch all configured FRED series, saving to CSV.

    Returns total number of new rows appended.
    """
    series_defs = load_fred_series()
    if not series_defs:
        log.warning("No FRED series configured in %s", SERIES_CONFIG)
        return 0

    total_new = 0

    for i, sdef in enumerate(series_defs, 1):
        sid = sdef["id"]
        name = sdef.get("name", sid)

        start_date = None
        if not full_sync:
            last = get_last_date(sid)
            if last is not None:
                start_date = last + timedelta(days=1)

        mode = "full history" if start_date is None else f"from {start_date}"
        log.info("[%d/%d] %s (%s) — %s", i, len(series_defs), sid, name, mode)

        try:
            df = get_series(sid, start_date=start_date)
        except Exception:
            log.exception("  FAILED to fetch %s", sid)
            continue

        if df.empty:
            log.info("  No new data")
            continue

        if full_sync:
            save_series_csv(sid, df)
            appended = len(df)
        else:
            appended = append_rows(sid, df)

        total_new += appended
        log.info("  +%d rows", appended)

    log.info("Done — %d new rows across %d series", total_new, len(series_defs))
    return total_new


def main():
    parser = argparse.ArgumentParser(description="Pull FRED data to CSV files")
    parser.add_argument("--full", action="store_true", help="Full re-sync (ignore existing data)")
    args = parser.parse_args()

    pull_fred(full_sync=args.full)

    # Rebuild the master Excel workbook
    log.info("Rebuilding master workbook...")
    from scripts.build_master_sheet import build_master_sheet

    build_master_sheet()
    log.info("Master workbook updated.")


if __name__ == "__main__":
    main()
