"""BEA data ingestion pipeline -- fetch NIPA tables and upsert into the database."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from backend.database import SessionLocal
from backend.models.timeseries import DataSeries, DataSource, Observation
from backend.services.bea_client import get_table

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_series.json"


def _load_bea_tables() -> list[dict[str, str]]:
    """Read the BEA table configurations from the seed file."""
    with open(SEED_PATH) as f:
        seed = json.load(f)
    return seed.get("bea", [])


def _parse_time_period(time_period: str) -> datetime | None:
    """Convert a BEA time period string (e.g. '2023Q1', '2023M06') to a date.

    Returns:
        A date object, or None if the format is unrecognized.
    """
    tp = time_period.strip()
    try:
        if "Q" in tp:
            year_str, q_str = tp.split("Q")
            year = int(year_str)
            quarter = int(q_str)
            month = (quarter - 1) * 3 + 1
            return datetime(year, month, 1).date()
        elif "M" in tp:
            year_str, m_str = tp.split("M")
            year = int(year_str)
            month = int(m_str)
            return datetime(year, month, 1).date()
        else:
            # Annual: just the year
            year = int(tp)
            return datetime(year, 1, 1).date()
    except (ValueError, IndexError):
        logger.warning("Could not parse BEA time period: %s", tp)
        return None


def ingest_bea() -> int:
    """Fetch all configured BEA tables and upsert observations into the database.

    Returns:
        Total number of observations upserted.
    """
    tables = _load_bea_tables()
    if not tables:
        logger.warning("No BEA tables configured in seed file")
        return 0

    total_upserted = 0
    db = SessionLocal()

    try:
        # Ensure the BEA data source exists
        source = db.query(DataSource).filter(DataSource.name == "BEA").first()
        if source is None:
            source = DataSource(
                name="BEA",
                base_url="https://apps.bea.gov/api/data",
                api_key_env_var="BEA_API_KEY",
            )
            db.add(source)
            db.flush()

        for table_cfg in tables:
            table_name: str = table_cfg["table"]
            frequency: str = table_cfg.get("frequency", "Q")
            series_code = f"{table_name}_{frequency}"

            logger.info("Fetching BEA table: %s (freq=%s)", table_name, frequency)

            # Ensure DataSeries record exists
            ds = (
                db.query(DataSeries)
                .filter(DataSeries.source_id == source.id, DataSeries.series_code == series_code)
                .first()
            )
            if ds is None:
                freq_label = {"Q": "quarterly", "M": "monthly", "A": "annual"}.get(
                    frequency, frequency
                )
                ds = DataSeries(
                    source_id=source.id,
                    series_code=series_code,
                    display_name=f"BEA {table_name}",
                    frequency=freq_label,
                )
                db.add(ds)
                db.flush()

            try:
                df = get_table(table_name, frequency=frequency)
            except Exception:
                logger.exception("Failed to fetch BEA table %s", table_name)
                continue

            if df.empty:
                logger.info("No data returned for BEA table %s", table_name)
                continue

            count = 0
            for _, row in df.iterrows():
                obs_date = _parse_time_period(str(row["time_period"]))
                if obs_date is None:
                    continue

                stmt = (
                    sqlite_upsert(Observation)
                    .values(
                        series_id=ds.id,
                        date=obs_date,
                        value=float(row["value"]),
                    )
                    .on_conflict_do_update(
                        index_elements=["series_id", "date"],
                        set_={"value": float(row["value"])},
                    )
                )
                db.execute(stmt)
                count += 1

            ds.last_updated = datetime.utcnow()
            total_upserted += count
            logger.info("Upserted %d observations for BEA/%s", count, series_code)

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("BEA ingestion failed")
        raise
    finally:
        db.close()

    logger.info("BEA ingestion complete: %d total observations", total_upserted)
    return total_upserted
