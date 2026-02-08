"""Tests for the FRED data pipeline: CSV store, DB integration, ingestion, and export."""

import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.timeseries import DataSeries, DataSource, Observation
from backend.pipeline.csv_store import (
    append_rows,
    get_last_date,
    load_series_csv,
    save_series_csv,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Return a temporary data directory for CSV tests."""
    return tmp_path / "data"


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A small DataFrame with date + value columns."""
    return pd.DataFrame(
        {
            "date": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
            "value": [4.5, 4.6, 4.7],
        }
    )


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# CSV Store tests
# ---------------------------------------------------------------------------

class TestCSVStoreRoundtrip:
    def test_save_and_load(self, tmp_data_dir: Path, sample_df: pd.DataFrame):
        """Write a CSV, read it back, verify data integrity."""
        save_series_csv("DGS10", sample_df, data_dir=tmp_data_dir)
        loaded = load_series_csv("DGS10", data_dir=tmp_data_dir)

        assert len(loaded) == 3
        assert list(loaded.columns) == ["date", "value"]
        assert loaded["date"].tolist() == sample_df["date"].tolist()
        assert loaded["value"].tolist() == pytest.approx(sample_df["value"].tolist())

    def test_load_nonexistent_returns_empty(self, tmp_data_dir: Path):
        """Loading a CSV that doesn't exist should return an empty DataFrame."""
        df = load_series_csv("NONEXISTENT", data_dir=tmp_data_dir)
        assert df.empty
        assert list(df.columns) == ["date", "value"]

    def test_get_last_date(self, tmp_data_dir: Path, sample_df: pd.DataFrame):
        save_series_csv("DGS10", sample_df, data_dir=tmp_data_dir)
        assert get_last_date("DGS10", data_dir=tmp_data_dir) == date(2024, 1, 4)

    def test_get_last_date_no_file(self, tmp_data_dir: Path):
        assert get_last_date("MISSING", data_dir=tmp_data_dir) is None


class TestCSVDiff:
    def test_append_only_new_rows(self, tmp_data_dir: Path, sample_df: pd.DataFrame):
        """append_rows should add only dates not already in the CSV."""
        save_series_csv("DGS10", sample_df, data_dir=tmp_data_dir)

        new_df = pd.DataFrame(
            {
                "date": [date(2024, 1, 4), date(2024, 1, 5)],  # 1/4 is a dup
                "value": [4.7, 4.8],
            }
        )
        appended = append_rows("DGS10", new_df, data_dir=tmp_data_dir)

        assert appended == 1  # only 1/5 is new
        loaded = load_series_csv("DGS10", data_dir=tmp_data_dir)
        assert len(loaded) == 4
        assert date(2024, 1, 5) in loaded["date"].tolist()

    def test_append_to_empty(self, tmp_data_dir: Path, sample_df: pd.DataFrame):
        """append_rows on a nonexistent CSV should create the file."""
        appended = append_rows("NEW_SERIES", sample_df, data_dir=tmp_data_dir)
        assert appended == 3
        loaded = load_series_csv("NEW_SERIES", data_dir=tmp_data_dir)
        assert len(loaded) == 3

    def test_append_no_new_rows(self, tmp_data_dir: Path, sample_df: pd.DataFrame):
        """Appending identical data should add 0 rows."""
        save_series_csv("DGS10", sample_df, data_dir=tmp_data_dir)
        appended = append_rows("DGS10", sample_df, data_dir=tmp_data_dir)
        assert appended == 0


# ---------------------------------------------------------------------------
# Database connection test
# ---------------------------------------------------------------------------

class TestDatabaseConnection:
    def test_create_tables_and_insert(self, in_memory_db):
        """Create schema, insert an observation, query it back."""
        db = in_memory_db

        source = DataSource(
            name="FRED", base_url="https://api.stlouisfed.org/fred", api_key_env_var="FRED_API_KEY"
        )
        db.add(source)
        db.flush()

        series = DataSeries(
            source_id=source.id,
            series_code="DGS10",
            display_name="10-Year Treasury",
            unit="Percent",
            frequency="daily",
        )
        db.add(series)
        db.flush()

        obs = Observation(series_id=series.id, date=date(2024, 1, 2), value=4.5)
        db.add(obs)
        db.commit()

        result = db.query(Observation).filter(Observation.series_id == series.id).all()
        assert len(result) == 1
        assert result[0].value == pytest.approx(4.5)
        assert result[0].date == date(2024, 1, 2)


# ---------------------------------------------------------------------------
# FRED API connection test (requires FRED_API_KEY)
# ---------------------------------------------------------------------------

class TestFredAPIConnection:
    @pytest.mark.skipif(
        not os.environ.get("FRED_API_KEY"),
        reason="FRED_API_KEY not set",
    )
    def test_fetch_dgs10_small_range(self):
        """Real API call: fetch DGS10 for a small date range."""
        from backend.services.fred_client import get_series

        df = get_series("DGS10", start_date="2024-01-02", end_date="2024-01-31")
        assert not df.empty
        assert "date" in df.columns
        assert "value" in df.columns
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Ingest idempotency test
# ---------------------------------------------------------------------------

class TestIngestUpsertIdempotent:
    def test_double_ingest_no_duplicates(self):
        """Running ingest twice with the same data should not create duplicates."""
        fake_df = pd.DataFrame(
            {
                "date": [date(2024, 1, 2), date(2024, 1, 3)],
                "value": [4.5, 4.6],
            }
        )

        # Use an in-memory DB for this test
        eng = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=eng)
        Session = sessionmaker(bind=eng)

        with (
            patch("backend.pipeline.ingest_fred.get_series", return_value=fake_df),
            patch("backend.pipeline.ingest_fred.get_last_date", return_value=None),
            patch("backend.pipeline.ingest_fred.append_rows", return_value=2),
            patch("backend.pipeline.ingest_fred.SessionLocal", Session),
        ):
            from backend.pipeline.ingest_fred import ingest_fred

            ingest_fred(full_sync=True)
            ingest_fred(full_sync=True)

        session = Session()
        # Verify no series has duplicate dates
        from sqlalchemy import func

        dupes = (
            session.query(Observation.series_id, Observation.date)
            .group_by(Observation.series_id, Observation.date)
            .having(func.count() > 1)
            .all()
        )
        assert len(dupes) == 0, f"Found duplicate observations: {dupes}"
        session.close()


