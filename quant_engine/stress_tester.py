from config import CONN_INFO
import asyncio
import psycopg
import pandas as pd

async def run_stress_tests():
    conn_info = CONN_INFO
    
    print("[+] Connecting to Hades Vault to fetch live positions for Stress Testing...")
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # 1. Fetch current live balances after rebalancing
            await cur.execute("""
                SELECT asset_ticker, SUM(quantity) as total_qty
                FROM portfolio_transactions
                GROUP BY asset_ticker;
            """)
            inventory_rows = await cur.fetchall()
            
            # 2. Fetch latest prices
            await cur.execute("""
                SELECT asset_ticker, close_price 
                FROM asset_historical_prices 
                WHERE price_date = (SELECT MAX(price_date) FROM asset_historical_prices);
            """)
            spot_rows = await cur.fetchall()

    portfolio = {row[0]: float(row[1]) for row in inventory_rows}
    spot_prices = {row[0]: float(row[1]) for row in spot_rows}
    
    active_tickers = [t for t in spot_prices if t in portfolio and portfolio[t] > 0]
    baseline_valuation = sum(portfolio[t] * spot_prices[t] for t in active_tickers)
    
    # Defined Historical Macro Shocks (% price changes during real crisis events)
    scenarios = {
        "2008 Global Financial Crisis": {
            "BTC": -0.65, "ETH": -0.70, "SOL": -0.75,
            "MSFT": -0.45, "AAPL": -0.50, "NVDA": -0.55, "AMD": -0.60, "TSLA": -0.55
        },
        "March 2020 COVID Liquidity Shock": {
            "BTC": -0.50, "ETH": -0.55, "SOL": -0.60,
            "MSFT": -0.28, "AAPL": -0.31, "NVDA": -0.35, "AMD": -0.38, "TSLA": -0.40
        },
        "2022 Crypto Deleveraging Contagion": {
            "BTC": -0.65, "ETH": -0.72, "SOL": -0.85,
            "MSFT": -0.25, "AAPL": -0.22, "NVDA": -0.45, "AMD": -0.50, "TSLA": -0.60
        },
        "Emergency Fed Rate Spike (Macro Squeeze)": {
            "BTC": -0.35, "ETH": -0.40, "SOL": -0.45,
            "MSFT": -0.15, "AAPL": -0.15, "NVDA": -0.25, "AMD": -0.25, "TSLA": -0.30
        }
    }
    
    print("\n=====================================================================")
    print("                 HADES MACRO STRESS-TESTING SUITE                    ")
    print("=====================================================================")
    print(f" Baseline Portfolio Value: ${baseline_valuation:,.2f}")
    print("---------------------------------------------------------------------")
    print(f"{'SCENARIO NAME':<38} | {'POST-CRASH VALUE':<18} | {'PORTFOLIO LOSS':<15}")
    print("---------------------------------------------------------------------")
    
    for scenario_name, shocks in scenarios.items():
        stressed_value = 0.0
        for ticker in active_tickers:
            current_spot = spot_prices[ticker]
            shock_pct = shocks.get(ticker, -0.25)
            stressed_spot = current_spot * (1 + shock_pct)
            stressed_value += portfolio[ticker] * stressed_spot
            
        dollar_loss = baseline_valuation - stressed_value
        pct_loss = (dollar_loss / baseline_valuation) * 100
        
        print(f" {scenario_name:<36} | ${stressed_value:>16,.2f} | -${dollar_loss:>12,.2f} ({pct_loss:.1f}%)")
        
    print("=====================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_stress_tests())
