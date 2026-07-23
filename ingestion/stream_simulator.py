import asyncio
import random
import time
from datetime import datetime, timezone
import psycopg

# Configuration for our mock financial market
TICKERS = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "BTC", "ETH", "SOL"]
ASSET_TYPES = ["STOCK", "STOCK", "STOCK", "STOCK", "STOCK", "CRYPTO", "CRYPTO", "CRYPTO"]

async def generate_mock_trade():
    """Generates a realistic randomized financial transaction record."""
    idx = random.randint(0, len(TICKERS) - 1)
    ticker = TICKERS[idx]
    asset_type = ASSET_TYPES[idx]
    
    # Simulating standard quantitative asset prices
    base_price = 150.0 if asset_type == "STOCK" else 3500.0 if ticker == "ETH" else 65000.0 if ticker == "BTC" else 120.0
    price = round(base_price * random.uniform(0.95, 1.05), 4)
    quantity = round(random.uniform(1, 50) if asset_type == "STOCK" else random.uniform(0.01, 2.5), 4)
    
    return (
        datetime.now(timezone.utc),
        ticker,
        asset_type,
        quantity,
        price,
        random.randint(100, 105), # Mock Portfolio ID
        random.randint(5000, 5050) # Mock Trader ID
    )

async def run_ingestion_engine():
    conn_info = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"
    
    print("[+] Initializing Hades High-Throughput Streaming Engine...")
    print("[+] Establishing asynchronous worker pools...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        print("[+] Streaming Engine Connected. Starting real-time ingestion market feed...\n")
        
        total_rows = 0
        start_time = time.time()
        
        # We will loop infinitely to simulate a live market data stream
        while True:
            # Batch together 2,500 fake trades at lightning speed
            batch = [await generate_mock_trade() for _ in range(2500)]
            
            async with conn.cursor() as cur:
                # Optimized multi-row insertion
                await cur.executemany("""
                    INSERT INTO portfolio_transactions 
                    (timestamp, asset_ticker, asset_type, quantity, price, portfolio_id, trader_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, batch)
            
            await conn.commit()
            
            total_rows += len(batch)
            elapsed = time.time() - start_time
            rows_per_sec = int(total_rows / elapsed) if elapsed > 0 else 0
            
            # Print a real-time terminal metrics dashboard
            print(f"\r🚀 INGESTED: {total_rows:,} total rows | SPEED: {rows_per_sec:,} rows/sec | STATUS: STREAMING...", end="", flush=True)
            
            # Tiny nap so your laptop CPU doesn't melt completely
            await asyncio.sleep(0.01)

if __name__ == "__main__":
    try:
        asyncio.run(run_ingestion_engine())
    except KeyboardInterrupt:
        print("\n\n[-] Streaming Engine safely halted by operator. Real-time data pipeline closed.")
