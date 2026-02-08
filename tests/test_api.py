"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_black_scholes_endpoint():
    payload = {"S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2, "option_type": "call"}
    response = client.post("/api/options/black-scholes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "price" in data
    assert abs(data["price"] - 10.45) < 0.1


def test_binomial_endpoint():
    payload = {
        "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
        "option_type": "call", "exercise": "european", "steps": 100,
    }
    response = client.post("/api/options/binomial", json=payload)
    assert response.status_code == 200
    assert "price" in response.json()


def test_monte_carlo_endpoint():
    payload = {
        "S": 100, "K": 100, "T": 1, "r": 0.05, "sigma": 0.2,
        "option_type": "call", "n_sims": 10000, "n_steps": 50,
        "variance_reduction": "antithetic",
    }
    response = client.post("/api/options/monte-carlo", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "price" in data
    assert "confidence_interval" in data


def test_implied_vol_endpoint():
    payload = {
        "market_price": 10.45, "S": 100, "K": 100, "T": 1,
        "r": 0.05, "option_type": "call",
    }
    response = client.post("/api/options/implied-vol", json=payload)
    assert response.status_code == 200
    assert "implied_vol" in response.json()


def test_data_series_endpoint():
    response = client.get("/api/data/series")
    assert response.status_code == 200


def test_macro_indicators():
    response = client.get("/api/macro/indicators")
    assert response.status_code == 200
