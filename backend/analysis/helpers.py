"""Shared helper functions for statistical analysis modules."""

import re


def sanitize_col(name: str) -> str:
    """Convert a column name into a safe, lowercase, underscore-separated identifier.

    Args:
        name: Original column name (may contain spaces, special characters, etc.).

    Returns:
        Sanitized column name suitable for use as a variable or DataFrame column.
    """
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def significance_stars(p_value: float) -> str:
    """Return significance stars based on the p-value.

    Args:
        p_value: The p-value from a statistical test.

    Returns:
        '***' if p < 0.01, '**' if p < 0.05, '*' if p < 0.10, '' otherwise.
    """
    if p_value < 0.01:
        return "***"
    elif p_value < 0.05:
        return "**"
    elif p_value < 0.10:
        return "*"
    return ""
