"""OLS regression analysis on financial time-series data."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import statsmodels.api as sm

from backend.analysis.helpers import sanitize_col, significance_stars

logger = logging.getLogger(__name__)


def run_regression(
    y: pd.Series,
    X: pd.DataFrame,
    add_constant: bool = True,
) -> dict[str, Any]:
    """Run an OLS regression and return structured results.

    Args:
        y: Dependent variable series.
        X: Independent variable(s) DataFrame.
        add_constant: Whether to add a constant (intercept) term.

    Returns:
        Dictionary containing coefficients, p-values, R-squared, and the
        full statsmodels summary text.
    """
    if add_constant:
        X = sm.add_constant(X)

    model = sm.OLS(y, X, missing="drop")
    results = model.fit()

    coefficients: dict[str, dict[str, Any]] = {}
    for name in results.params.index:
        coefficients[name] = {
            "coefficient": float(results.params[name]),
            "std_error": float(results.bse[name]),
            "t_stat": float(results.tvalues[name]),
            "p_value": float(results.pvalues[name]),
            "significance": significance_stars(float(results.pvalues[name])),
        }

    return {
        "r_squared": float(results.rsquared),
        "adj_r_squared": float(results.rsquared_adj),
        "f_statistic": float(results.fvalue),
        "f_p_value": float(results.f_pvalue),
        "n_obs": int(results.nobs),
        "coefficients": coefficients,
        "summary": results.summary().as_text(),
    }


def run_all_regressions(
    csv_path: str | Path,
    out_dir: str | Path = "output",
) -> dict[str, Any]:
    """Run pairwise regressions for all numeric columns against the first column.

    Reads a CSV file where the first numeric column is treated as the dependent
    variable and all other numeric columns are used as independent variables
    (one at a time, simple regressions).

    Args:
        csv_path: Path to the input CSV with a date column and numeric columns.
        out_dir: Directory to save results CSV.

    Returns:
        Dictionary mapping each independent variable name to its regression results.
    """
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path, parse_dates=[0])
    df.columns = [sanitize_col(c) for c in df.columns]

    # Drop the date column and work with numeric columns only
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if len(numeric_cols) < 2:
        logger.warning("Need at least 2 numeric columns for regression; found %d", len(numeric_cols))
        return {}

    dep_var = numeric_cols[0]
    indep_vars = numeric_cols[1:]

    all_results: dict[str, Any] = {}
    summary_rows: list[dict[str, Any]] = []

    for iv in indep_vars:
        subset = df[[dep_var, iv]].dropna()
        if len(subset) < 3:
            logger.warning("Skipping %s -- too few observations (%d)", iv, len(subset))
            continue

        result = run_regression(subset[dep_var], subset[[iv]])
        all_results[iv] = result

        # Build summary row
        coeff_info = result["coefficients"].get(iv, {})
        summary_rows.append(
            {
                "independent_var": iv,
                "coefficient": coeff_info.get("coefficient"),
                "p_value": coeff_info.get("p_value"),
                "significance": coeff_info.get("significance"),
                "r_squared": result["r_squared"],
                "n_obs": result["n_obs"],
            }
        )

    # Save summary to CSV
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        summary_path = out_dir / "regression_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        logger.info("Regression summary saved to %s", summary_path)

    return all_results
