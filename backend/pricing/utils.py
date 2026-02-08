"""Shared mathematical utilities for option pricing models."""

import numpy as np
from scipy.stats import norm


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function.

    Args:
        x: Value at which to evaluate the CDF.

    Returns:
        Probability that a standard normal variable is less than or equal to x.
    """
    return float(norm.cdf(x))


def norm_pdf(x: float) -> float:
    """Standard normal probability density function.

    Args:
        x: Value at which to evaluate the PDF.

    Returns:
        Density of the standard normal distribution at x.
    """
    return float(norm.pdf(x))


def d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Compute the Black-Scholes d1 parameter.

    Args:
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized, continuous).
        sigma: Volatility (annualized).

    Returns:
        The d1 value used in Black-Scholes formulas.
    """
    return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))


def d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Compute the Black-Scholes d2 parameter.

    Args:
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized, continuous).
        sigma: Volatility (annualized).

    Returns:
        The d2 value used in Black-Scholes formulas.
    """
    return d1(S, K, T, r, sigma) - sigma * np.sqrt(T)


def validate_inputs(S: float, K: float, T: float, r: float, sigma: float) -> None:
    """Validate common option pricing inputs.

    Args:
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate.
        sigma: Volatility.

    Raises:
        ValueError: If any input is invalid.
    """
    if S <= 0:
        raise ValueError(f"Spot price S must be positive, got {S}")
    if K <= 0:
        raise ValueError(f"Strike price K must be positive, got {K}")
    if T <= 0:
        raise ValueError(f"Time to expiration T must be positive, got {T}")
    if sigma <= 0:
        raise ValueError(f"Volatility sigma must be positive, got {sigma}")


def validate_option_type(option_type: str) -> str:
    """Normalize and validate option type string.

    Args:
        option_type: 'call' or 'put' (case-insensitive).

    Returns:
        Lowercased option type string.

    Raises:
        ValueError: If option_type is not 'call' or 'put'.
    """
    option_type = option_type.lower().strip()
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got '{option_type}'")
    return option_type
