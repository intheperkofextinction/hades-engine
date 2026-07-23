from config import CONN_INFO
import asyncio
import psycopg

async def initialize_hades_db():
    # Credentials matching your active Docker container
    conn_info = CONN_INFO
    
    print("[+] Connecting to PostgreSQL inside Docker...")
    
    # Connect asynchronously
    conn = await psycopg.AsyncConnection.connect(conn_info)
    async with conn:
        async with conn.cursor() as cur:
            # 1. Create Core Transaction Log Table
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_transactions (
                    transaction_id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    asset_ticker VARCHAR(10) NOT NULL,
                    asset_type VARCHAR(20) NOT NULL,
                    quantity NUMERIC(18, 4) NOT NULL,
                    price NUMERIC(18, 4) NOT NULL,
                    portfolio_id INT NOT NULL,
                    trader_id INT NOT NULL
                );
            """)
            
            # 2. Add BRIN Index for fast chronological range queries
            await cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_txn_timestamp_brin 
                ON portfolio_transactions USING brin (timestamp);
            """)
            
            # 3. Add Composite Index for fast risk evaluation lookups
            await cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_portfolio_asset 
                ON portfolio_transactions (portfolio_id, asset_ticker);
            """)
            
            await conn.commit()
            print("[+] Database tables and optimized BRIN indexes successfully deployed!")

if __name__ == "__main__":
    asyncio.run(initialize_hades_db())
