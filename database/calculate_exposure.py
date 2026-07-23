from config import CONN_INFO
import asyncio
import psycopg

async def calculate_live_exposure():
    conn_info = CONN_INFO
    
    print("[+] Connecting to Hades Risk Vault...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # High-speed SQL aggregation query
            await cur.execute("""
                SELECT 
                    asset_ticker,
                    asset_type,
                    SUM(quantity) as total_quantity,
                    ROUND(SUM(quantity * price), 2) as total_value_usd,
                    COUNT(*) as total_trades
                FROM portfolio_transactions
                GROUP BY asset_ticker, asset_type
                ORDER BY total_value_usd DESC;
            """)
            
            rows = await cur.fetchall()
            
            print("\n=====================================================================")
            print("                HADES REAL-TIME RISK EXPOSURE REPORT                 ")
            print("=====================================================================")
            print(f"{'TICKER':<10}{'TYPE':<12}{'TOTAL QTY':<15}{'EXPOSURE (USD)':<20}{'TRADES':<10}")
            print("---------------------------------------------------------------------")
            
            grand_total = 0.0
            for row in rows:
                ticker, asset_type, qty, usd_val, trades = row
                grand_total += float(usd_val)
                print(f"{ticker:<10}{asset_type:<12}{float(qty):<15,.2f}  ${float(usd_val):<19,.2f}{trades:<10}")
                
            print("---------------------------------------------------------------------")
            print(f"TOTAL PORTFOLIO RISK EXPOSURE: ${grand_total:,.2f}")
            print("=====================================================================\n")

if __name__ == "__main__":
    asyncio.run(calculate_live_exposure())
