"""Cox-Ross-Rubinstein binomial tree option pricing.

Supports European and American exercise for calls and puts.
Uses numpy for efficient backward induction through the tree.
"""

import numpy as np

from backend.pricing.utils import validate_inputs, validate_option_type


def binomial_tree(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    exercise: str = "european",
    steps: int = 100,
) -> dict:
    """Price an option using the CRR binomial tree model.

    Args:
        S: Current underlying price.
        K: Strike price.
        T: Time to expiration in years.
        r: Risk-free interest rate (annualized, continuous compounding).
        sigma: Volatility of the underlying (annualized).
        option_type: 'call' or 'put'.
        exercise: 'european' or 'american'.
        steps: Number of time steps in the tree.

    Returns:
        Dictionary with keys:
            price: Option price.
            delta: First-order Greek approximated from the first step of the tree.
            tree:  Dictionary containing the full stock and option price trees
                   as 1-D arrays at each time step (list of arrays).

    Raises:
        ValueError: If inputs are invalid.
    """
    validate_inputs(S, K, T, r, sigma)
    option_type = validate_option_type(option_type)

    exercise = exercise.lower().strip()
    if exercise not in ("european", "american"):
        raise ValueError(f"exercise must be 'european' or 'american', got '{exercise}'")
    if steps < 1:
        raise ValueError(f"steps must be >= 1, got {steps}")

    dt = T / steps

    # CRR parameterization
    u = np.exp(sigma * np.sqrt(dt))
    d = 1.0 / u
    disc = np.exp(-r * dt)
    p = (np.exp(r * dt) - d) / (u - d)  # risk-neutral up probability

    # --- Build terminal stock prices ---
    # At step N, node j has stock price S * u^j * d^(N-j)
    j = np.arange(steps + 1)
    stock_terminal = S * u ** (2 * j - steps)

    # --- Terminal payoff ---
    if option_type == "call":
        option_values = np.maximum(stock_terminal - K, 0.0)
    else:
        option_values = np.maximum(K - stock_terminal, 0.0)

    # Store trees if desired (only store a few levels for large trees)
    store_full = steps <= 500
    stock_tree = []
    option_tree = []

    if store_full:
        stock_tree.append(stock_terminal.copy())
        option_tree.append(option_values.copy())

    # --- Backward induction ---
    for i in range(steps - 1, -1, -1):
        # Discounted expected value under risk-neutral measure
        option_values = disc * (p * option_values[1:] + (1 - p) * option_values[:-1])

        # American exercise: check early exercise at each node
        if exercise == "american":
            j_i = np.arange(i + 1)
            stock_i = S * u ** (2 * j_i - i)
            if option_type == "call":
                intrinsic = np.maximum(stock_i - K, 0.0)
            else:
                intrinsic = np.maximum(K - stock_i, 0.0)
            option_values = np.maximum(option_values, intrinsic)

        if store_full:
            stock_tree.append(
                S * u ** (2 * np.arange(i + 1) - i)
            )
            option_tree.append(option_values.copy())

    price = float(option_values[0])

    # --- Delta from the first step ---
    S_up = S * u
    S_down = S * d
    # Recompute option values at step 1 for delta
    # We can get them from backward induction; they were the values at i=1
    # But it is simpler to just re-derive from stored tree or re-price sub-trees.
    # Use the one-step values: discount the terminal payoff one step back would give
    # the values at step 1, but we already overwrote them. Re-derive:
    j1 = np.arange(steps + 1)
    stock_t = S * u ** (2 * j1 - steps)
    if option_type == "call":
        payoff = np.maximum(stock_t - K, 0.0)
    else:
        payoff = np.maximum(K - stock_t, 0.0)

    vals = payoff.copy()
    for i in range(steps - 1, 0, -1):
        vals = disc * (p * vals[1:] + (1 - p) * vals[:-1])
        if exercise == "american":
            j_i = np.arange(i + 1)
            stock_i = S * u ** (2 * j_i - i)
            if option_type == "call":
                intrinsic = np.maximum(stock_i - K, 0.0)
            else:
                intrinsic = np.maximum(K - stock_i, 0.0)
            vals = np.maximum(vals, intrinsic)

    # vals now has 2 elements: V(up) and V(down) at step 1
    delta = float((vals[1] - vals[0]) / (S_up - S_down))

    # Reverse stored trees so index 0 is t=0
    if store_full:
        stock_tree.reverse()
        option_tree.reverse()

    return {
        "price": price,
        "delta": delta,
        "tree": {
            "stock": stock_tree if store_full else [],
            "option": option_tree if store_full else [],
        },
    }
