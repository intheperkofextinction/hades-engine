import asyncio
import psycopg
import pandas as pd
import numpy as np
from datetime import datetime

# Institutional Compliance Limit Configuration
MAX_VAR_PORTFOLIO_PCT = 0.15   # Max allowed 95% VaR: 15% of Portfolio Value
MAX_CVAR_PORTFOLIO_PCT = 0.20  # Max allowed 95% CVaR: 20% of Portfolio Value

async def evaluate_compliance_and_sentinel():
    conn_info = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"
    
    print("[+] Connecting to Hades Vault to establish Compliance Audit Tables...")
    
    async with await psycopg.AsyncConnection.connect(conn_info) as conn:
        async with conn.cursor() as cur:
            # Create immutable compliance audit table
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS risk_alerts (
                    id SERIAL PRIMARY KEY,
                    alert_timestamp TIMESTAMP NOT NULL,
                    metric_type VARCHAR(20) NOT NULL,
                    current_value NUMERIC(16, 2) NOT NULL,
                    threshold_value NUMERIC(16, 2) NOT NULL,
                    portfolio_valuation NUMERIC(16, 2) NOT NULL,
                    severity VARCHAR(10) NOT NULL,
                    status VARCHAR(20) NOT NULL
                );
            """)
            await conn.commit()
            
            # 1. Gather positions & prices
            await cur.execute("""
                SELECT asset_ticker, SUM(quantity) as total_qty
                FROM portfolio_transactions
                GROUP BY asset_ticker;
            """)
            inventory_rows = await cur.fetchall()
            
            await cur.execute("""
                SELECT asset_ticker, price_date, close_price 
                FROM asset_historical_prices 
                ORDER BY price_date ASC;
            """)
            price_rows = await cur.fetchall()

    portfolio = {row[0]: float(row[1]) for row in inventory_rows}
    df = pd.DataFrame(price_rows, columns=['ticker', 'date', 'price'])
    df['price'] = pd.to_numeric(df['price'])
    matrix_df = df.pivot(index='date', columns='ticker', values='price')
    
    active_tickers = [t for t in matrix_df.columns if t in portfolio]
    matrix_df = matrix_df[active_tickers]
    spot_prices = matrix_df.iloc[-1]
    
    returns_df = np.log(matrix_df / matrix_df.shift(1)).dropna()
    daily_drift = returns_df.mean()
    daily_vol = returns_df.std()
    
    current_portfolio_value = sum(portfolio[ticker] * spot_prices[ticker] for ticker in active_tickers)
    
    # 2. Run high-speed Monte Carlo pass (10,000 paths)
    NUM_SIMULATIONS = 10000
    DAYS_HORIZON = 30
    final_portfolio_values = np.zeros(NUM_SIMULATIONS)
    
    for ticker in active_tickers:
        S0, mu, sigma, qty = spot_prices[ticker], daily_drift[ticker], daily_vol[ticker], portfolio[ticker]
        shocks = np.random.normal(0, 1, size=(DAYS_HORIZON, NUM_SIMULATIONS))
        paths = np.zeros((DAYS_HORIZON + 1, NUM_SIMULATIONS))
        paths[0] = S0
        for t in range(1, DAYS_HORIZON + 1):
            paths[t] = paths[t-1] * np.exp((mu - 0.5 * sigma**2) + sigma * shocks[t-1])
        final_portfolio_values += paths[-1] * qty

    gains_losses = final_portfolio_values - current_portfolio_value
    var_95 = abs(np.percentile(gains_losses, 5))
    cvar_95 = abs(gains_losses[gains_losses <= -var_95].mean())
    
    # Calculate dollar threshold limits
    var_limit = current_portfolio_value * MAX_VAR_PORTFOLIO_PCT
    cvar_limit = current_portfolio_value * MAX_CVAR_PORTFOLIO_PCT
    
    print("\n=====================================================================")
    print("             HADES SENTINEL COMPLIANCE AUDIT ENGINE                 ")
    print("=====================================================================")
    print(f" Portfolio Value : ${current_portfolio_value:,.2f}")
    print(f" Calculated 95% VaR  : ${var_95:,.2f}  | Allowed Limit: ${var_limit:,.2f}")
    print(f" Calculated 95% CVaR : ${cvar_95:,.2f}  | Allowed Limit: ${cvar_limit:,.2f}")
    print("---------------------------------------------------------------------")

    alerts_to_log = []
    
    # Check VaR Limit
    if var_95 > var_limit:
        print(f" [CRITICAL BREACH] 95% VaR exceeds allowed 15% threshold!")
        alerts_to_log.append((datetime.now(), 'VAR_95_BREACH', var_95, var_limit, current_portfolio_value, 'CRITICAL', 'OPEN'))
    else:
        print(" [OK] 95% VaR is within institutional safety parameters.")

    # Check CVaR Limit
    if cvar_95 > cvar_limit:
        print(f" [CRITICAL BREACH] 95% CVaR exceeds allowed 20% threshold!")
        alerts_to_log.append((datetime.now(), 'CVAR_95_BREACH', cvar_95, cvar_limit, current_portfolio_value, 'CRITICAL', 'OPEN'))
    else:
        print(" [OK] 95% CVaR is within institutional safety parameters.")

    # 3. Commit breaches to Postgres if any rule failed
    if alerts_to_log:
        async with await psycopg.AsyncConnection.connect(conn_info) as conn:
            async with conn.cursor() as cur:
                await cur.executemany("""
                    INSERT INTO risk_alerts (alert_timestamp, metric_type, current_value, threshold_value, portfolio_valuation, severity, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, alerts_to_log)
                await conn.commit()
        print(f"\n[!] ALERT SENTINEL: Logged {len(alerts_to_log)} breach incident(s) into database.")
    else:
        print("\n[+] All risk parameters passed. Portfolio status: SAFE.")
        
    print("=====================================================================\n")

if __name__ == "__main__":
    asyncio.run(evaluate_compliance_and_sentinel())
