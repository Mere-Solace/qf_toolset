"""FRED data ingestion pipeline -- fetch series and upsert into the database.

Supports incremental fetching: CSV files in ``data/raw/fred/`` act as the
source of truth for what has already been downloaded.  Only observations newer
than the last CSV date are requested from the FRED API.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from backend.database import SessionLocal
from backend.models.timeseries import DataSeries, DataSource, Observation
from backend.pipeline.csv_store import append_rows, get_last_date
from backend.services.fred_client import get_series

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_series.json"


def _load_fred_series() -> list[dict]:
    """Read the FRED series list from the seed file.

    Supports both the legacy flat list format and the new categorised format.
    Returns a list of dicts with keys: id, name, unit, frequency, category.
    """
    with open(SEED_PATH) as f:
        seed = json.load(f)

    raw = seed.get("fred", [])

    # Legacy format: flat list of series ID strings
    if isinstance(raw, list):
        return [{"id": sid, "name": sid, "unit": "", "frequency": "daily", "category": ""} for sid in raw]

    # New format: dict of category -> list of series objects
    series_list: list[dict] = []
    for _category, items in raw.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    series_list.append(item)
    return series_list


def ingest_fred(full_sync: bool = False) -> int:
    """Fetch all configured FRED series and upsert observations into the database.

    When *full_sync* is ``True`` every series is fetched regardless of what is
    already stored locally.  Otherwise an incremental strategy is used: the CSV
    files under ``data/raw/fred/`` record the last-fetched date and only newer
    observations are requested from the FRED API.

    Returns:
        Total number of observations upserted.
    """
    series_defs = _load_fred_series()
    if not series_defs:
        logger.warning("No FRED series configured in seed file")
        return 0

    total_upserted = 0
    db = SessionLocal()

    try:
        # Ensure the FRED data source exists
        source = db.query(DataSource).filter(DataSource.name == "FRED").first()
        if source is None:
            source = DataSource(
                name="FRED",
                base_url="https://api.stlouisfed.org/fred",
                api_key_env_var="FRED_API_KEY",
            )
            db.add(source)
            db.flush()

        for sdef in series_defs:
            sid = sdef["id"]

            # Ensure the DataSeries record exists, updating metadata if needed
            ds = (
                db.query(DataSeries)
                .filter(DataSeries.source_id == source.id, DataSeries.series_code == sid)
                .first()
            )
            if ds is None:
                ds = DataSeries(
                    source_id=source.id,
                    series_code=sid,
                    display_name=sdef.get("name", sid),
                    unit=sdef.get("unit", ""),
                    frequency=sdef.get("frequency", "daily"),
                )
                db.add(ds)
                db.flush()
            else:
                # Update metadata from seed if display_name is just the code
                if ds.display_name == ds.series_code and sdef.get("name"):
                    ds.display_name = sdef["name"]
                if not ds.unit and sdef.get("unit"):
                    ds.unit = sdef["unit"]
                if ds.frequency == "daily" and sdef.get("frequency"):
                    ds.frequency = sdef["frequency"]

            # ── Incremental fetch via CSV store ──────────────────────────
            start_date = None
            if not full_sync:
                last = get_last_date(sid)
                if last is not None:
                    start_date = last + timedelta(days=1)

            logger.info(
                "Fetching FRED series: %s (from %s)",
                sid,
                start_date or "full history",
            )

            try:
                df = get_series(sid, start_date=start_date)
            except Exception:
                logger.exception("Failed to fetch FRED series %s", sid)
                continue

            if df.empty:
                logger.info("No new data for FRED series %s", sid)
                continue

            # Persist to CSV
            appended = append_rows(sid, df)
            logger.info("Appended %d rows to CSV for %s", appended, sid)

            # Upsert observations to DB
            for _, row in df.iterrows():
                stmt = (
                    sqlite_upsert(Observation)
                    .values(
                        series_id=ds.id,
                        date=row["date"],
                        value=float(row["value"]),
                    )
                    .on_conflict_do_update(
                        index_elements=["series_id", "date"],
                        set_={"value": float(row["value"])},
                    )
                )
                db.execute(stmt)

            ds.last_updated = datetime.utcnow()
            total_upserted += len(df)
            logger.info("Upserted %d observations for FRED/%s", len(df), sid)

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("FRED ingestion failed")
        raise
    finally:
        db.close()

    logger.info("FRED ingestion complete: %d total observations", total_upserted)
    return total_upserted
