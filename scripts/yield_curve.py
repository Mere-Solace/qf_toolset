"""Yield curve analysis.

Analyze the term structure of interest rates: PCA decomposition (level, slope,
curvature), historical comparison, inversion detection.

Data sources (from data/raw/fred/):
    - DGS3MO, DGS1, DGS2, DGS5, DGS10, DGS30: treasury rates
    - T10Y2Y, T10Y3M: spread measures
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# TODO: implement
