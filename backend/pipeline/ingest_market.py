"""Yahoo Finance market data ingestion pipeline."""

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from backend.database import SessionLocal
from backend.models.timeseries import DataSeries, DataSource, Observation
from backend.services.market_data import get_history

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_series.json"


def _load_yahoo_tickers() -> list[str]:
    """Read the Yahoo Finance ticker list from the seed file."""
    with open(SEED_PATH) as f:
        seed = json.load(f)
    return seed.get("yahoo", [])


def ingest_market(period: str = "5d", interval: str = "1d") -> int:
    """Fetch recent market data for all configured tickers and upsert into the database.

    Args:
        period: Lookback period for yfinance (default '5d' for the scheduler's
                frequent runs; use '5y' or 'max' for backfills).
        interval: Bar interval (default '1d').

    Returns:
        Total number of observations upserted.
    """
    tickers = _load_yahoo_tickers()
    if not tickers:
        logger.warning("No Yahoo tickers configured in seed file")
        return 0

    total_upserted = 0
    db = SessionLocal()

    try:
        # Ensure the YAHOO data source exists
        source = db.query(DataSource).filter(DataSource.name == "YAHOO").first()
        if source is None:
            source = DataSource(
                name="YAHOO",
                base_url="https://finance.yahoo.com",
                api_key_env_var="",
            )
            db.add(source)
            db.flush()

        for ticker in tickers:
            logger.info("Fetching Yahoo data: %s (period=%s, interval=%s)", ticker, period, interval)

            # Ensure DataSeries record exists
            ds = (
                db.query(DataSeries)
                .filter(DataSeries.source_id == source.id, DataSeries.series_code == ticker)
                .first()
            )
            if ds is None:
                ds = DataSeries(
                    source_id=source.id,
                    series_code=ticker,
                    display_name=ticker,
                    frequency="daily",
                    unit="USD",
                )
                db.add(ds)
                db.flush()

            try:
                df = get_history(ticker, period=period, interval=interval)
            except Exception:
                logger.exception("Failed to fetch Yahoo data for %s", ticker)
                continue

            if df.empty:
                logger.info("No data returned for Yahoo/%s", ticker)
                continue

            count = 0
            for idx, row in df.iterrows():
                obs_date = idx.date() if hasattr(idx, "date") else idx

                # Store the Close price as the observation value
                stmt = (
                    sqlite_upsert(Observation)
                    .values(
                        series_id=ds.id,
                        date=obs_date,
                        value=float(row["Close"]),
                    )
                    .on_conflict_do_update(
                        index_elements=["series_id", "date"],
                        set_={"value": float(row["Close"])},
                    )
                )
                db.execute(stmt)
                count += 1

            ds.last_updated = datetime.utcnow()
            total_upserted += count
            logger.info("Upserted %d observations for Yahoo/%s", count, ticker)

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Yahoo market ingestion failed")
        raise
    finally:
        db.close()

    logger.info("Yahoo ingestion complete: %d total observations", total_upserted)
    return total_upserted
