"""Macroeconomic data API router -- FRED/BLS/BEA series, yield curve, indicators,
multi-series comparison, cross-correlation, and recession risk scoring."""

import json
import logging
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.timeseries import DataSeries, Observation
from backend.schemas.macro import (
    CorrelationMatrix,
    CorrelationPair,
    CorrelationRequest,
    CorrelationResponse,
    IndicatorSummary,
    MultiSeriesRequest,
    MultiSeriesResponse,
    RecessionRiskResponse,
    RecessionSignal,
    SeriesCatalogEntry,
    SeriesColumn,
    SeriesDataPoint,
    SeriesResponse,
    YieldCurvePoint,
    YieldCurveResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/macro", tags=["macro"])

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_series.json"

# Treasury maturities used for the yield curve snapshot.
_YIELD_CURVE_SERIES = ["DGS3MO", "DGS1", "DGS2", "DGS5", "DGS10", "DGS30"]

# Key macro indicators displayed on the dashboard.
_KEY_INDICATORS: list[dict] = [
    {"code": "GDP", "name": "Real GDP", "unit": "Billions $"},
    {"code": "CPIAUCSL", "name": "CPI (All Urban)", "unit": "Index"},
    {"code": "UNRATE", "name": "Unemployment Rate", "unit": "%"},
    {"code": "FEDFUNDS", "name": "Fed Funds Rate", "unit": "%"},
    {"code": "DGS10", "name": "10-Year Treasury", "unit": "%"},
    {"code": "DGS2", "name": "2-Year Treasury", "unit": "%"},
    {"code": "T10Y2Y", "name": "10Y-2Y Spread", "unit": "%"},
    {"code": "BAMLH0A0HYM2", "name": "HY OAS", "unit": "bps"},
    {"code": "MANEMP", "name": "Mfg Employment", "unit": "Thousands"},
    {"code": "NFCI", "name": "Financial Conditions", "unit": "Index"},
]


def _load_seed_category_map() -> dict[str, str]:
    """Build a series_id -> category lookup from the seed file."""
    try:
        with open(SEED_PATH) as f:
            seed = json.load(f)
        fred = seed.get("fred", {})
        if isinstance(fred, dict):
            mapping: dict[str, str] = {}
            for _cat, items in fred.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "id" in item:
                            mapping[item["id"]] = item.get("category", "")
            return mapping
    except Exception:
        pass
    return {}


# ── Single series ──


@router.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: str,
    start: date | None = Query(None, description="Start date (inclusive)"),
    end: date | None = Query(None, description="End date (inclusive)"),
    db: Session = Depends(get_db),
) -> SeriesResponse:
    """Return observations for a tracked data series, optionally filtered by date range."""
    series = db.query(DataSeries).filter(DataSeries.series_code == series_id).first()
    if series is None:
        raise HTTPException(status_code=404, detail=f"Series '{series_id}' not found")

    query = db.query(Observation).filter(Observation.series_id == series.id)
    if start is not None:
        query = query.filter(Observation.date >= start)
    if end is not None:
        query = query.filter(Observation.date <= end)
    query = query.order_by(Observation.date)

    observations = query.all()
    data = [SeriesDataPoint(date=obs.date, value=obs.value) for obs in observations]

    return SeriesResponse(
        series_id=series.series_code,
        display_name=series.display_name,
        unit=series.unit,
        data=data,
    )


# ── Catalog (list available series for the selector UI) ──


@router.get("/catalog", response_model=list[SeriesCatalogEntry])
async def get_catalog(db: Session = Depends(get_db)) -> list[SeriesCatalogEntry]:
    """Return all available series with metadata for the series selector."""
    category_map = _load_seed_category_map()

    all_series = db.query(DataSeries).all()
    entries: list[SeriesCatalogEntry] = []

    for s in all_series:
        stats = (
            db.query(
                func.count(Observation.id),
                func.min(Observation.date),
                func.max(Observation.date),
            )
            .filter(Observation.series_id == s.id)
            .first()
        )
        count, first_dt, last_dt = stats if stats else (0, None, None)

        entries.append(
            SeriesCatalogEntry(
                series_id=s.series_code,
                display_name=s.display_name,
                unit=s.unit,
                frequency=s.frequency,
                category=category_map.get(s.series_code, ""),
                observation_count=count,
                first_date=first_dt,
                last_date=last_dt,
            )
        )

    return entries


