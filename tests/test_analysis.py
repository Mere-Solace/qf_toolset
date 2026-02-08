"""Tests for analysis module."""
import pytest
import numpy as np
import pandas as pd
from backend.analysis.helpers import sanitize_col, significance_stars


class TestHelpers:
    def test_sanitize_col_basic(self):
        assert sanitize_col("10 Yr") == "X_10_Yr"

    def test_sanitize_col_special_chars(self):
        assert sanitize_col("CPI - AUCSL") == "CPI___AUCSL"

    def test_sanitize_col_leading_number(self):
        assert sanitize_col("2s-10s") == "X_2s_10s"

    def test_sanitize_col_clean(self):
        assert sanitize_col("FEDFUNDS") == "FEDFUNDS"

    def test_significance_stars_high(self):
        assert significance_stars(0.001) == "***"

    def test_significance_stars_medium(self):
        assert significance_stars(0.03) == "**"

    def test_significance_stars_low(self):
        assert significance_stars(0.08) == "*"

    def test_significance_stars_none(self):
        assert significance_stars(0.15) == ""
