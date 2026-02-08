"""BLS data ingestion pipeline -- fetch series and upsert into the database."""

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from backend.database import SessionLocal
from backend.models.timeseries import DataSeries, DataSource, Observation
from backend.services.bls_client import get_series

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_series.json"


def _load_bls_series_ids() -> list[str]:
    """Read the BLS series list from the seed file."""
    with open(SEED_PATH) as f:
        seed = json.load(f)
    return seed.get("bls", [])


def ingest_bls(
    start_year: int | None = None,
    end_year: int | None = None,
) -> int:
    """Fetch all configured BLS series and upsert observations into the database.

    Args:
        start_year: First year to request. Defaults to current year minus 10.
        end_year: Last year to request. Defaults to current year.

    Returns:
        Total number of observations upserted.
    """
    series_ids = _load_bls_series_ids()
    if not series_ids:
        logger.warning("No BLS series configured in seed file")
        return 0

    now = datetime.utcnow()
    if end_year is None:
        end_year = now.year
    if start_year is None:
        start_year = end_year - 10

    total_upserted = 0
    db = SessionLocal()

    try:
        # Ensure the BLS data source exists
        source = db.query(DataSource).filter(DataSource.name == "BLS").first()
        if source is None:
            source = DataSource(
                name="BLS",
                base_url="https://api.bls.gov/publicAPI/v2",
                api_key_env_var="BLS_API_KEY",
            )
            db.add(source)
            db.flush()

        # Ensure DataSeries records exist for each BLS series
        series_map: dict[str, DataSeries] = {}
        for sid in series_ids:
            ds = (
                db.query(DataSeries)
                .filter(DataSeries.source_id == source.id, DataSeries.series_code == sid)
                .first()
            )
            if ds is None:
                ds = DataSeries(
                    source_id=source.id,
                    series_code=sid,
                    display_name=sid,
                    frequency="monthly",
                )
                db.add(ds)
                db.flush()
            series_map[sid] = ds

        # BLS allows up to 50 series per request
        logger.info("Fetching BLS series: %s (%d-%d)", series_ids, start_year, end_year)

        try:
            df = get_series(series_ids, start_year=start_year, end_year=end_year)
        except Exception:
            logger.exception("Failed to fetch BLS series")
            db.rollback()
            return 0

        if df.empty:
            logger.info("No data returned from BLS")
            return 0

        for _, row in df.iterrows():
            sid = row["series_id"]
            ds = series_map.get(sid)
            if ds is None:
                continue

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
            total_upserted += 1

        # Update last_updated for all series
        for ds in series_map.values():
            ds.last_updated = datetime.utcnow()

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("BLS ingestion failed")
        raise
    finally:
        db.close()

    logger.info("BLS ingestion complete: %d total observations", total_upserted)
    return total_upserted
