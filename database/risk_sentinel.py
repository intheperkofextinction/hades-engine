from config import CONN_INFO
import asyncio
import psycopg

# Risk threshold: No single asset should exceed 15% of total portfolio value
MAX_ALLOCATION_PERCENTAGE = 15.0

async def audit_portfolio_risk():
    conn_info = CONN_INFO
    
    print("[+] Fetching real-time parameters from Hades Vault...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # 1. First, get the Grand Total Value of the entire portfolio
            await cur.execute("SELECT COALESCE(SUM(quantity * price), 0) FROM portfolio_transactions;")
            result = await cur.fetchone()
            grand_total = float(result[0])
            
            if grand_total == 0:
                print("[-] Portfolio is empty. No risk to analyze.")
                return
                
            # 2. Get individual asset exposure
            await cur.execute("""
                SELECT 
                    asset_ticker,
                    ROUND(SUM(quantity * price), 2) as total_value_usd
                FROM portfolio_transactions
                GROUP BY asset_ticker
                ORDER BY total_value_usd DESC;
            """)
            rows = await cur.fetchall()
            
            print("\n=====================================================================")
            print("                HADES AUTOMATED RISK SENTINEL AUDIT                  ")
            print("=====================================================================")
            print(f"{'ASSET':<10}{'EXPOSURE (USD)':<22}{'ALLOCATION %':<15}{'STATUS':<12}")
            print("---------------------------------------------------------------------")
            
            for row in rows:
                ticker, usd_val = row
                usd_val_float = float(usd_val)
                
                # Calculate what % of the overall fund this asset represents
                allocation_pct = (usd_val_float / grand_total) * 100
                
                # Check if it breaches our risk parameters
                if allocation_pct > MAX_ALLOCATION_PERCENTAGE:
                    status = "🚨 BREACH"
                else:
                    status = "✅ SAFE"
                    
                print(f"{ticker:<10}${usd_val_float:<21,.2f}{allocation_pct:<15.2f}%{status:<12}")
                
            print("---------------------------------------------------------------------")
            print(f"TOTAL ASSETS UNDER MANAGEMENT: ${grand_total:,.2f}")
            print("=====================================================================\n")

if __name__ == "__main__":
    asyncio.run(audit_portfolio_risk())
