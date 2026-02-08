"""Top-level API router that aggregates all sub-routers."""

from fastapi import APIRouter

from backend.api.analysis import router as analysis_router
from backend.api.data import router as data_router
from backend.api.macro import router as macro_router
from backend.api.market import router as market_router
from backend.api.options import router as options_router
from backend.api.ws import router as ws_router

api_router = APIRouter()

api_router.include_router(market_router)
api_router.include_router(macro_router)
api_router.include_router(options_router)
api_router.include_router(analysis_router)
api_router.include_router(data_router)
api_router.include_router(ws_router)
