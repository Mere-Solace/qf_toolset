"""Migrate existing CSV files from data/raw/ into the SQLite database.

Reads all CSV files, downsamples to monthly frequency (first observation of
each month), and inserts the data into the observations table with appropriate
series references.

Usage:
    python -m scripts.migrate_data
"""

import logging
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import Base, SessionLocal, engine
from backend.models.timeseries import DataSeries, DataSource, Observation

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"


def _detect_date_column(df: pd.DataFrame) -> str | None:
    """Heuristically find the date column in a DataFrame."""
    for col in df.columns:
        col_lower = col.lower()
        if "date" in col_lower or "time" in col_lower or "period" in col_lower:
            return col
    # Try the first column
    if len(df.columns) > 0:
        try:
            pd.to_datetime(df.iloc[:, 0], errors="raise")
            return df.columns[0]
        except Exception:
            pass
    return None


def _downsample_to_monthly(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Downsample a DataFrame to monthly by taking the first observation of each month.

    Args:
        df: Input DataFrame with a parseable date column.
        date_col: Name of the date column.

    Returns:
        Monthly DataFrame with date as index.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df.dropna(subset=[date_col], inplace=True)
    df.sort_values(date_col, inplace=True)

    # Create a year-month grouping key and take the first row of each group
    df["_ym"] = df[date_col].dt.to_period("M")
    monthly = df.groupby("_ym").first().reset_index(drop=True)
    monthly.drop(columns=["_ym"], errors="ignore", inplace=True)
    return monthly


def migrate() -> int:
    """Run the full CSV-to-SQLite migration.

    Returns:
        Total number of observations inserted.
    """
    if not RAW_DIR.exists():
        logger.error("Raw data directory does not exist: %s", RAW_DIR)
        return 0

    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        logger.warning("No CSV files found in %s", RAW_DIR)
        return 0

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    total = 0

    try:
        # Ensure a generic CSV data source exists
        source = db.query(DataSource).filter(DataSource.name == "CSV_IMPORT").first()
        if source is None:
            source = DataSource(
                name="CSV_IMPORT",
                base_url="",
                api_key_env_var="",
            )
            db.add(source)
            db.flush()

        for csv_file in csv_files:
            logger.info("Processing: %s", csv_file.name)

            try:
                df = pd.read_csv(csv_file)
            except Exception:
                logger.exception("Failed to read %s", csv_file.name)
                continue

            if df.empty:
                logger.info("Skipping empty file: %s", csv_file.name)
                continue

            date_col = _detect_date_column(df)
            if date_col is None:
                logger.warning("No date column found in %s -- skipping", csv_file.name)
                continue

            # Downsample to monthly
            df = _downsample_to_monthly(df, date_col)

            # Each non-date numeric column becomes a separate series
            numeric_cols = [c for c in df.select_dtypes(include="number").columns if c != date_col]

            for col_name in numeric_cols:
                series_code = f"{csv_file.stem}__{col_name}"

                ds = (
                    db.query(DataSeries)
                    .filter(
                        DataSeries.source_id == source.id,
                        DataSeries.series_code == series_code,
                    )
                    .first()
                )
                if ds is None:
                    ds = DataSeries(
                        source_id=source.id,
                        series_code=series_code,
                        display_name=f"{csv_file.stem} - {col_name}",
                        frequency="monthly",
                    )
                    db.add(ds)
                    db.flush()

                count = 0
                for _, row in df.iterrows():
                    obs_date = pd.to_datetime(row[date_col]).date()
                    value = row[col_name]
                    if pd.isna(value):
                        continue

                    stmt = (
                        sqlite_upsert(Observation)
                        .values(
                            series_id=ds.id,
                            date=obs_date,
                            value=float(value),
                        )
                        .on_conflict_do_update(
                            index_elements=["series_id", "date"],
                            set_={"value": float(value)},
                        )
                    )
                    db.execute(stmt)
                    count += 1

                total += count
                logger.info("  Inserted %d observations for series '%s'", count, series_code)

        db.commit()
        logger.info("Migration complete: %d total observations", total)

    except Exception:
        db.rollback()
        logger.exception("Migration failed")
        raise
    finally:
        db.close()

    return total


if __name__ == "__main__":
    migrate()
