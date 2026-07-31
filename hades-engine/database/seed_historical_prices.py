import asyncio
import psycopg
import random
from datetime import datetime, timedelta

async def seed_market_history():
    conn_info = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"
    
    print("[+] Connecting to Hades Vault to establish Historical Market Tables...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # 1. Create the Historical Table if it doesn't exist
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS asset_historical_prices (
                    id SERIAL PRIMARY KEY,
                    asset_ticker VARCHAR(10) NOT NULL,
                    price_date DATE NOT NULL,
                    close_price NUMERIC(16, 4) NOT NULL,
                    UNIQUE(asset_ticker, price_date)
                );
            """)
            
            # Indexing optimization: ensure quick lookups when sorting historical trends by date
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_hist_ticker_date ON asset_historical_prices(asset_ticker, price_date);")
            await conn.commit()
            print("[+] Database schema verified. Generating 365 days of price histories...")
            
            # Defining core base asset parameters for realistic simulation foundations
            assets = {
                'BTC': {'base': 65000.0, 'volatility': 0.04},
                'ETH': {'base': 3400.0, 'volatility': 0.05},
                'AAPL': {'base': 210.0, 'volatility': 0.015},
                'NVDA': {'base': 125.0, 'volatility': 0.03},
                'MSFT': {'base': 420.0, 'volatility': 0.012}
            }
            
            today = datetime.now().date()
            insert_payload = []
            
            # 2. Build the historical data matrix loop
            for ticker, params in assets.items():
                current_price = params['base']
                vol = params['volatility']
                
                for day_offset in range(365, -1, -1):
                    target_date = today - timedelta(days=day_offset)
                    
                    # Generate a random daily percentage shift around a slight positive upward drift
                    daily_return = random.normalvariate(0.0005, vol)
                    current_price *= (1 + daily_return)
                    
                    # Ensure pricing never drops below unrealistic numbers
                    current_price = max(current_price, 0.01)
                    
                    insert_payload.append((ticker, target_date, current_price))
            
            # 3. High-speed transactional bulk insertion
            print(f"[+] Bulk loading {len(insert_payload)} data records into Postgres...")
            await cur.executemany("""
                INSERT INTO asset_historical_prices (asset_ticker, price_date, close_price)
                VALUES (%s, %s, %s)
                ON CONFLICT (asset_ticker, price_date) DO UPDATE 
                SET close_price = EXCLUDED.close_price;
            """, insert_payload)
            
            await conn.commit()
            print("[+] Data matrix integration complete. Market history successfully built.")

if __name__ == "__main__":
    asyncio.run(seed_market_history())
