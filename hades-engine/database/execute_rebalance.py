import asyncio
import psycopg
from datetime import datetime, timezone

MAX_ALLOCATION_PERCENTAGE = 15.0

async def execute_smart_rebalancing():
    conn_info = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"
    
    print("[+] Waking up Hades Automated Execution Desk...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # 1. Fetch total portfolio value to determine thresholds
            await cur.execute("SELECT COALESCE(SUM(quantity * price), 0) FROM portfolio_transactions;")
            grand_total = float((await cur.fetchone())[0])
            
            if grand_total == 0:
                print("[-] Portfolio is empty. No trades to route.")
                return
                
            max_allowed_usd = grand_total * (MAX_ALLOCATION_PERCENTAGE / 100.0)
            
            # 2. Find any assets that currently breach our threshold
            await cur.execute("""
                SELECT 
                    asset_ticker,
                    asset_type,
                    SUM(quantity) as total_qty,
                    SUM(quantity * price) as total_value_usd,
                    SUM(quantity * price) / NULLIF(SUM(quantity), 0) as weighted_avg_price
                FROM portfolio_transactions
                GROUP BY asset_ticker, asset_type
                HAVING SUM(quantity * price) > %s;
            """, (max_allowed_usd,))
            
            breached_assets = await cur.fetchall()
            
            if not breached_assets:
                print("[+] Portfolio is perfectly optimized. No balancing trades required.")
                return
                
            print(f"\n[🚨 ALERT] Found {len(breached_assets)} position(s) requiring immediate compliance remediation.\n")
            print("--------------------------------------------------------------------------------")
            print(f"{'TICKER':<10}{'TRADE ACTION':<15}{'QUANTITY TO SELL':<20}{'EXECUTION PRICE':<18}")
            print("--------------------------------------------------------------------------------")
            
            # 3. Generate and execute offsetting market orders for breached assets
            for row in breached_assets:
                ticker, asset_type, total_qty, total_val, avg_price = row
                total_val = float(total_val)
                avg_price = float(avg_price)
                
                # Calculate exactly how many dollars and units to shave off
                usd_to_shave = total_val - max_allowed_usd
                qty_to_sell = usd_to_shave / avg_price
                
                # Institutional sell orders are logged as a negative quantity
                negative_qty = -qty_to_sell
                
                print(f"{ticker:<10}{'ALGO_MARKET_SELL':<15}{qty_to_sell:<20,.4f}${avg_price:<17,.2f}")
                
                # Insert the rebalancing transaction into the ledger
                await cur.execute("""
                    INSERT INTO portfolio_transactions (
                        timestamp, asset_ticker, asset_type, quantity, price, portfolio_id, trader_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (
                    datetime.now(timezone.utc),
                    ticker,
                    asset_type,
                    negative_qty,
                    avg_price,
                    999,  # Institutional Rebalance Portfolio ID
                    777   # Hades Automated Execution Bot ID
                ))
            
            # Commit the execution to the ledger permanently
            await conn.commit()
            print("--------------------------------------------------------------------------------")
            print("[+] All orders successfully cleared and settled through database ledger.")
            print("[+] Re-running system diagnostic check...\n")
            
            # 4. Final verification verification report
            await cur.execute("""
                SELECT 
                    asset_ticker,
                    ROUND(SUM(quantity * price), 2) as total_value_usd
                FROM portfolio_transactions
                GROUP BY asset_ticker
                ORDER BY total_value_usd DESC;
            """)
            updated_rows = await cur.fetchall()
            
            await cur.execute("SELECT COALESCE(SUM(quantity * price), 0) FROM portfolio_transactions;")
            new_grand_total = float((await cur.fetchone())[0])
            
            print("=====================================================================")
            print("             POST-EXECUTION COMPLIANCE VERIFICATION                  ")
            print("=====================================================================")
            print(f"{'ASSET':<10}{'UPDATED EXPOSURE (USD)':<25}{'NEW ALLOCATION %':<15}")
            print("---------------------------------------------------------------------")
            for u_row in updated_rows:
                u_ticker, u_val = u_row
                u_val_float = float(u_val)
                new_alloc = (u_val_float / new_grand_total) * 100 if new_grand_total > 0 else 0
                print(f"{u_ticker:<10}${u_val_float:<24,.2f}{new_alloc:<15.2f}%")
            print("---------------------------------------------------------------------")
            print(f"TOTAL ADJUSTED AUM: ${new_grand_total:,.2f}")
            print("=====================================================================\n")

if __name__ == "__main__":
    asyncio.run(execute_smart_rebalancing())