# ---------------------------------------------------------------------------
# Master XLSX export test
# ---------------------------------------------------------------------------

class TestMasterXLSXExport:
    def test_export_creates_file_with_summary(self, tmp_path: Path):
        """export_master_workbook should create an xlsx with a Summary sheet."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Seed data
        source = DataSource(name="FRED", base_url="", api_key_env_var="")
        session.add(source)
        session.flush()

        series = DataSeries(
            source_id=source.id,
            series_code="DGS10",
            display_name="10-Year Treasury",
            unit="Percent",
            frequency="daily",
        )
        session.add(series)
        session.flush()

        for i, val in enumerate([4.5, 4.6, 4.7]):
            session.add(Observation(series_id=series.id, date=date(2024, 1, 2 + i), value=val))
        session.commit()

        master_path = tmp_path / "macro_master.xlsx"

        with patch("backend.pipeline.export_excel.SessionLocal", Session):
            from backend.pipeline.export_excel import export_master_workbook

            result = export_master_workbook(path=master_path)

        assert result == master_path
        assert master_path.exists()

        # Verify sheets
        with pd.ExcelFile(master_path, engine="openpyxl") as xls:
            assert "Summary" in xls.sheet_names
            assert "DGS10" in xls.sheet_names

            summary = pd.read_excel(xls, "Summary")
            assert "series_code" in summary.columns
            assert summary.iloc[0]["series_code"] == "DGS10"

        session.close()
