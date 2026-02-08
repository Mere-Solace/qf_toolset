"""Data management API router -- series listing, Excel export, pipeline triggers."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.timeseries import DataSeries

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/series")
async def list_series(db: Session = Depends(get_db)) -> list[dict]:
    """Return every tracked data series with its source and metadata."""
    series_list = db.query(DataSeries).all()
    return [
        {
            "id": s.id,
            "series_code": s.series_code,
            "display_name": s.display_name,
            "frequency": s.frequency,
            "unit": s.unit,
            "source_id": s.source_id,
            "last_updated": s.last_updated.isoformat() if s.last_updated else None,
        }
        for s in series_list
    ]


@router.get("/export/excel")
async def export_excel() -> dict:
    """Generate a consolidated Excel workbook of all tracked series."""
    try:
        from backend.services.excel_export import export_all

        filepath = export_all()
        return {"filepath": filepath, "message": "Excel export completed successfully."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel export failed: {exc}")


@router.post("/pipeline/trigger")
async def trigger_pipeline(
    source: str = Query("all", description="Pipeline source to trigger: all, fred, bls, bea, market"),
) -> dict:
    """Manually trigger a data-ingestion pipeline run.

    Pass *source* to limit the run to a single provider, or use ``all`` to run
    every pipeline sequentially.
    """
    runners: dict[str, str] = {
        "fred": "backend.pipeline.ingest_fred",
        "bls": "backend.pipeline.ingest_bls",
        "bea": "backend.pipeline.ingest_bea",
        "market": "backend.pipeline.ingest_market",
    }

    sources_to_run = list(runners.keys()) if source == "all" else [source]
    results: dict[str, str] = {}

    for src in sources_to_run:
        module_path = runners.get(src)
        if module_path is None:
            results[src] = f"Unknown source '{src}'"
            continue
        try:
            import importlib

            mod = importlib.import_module(module_path)
            mod.run()  # type: ignore[attr-defined]
            results[src] = "ok"
        except Exception as exc:
            results[src] = f"error: {exc}"

    return {"triggered": sources_to_run, "results": results}
