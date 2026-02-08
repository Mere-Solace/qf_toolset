"""Pydantic schemas for option-pricing endpoints."""

from pydantic import BaseModel


class BlackScholesRequest(BaseModel):
    """Inputs for the Black-Scholes analytical pricer."""

    S: float  # spot price
    K: float  # strike
    T: float  # time to expiry (years)
    r: float  # risk-free rate
    sigma: float  # volatility
    option_type: str = "call"


class PricingResult(BaseModel):
    """Black-Scholes price and full set of analytical Greeks."""

    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class BinomialRequest(BlackScholesRequest):
    """Inputs for the CRR binomial-tree pricer."""

    exercise: str = "european"
    steps: int = 100


class BinomialResult(BaseModel):
    """Binomial-tree pricing output."""

    price: float
    delta: float


class MonteCarloRequest(BlackScholesRequest):
    """Inputs for the Monte-Carlo option pricer."""

    n_sims: int = 100000
    n_steps: int = 252
    variance_reduction: str = "antithetic"


class MonteCarloResult(BaseModel):
    """Monte-Carlo pricing output with uncertainty metrics."""

    price: float
    std_error: float
    confidence_interval: list[float]
    sample_paths: list[list[float]]


class ImpliedVolRequest(BaseModel):
    """Inputs for the implied-volatility solver."""

    market_price: float
    S: float
    K: float
    T: float
    r: float
    option_type: str = "call"


class ImpliedVolResult(BaseModel):
    """Implied-volatility solver output."""

    implied_vol: float


class GreeksSurfaceRequest(BaseModel):
    """Inputs for generating a 2-D Greeks surface over strike and maturity."""

    S: float
    K_min: float
    K_max: float
    K_steps: int = 20
    T_min: float = 0.1
    T_max: float = 2.0
    T_steps: int = 20
    r: float = 0.05
    sigma: float = 0.2
    option_type: str = "call"
