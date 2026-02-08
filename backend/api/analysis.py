"""Statistical-analysis API router -- regression and VAR models."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.schemas.analysis import (
    RegressionResult,
    RunAnalysisRequest,
    VARResult,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Default location for persisted analysis results.
_RESULTS_DIR = Path("data/analysis_results")


@router.get("/regression/results", response_model=list[RegressionResult])
async def get_regression_results() -> list[RegressionResult]:
    """Load the most recently saved regression results from disk."""
    results_file = _RESULTS_DIR / "regression.json"
    if not results_file.exists():
        raise HTTPException(status_code=404, detail="No regression results found. Run an analysis first.")
    try:
        raw = json.loads(results_file.read_text())
        return [RegressionResult(**item) for item in raw]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load regression results: {exc}")


@router.get("/var/results", response_model=VARResult)
async def get_var_results() -> VARResult:
    """Load the most recently saved VAR model results from disk."""
    results_file = _RESULTS_DIR / "var.json"
    if not results_file.exists():
        raise HTTPException(status_code=404, detail="No VAR results found. Run an analysis first.")
    try:
        raw = json.loads(results_file.read_text())
        return VARResult(**raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load VAR results: {exc}")


@router.post("/regression/run", response_model=list[RegressionResult])
async def run_regression(req: RunAnalysisRequest | None = None) -> list[RegressionResult]:
    """Trigger a regression analysis and return the results.

    If *csv_path* is provided it is used as the input dataset; otherwise the
    service falls back to its default data source.
    """
    try:
        from backend.analysis.regression import run_regression as _run

        csv_path = req.csv_path if req else None
        results = _run(csv_path=csv_path)

        # Persist results for later retrieval.
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (_RESULTS_DIR / "regression.json").write_text(
            json.dumps([r if isinstance(r, dict) else r for r in results], default=str)
        )

        return [RegressionResult(**r) if isinstance(r, dict) else r for r in results]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Regression analysis failed: {exc}")


@router.post("/var/run", response_model=VARResult)
async def run_var(req: RunAnalysisRequest | None = None) -> VARResult:
    """Trigger a VAR model estimation and return the results."""
    try:
        from backend.analysis.var_model import run_var as _run

        csv_path = req.csv_path if req else None
        result = _run(csv_path=csv_path)

        # Persist results for later retrieval.
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (_RESULTS_DIR / "var.json").write_text(
            json.dumps(result if isinstance(result, dict) else result, default=str)
        )

        return VARResult(**result) if isinstance(result, dict) else result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"VAR analysis failed: {exc}")
