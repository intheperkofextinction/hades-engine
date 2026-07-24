import sys
import os

# Add parent directory (hades-engine root) to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
import yfinance as yf
import logging
from config import CONN_INFO

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TICKER_MAP = {
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA"
}

def fetch_and_seed_real_data():
    logging.info("📡 Downloading 1 year of real historical price data from Yahoo Finance...")
    
    data = yf.download(list(TICKER_MAP.keys()), period="1y")["Close"]
    
    with psycopg.connect(CONN_INFO) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE asset_historical_prices;")
            
            total_records = 0
            for yf_symbol, db_symbol in TICKER_MAP.items():
                price_series = data[yf_symbol].dropna()
                
                for price_date, close_price in price_series.items():
                    cur.execute("""
                        INSERT INTO asset_historical_prices (asset_ticker, price_date, close_price)
                        VALUES (%s, %s, %s);
                    """, (db_symbol, price_date.strftime('%Y-%m-%d'), float(close_price)))
                    total_records += 1
                    
            conn.commit()
            logging.info(f"✅ Successfully seeded {total_records} real historical price records into PostgreSQL!")

if __name__ == "__main__":
    fetch_and_seed_real_data()
