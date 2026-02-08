"""WebSocket endpoint for streaming live price updates."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)

# Tickers streamed to every connected client.
_WATCH_TICKERS = ["SPY", "GLD", "^TNX"]
_UPDATE_INTERVAL_SECONDS = 5


async def _fetch_prices(tickers: list[str]) -> list[dict]:
    """Fetch the latest prices for *tickers* via yfinance (run in a thread)."""
    import yfinance as yf

    loop = asyncio.get_running_loop()

    def _get() -> list[dict]:
        results: list[dict] = []
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                info = t.fast_info
                results.append(
                    {
                        "ticker": ticker,
                        "price": float(info.last_price) if info.last_price else 0.0,
                        "previous_close": float(info.previous_close) if info.previous_close else 0.0,
                    }
                )
            except Exception:
                results.append({"ticker": ticker, "price": 0.0, "previous_close": 0.0})
        return results

    return await loop.run_in_executor(None, _get)


@router.websocket("/prices")
async def price_stream(ws: WebSocket) -> None:
    """Stream live price updates for a fixed watchlist every few seconds.

    The client receives a JSON array of ``{ticker, price, previous_close}``
    objects on each tick.
    """
    await ws.accept()
    logger.info("WebSocket client connected for price stream")

    try:
        while True:
            prices = await _fetch_prices(_WATCH_TICKERS)
            await ws.send_text(json.dumps(prices))
            await asyncio.sleep(_UPDATE_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("Unexpected error in WebSocket price stream")
        await ws.close(code=1011)
