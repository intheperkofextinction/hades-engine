from config import CONN_INFO
import asyncio
import psycopg
import pandas as pd
import numpy as np

async def run_portfolio_monte_carlo():
    conn_info = CONN_INFO
    
    print("[+] Step 1: Querying live trade desk inventory balances...")
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # Fetch current live aggregate position volumes
            await cur.execute("""
                SELECT asset_ticker, SUM(quantity) as total_qty
                FROM portfolio_transactions
                GROUP BY asset_ticker;
            """)
            inventory_rows = await cur.fetchall()
            
            # Fetch complete historical pricing logs
            await cur.execute("""
                SELECT asset_ticker, price_date, close_price 
                FROM asset_historical_prices 
                ORDER BY price_date ASC;
            """)
            price_rows = await cur.fetchall()

    portfolio = {row[0]: float(row[1]) for row in inventory_rows}
    
    df = pd.DataFrame(price_rows, columns=['ticker', 'date', 'price'])
    df['price'] = pd.to_numeric(df['price'])
    matrix_df = df.pivot(index='date', columns='ticker', values='price')
    
    active_tickers = [t for t in matrix_df.columns if t in portfolio]
    matrix_df = matrix_df[active_tickers]
    
    spot_prices = matrix_df.iloc[-1]
    returns_df = np.log(matrix_df / matrix_df.shift(1)).dropna()
    
    daily_drift = returns_df.mean()
    daily_vol = returns_df.std()
    
    current_portfolio_value = sum(portfolio[ticker] * spot_prices[ticker] for ticker in active_tickers)
    
    print(f"[+] Loaded baseline positions. Current Assets Value: ${current_portfolio_value:,.2f}")
    print("[+] Step 2: Spinning up Vectorized Monte Carlo Matrix (10,000 paths, 30-day forecast)...")
    
    NUM_SIMULATIONS = 10000
    DAYS_HORIZON = 30
    CONFIDENCE_LEVEL = 0.95
    
    final_portfolio_values = np.zeros(NUM_SIMULATIONS)
    
    for ticker in active_tickers:
        S0 = spot_prices[ticker]
        mu = daily_drift[ticker]
        sigma = daily_vol[ticker]
        qty = portfolio[ticker]
        
        random_shocks = np.random.normal(0, 1, size=(DAYS_HORIZON, NUM_SIMULATIONS))
        
        price_paths = np.zeros((DAYS_HORIZON + 1, NUM_SIMULATIONS))
        price_paths[0] = S0
        
        for t in range(1, DAYS_HORIZON + 1):
            price_paths[t] = price_paths[t-1] * np.exp((mu - 0.5 * sigma**2) + sigma * random_shocks[t-1])
            
        final_asset_prices = price_paths[-1]
        final_portfolio_values += final_asset_prices * qty
        
    portfolio_gains_losses = final_portfolio_values - current_portfolio_value
    
    var_threshold = np.percentile(portfolio_gains_losses, (1 - CONFIDENCE_LEVEL) * 100)
    cvar_threshold = portfolio_gains_losses[portfolio_gains_losses <= var_threshold].mean()
    
    print("\n=====================================================================")
    print("                HADES SYSTEM QUANTITATIVE RISK REPORT               ")
    print("=====================================================================")
    print(f" Total Portfolio Valuation : ${current_portfolio_value:,.2f}")
    print(f" Forecast Horizon Parameters: {DAYS_HORIZON} Trading Days | 10,000 Runs")
    print(f" Applied Target Confidence  : {CONFIDENCE_LEVEL * 100:.1f}%")
    print("---------------------------------------------------------------------")
    print(f" Value at Risk (95% VaR)    : ${abs(var_threshold):,.2f}")
    print(f" Conditional VaR (95% CVaR) : ${abs(cvar_threshold):,.2f}")
    print("---------------------------------------------------------------------")
    print(f" Risk Verdict: There is a 5% chance the asset pool will drop by at\n"
          f" least ${abs(var_threshold):,.2f} over the next {DAYS_HORIZON} days.")
    print(f" In those worst-case failures, the average expected drop is ${abs(cvar_threshold):,.2f}.")
    print("=====================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_portfolio_monte_carlo())
