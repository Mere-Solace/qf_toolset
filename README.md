# QF Toolset

Python toolkit for fixed-income and macro-financial analysis, built for SMIF (Student Managed Investment Fund) research. Data sourced from FRED (Federal Reserve Economic Data) and yfinance.

## What's Here

**`tools/`** — core analytical library (~2,600 lines)

| Module | Purpose |
|--------|---------|
| `series.py` | `TimeSeries` and `Panel` — chainable containers with `.pct_change()`, `.rolling_vol()`, `.zscore()`, `.drawdown()`, `.pca()`, `.cointegration()` |
| `portfolio.py` | `Portfolio` — risk contribution, key-rate duration (empirical OLS), benchmark-relative metrics (TE, IR, alpha/beta), drawdown decomposition, rolling Sharpe |
| `securities.py` | `Ticker`, `FI_ETF`, `Equity`, `BondMath` — carry decomposition, rate sensitivity, duration/convexity/DV01, total return attribution |
| `charts.py` | `Chart` — composable multi-panel plots (time series, histogram, heatmap, percentile fan, regime shading) |
| `data.py` | `load_fred()`, `load_yfinance()`, `load_master()`, `align()` — unified loaders with local CSV caching |
| `excel.py` | `NotebookWorkbook`, `NotebookOutput` — idempotent Excel export with per-notebook output directories |
| `palette.py` | Named colour constants and gradient helpers (IB palette) |

**`models/`** — research notebooks by theme

```
treasuries_spring26/
  fisher_decomposition.ipynb   — nominal yield = real rate + breakeven + term premium (TIPS data)
  yield_vol_garch.ipynb        — GARCH(1,1) on 10Y yield volatility
  etf_analysis.ipynb           — carry/price decomposition, rate sensitivities across duration buckets
  etf_frontier.ipynb           — efficient frontier across SHY / IEF / TLT / BND
  portfolio_vs_benchmark.ipynb — core-bond vs. AGG: KRD profiles, risk contribution, active return
  treasuries_analysis.ipynb    — yield curve dynamics, spread analysis, term structure

macro_regimes_spring26/
  bvar.ipynb                   — Bayesian VAR (7 series, Minnesota prior, impulse responses, FEVD)
  hmm_regime_detection.ipynb   — Hidden Markov Model: expansion / slowdown / contraction regimes

portfolio_spring26/
  efficient-frontier.ipynb     — mean-variance optimization with weight constraints
  monte-carlo.ipynb            — GBM path simulation, percentile fan, tail risk
  portfolio_comparison.ipynb   — multi-portfolio comparison: drawdowns, rolling Sharpe, metrics

exploration/                   — past analyses (Phillips curve, stochastic processes, data overview)
```

**`scripts/`** — data automation

```
pull_fred.py          — incremental FRED pulls across 45+ series → CSV cache → Excel workbook
build_master_sheet.py — rebuild master_workbook.xlsx from cached CSVs (preserves user sheets)
pull_fiscal_data.py   — fiscal data pull (Treasury, CBO)
ypull.py              — yfinance price pull to CSV
```

**`config/series.json`** — 45 FRED series definitions across 9 categories (Treasury rates, spreads, inflation, employment, monetary, fiscal, growth, housing, credit)

## Data Flow

```
config/series.json
    ↓
scripts/pull_fred.py  (incremental API fetch)
    ↓
data/raw/fred/*.csv   (per-series, date + value, append-only)
    ↓
data/master_workbook.xlsx  (outer-joined, forward-filled, 9 sheets)
    ↓
models/**/*.ipynb → models/**/output/  (per-notebook Excel + plots)
```

## Setup

```bash
# Install
pip install -e .

# Configure
cp .env.example .env         # add FRED_API_KEY (https://fred.stlouisfed.org/docs/api/api_key.html)

# Pull data
python scripts/pull_fred.py          # incremental update
python scripts/pull_fred.py --full   # full re-sync from scratch
```

Requires Python 3.11+.
