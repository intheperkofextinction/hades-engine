import asyncio
import psycopg

# Strict risk parameters
MAX_ALLOCATION_PERCENTAGE = 15.0

async def calculate_portfolio_rebalancing():
    conn_info = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"
    
    print("[+] Connecting to Hades Risk Engine for portfolio optimization...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # 1. Fetch the overall portfolio value
            await cur.execute("SELECT COALESCE(SUM(quantity * price), 0) FROM portfolio_transactions;")
            grand_total = float((await cur.fetchone())[0])
            
            if grand_total == 0:
                print("[-] No asset exposure detected. Rebalancing aborted.")
                return
            
            # Calculate the maximum allowable dollar value per single asset
            max_allowed_usd_per_asset = grand_total * (MAX_ALLOCATION_PERCENTAGE / 100.0)
            
            # 2. Get asset metrics along with the implied weighted current price
            await cur.execute("""
                SELECT 
                    asset_ticker,
                    SUM(quantity) as total_qty,
                    SUM(quantity * price) as total_value_usd,
                    SUM(quantity * price) / NULLIF(SUM(quantity), 0) as weighted_avg_price
                FROM portfolio_transactions
                GROUP BY asset_ticker
                ORDER BY total_value_usd DESC;
            """)
            rows = await cur.fetchall()
            
            print("\n==========================================================================================")
            print("                       HADES QUANTITATIVE REBALANCING REPORT                              ")
            print("==========================================================================================")
            print(f"{'ASSET':<10}{'CURRENT VAL':<18}{'ALLOC %':<10}{'RECOMMENDATION':<16}{'REDUCE (USD)':<18}{'REDUCE (QTY)':<12}")
            print("------------------------------------------------------------------------------------------")
            
            for row in rows:
                ticker, total_qty, total_val, avg_price = row
                total_val = float(total_val)
                total_qty = float(total_qty)
                avg_price = float(avg_price) if avg_price else 0.0
                
                allocation_pct = (total_val / grand_total) * 100
                
                # If the asset exceeds our 15% rule, compute the trim requirements
                if allocation_pct > MAX_ALLOCATION_PERCENTAGE:
                    usd_to_sell = total_val - max_allowed_usd_per_asset
                    qty_to_sell = usd_to_sell / avg_price if avg_price > 0 else 0
                    action = "🚨 FORCE TRIM"
                    usd_str = f"${usd_to_sell:,.2f}"
                    qty_str = f"{qty_to_sell:,.2f}"
                else:
                    action = "✅ MAINTAIN"
                    usd_str = "$0.00"
                    qty_str = "0.00"
                    
                print(f"{ticker:<10}${total_val:<17,.2f}{allocation_pct:<10.2f}%{action:<16}{usd_str:<18}{qty_str:<12}")
                
            print("------------------------------------------------------------------------------------------")
            print(f"TOTAL PORTFOLIO VALUE: ${grand_total:,.2f}")
            print(f"MAX RISK CAP PER ASSET (15.00%): ${max_allowed_usd_per_asset:,.2f}")
            print("==========================================================================================\n")

if __name__ == "__main__":
    asyncio.run(calculate_portfolio_rebalancing())
