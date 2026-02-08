"""Tests for option pricing module."""
import math
import pytest
from backend.pricing.black_scholes import black_scholes
from backend.pricing.binomial import binomial_tree
from backend.pricing.monte_carlo import monte_carlo
from backend.pricing.implied_vol import implied_vol


# Known BS values: S=100, K=100, T=1, r=0.05, sigma=0.2
# Call ~10.4506, Put ~5.5735
BS_CALL = 10.4506
BS_PUT = 5.5735
TOL = 0.01  # 1 cent tolerance for BS
MC_TOL = 0.15  # wider for Monte Carlo


class TestBlackScholes:
    def test_call_price(self):
        result = black_scholes(100, 100, 1, 0.05, 0.2, "call")
        assert abs(result["price"] - BS_CALL) < TOL

    def test_put_price(self):
        result = black_scholes(100, 100, 1, 0.05, 0.2, "put")
        assert abs(result["price"] - BS_PUT) < TOL

    def test_put_call_parity(self):
        call = black_scholes(100, 100, 1, 0.05, 0.2, "call")
        put = black_scholes(100, 100, 1, 0.05, 0.2, "put")
        # C - P = S - K*exp(-rT)
        lhs = call["price"] - put["price"]
        rhs = 100 - 100 * math.exp(-0.05)
        assert abs(lhs - rhs) < 1e-6

    def test_greeks_present(self):
        result = black_scholes(100, 100, 1, 0.05, 0.2, "call")
        for key in ["price", "delta", "gamma", "theta", "vega", "rho"]:
            assert key in result

    def test_call_delta_range(self):
        result = black_scholes(100, 100, 1, 0.05, 0.2, "call")
        assert 0 < result["delta"] < 1

    def test_put_delta_range(self):
        result = black_scholes(100, 100, 1, 0.05, 0.2, "put")
        assert -1 < result["delta"] < 0

    def test_gamma_positive(self):
        result = black_scholes(100, 100, 1, 0.05, 0.2, "call")
        assert result["gamma"] > 0

    def test_vega_positive(self):
        result = black_scholes(100, 100, 1, 0.05, 0.2, "call")
        assert result["vega"] > 0

    def test_deep_itm_call(self):
        result = black_scholes(150, 100, 1, 0.05, 0.2, "call")
        intrinsic = 150 - 100 * math.exp(-0.05)
        assert result["price"] > intrinsic

    def test_deep_otm_call(self):
        result = black_scholes(50, 100, 1, 0.05, 0.2, "call")
        assert result["price"] < 1.0


class TestBinomial:
    def test_european_call_converges_to_bs(self):
        result = binomial_tree(100, 100, 1, 0.05, 0.2, "call", "european", 500)
        assert abs(result["price"] - BS_CALL) < 0.05

    def test_european_put_converges_to_bs(self):
        result = binomial_tree(100, 100, 1, 0.05, 0.2, "put", "european", 500)
        assert abs(result["price"] - BS_PUT) < 0.05

    def test_american_put_geq_european(self):
        eur = binomial_tree(100, 100, 1, 0.05, 0.2, "put", "european", 200)
        ame = binomial_tree(100, 100, 1, 0.05, 0.2, "put", "american", 200)
        assert ame["price"] >= eur["price"] - 1e-6

    def test_american_call_equals_european(self):
        # No dividends: American call = European call
        eur = binomial_tree(100, 100, 1, 0.05, 0.2, "call", "european", 200)
        ame = binomial_tree(100, 100, 1, 0.05, 0.2, "call", "american", 200)
        assert abs(ame["price"] - eur["price"]) < 0.05


class TestMonteCarlo:
    def test_call_price(self):
        result = monte_carlo(100, 100, 1, 0.05, 0.2, "call", 200000, 252, "antithetic")
        assert abs(result["price"] - BS_CALL) < MC_TOL

    def test_put_price(self):
        result = monte_carlo(100, 100, 1, 0.05, 0.2, "put", 200000, 252, "antithetic")
        assert abs(result["price"] - BS_PUT) < MC_TOL

    def test_confidence_interval(self):
        result = monte_carlo(100, 100, 1, 0.05, 0.2, "call", 100000, 252, "antithetic")
        ci = result["confidence_interval"]
        assert ci[0] < result["price"] < ci[1]

    def test_sample_paths_returned(self):
        result = monte_carlo(100, 100, 1, 0.05, 0.2, "call", 10000, 50, "antithetic")
        assert len(result["sample_paths"]) == 5
        assert len(result["sample_paths"][0]) == 51  # n_steps + 1


class TestImpliedVol:
    def test_recovers_known_vol(self):
        # Price an option with sigma=0.2, then recover it
        bs = black_scholes(100, 100, 1, 0.05, 0.2, "call")
        iv = implied_vol(bs["price"], 100, 100, 1, 0.05, "call")
        assert abs(iv - 0.2) < 1e-4

    def test_put_iv(self):
        bs = black_scholes(100, 100, 1, 0.05, 0.3, "put")
        iv = implied_vol(bs["price"], 100, 100, 1, 0.05, "put")
        assert abs(iv - 0.3) < 1e-4
