import asyncio
import psycopg
import pandas as pd
import numpy as np

async def compute_portfolio_risk_profiles():
    conn_info = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"
    
    print("[+] Fetching historical market assets out of Postgres...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # Pull the data sorted chronologically so returns calculate correctly
            await cur.execute("""
                SELECT asset_ticker, price_date, close_price 
                FROM asset_historical_prices 
                ORDER BY price_date ASC;
            """)
            rows = await cur.fetchall()
            
    # Step 1: Turn raw database tuples into a structured Pandas DataFrame
    df = pd.DataFrame(rows, columns=['ticker', 'date', 'price'])
    
    # Force the price column to act as numbers instead of text strings
    df['price'] = pd.to_numeric(df['price'])
    
    # Step 2: Reshape the data (Pivot). 
    # This turns tickers into column headers and dates into rows, like a clean matrix spreadsheet.
    matrix_df = df.pivot(index='date', columns='ticker', values='price')
    
    print("\n[+] Transformed Market Price Matrix (Most Recent 5 Days):")
    print(matrix_df.tail())
    
    # Step 3: Vectorized Log Returns Calculation using NumPy
    # Instead of looping line by line, this divides the entire matrix table at once
    returns_df = np.log(matrix_df / matrix_df.shift(1)).dropna()
    
    # Step 4: Extract Statistical Risk Attributes
    print("\n=====================================================================")
    print("                HADES PORTFOLIO QUANT RISK PROFILES                 ")
    print("=====================================================================")
    
    for asset in matrix_df.columns:
        # Calculate daily risk profiles
        daily_vol = returns_df[asset].std()
        daily_drift = returns_df[asset].mean()
        
        # Annualize the daily volatility to scale it up across a standard trading year (252 days)
        annualized_vol = daily_vol * np.sqrt(252)
        
        print(f"Asset Ticker: {asset:<6} | Daily Drift: {daily_drift:+.6f} | Daily Vol: {daily_vol:.4f} | Annualized Vol: {annualized_vol*100:.2f}%")
        
    print("=====================================================================\n")

if __name__ == "__main__":
    asyncio.run(compute_portfolio_risk_profiles())
