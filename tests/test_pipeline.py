"""Tests for data pipeline components."""
import pytest
from unittest.mock import patch, MagicMock
from backend.services.fred_client import get_series as fred_get_series
from backend.services.bls_client import get_series as bls_get_series


class TestFredClient:
    @patch("backend.services.fred_client.Fred")
    def test_get_series(self, mock_fred_cls):
        import pandas as pd
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = pd.Series(
            [4.5, 4.6], index=pd.to_datetime(["2024-01-01", "2024-02-01"])
        )
        mock_fred_cls.return_value = mock_fred

        df = fred_get_series("DGS10", "2024-01-01", "2024-02-01")
        assert len(df) == 2
        mock_fred.get_series.assert_called_once()


class TestBLSClient:
    @patch("backend.services.bls_client.requests.post")
    def test_get_series(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [{
                    "seriesID": "CES0000000001",
                    "data": [
                        {"year": "2024", "period": "M01", "value": "157000"},
                        {"year": "2024", "period": "M02", "value": "158000"},
                    ]
                }]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        df = bls_get_series(["CES0000000001"], 2024, 2024)
        assert len(df) == 2
