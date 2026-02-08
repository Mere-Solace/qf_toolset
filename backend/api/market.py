"""Market-data API router -- quotes, history, and financial-statement exports."""

from fastapi import APIRouter, HTTPException, Query

from backend.schemas.market import (
    FinancialsExportResponse,
    OHLCVPoint,
    QuoteResponse,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote/{ticker}", response_model=QuoteResponse)
async def get_quote(ticker: str) -> QuoteResponse:
    """Return the latest quote for *ticker* using yfinance via market_data service."""
    try:
        from backend.services.market_data import get_quote

        data = get_quote(ticker)
        return QuoteResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {ticker}: {exc}")


@router.get("/history/{ticker}", response_model=list[OHLCVPoint])
async def get_history(
    ticker: str,
    period: str = Query("1y", description="Lookback period, e.g. 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    interval: str = Query("1d", description="Bar interval, e.g. 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo"),
) -> list[OHLCVPoint]:
    """Return historical OHLCV bars for *ticker*."""
    try:
        from backend.services.market_data import get_history

        rows = get_history(ticker, period=period, interval=interval)
        return [OHLCVPoint(**row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {ticker}: {exc}")


@router.get("/financials/{ticker}")
async def get_financials(ticker: str) -> dict:
    """Return financial statements (income, balance sheet, cash flow) as JSON."""
    try:
        from backend.services.financial_statements import get_financials

        return get_financials(ticker)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch financials for {ticker}: {exc}")


@router.post("/financials/{ticker}/export", response_model=FinancialsExportResponse)
async def export_financials(ticker: str) -> FinancialsExportResponse:
    """Export financial statements for *ticker* to an Excel file."""
    try:
        from backend.services.financial_statements import export

        result = export(ticker)
        return FinancialsExportResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed for {ticker}: {exc}")
