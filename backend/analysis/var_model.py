"""Vector Autoregression (VAR) analysis on financial time-series data."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from statsmodels.tsa.api import VAR

from backend.analysis.helpers import sanitize_col

logger = logging.getLogger(__name__)


def run_var_analysis(
    csv_path: str | Path,
    out_dir: str | Path = "output/var_results",
    max_lags: int | None = None,
    ic: str = "aic",
) -> dict[str, Any]:
    """Fit a VAR model to time-series data and return diagnostics and forecasts.

    Reads a CSV file, selects numeric columns, differences the data if needed
    for stationarity, selects the optimal lag order, fits the model, and
    produces impulse response functions and forecast error variance decompositions.

    Args:
        csv_path: Path to the input CSV with a date column and numeric columns.
        out_dir: Directory to save output files (IRF plots, FEVD tables).
        max_lags: Maximum number of lags to test. If None, statsmodels picks a default.
        ic: Information criterion for lag selection ('aic', 'bic', 'hqic', 'fpe').

    Returns:
        Dictionary with keys:
            - lag_order: selected lag order
            - aic / bic / hqic / fpe: information criterion values
            - granger_causality: pairwise Granger causality test results
            - irf: impulse response function data (dict of arrays)
            - fevd: forecast error variance decomposition (dict of DataFrames)
            - summary: model summary text
    """
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path, parse_dates=[0], index_col=0)
    df.columns = [sanitize_col(c) for c in df.columns]

    # Keep only numeric columns
    df = df.select_dtypes(include="number").dropna()
    if df.shape[1] < 2:
        raise ValueError("VAR requires at least 2 numeric series; found %d" % df.shape[1])

    # Difference the data to address non-stationarity
    df_diff = df.diff().dropna()

    # Fit VAR model
    model = VAR(df_diff)

    # Select lag order
    lag_selection = model.select_order(maxlags=max_lags)
    selected_lag = getattr(lag_selection, ic, 1)
    if selected_lag is None or selected_lag < 1:
        selected_lag = 1
    # select_order returns a LagOrderResults; get the recommended lag count
    try:
        selected_lag = lag_selection.selected_orders[ic]
    except (AttributeError, KeyError):
        selected_lag = 1

    logger.info("Selected VAR lag order: %d (by %s)", selected_lag, ic)

    results = model.fit(maxlags=selected_lag)

    # Impulse Response Functions
    irf = results.irf(periods=20)
    irf_data: dict[str, list] = {}
    for i, col in enumerate(df_diff.columns):
        irf_data[col] = irf.irfs[:, :, i].tolist()

    # Save IRF plot
    try:
        fig = irf.plot(orth=False)
        fig.savefig(str(out_dir / "irf_plot.png"), dpi=150, bbox_inches="tight")
        logger.info("IRF plot saved to %s", out_dir / "irf_plot.png")
    except Exception:
        logger.warning("Could not save IRF plot", exc_info=True)

    # Forecast Error Variance Decomposition
    fevd = results.fevd(periods=20)
    fevd_data: dict[str, pd.DataFrame] = {}
    for i, col in enumerate(df_diff.columns):
        fevd_df = pd.DataFrame(
            fevd.decomp[i],
            columns=df_diff.columns.tolist(),
        )
        fevd_df.index.name = "period"
        fevd_data[col] = fevd_df
        fevd_df.to_csv(out_dir / f"fevd_{col}.csv")

    # Granger causality tests
    granger_results: dict[str, dict[str, Any]] = {}
    for caused in df_diff.columns:
        for causing in df_diff.columns:
            if caused == causing:
                continue
            try:
                test = results.test_causality(caused, [causing], kind="f")
                granger_results[f"{causing}->{caused}"] = {
                    "f_stat": float(test.test_statistic),
                    "p_value": float(test.pvalue),
                    "df": test.df,
                }
            except Exception:
                logger.debug(
                    "Granger causality test failed for %s -> %s",
                    causing,
                    caused,
                    exc_info=True,
                )

    return {
        "lag_order": selected_lag,
        "aic": float(results.aic),
        "bic": float(results.bic),
        "hqic": float(results.hqic),
        "fpe": float(results.fpe),
        "granger_causality": granger_results,
        "irf": irf_data,
        "fevd": {k: v.to_dict() for k, v in fevd_data.items()},
        "summary": str(results.summary()),
    }
