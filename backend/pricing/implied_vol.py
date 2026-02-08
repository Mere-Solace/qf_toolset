"""Implied volatility solver using Newton-Raphson with bisection fallback.

Recovers the volatility parameter that equates the Black-Scholes model
price to an observed market price.
"""

import numpy as np

from backend.pricing.black_scholes import black_scholes
from backend.pricing.utils import validate_option_type


def implied_vol(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    tol: float = 1e-8,
    max_iter: int = 100,
) -> float:
    """Compute implied volatility via Newton-Raphson with bisection fallback.

    Args:
        market_price: Observed market price of the option.
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized, continuous compounding).
        option_type: 'call' or 'put'.
        tol: Convergence tolerance for the price difference.
        max_iter: Maximum number of iterations for each method.

    Returns:
        Implied volatility as a float.

    Raises:
        ValueError: If inputs are invalid or no solution can be found.
    """
    option_type = validate_option_type(option_type)

    if market_price <= 0:
        raise ValueError(f"market_price must be positive, got {market_price}")
    if S <= 0:
        raise ValueError(f"Spot price S must be positive, got {S}")
    if K <= 0:
        raise ValueError(f"Strike price K must be positive, got {K}")
    if T <= 0:
        raise ValueError(f"Time to expiration T must be positive, got {T}")

    # Check arbitrage bounds
    discount = np.exp(-r * T)
    if option_type == "call":
        intrinsic = max(S - K * discount, 0.0)
        upper_bound = S
    else:
        intrinsic = max(K * discount - S, 0.0)
        upper_bound = K * discount

    if market_price < intrinsic - tol:
        raise ValueError(
            f"Market price {market_price} is below intrinsic value {intrinsic:.6f}. "
            "No valid implied volatility exists."
        )
    if market_price > upper_bound + tol:
        raise ValueError(
            f"Market price {market_price} exceeds the theoretical upper bound "
            f"{upper_bound:.6f}. No valid implied volatility exists."
        )

    # --- Brenner-Subrahmanyam initial guess ---
    sigma = np.sqrt(2.0 * np.pi / T) * market_price / S
    sigma = np.clip(sigma, 0.01, 5.0)

    # --- Newton-Raphson ---
    for _ in range(max_iter):
        result = black_scholes(S, K, T, r, sigma, option_type)
        price = result["price"]
        # Vega is returned per 1% move; convert back to per-unit
        vega = result["vega"] / 0.01

        diff = price - market_price

        if abs(diff) < tol:
            return float(sigma)

        if vega < 1e-12:
            # Vega too small for Newton step; break to bisection
            break

        sigma_new = sigma - diff / vega
        # Keep sigma in a reasonable range
        sigma_new = np.clip(sigma_new, 1e-6, 10.0)
        sigma = sigma_new
    else:
        # Newton converged within tolerance is handled above;
        # if we reach here, check one last time
        if abs(diff) < tol:
            return float(sigma)

    # --- Bisection fallback ---
    sigma_low = 1e-6
    sigma_high = 10.0

    # Verify bracket: price(sigma_low) should be < market_price < price(sigma_high)
    price_low = black_scholes(S, K, T, r, sigma_low, option_type)["price"]
    price_high = black_scholes(S, K, T, r, sigma_high, option_type)["price"]

    if not (price_low <= market_price <= price_high):
        raise ValueError(
            f"Cannot bracket implied volatility. BS price range "
            f"[{price_low:.6f}, {price_high:.6f}] does not contain "
            f"market price {market_price:.6f}."
        )

    for _ in range(max_iter):
        sigma_mid = 0.5 * (sigma_low + sigma_high)
        price_mid = black_scholes(S, K, T, r, sigma_mid, option_type)["price"]
        diff = price_mid - market_price

        if abs(diff) < tol or (sigma_high - sigma_low) < tol:
            return float(sigma_mid)

        if diff > 0:
            sigma_high = sigma_mid
        else:
            sigma_low = sigma_mid

    # Return best estimate after max iterations
    return float(0.5 * (sigma_low + sigma_high))
