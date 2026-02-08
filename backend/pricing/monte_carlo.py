"""Monte Carlo option pricing via Geometric Brownian Motion simulation.

Fully numpy-vectorized. Supports antithetic variates and control variate
variance reduction techniques.
"""

from typing import Optional

import numpy as np

from backend.pricing.utils import validate_inputs, validate_option_type


def _payoff(paths: np.ndarray, K: float, option_type: str) -> np.ndarray:
    """Compute terminal payoff for each path.

    Args:
        paths: Array of shape (n_sims, n_steps+1) with simulated price paths.
        K: Strike price.
        option_type: 'call' or 'put'.

    Returns:
        1-D array of payoffs of length n_sims.
    """
    terminal = paths[:, -1]
    if option_type == "call":
        return np.maximum(terminal - K, 0.0)
    return np.maximum(K - terminal, 0.0)


def _geometric_asian_payoff(paths: np.ndarray, K: float, option_type: str) -> np.ndarray:
    """Compute geometric average Asian option payoff for control variate.

    The geometric average has a closed-form price under GBM, making it a
    good control variate for path-dependent or vanilla Monte Carlo.

    Args:
        paths: Array of shape (n_sims, n_steps+1) with simulated price paths.
        K: Strike price.
        option_type: 'call' or 'put'.

    Returns:
        1-D array of geometric Asian payoffs.
    """
    # Geometric mean of prices along each path (excluding the initial price)
    log_prices = np.log(paths[:, 1:])
    geo_mean = np.exp(np.mean(log_prices, axis=1))
    if option_type == "call":
        return np.maximum(geo_mean - K, 0.0)
    return np.maximum(K - geo_mean, 0.0)


def _geometric_asian_closed_form(
    S: float, K: float, T: float, r: float, sigma: float, n_steps: int, option_type: str
) -> float:
    """Closed-form price of a geometric average Asian option under GBM.

    Used as the known expectation for the control variate.

    Args:
        S: Spot price.
        K: Strike.
        T: Time to expiry.
        r: Risk-free rate.
        sigma: Volatility.
        n_steps: Number of monitoring points.
        option_type: 'call' or 'put'.

    Returns:
        Closed-form geometric Asian option price.
    """
    from backend.pricing.utils import norm_cdf

    n = n_steps
    sigma_adj = sigma * np.sqrt((2 * n + 1) / (6 * (n + 1)))
    r_adj = 0.5 * (r - 0.5 * sigma ** 2 + sigma_adj ** 2)

    d1 = (np.log(S / K) + (r_adj + 0.5 * sigma_adj ** 2) * T) / (sigma_adj * np.sqrt(T))
    d2 = d1 - sigma_adj * np.sqrt(T)

    discount = np.exp(-r * T)
    if option_type == "call":
        price = discount * (S * np.exp(r_adj * T) * norm_cdf(d1) - K * norm_cdf(d2))
    else:
        price = discount * (K * norm_cdf(-d2) - S * np.exp(r_adj * T) * norm_cdf(-d1))

    return float(price)


def monte_carlo(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    n_sims: int = 100_000,
    n_steps: int = 252,
    variance_reduction: Optional[str] = "antithetic",
    seed: Optional[int] = None,
) -> dict:
    """Price a European option via Monte Carlo simulation of GBM paths.

    Args:
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized, continuous compounding).
        sigma: Volatility of the underlying (annualized).
        option_type: 'call' or 'put'.
        n_sims: Number of simulation paths. With antithetic variates the
                effective number of paths is 2 * n_sims.
        n_steps: Number of time steps per path (e.g. 252 for daily).
        variance_reduction: One of 'antithetic', 'control_variate', or None.
        seed: Random seed for reproducibility (optional).

    Returns:
        Dictionary with keys:
            price:               Discounted expected payoff (option price).
            std_error:           Standard error of the price estimate.
            confidence_interval: Tuple (lower, upper) for 95% CI.
            sample_paths:        List of 5 sample price paths (each a list of floats).

    Raises:
        ValueError: If inputs are invalid.
    """
    validate_inputs(S, K, T, r, sigma)
    option_type = validate_option_type(option_type)

    if variance_reduction is not None:
        variance_reduction = variance_reduction.lower().strip()
        if variance_reduction not in ("antithetic", "control_variate"):
            raise ValueError(
                f"variance_reduction must be 'antithetic', 'control_variate', or None, "
                f"got '{variance_reduction}'"
            )

    rng = np.random.default_rng(seed)
    dt = T / n_steps
    nudt = (r - 0.5 * sigma ** 2) * dt
    sig_sqrt_dt = sigma * np.sqrt(dt)

    # Generate standard normal increments: shape (n_sims, n_steps)
    Z = rng.standard_normal((n_sims, n_steps))

    # --- Build paths via vectorized cumulative sum of log-returns ---
    log_increments = nudt + sig_sqrt_dt * Z
    log_paths = np.concatenate(
        [np.zeros((n_sims, 1)), np.cumsum(log_increments, axis=1)], axis=1
    )
    paths = S * np.exp(log_paths)

    discount = np.exp(-r * T)

    if variance_reduction == "antithetic":
        # Mirror paths using -Z
        log_increments_anti = nudt - sig_sqrt_dt * Z
        log_paths_anti = np.concatenate(
            [np.zeros((n_sims, 1)), np.cumsum(log_increments_anti, axis=1)], axis=1
        )
        paths_anti = S * np.exp(log_paths_anti)

        payoffs_orig = _payoff(paths, K, option_type)
        payoffs_anti = _payoff(paths_anti, K, option_type)
        # Average paired payoffs to reduce variance
        payoffs = 0.5 * (payoffs_orig + payoffs_anti)
        discounted = discount * payoffs

    elif variance_reduction == "control_variate":
        payoffs_vanilla = _payoff(paths, K, option_type)
        payoffs_cv = _geometric_asian_payoff(paths, K, option_type)
        cv_true = _geometric_asian_closed_form(S, K, T, r, sigma, n_steps, option_type)

        # Optimal beta via covariance / variance
        cov_matrix = np.cov(payoffs_vanilla, payoffs_cv)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] > 0 else 0.0

        adjusted = payoffs_vanilla - beta * (payoffs_cv - cv_true)
        discounted = discount * adjusted

    else:
        # No variance reduction
        payoffs = _payoff(paths, K, option_type)
        discounted = discount * payoffs

    price = float(np.mean(discounted))
    std_error = float(np.std(discounted, ddof=1) / np.sqrt(len(discounted)))
    ci_lower = price - 1.96 * std_error
    ci_upper = price + 1.96 * std_error

    # Select 5 sample paths evenly spaced across simulations
    sample_indices = np.linspace(0, n_sims - 1, 5, dtype=int)
    sample_paths = [paths[i].tolist() for i in sample_indices]

    return {
        "price": price,
        "std_error": std_error,
        "confidence_interval": (float(ci_lower), float(ci_upper)),
        "sample_paths": sample_paths,
    }
