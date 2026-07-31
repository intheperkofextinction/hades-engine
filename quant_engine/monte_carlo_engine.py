import sys
import os
import numpy as np
import pandas as pd
import asyncio
import psycopg

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CONN_INFO


def calculate_var_cvar(portfolio_returns: np.ndarray, confidence_level: float = 0.95):
    """
    Calculates Value at Risk (VaR) and Conditional Value at Risk (CVaR / Expected Shortfall).
    """
    if len(portfolio_returns) == 0:
        raise ValueError("Portfolio returns array cannot be empty.")
    if not (0 < confidence_level < 1):
        raise ValueError("Confidence level must be strictly between 0 and 1.")

    cutoff_percentile = (1.0 - confidence_level) * 100
    var = float(np.percentile(portfolio_returns, cutoff_percentile))

    tail_losses = portfolio_returns[portfolio_returns <= var]
    cvar = float(np.mean(tail_losses)) if len(tail_losses) > 0 else var

    return var, cvar


def simulate_gbm_paths(S0: float, mu: float, sigma: float, days: int = 30, num_paths: int = 10000):
    """
    Simulates Geometric Brownian Motion (GBM) price paths for an asset.
    """
    if S0 <= 0:
        raise ValueError("Initial price S0 must be greater than zero.")
    if sigma < 0:
        raise ValueError("Volatility sigma cannot be negative.")

    dt = 1.0 / 252.0  # Daily time step assuming 252 trading days per year
    
    Z = np.random.standard_normal((num_paths, days))
    
    drift_term = (mu - 0.5 * sigma**2) * dt
    diffusion_term = sigma * np.sqrt(dt) * Z
    daily_log_returns = drift_term + diffusion_term
    
    price_paths = S0 * np.exp(np.cumsum(daily_log_returns, axis=1))
    return price_paths


async def run_portfolio_monte_carlo(days: int = 30, num_paths: int = 10000, confidence_level: float = 0.95):
    """
    Runs an end-to-end Monte Carlo simulation across actual portfolio holdings
    using historical asset prices from PostgreSQL.
    """
    print("[+] Step 1: Querying live trade desk inventory balances & price history...")
    
    async with await psycopg.AsyncConnection.connect(CONN_INFO) as conn:
        async with conn.cursor() as cur:
            # Query portfolio inventory
            await cur.execute("""
                SELECT asset_ticker, SUM(quantity) as total_qty
                FROM portfolio_transactions
                GROUP BY asset_ticker;
            """)
            inventory_rows = await cur.fetchall()

            # Query historical close prices
            await cur.execute("""
                SELECT asset_ticker, price_date, close_price
                FROM asset_historical_prices
                ORDER BY asset_ticker, price_date ASC;
            """)
            price_rows = await cur.fetchall()

    if not inventory_rows:
        print("[!] No positions found in portfolio_transactions.")
        return

    portfolio = {row[0]: float(row[1]) for row in inventory_rows if float(row[1]) > 0}
    
    # Load price data into Pandas DataFrame
    df = pd.DataFrame(price_rows, columns=["asset_ticker", "price_date", "close_price"])
    df["close_price"] = df["close_price"].astype(float)
    
    simulated_final_asset_values = {}
    current_portfolio_value = 0.0

    print("[+] Step 2: Estimating annualized drift (mu) and volatility (sigma) from DB price history...")
    for ticker, qty in portfolio.items():
        asset_df = df[df["asset_ticker"] == ticker].sort_values("price_date")
        
        if asset_df.empty or len(asset_df) < 2:
            print(f"    [!] Warning: Insufficient price history for {ticker}. Skipping...")
            continue

        prices = asset_df["close_price"].values
        S0 = prices[-1]  # Latest spot price
        
        # Calculate daily log returns
        log_returns = np.log(prices[1:] / prices[:-1])
        
        # Annualized drift (mu) and volatility (sigma)
        daily_mu = np.mean(log_returns)
        daily_sigma = np.std(log_returns)
        
        annual_mu = daily_mu * 252
        annual_sigma = daily_sigma * np.sqrt(252)

        # Generate 10,000 Geometric Brownian Motion trajectories
        paths = simulate_gbm_paths(S0=S0, mu=annual_mu, sigma=annual_sigma, days=days, num_paths=num_paths)
        
        # Extract Day 30 ending prices across all 10,000 simulation paths
        final_prices = paths[:, -1]
        
        # Aggregate path dollar values for this ticker
        simulated_final_asset_values[ticker] = final_prices * qty
        current_portfolio_value += S0 * qty

    if current_portfolio_value == 0:
        print("[!] Total current portfolio value is $0. Aborting simulation.")
        return

    print(f"[+] Total Current Portfolio Value: ${current_portfolio_value:,.2f}")

    # Step 3: Sum simulated asset values across all paths to get ending portfolio values
    total_simulated_ending_values = sum(simulated_final_asset_values.values())
    
    # Calculate simulated percentage returns of the whole portfolio
    simulated_portfolio_returns = (total_simulated_ending_values - current_portfolio_value) / current_portfolio_value

    # Step 4: Calculate 30-Day VaR & CVaR on the simulated portfolio returns
    var, cvar = calculate_var_cvar(simulated_portfolio_returns, confidence_level=confidence_level)

    print(f"[+] Step 3: Monte Carlo Simulation Complete ({num_paths:,} paths, {days}-day horizon)")
    print(f"    • {days}-Day {confidence_level:.0%} VaR:  {var:.2%}  (-${abs(var * current_portfolio_value):,.2f})")
    print(f"    • {days}-Day {confidence_level:.0%} CVaR: {cvar:.2%}  (-${abs(cvar * current_portfolio_value):,.2f})")

    return {
        "portfolio_value": current_portfolio_value,
        "var_95": var,
        "cvar_95": cvar,
        "simulated_returns": simulated_portfolio_returns
    }


if __name__ == "__main__":
    asyncio.run(run_portfolio_monte_carlo())
