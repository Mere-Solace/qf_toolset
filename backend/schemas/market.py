"""Pydantic schemas for market data endpoints."""

from datetime import date

from pydantic import BaseModel


class QuoteResponse(BaseModel):
    """Current quote for a single ticker."""

    ticker: str
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: float | None = None


class HistoryRequest(BaseModel):
    """Parameters for historical price queries."""

    period: str = "1y"
    interval: str = "1d"


class OHLCVPoint(BaseModel):
    """Single OHLCV bar."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class FinancialsExportResponse(BaseModel):
    """Result of a financial-statements Excel export."""

    filepath: str
    message: str
