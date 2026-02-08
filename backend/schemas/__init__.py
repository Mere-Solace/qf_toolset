"""Pydantic schemas package -- re-exports all schema classes."""

from backend.schemas.analysis import (
    RegressionCoefficient,
    RegressionResult,
    RunAnalysisRequest,
    VARResult,
)
from backend.schemas.macro import (
    IndicatorSummary,
    SeriesDataPoint,
    SeriesResponse,
    YieldCurvePoint,
    YieldCurveResponse,
)
from backend.schemas.market import (
    FinancialsExportResponse,
    HistoryRequest,
    OHLCVPoint,
    QuoteResponse,
)
from backend.schemas.options import (
    BinomialRequest,
    BinomialResult,
    BlackScholesRequest,
    GreeksSurfaceRequest,
    ImpliedVolRequest,
    ImpliedVolResult,
    MonteCarloRequest,
    MonteCarloResult,
    PricingResult,
)

__all__ = [
    # market
    "QuoteResponse",
    "HistoryRequest",
    "OHLCVPoint",
    "FinancialsExportResponse",
    # macro
    "SeriesDataPoint",
    "SeriesResponse",
    "YieldCurvePoint",
    "YieldCurveResponse",
    "IndicatorSummary",
    # options
    "BlackScholesRequest",
    "PricingResult",
    "BinomialRequest",
    "BinomialResult",
    "MonteCarloRequest",
    "MonteCarloResult",
    "ImpliedVolRequest",
    "ImpliedVolResult",
    "GreeksSurfaceRequest",
    # analysis
    "RegressionCoefficient",
    "RegressionResult",
    "VARResult",
    "RunAnalysisRequest",
]
