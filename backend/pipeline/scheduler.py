"""APScheduler configuration for automated data ingestion and export jobs."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.pipeline.export_excel import export_master_workbook, run_export
from backend.pipeline.ingest_bea import ingest_bea
from backend.pipeline.ingest_bls import ingest_bls
from backend.pipeline.ingest_fred import ingest_fred
from backend.pipeline.ingest_market import ingest_market

logger = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Create and configure the APScheduler instance with all data jobs.

    Schedule:
        - market_data: every 15 min during 9:30-16:00 ET on weekdays
        - fred: daily at 7:00 AM ET
        - bls: monthly on the 1st at 8:30 AM ET
        - bea: quarterly on the 1st of Jan/Apr/Jul/Oct at 8:30 AM ET
        - export: daily at 6:00 PM ET

    Returns:
        Configured (but not yet started) BackgroundScheduler.
    """
    scheduler = BackgroundScheduler(timezone="US/Eastern")

    # Yahoo Finance market data -- every 15 minutes during market hours, weekdays
    scheduler.add_job(
        ingest_market,
        CronTrigger(
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/15",
            timezone="US/Eastern",
        ),
        id="ingest_market",
        name="Ingest Yahoo market data",
        replace_existing=True,
    )

    # FRED data -- daily at 7:00 AM ET, then export master workbook
    def _ingest_fred_and_export() -> None:
        ingest_fred()
        export_master_workbook()

    scheduler.add_job(
        _ingest_fred_and_export,
        CronTrigger(
            hour=7,
            minute=0,
            timezone="US/Eastern",
        ),
        id="ingest_fred",
        name="Ingest FRED data + master export",
        replace_existing=True,
    )

    # BLS data -- monthly on the 1st at 8:30 AM ET
    scheduler.add_job(
        ingest_bls,
        CronTrigger(
            day=1,
            hour=8,
            minute=30,
            timezone="US/Eastern",
        ),
        id="ingest_bls",
        name="Ingest BLS data",
        replace_existing=True,
    )

    # BEA data -- quarterly on the 1st of Jan, Apr, Jul, Oct at 8:30 AM ET
    scheduler.add_job(
        ingest_bea,
        CronTrigger(
            month="1,4,7,10",
            day=1,
            hour=8,
            minute=30,
            timezone="US/Eastern",
        ),
        id="ingest_bea",
        name="Ingest BEA data",
        replace_existing=True,
    )

    # Excel snapshot export -- daily at 6:00 PM ET
    scheduler.add_job(
        run_export,
        CronTrigger(
            hour=18,
            minute=0,
            timezone="US/Eastern",
        ),
        id="export_excel",
        name="Export data to Excel",
        replace_existing=True,
    )

    # Master workbook export -- daily at 6:00 PM ET (after snapshot)
    scheduler.add_job(
        export_master_workbook,
        CronTrigger(
            hour=18,
            minute=5,
            timezone="US/Eastern",
        ),
        id="export_master_xlsx",
        name="Export master XLSX workbook",
        replace_existing=True,
    )

    logger.info("Scheduler configured with %d jobs", len(scheduler.get_jobs()))
    return scheduler


def start_scheduler() -> BackgroundScheduler:
    """Create, start, and return the scheduler."""
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
