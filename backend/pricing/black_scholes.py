"""Black-Scholes option pricing with analytical Greeks.

Implements the closed-form Black-Scholes-Merton model for European options
on non-dividend-paying underlyings. All Greeks are computed analytically.
"""

import numpy as np

from backend.pricing.utils import (
    d1,
    d2,
    norm_cdf,
    norm_pdf,
    validate_inputs,
    validate_option_type,
)


def black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> dict:
    """Price a European option using the Black-Scholes formula with analytical Greeks.

    Args:
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized, continuous compounding).
        sigma: Volatility of the underlying (annualized).
        option_type: 'call' or 'put'.

    Returns:
        Dictionary with keys:
            price: Option price.
            delta: dV/dS, sensitivity to underlying price.
            gamma: d^2V/dS^2, sensitivity of delta to underlying price.
            theta: dV/dT (per calendar day), sensitivity to time decay.
            vega:  dV/d(sigma) (per 1% move), sensitivity to volatility.
            rho:   dV/dr (per 1% move), sensitivity to interest rate.

    Raises:
        ValueError: If inputs are invalid.
    """
    validate_inputs(S, K, T, r, sigma)
    option_type = validate_option_type(option_type)

    d1_val = d1(S, K, T, r, sigma)
    d2_val = d2(S, K, T, r, sigma)
    sqrt_T = np.sqrt(T)
    discount = np.exp(-r * T)

    # --- Price ---
    if option_type == "call":
        price = S * norm_cdf(d1_val) - K * discount * norm_cdf(d2_val)
    else:
        price = K * discount * norm_cdf(-d2_val) - S * norm_cdf(-d1_val)

    # --- Delta ---
    if option_type == "call":
        delta = norm_cdf(d1_val)
    else:
        delta = norm_cdf(d1_val) - 1.0

    # --- Gamma (same for call and put) ---
    gamma = norm_pdf(d1_val) / (S * sigma * sqrt_T)

    # --- Theta ---
    # Common term: -(S * sigma * N'(d1)) / (2 * sqrt(T))
    theta_common = -(S * norm_pdf(d1_val) * sigma) / (2.0 * sqrt_T)
    if option_type == "call":
        theta = theta_common - r * K * discount * norm_cdf(d2_val)
    else:
        theta = theta_common + r * K * discount * norm_cdf(-d2_val)
    # Convert from per-year to per-calendar-day
    theta = theta / 365.0

    # --- Vega (same for call and put) ---
    # dV/d(sigma), scaled to per 1% (0.01) change in volatility
    vega = S * norm_pdf(d1_val) * sqrt_T * 0.01

    # --- Rho ---
    # dV/dr, scaled to per 1% (0.01) change in rate
    if option_type == "call":
        rho = K * T * discount * norm_cdf(d2_val) * 0.01
    else:
        rho = -K * T * discount * norm_cdf(-d2_val) * 0.01

    return {
        "price": float(price),
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta),
        "vega": float(vega),
        "rho": float(rho),
    }
