"""SQLAlchemy ORM models for time-series financial data."""

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class DataSource(Base):
    """Represents a data provider (FRED, BLS, BEA, YAHOO)."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    api_key_env_var: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    series: Mapped[list["DataSeries"]] = relationship(
        "DataSeries", back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id}, name='{self.name}')>"


class DataSeries(Base):
    """A specific data series from a source (e.g., DGS10 from FRED)."""

    __tablename__ = "data_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_sources.id"), nullable=False
    )
    series_code: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    source: Mapped["DataSource"] = relationship("DataSource", back_populates="series")
    observations: Mapped[list["Observation"]] = relationship(
        "Observation", back_populates="series", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DataSeries(id={self.id}, code='{self.series_code}')>"


class Observation(Base):
    """A single date/value observation for a data series."""

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_series.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    series: Mapped["DataSeries"] = relationship("DataSeries", back_populates="observations")

    __table_args__ = (
        UniqueConstraint("series_id", "date", name="uq_series_date"),
        Index("ix_observations_date", "date"),
    )

    def __repr__(self) -> str:
        return f"<Observation(series_id={self.series_id}, date={self.date}, value={self.value})>"
