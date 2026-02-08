"""Option-pricing API router -- Black-Scholes, binomial, Monte Carlo, implied vol."""

import numpy as np
from fastapi import APIRouter, HTTPException

from backend.schemas.options import (
    BinomialRequest,
    BinomialResult,
    BlackScholesRequest,
    GreeksSurfaceRequest,
    ImpliedVolRequest,
    ImpliedVolResult,
    MonteCarloRequest,
    MonteCarloResult,
    PricingResult,
)

router = APIRouter(prefix="/options", tags=["options"])


@router.post("/black-scholes", response_model=PricingResult)
async def price_black_scholes(req: BlackScholesRequest) -> PricingResult:
    """Price a European option using the analytical Black-Scholes model."""
    try:
        from backend.pricing.black_scholes import black_scholes

        result = black_scholes(
            S=req.S, K=req.K, T=req.T, r=req.r, sigma=req.sigma, option_type=req.option_type,
        )
        return PricingResult(**result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/binomial", response_model=BinomialResult)
async def price_binomial(req: BinomialRequest) -> BinomialResult:
    """Price an option using the CRR binomial tree."""
    try:
        from backend.pricing.binomial import binomial_tree

        result = binomial_tree(
            S=req.S,
            K=req.K,
            T=req.T,
            r=req.r,
            sigma=req.sigma,
            option_type=req.option_type,
            exercise=req.exercise,
            steps=req.steps,
        )
        return BinomialResult(price=result["price"], delta=result["delta"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/monte-carlo", response_model=MonteCarloResult)
async def price_monte_carlo(req: MonteCarloRequest) -> MonteCarloResult:
    """Price an option using Monte-Carlo simulation."""
    try:
        from backend.pricing.monte_carlo import monte_carlo

        result = monte_carlo(
            S=req.S,
            K=req.K,
            T=req.T,
            r=req.r,
            sigma=req.sigma,
            option_type=req.option_type,
            n_sims=req.n_sims,
            n_steps=req.n_steps,
            variance_reduction=req.variance_reduction,
        )
        return MonteCarloResult(**result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/implied-vol", response_model=ImpliedVolResult)
async def compute_implied_vol(req: ImpliedVolRequest) -> ImpliedVolResult:
    """Solve for the implied volatility that matches the given market price."""
    try:
        from backend.pricing.implied_vol import implied_vol

        iv = implied_vol(
            market_price=req.market_price,
            S=req.S,
            K=req.K,
            T=req.T,
            r=req.r,
            option_type=req.option_type,
        )
        return ImpliedVolResult(implied_vol=iv)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/greeks-surface")
async def greeks_surface(
    S: float,
    K_min: float,
    K_max: float,
    K_steps: int = 20,
    T_min: float = 0.1,
    T_max: float = 2.0,
    T_steps: int = 20,
    r: float = 0.05,
    sigma: float = 0.2,
    option_type: str = "call",
) -> dict:
    """Generate a 2-D grid of Greeks over strike and time-to-expiry dimensions.

    Returns a dictionary with arrays for strikes, maturities, and a nested
    grid of Greeks at each (K, T) point.
    """
    try:
        from backend.pricing.black_scholes import black_scholes

        strikes = np.linspace(K_min, K_max, K_steps).tolist()
        maturities = np.linspace(T_min, T_max, T_steps).tolist()

        grid: list[list[dict]] = []
        for t_val in maturities:
            row: list[dict] = []
            for k_val in strikes:
                result = black_scholes(S=S, K=k_val, T=t_val, r=r, sigma=sigma, option_type=option_type)
                row.append(result)
            grid.append(row)

        return {
            "strikes": strikes,
            "maturities": maturities,
            "grid": grid,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