# ── Yield curve ──


@router.get("/yield-curve", response_model=YieldCurveResponse)
async def get_yield_curve(db: Session = Depends(get_db)) -> YieldCurveResponse:
    """Return the latest Treasury yield-curve snapshot (3M .. 30Y)."""
    points: list[YieldCurvePoint] = []
    latest_date: date | None = None

    for code in _YIELD_CURVE_SERIES:
        series = db.query(DataSeries).filter(DataSeries.series_code == code).first()
        if series is None:
            continue

        obs = (
            db.query(Observation)
            .filter(Observation.series_id == series.id)
            .order_by(desc(Observation.date))
            .first()
        )
        if obs is None:
            continue

        # Derive a human-readable maturity label from the series code.
        raw = code.replace("DGS", "")
        maturity_label = raw + ("M" if raw.endswith("MO") else "Y")
        maturity_label = maturity_label.replace("MOM", "M")
        points.append(YieldCurvePoint(maturity=maturity_label, rate=obs.value))

        if latest_date is None or obs.date > latest_date:
            latest_date = obs.date

    if not points:
        raise HTTPException(status_code=404, detail="No yield-curve data available")

    return YieldCurveResponse(date=latest_date, points=points)  # type: ignore[arg-type]


# ── Key indicators summary ──


@router.get("/indicators", response_model=list[IndicatorSummary])
async def get_indicators(db: Session = Depends(get_db)) -> list[IndicatorSummary]:
    """Return the latest value (and period-over-period change) for key macro indicators."""
    summaries: list[IndicatorSummary] = []

    for ind in _KEY_INDICATORS:
        series = db.query(DataSeries).filter(DataSeries.series_code == ind["code"]).first()
        if series is None:
            continue

        recent = (
            db.query(Observation)
            .filter(Observation.series_id == series.id)
            .order_by(desc(Observation.date))
            .limit(2)
            .all()
        )
        if not recent:
            continue

        value = recent[0].value
        change = (recent[0].value - recent[1].value) if len(recent) > 1 else None
        summaries.append(
            IndicatorSummary(
                name=ind["name"],
                value=value,
                change=change,
                unit=ind["unit"],
            )
        )

    return summaries


# ── Multi-series (date-aligned, optional Z-score normalization) ──


@router.post("/multi-series", response_model=MultiSeriesResponse)
async def get_multi_series(
    body: MultiSeriesRequest,
    db: Session = Depends(get_db),
) -> MultiSeriesResponse:
    """Fetch multiple series and align them on a common date index.

    If ``normalize`` is True, each series is Z-score normalised so indicators
    of different scales can be plotted on the same axis.
    """
    if not body.series_ids:
        raise HTTPException(status_code=400, detail="At least one series_id is required")
    if len(body.series_ids) > 20:
        raise HTTPException(status_code=400, detail="Max 20 series per request")

    # Build a {series_code: DataFrame} map
    frames: dict[str, pd.DataFrame] = {}
    meta: dict[str, dict] = {}

    for sid in body.series_ids:
        series = db.query(DataSeries).filter(DataSeries.series_code == sid).first()
        if series is None:
            continue

        query = db.query(Observation.date, Observation.value).filter(
            Observation.series_id == series.id
        )
        if body.start:
            query = query.filter(Observation.date >= body.start)
        if body.end:
            query = query.filter(Observation.date <= body.end)
        query = query.order_by(Observation.date)

        rows = query.all()
        if not rows:
            continue

        df = pd.DataFrame(rows, columns=["date", sid])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        frames[sid] = df
        meta[sid] = {"display_name": series.display_name, "unit": series.unit}

    if not frames:
        raise HTTPException(status_code=404, detail="No data found for the requested series")

    # Outer join on date index so every date with any observation is included
    combined = pd.concat(frames.values(), axis=1, join="outer").sort_index()

    # Z-score normalisation
    if body.normalize:
        for col in combined.columns:
            mean = combined[col].mean()
            std = combined[col].std()
            if std and std > 0:
                combined[col] = (combined[col] - mean) / std

    dates = [d.date() for d in combined.index]
    columns: list[SeriesColumn] = []
    for sid in combined.columns:
        vals = combined[sid].tolist()
        # Convert NaN to None for JSON
        vals = [None if (isinstance(v, float) and np.isnan(v)) else v for v in vals]
        m = meta.get(sid, {})
        columns.append(
            SeriesColumn(
                series_id=sid,
                display_name=m.get("display_name", sid),
                unit="Z-score" if body.normalize else m.get("unit", ""),
                values=vals,
            )
        )

    return MultiSeriesResponse(dates=dates, series=columns)


