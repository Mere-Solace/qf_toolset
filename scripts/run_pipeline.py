"""CLI entry point for running data ingestion pipelines on demand.

Usage:
    python -m scripts.run_pipeline --source fred
    python -m scripts.run_pipeline --source all
    python -m scripts.run_pipeline --source market --period 5y
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Parse arguments and run the selected ingestion pipeline(s)."""
    parser = argparse.ArgumentParser(
        description="Run financial data ingestion pipelines.",
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["fred", "bls", "bea", "market", "export", "all"],
        help="Which data source to ingest (or 'all' for everything).",
    )
    parser.add_argument(
        "--period",
        type=str,
        default="5d",
        help="Lookback period for Yahoo market data (e.g. '5d', '1y', '5y', 'max'). "
             "Only used with --source market.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Start year for BLS data ingestion.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="End year for BLS data ingestion.",
    )

    args = parser.parse_args()

    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)

    sources = [args.source] if args.source != "all" else ["fred", "bls", "bea", "market", "export"]

    for source in sources:
        logger.info("Running pipeline: %s", source)

        try:
            if source == "fred":
                from backend.pipeline.ingest_fred import ingest_fred
                count = ingest_fred()
                logger.info("FRED: %d observations upserted", count)

            elif source == "bls":
                from backend.pipeline.ingest_bls import ingest_bls
                count = ingest_bls(
                    start_year=args.start_year,
                    end_year=args.end_year,
                )
                logger.info("BLS: %d observations upserted", count)

            elif source == "bea":
                from backend.pipeline.ingest_bea import ingest_bea
                count = ingest_bea()
                logger.info("BEA: %d observations upserted", count)

            elif source == "market":
                from backend.pipeline.ingest_market import ingest_market
                count = ingest_market(period=args.period)
                logger.info("Market: %d observations upserted", count)

            elif source == "export":
                from backend.pipeline.export_excel import run_export
                files = run_export()
                logger.info("Export: %d files created", len(files))

        except Exception:
            logger.exception("Pipeline '%s' failed", source)
            if args.source != "all":
                sys.exit(1)

    logger.info("All requested pipelines complete.")


if __name__ == "__main__":
    main()
