"""Phillips Curve analysis: U.S. unemployment rate vs. CPI-derived inflation (1990–present).

Reads UNRATE and CPIAUCSL data from the project master workbook (or fetches
from FRED if a FRED_API_KEY is configured), computes 12-month log-difference
inflation, runs OLS, and produces two charts (time-series + scatter).
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import statsmodels.api as sm

# Use a terminal-friendly backend if available, otherwise Agg with savefig
try:
    matplotlib.use("module://matplotlib-backend-kitty")
except Exception:
    try:
        matplotlib.use("module://matplotlib-backend-sixel")
    except Exception:
        matplotlib.use("Agg")

# Allow importing from project lib/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

START = "1990-01-01"
WORKBOOK = os.path.join(os.path.dirname(__file__), "..", "data", "master_workbook.xlsx")


def load_from_workbook() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load unemployment and CPI data from the project master workbook."""
    # Unemployment from Employment sheet
    df_emp = pd.read_excel(WORKBOOK, sheet_name="Employment")
    df_emp.columns = ["date"] + list(df_emp.columns[1:])
    df_emp["date"] = pd.to_datetime(df_emp["date"], errors="coerce")
    df_unemp = df_emp[["date", "Unemployment Rate (%)"]].dropna()
    df_unemp.columns = ["date", "unemployment"]
    df_unemp["unemployment"] = pd.to_numeric(df_unemp["unemployment"], errors="coerce")

    # CPI from Inflation sheet
    df_inf = pd.read_excel(WORKBOOK, sheet_name="Inflation")
    df_inf.columns = ["date"] + list(df_inf.columns[1:])
    df_inf["date"] = pd.to_datetime(df_inf["date"], errors="coerce")
    df_cpi = df_inf[["date", "CPI All Urban (Index)"]].dropna()
    df_cpi.columns = ["date", "cpi"]
    df_cpi["cpi"] = pd.to_numeric(df_cpi["cpi"], errors="coerce")
    df_cpi = df_cpi.dropna()

    return df_unemp, df_cpi


