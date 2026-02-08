"""Export all stored series observations to Excel workbooks."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.database import SessionLocal
from backend.models.timeseries import DataSeries, DataSource, Observation
from backend.services.excel_export import export_dataframe_to_excel

logger = logging.getLogger(__name__)

DEFAULT_EXPORT_DIR = Path("data/exports")


def run_export(export_dir: str | Path | None = None) -> list[Path]:
    """Export all observations from the database to Excel files, one per data source.

    Args:
        export_dir: Directory for output files. Defaults to data/exports/.

    Returns:
        List of paths to the created Excel files.
    """
    out = Path(export_dir) if export_dir else DEFAULT_EXPORT_DIR
    out.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []
    db = SessionLocal()

    try:
        sources = db.query(DataSource).all()

        for source in sources:
            series_list = (
                db.query(DataSeries)
                .filter(DataSeries.source_id == source.id)
                .all()
            )

            if not series_list:
                continue

            timestamp = datetime.utcnow().strftime("%Y%m%d")
            filepath = out / f"{source.name.lower()}_{timestamp}.xlsx"

            for ds in series_list:
                observations = (
                    db.query(Observation)
                    .filter(Observation.series_id == ds.id)
                    .order_by(Observation.date)
                    .all()
                )

                if not observations:
                    continue

                df = pd.DataFrame(
                    [{"date": obs.date, "value": obs.value} for obs in observations]
                )
                df.set_index("date", inplace=True)

                sheet_name = ds.series_code[:31]  # Excel sheet names max 31 chars
                export_dataframe_to_excel(df, filepath, sheet_name=sheet_name)

            if filepath.exists():
                created_files.append(filepath)
                logger.info("Exported %s data to %s", source.name, filepath)

    except Exception:
        logger.exception("Excel export failed")
        raise
    finally:
        db.close()

    logger.info("Export complete: %d files created", len(created_files))
    return created_files


DEFAULT_MASTER_PATH = Path("data/macro_master.xlsx")


def export_master_workbook(path: str | Path | None = None) -> Path:
    """Create or update a single master Excel workbook with all FRED series.

    One sheet per series (date + value), plus a ``Summary`` sheet with the
    latest value for every series.  Only rewrites sheets whose row count has
    changed.
    """
    filepath = Path(path) if path else DEFAULT_MASTER_PATH
    filepath.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        source = db.query(DataSource).filter(DataSource.name == "FRED").first()
        if source is None:
            logger.warning("No FRED data source found -- skipping master export")
            return filepath

        series_list = (
            db.query(DataSeries)
            .filter(DataSeries.source_id == source.id)
            .order_by(DataSeries.series_code)
            .all()
        )

        if not series_list:
            logger.info("No FRED series to export")
            return filepath

        # Build per-series DataFrames and a summary row list
        summary_rows: list[dict] = []
        series_frames: dict[str, pd.DataFrame] = {}

        for ds in series_list:
            observations = (
                db.query(Observation)
                .filter(Observation.series_id == ds.id)
                .order_by(Observation.date)
                .all()
            )
            if not observations:
                continue

            df = pd.DataFrame(
                [{"date": obs.date, "value": obs.value} for obs in observations]
            )
            sheet_name = ds.series_code[:31]
            series_frames[sheet_name] = df

            last_obs = observations[-1]
            summary_rows.append(
                {
                    "series_code": ds.series_code,
                    "display_name": ds.display_name,
                    "latest_date": last_obs.date,
                    "latest_value": last_obs.value,
                    "unit": ds.unit,
                    "frequency": ds.frequency,
                    "observations": len(observations),
                }
            )

        # Determine which sheets need updating (compare row counts with existing file)
        existing_counts: dict[str, int] = {}
        if filepath.exists():
            try:
                with pd.ExcelFile(filepath, engine="openpyxl") as xls:
                    for name in xls.sheet_names:
                        existing_counts[name] = len(pd.read_excel(xls, name))
            except Exception:
                existing_counts = {}

        # Write summary + per-series sheets
        summary_df = pd.DataFrame(summary_rows)

        from backend.services.excel_export import export_dataframe_to_excel

        # Always update Summary
        export_dataframe_to_excel(summary_df, filepath, sheet_name="Summary")

        for sheet_name, df in series_frames.items():
            if existing_counts.get(sheet_name) == len(df):
                continue  # no new rows
            df_indexed = df.set_index("date")
            export_dataframe_to_excel(df_indexed, filepath, sheet_name=sheet_name)

        logger.info(
            "Master workbook updated at %s (%d series)", filepath, len(series_frames)
        )

    except Exception:
        logger.exception("Master workbook export failed")
        raise
    finally:
        db.close()

    return filepath
