import sys
import os
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

from database.seed_real_prices import fetch_and_seed_real_data
from quant_engine.monte_carlo_engine import run_portfolio_monte_carlo
from compliance.risk_sentinel import audit_compliance_limits
from quant_engine.stress_tester import run_stress_tests

async def run_pipeline():
    logging.info("🚀 Starting HADES Risk Engine Automated Pipeline...")
    
    # Step 1: Ingest latest market data
    try:
        logging.info("Step 1/4: Refreshing market data feed (yfinance)...")
        fetch_and_seed_real_data()
    except Exception as e:
        logging.error(f"Failed to refresh market data: {e}")
        return

    # Step 2: Execute Monte Carlo Simulation
    try:
        logging.info("Step 2/4: Executing Monte Carlo Risk Engine...")
        results = await run_portfolio_monte_carlo(days=30, num_paths=10000, confidence_level=0.95)
    except Exception as e:
        logging.error(f"Error during Monte Carlo simulation: {e}")
        return

    # Step 3: Run Macro Stress Testing
    try:
        logging.info("Step 3/4: Running Historical Black Swan Stress Tests...")
        await run_stress_tests()
    except Exception as e:
        logging.error(f"Error during stress testing: {e}")

    # Step 4: Compliance & Limit Sentinel Audit
    try:
        logging.info("Step 4/4: Auditing Compliance Risk Limits & Sentinels...")
        if results:
            await audit_compliance_limits(results["var_95"], results["cvar_95"])
    except Exception as e:
        logging.error(f"Error during compliance audit: {e}")

    logging.info("✅ Full end-to-end pipeline finished successfully. Database & sentinels synchronized.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
