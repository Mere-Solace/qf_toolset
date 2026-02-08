"""FastAPI application entry point for the Financial Analysis API."""

import logging
import logging.handlers
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.api.router import api_router
from backend.config import settings
from backend.database import Base, SessionLocal, engine

# ---------------------------------------------------------------------------
# Logging — console + rotating file under logs/
# ---------------------------------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Console handler
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
root_logger.addHandler(console)

# Rotating file handler — 5 MB per file, keep 5 backups
file_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "app.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Analysis API",
    version="1.0.0",
    description="Backend for financial data ingestion, option pricing, and macro analysis.",
)

# ---------------------------------------------------------------------------
# CORS -- allow the configured front-end origins
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup -- create DB tables and kick off the background data scheduler
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup() -> None:
    """Initialise the database schema and start the periodic ingestion scheduler."""
    logger.info("Creating database tables ...")
    Base.metadata.create_all(bind=engine)

    # Verify DB connectivity at startup
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection verified")
    except Exception:
        logger.error("Database connection FAILED at startup", exc_info=True)

    # Check FRED API key
    if not settings.fred_api_key:
        logger.warning("FRED_API_KEY is not set — data ingestion will be skipped")

    try:
        from backend.pipeline.scheduler import start_scheduler

        start_scheduler()
        logger.info("Pipeline scheduler started")
    except Exception:
        logger.warning("Could not start pipeline scheduler -- continuing without it", exc_info=True)

    # Run a full FRED data sync in a background thread so the API is
    # available immediately while data is being fetched.
    if settings.fred_api_key:

        def _startup_sync() -> None:
            try:
                from backend.pipeline.ingest_fred import ingest_fred

                logger.info("Syncing FRED data...")
                ingest_fred(full_sync=False)
                logger.info("Startup FRED sync complete")
            except Exception:
                logger.error("Startup FRED sync failed", exc_info=True)

        threading.Thread(target=_startup_sync, daemon=True, name="fred-startup-sync").start()


# ---------------------------------------------------------------------------
# Include all API routes under /api
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix="/api")


# ---------------------------------------------------------------------------
# Health checks (outside /api prefix for simple uptime monitoring)
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    """Lightweight liveness probe."""
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict:
    """Database connectivity check with table counts."""
    checks: dict = {"database": "error", "tables": {}, "fred_api_key_set": bool(settings.fred_api_key)}
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"

        # Count rows in key tables
        for table in ["data_sources", "data_series", "observations"]:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))  # noqa: S608
                checks["tables"][table] = result.scalar()
            except Exception:
                checks["tables"][table] = "missing"
        db.close()
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        logger.error("Health check DB failure", exc_info=True)
    return checks
