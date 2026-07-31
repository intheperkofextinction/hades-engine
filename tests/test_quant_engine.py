import pytest
import numpy as np
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_engine.monte_carlo_engine import calculate_var_cvar, simulate_gbm_paths


class TestMonteCarloEngine:

    def test_var_cvar_known_distribution(self):
        """Test VaR and CVaR calculations against a known deterministic return array."""
        # 100 evenly spaced returns from -10% (-0.10) to +10% (+0.10)
        returns = np.linspace(-0.10, 0.10, 100)
        
        # At 95% confidence, VaR should isolate the lowest 5% quantile
        var_95, cvar_95 = calculate_var_cvar(returns, confidence_level=0.95)
        
        # 5th percentile of [-0.10 ... 0.10] is approximately -0.09
        assert var_95 < 0, "VaR should represent a negative return threshold"
        assert var_95 == pytest.approx(-0.0905, abs=1e-3)
        
        # CVaR (Expected Shortfall) must be strictly equal to or worse (more negative) than VaR
        assert cvar_95 <= var_95, "CVaR must be worse than or equal to VaR"

    def test_cvar_always_worse_than_var(self):
        """Property-based test: CVaR must always be <= VaR across random normal distributions."""
        np.random.seed(42)
        returns = np.random.normal(loc=0.001, scale=0.02, size=5000)
        
        var_95, cvar_95 = calculate_var_cvar(returns, confidence_level=0.95)
        assert cvar_95 <= var_95

    def test_invalid_confidence_level_raises_error(self):
        """Edge case test: Invalid confidence levels (>1 or <0) must raise ValueError."""
        returns = np.array([-0.05, 0.01, 0.02])
        
        with pytest.raises(ValueError, match="Confidence level must be strictly between 0 and 1"):
            calculate_var_cvar(returns, confidence_level=1.5)
            
        with pytest.raises(ValueError, match="Confidence level must be strictly between 0 and 1"):
            calculate_var_cvar(returns, confidence_level=-0.1)

    def test_empty_returns_raises_error(self):
        """Edge case test: Empty return array must raise ValueError."""
        empty_returns = np.array([])
        with pytest.raises(ValueError, match="Portfolio returns array cannot be empty"):
            calculate_var_cvar(empty_returns, confidence_level=0.95)

    def test_gbm_simulation_shape_and_values(self):
        """Test Geometric Brownian Motion simulator path shape and non-negativity."""
        S0 = 100.0
        mu = 0.05
        sigma = 0.20
        days = 30
        num_paths = 1000
        
        paths = simulate_gbm_paths(S0=S0, mu=mu, sigma=sigma, days=days, num_paths=num_paths)
        
        # Check matrix dimensions: (1000 paths, 30 days)
        assert paths.shape == (num_paths, days)
        
        # Asset prices under GBM can never be negative or NaN
        assert np.all(paths > 0), "Simulated asset prices must remain positive"
        assert not np.isnan(paths).any(), "Simulated path values must not contain NaNs"

    def test_gbm_invalid_inputs(self):
        """Edge case test: Non-positive starting prices or negative volatilities must fail."""
        with pytest.raises(ValueError, match="Initial price S0 must be greater than zero"):
            simulate_gbm_paths(S0=-50.0, mu=0.05, sigma=0.20)
            
        with pytest.raises(ValueError, match="Volatility sigma cannot be negative"):
            simulate_gbm_paths(S0=100.0, mu=0.05, sigma=-0.10)
