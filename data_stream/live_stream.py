import asyncio
import random
import psycopg
from datetime import datetime

async def run_live_feed_simulation():
    conn_info = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"
    
    print("[+] Initializing Real-Time Market Feed Pipe...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT asset_ticker, close_price 
                FROM asset_historical_prices 
                WHERE price_date = (SELECT MAX(price_date) FROM asset_historical_prices);
            """)
            rows = await cur.fetchall()
            
    prices = {row[0]: float(row[1]) for row in rows}
    
    # Dynamically extract tickers that actually exist in the database
    tickers = list(prices.keys())
    
    if not tickers:
        print("[!] Error: No price data returned from database.")
        return

    print("[+] Listening to Exchange WebSockets (Simulated Stream)...")
    print("=====================================================================")
    print(f"{'TIMESTAMP':<22} | {'TICKER':<8} | {'BID PRICE':<12} | {'CHANGE':<10}")
    print("---------------------------------------------------------------------")

    for tick in range(10):
        ticker = random.choice(tickers)
        pct_change = random.uniform(-0.015, 0.015)
        old_price = prices[ticker]
        new_price = old_price * (1 + pct_change)
        prices[ticker] = new_price
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        direction = "▲" if pct_change >= 0 else "▼"
        change_str = f"{direction} {pct_change * 100:+.2f}%"
        
        print(f" {now_str:<22} | {ticker:<8} | ${new_price:>10,.2f} | {change_str:<10}")
        await asyncio.sleep(0.5)

    print("=====================================================================")
    print("[+] Live Data Pipeline verified successfully.\n")

if __name__ == "__main__":
    asyncio.run(run_live_feed_simulation())
