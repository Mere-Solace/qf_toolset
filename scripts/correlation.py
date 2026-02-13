"""Cross-series correlation and lag analysis.

Compute pairwise correlations between macro series, detect optimal lead/lag
relationships, and identify regime changes in correlations.

Data sources: any CSVs in data/raw/fred/
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# TODO: implement
