"""Pydantic schemas for macroeconomic data endpoints."""

from datetime import date

from pydantic import BaseModel


class SeriesDataPoint(BaseModel):
    """Single date/value observation."""

    date: date
    value: float


class SeriesResponse(BaseModel):
    """Full series payload returned to the client."""

    series_id: str
    display_name: str
    unit: str
    data: list[SeriesDataPoint]


class YieldCurvePoint(BaseModel):
    """One maturity point on the yield curve."""

    maturity: str
    rate: float


class YieldCurveResponse(BaseModel):
    """Snapshot of the Treasury yield curve for a given date."""

    date: date
    points: list[YieldCurvePoint]


class IndicatorSummary(BaseModel):
    """Summary of a key macroeconomic indicator."""

    name: str
    value: float
    change: float | None = None
    unit: str


# ── Catalog ──


class SeriesCatalogEntry(BaseModel):
    """Describes one available series for the selector UI."""

    series_id: str
    display_name: str
    unit: str
    frequency: str
    category: str
    observation_count: int
    first_date: date | None = None
    last_date: date | None = None


# ── Multi-series ──


class MultiSeriesRequest(BaseModel):
    """Request body for fetching multiple series aligned by date."""

    series_ids: list[str]
    start: date | None = None
    end: date | None = None
    normalize: bool = False  # Z-score normalize for comparison


class SeriesColumn(BaseModel):
    """One column of a multi-series response."""

    series_id: str
    display_name: str
    unit: str
    values: list[float | None]


class MultiSeriesResponse(BaseModel):
    """Multiple series aligned on a common date index."""

    dates: list[date]
    series: list[SeriesColumn]


# ── Correlation ──


class CorrelationRequest(BaseModel):
    """Request body for cross-correlation analysis."""

    series_ids: list[str]
    start: date | None = None
    end: date | None = None
    max_lag: int = 12  # months


class CorrelationPair(BaseModel):
    """Cross-correlation between two series at the optimal lag."""

    series_a: str
    series_b: str
    correlation: float
    optimal_lag: int  # positive = A leads B


class CorrelationMatrix(BaseModel):
    """Pairwise contemporaneous correlations."""

    series_ids: list[str]
    display_names: list[str]
    matrix: list[list[float]]


class CorrelationResponse(BaseModel):
    """Full cross-correlation analysis result."""

    contemporaneous: CorrelationMatrix
    lagged: list[CorrelationPair]


# ── Composite / Recession risk ──


class RecessionSignal(BaseModel):
    """Individual recession risk signal."""

    name: str
    series_id: str
    signal: bool
    value: float
    threshold: str
    description: str


class RecessionRiskResponse(BaseModel):
    """Composite recession risk assessment."""

    score: int  # 0-10
    total_signals: int
    signals: list[RecessionSignal]