# ── Cross-correlation analysis ──


@router.post("/correlation", response_model=CorrelationResponse)
async def get_correlation(
    body: CorrelationRequest,
    db: Session = Depends(get_db),
) -> CorrelationResponse:
    """Compute pairwise contemporaneous and lagged cross-correlations.

    Returns a correlation matrix plus the optimal lag (in periods) for each pair,
    identifying which series leads or lags the other.
    """
    if len(body.series_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 series required")
    if len(body.series_ids) > 15:
        raise HTTPException(status_code=400, detail="Max 15 series for correlation")

    # Fetch all series into a single DataFrame
    frames: dict[str, pd.DataFrame] = {}
    names: dict[str, str] = {}

    for sid in body.series_ids:
        series = db.query(DataSeries).filter(DataSeries.series_code == sid).first()
        if series is None:
            continue
        query = db.query(Observation.date, Observation.value).filter(
            Observation.series_id == series.id
        )
        if body.start:
            query = query.filter(Observation.date >= body.start)
        if body.end:
            query = query.filter(Observation.date <= body.end)

        rows = query.order_by(Observation.date).all()
        if not rows:
            continue

        df = pd.DataFrame(rows, columns=["date", sid])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        frames[sid] = df
        names[sid] = series.display_name

    if len(frames) < 2:
        raise HTTPException(status_code=404, detail="Not enough series with data")

    # Resample all to monthly end-of-month to align different frequencies
    monthly_frames = {}
    for sid, df in frames.items():
        resampled = df.resample("ME").last().dropna()
        monthly_frames[sid] = resampled

    combined = pd.concat(monthly_frames.values(), axis=1, join="inner").dropna()
    if combined.empty or len(combined) < 6:
        raise HTTPException(status_code=422, detail="Insufficient overlapping data for correlation")

    valid_ids = list(combined.columns)

    # Contemporaneous correlation matrix
    corr_matrix = combined.corr()
    matrix_values = corr_matrix.values.tolist()

    contemporaneous = CorrelationMatrix(
        series_ids=valid_ids,
        display_names=[names.get(sid, sid) for sid in valid_ids],
        matrix=[[round(v, 4) for v in row] for row in matrix_values],
    )

    # Lagged cross-correlation for each pair
    lagged_pairs: list[CorrelationPair] = []
    max_lag = min(body.max_lag, len(combined) // 3)

    for a, b in combinations(valid_ids, 2):
        best_corr = 0.0
        best_lag = 0
        sa = combined[a]
        sb = combined[b]

        for lag in range(-max_lag, max_lag + 1):
            if lag > 0:
                corr = sa.iloc[:-lag].corr(sb.iloc[lag:])
            elif lag < 0:
                corr = sa.iloc[-lag:].corr(sb.iloc[:lag])
            else:
                corr = sa.corr(sb)

            if not np.isnan(corr) and abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        lagged_pairs.append(
            CorrelationPair(
                series_a=a,
                series_b=b,
                correlation=round(best_corr, 4),
                optimal_lag=best_lag,
            )
        )

    lagged_pairs.sort(key=lambda p: abs(p.correlation), reverse=True)

    return CorrelationResponse(contemporaneous=contemporaneous, lagged=lagged_pairs)


# ── Recession risk score ──


_RECESSION_CHECKS = [
    {
        "name": "Yield Curve (10Y-3M)",
        "series_id": "T10Y3M",
        "check": lambda v: v < 0,
        "threshold": "< 0 (inverted)",
        "desc": "10Y-3M spread inverted; historically precedes recession by 12-18mo",
    },
    {
        "name": "Yield Curve (10Y-2Y)",
        "series_id": "T10Y2Y",
        "check": lambda v: v < 0,
        "threshold": "< 0 (inverted)",
        "desc": "10Y-2Y spread inverted; every inversion since 1955 preceded recession",
    },
    {
        "name": "HY Credit Spread",
        "series_id": "BAMLH0A0HYM2",
        "check": lambda v: v > 5.0,
        "threshold": "> 500 bps",
        "desc": "High yield OAS above 500bps signals elevated credit stress",
    },
    {
        "name": "Manufacturing Employment",
        "series_id": "MANEMP",
        "check": lambda v: v < 12_000,
        "threshold": "< 12,000K (declining)",
        "desc": "Manufacturing employment below 12M signals sector weakness",
    },
    {
        "name": "Chicago Fed NFCI",
        "series_id": "NFCI",
        "check": lambda v: v > 0,
        "threshold": "> 0 (tighter than avg)",
        "desc": "Positive NFCI means financial conditions tighter than average",
    },
    {
        "name": "Financial Stress (StL Fed)",
        "series_id": "STLFSI4",
        "check": lambda v: v > 1.0,
        "threshold": "> 1.0 (elevated)",
        "desc": "StL Fed stress index above 1 std deviation indicates stress",
    },
    {
        "name": "Sahm Rule",
        "series_id": "SAHMREALTIME",
        "check": lambda v: v >= 0.5,
        "threshold": ">= 0.50 pp",
        "desc": "3-month avg unemployment rise >= 0.5pp triggers Sahm recession signal",
    },
    {
        "name": "Recession Probability",
        "series_id": "RECPROUSM156N",
        "check": lambda v: v > 30,
        "threshold": "> 30%",
        "desc": "Smoothed recession probability above 30% indicates elevated risk",
    },
    {
        "name": "Chicago Fed Activity",
        "series_id": "CFNAI",
        "check": lambda v: v < -0.7,
        "threshold": "< -0.70",
        "desc": "CFNAI below -0.7 signals recession may have begun",
    },
    {
        "name": "Leading Index (US)",
        "series_id": "USSLIND",
        "check": lambda v: v < 0,
        "threshold": "< 0 (declining)",
        "desc": "Negative leading index suggests deteriorating economic outlook",
    },
]


@router.get("/recession-risk", response_model=RecessionRiskResponse)
async def get_recession_risk(db: Session = Depends(get_db)) -> RecessionRiskResponse:
    """Score recession risk from 0-10 based on current indicator readings."""
    signals: list[RecessionSignal] = []

    for check in _RECESSION_CHECKS:
        sid = check["series_id"]
        series = db.query(DataSeries).filter(DataSeries.series_code == sid).first()
        if series is None:
            continue

        obs = (
            db.query(Observation)
            .filter(Observation.series_id == series.id)
            .order_by(desc(Observation.date))
            .first()
        )
        if obs is None:
            continue

        triggered = check["check"](obs.value)
        signals.append(
            RecessionSignal(
                name=check["name"],
                series_id=sid,
                signal=triggered,
                value=round(obs.value, 4),
                threshold=check["threshold"],
                description=check["desc"],
            )
        )

    score = sum(1 for s in signals if s.signal)

    return RecessionRiskResponse(
        score=score,
        total_signals=len(signals),
        signals=signals,
    )