def load_from_fred() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch data directly from FRED API (requires FRED_API_KEY in .env)."""
    from lib.fred_client import get_series

    df_unemp = get_series("UNRATE", start_date="1989-01-01")
    df_unemp.rename(columns={"value": "unemployment"}, inplace=True)
    df_unemp["date"] = pd.to_datetime(df_unemp["date"])

    df_cpi = get_series("CPIAUCSL", start_date="1989-01-01")
    df_cpi.rename(columns={"value": "cpi"}, inplace=True)
    df_cpi["date"] = pd.to_datetime(df_cpi["date"])

    return df_unemp, df_cpi


def main():
    # ------------------------------------------------------------------
    # 1. Load data (workbook preferred, FRED API as fallback)
    # ------------------------------------------------------------------
    if os.path.exists(WORKBOOK):
        print(f"Loading data from master workbook: {os.path.basename(WORKBOOK)}")
        df_unemp, df_cpi = load_from_workbook()
    else:
        print("Fetching data from FRED API...")
        df_unemp, df_cpi = load_from_fred()

    # ------------------------------------------------------------------
    # 2. Compute 12-month inflation: π_t = 100*(log(CPI_t) - log(CPI_{t-12}))
    # ------------------------------------------------------------------
    df_cpi = df_cpi.sort_values("date").reset_index(drop=True)
    df_cpi["log_cpi"] = np.log(df_cpi["cpi"])
    df_cpi["inflation"] = 100.0 * (df_cpi["log_cpi"] - df_cpi["log_cpi"].shift(12))
    df_cpi = df_cpi[["date", "inflation"]].dropna()
    df_cpi = df_cpi[df_cpi["date"] >= START]

    # Filter unemployment to 1990+
    df_unemp = df_unemp[df_unemp["date"] >= START]

    # ------------------------------------------------------------------
    # 3. Merge on date, dropping rows where inflation is missing
    # ------------------------------------------------------------------
    df = pd.merge(df_unemp, df_cpi, on="date", how="inner").dropna()
    df = df.sort_values("date").reset_index(drop=True)
    print(f"\nMerged dataset: {len(df)} monthly observations "
          f"({df['date'].min().strftime('%Y-%m')} to {df['date'].max().strftime('%Y-%m')})\n")

    # ------------------------------------------------------------------
    # 4. OLS regression: inflation = β0 + β1 * unemployment + ε
    # ------------------------------------------------------------------
    X = sm.add_constant(df["unemployment"])
    model = sm.OLS(df["inflation"], X).fit()

    b0, b1 = model.params
    se0, se1 = model.bse
    r2 = model.rsquared

    print("=" * 60)
    print("OLS Regression: inflation ~ unemployment")
    print("=" * 60)
    print(f"  Intercept (β₀):    {b0:8.4f}   (SE = {se0:.4f})")
    print(f"  Slope (β₁):        {b1:8.4f}   (SE = {se1:.4f})")
    print(f"  R²:                {r2:8.4f}")
    print(f"  N observations:    {int(model.nobs)}")
    print("=" * 60)
    print(f"\nInterpretation: A 1 percentage-point increase in the unemployment")
    print(f"rate is associated with a {b1:.3f} percentage-point change in the")
    print(f"12-month inflation rate (slope {'negative' if b1 < 0 else 'positive'}, "
          f"consistent with {'the Phillips Curve' if b1 < 0 else 'an unexpected positive relationship'}).")
    if abs(r2) < 0.15:
        print(f"The R² of {r2:.3f} is quite low, indicating that unemployment alone")
        print("explains only a small share of inflation variation in this period.")
    print()

    # ------------------------------------------------------------------
    # 5. Chart 1: Time-series with dual y-axes
    # ------------------------------------------------------------------
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    color_unemp = "#1f77b4"
    color_infl = "#d62728"

    ax1.set_xlabel("Date")
    ax1.set_ylabel("Unemployment Rate (%)", color=color_unemp)
    ax1.plot(df["date"], df["unemployment"], color=color_unemp, linewidth=1.2,
             label="Unemployment Rate")
    ax1.tick_params(axis="y", labelcolor=color_unemp)

    ax2 = ax1.twinx()
    ax2.set_ylabel("Inflation Rate (%)", color=color_infl)
    ax2.plot(df["date"], df["inflation"], color=color_infl, linewidth=1.2,
             label="12-Month Inflation")
    ax2.tick_params(axis="y", labelcolor=color_infl)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    ax1.set_title("U.S. Unemployment Rate and Inflation (1990–Present)")
    fig1.tight_layout()

    output_dir = os.path.dirname(__file__)
    os.makedirs(output_dir, exist_ok=True)

    ts_path = os.path.join(output_dir, "unemployment_inflation_timeseries.png")
    fig1.savefig(ts_path, dpi=150)
    print(f"Time-series chart saved to: {os.path.abspath(ts_path)}")

    try:
        plt.show()
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 6. Chart 2: Scatter plot with regression line
    # ------------------------------------------------------------------
    fig2, ax3 = plt.subplots(figsize=(8, 6))
    ax3.scatter(df["unemployment"], df["inflation"], alpha=0.4, s=18,
                color="#1f77b4", edgecolors="none", label="Monthly observations")

    x_line = np.linspace(df["unemployment"].min(), df["unemployment"].max(), 100)
    y_line = b0 + b1 * x_line
    ax3.plot(x_line, y_line, color="#d62728", linewidth=2, label="OLS fit")

    eq_text = (f"π = {b0:.2f} {'+' if b1 >= 0 else '−'} {abs(b1):.2f} × U\n"
               f"R² = {r2:.3f}")
    ax3.annotate(eq_text, xy=(0.05, 0.92), xycoords="axes fraction",
                 fontsize=11, verticalalignment="top",
                 bbox=dict(boxstyle="round,pad=0.4", fc="wheat", alpha=0.8))

    ax3.set_xlabel("Unemployment Rate (%)")
    ax3.set_ylabel("12-Month Inflation Rate (%)")
    ax3.set_title("Phillips Curve Scatter: Inflation vs. Unemployment (1990–Present)")
    ax3.legend(loc="upper right")
    fig2.tight_layout()

    sc_path = os.path.join(os.path.dirname(__file__), "unemployment_inflation_scatter.png")
    fig2.savefig(sc_path, dpi=150)
    print(f"Scatter chart saved to:     {os.path.abspath(sc_path)}")

    try:
        plt.show()
    except Exception:
        pass

    plt.close("all")


if __name__ == "__main__":
    main()
