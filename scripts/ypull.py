"""Pull yfinance price data for a ticker and save to data/temp/temp_{TICKER}.csv

Usage:
    python scripts/ypull.py TICKER [--start YYYY-MM-DD] [--end YYYY-MM-DD]
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.data import load_yfinance

TEMP_DIR = PROJECT_ROOT / "data" / "temp"


def main():
    parser = argparse.ArgumentParser(description="Pull yfinance data to data/temp/")
    parser.add_argument("ticker", type=str, help="Ticker symbol (e.g. SPY, TLT)")
    parser.add_argument("--start", type=str, default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=None, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    df = load_yfinance(ticker, start=args.start, end=args.end)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TEMP_DIR / f"temp_{ticker}.csv"

    df.index.name = "date"
    df.to_csv(out_path)

    print(f"{ticker}: {len(df)} rows → {out_path}")


if __name__ == "__main__":
    main()
