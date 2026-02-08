# Financial Analysis Toolset

Full-stack financial analysis platform with Python backend, React frontend, and R analysis scripts.

## Features

- **Market Data** - Real-time quotes and historical data via Yahoo Finance
- **Macro Indicators** - FRED, BLS, and BEA data pipelines with automated ingestion
- **Option Pricing** - Black-Scholes, binomial tree, and Monte Carlo models with full Greeks
- **Statistical Analysis** - OLS regression and VAR models for macro/market relationships
- **Yield Curve** - Live and historical Treasury yield curve visualization
- **Data Pipeline** - Scheduled ingestion into SQLite with Excel export

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- R 4.x (optional, for R analysis scripts)

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys (FRED, BLS, BEA)

# Run database migration
python scripts/migrate_data.py

# Start the API server
uvicorn backend.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at http://localhost:5173 and proxies API calls to the backend at http://localhost:8000.

### R Analysis (Optional)

```bash
cd r_analysis
Rscript install_packages.R
Rscript regression_10yr.R
Rscript correlation/cci_pce.R
Rscript correlation/spy_bond.R
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market/quote/{ticker}` | Current quote |
| GET | `/api/market/history/{ticker}` | Historical OHLCV |
| POST | `/api/market/financials/{ticker}/export` | Export financials to Excel |
| GET | `/api/macro/yield-curve` | Current yield curve |
| GET | `/api/macro/indicators` | Key macro indicators |
| POST | `/api/options/black-scholes` | BS pricing + Greeks |
| POST | `/api/options/binomial` | Binomial tree pricing |
| POST | `/api/options/monte-carlo` | Monte Carlo pricing |
| POST | `/api/options/implied-vol` | Implied volatility solver |
| POST | `/api/analysis/regression/run` | Run regression analysis |
| POST | `/api/analysis/var/run` | Run VAR analysis |
| WS | `/api/ws/prices` | Live price stream |

## Project Structure

```
finance/
├── backend/          # FastAPI backend
│   ├── api/          # Route handlers
│   ├── models/       # SQLAlchemy ORM
│   ├── schemas/      # Pydantic models
│   ├── services/     # Data clients (FRED, BLS, BEA, Yahoo)
│   ├── pipeline/     # Scheduled data ingestion
│   ├── pricing/      # Option pricing models
│   └── analysis/     # Statistical analysis
├── frontend/         # React + Vite + TypeScript
├── r_analysis/       # R regression and correlation scripts
├── data/             # SQLite DB + raw CSVs
├── output/           # Plots and analysis results
├── scripts/          # CLI utilities
└── tests/            # pytest suite
```

## Running Tests

```bash
pytest tests/ -v
```
