import streamlit as st
import psycopg
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(
    page_title="HADES Risk & Execution Command Center",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ HADES Quantitative Risk & Execution Desk")
st.caption("Institutional Asset Management & Automated Compliance Monitoring Platform")

DB_INFO = "dbname=hades_risk user=hades_admin password=hades_secure_pass host=127.0.0.1 port=5432"

def load_data():
    conn = psycopg.connect(DB_INFO)
    
    # Portfolio Positions
    df_positions = pd.read_sql_query("""
        SELECT asset_ticker, SUM(quantity) as qty
        FROM portfolio_transactions
        GROUP BY asset_ticker;
    """, conn)
    
    # Spot Prices
    df_prices = pd.read_sql_query("""
        SELECT asset_ticker, close_price 
        FROM asset_historical_prices 
        WHERE price_date = (SELECT MAX(price_date) FROM asset_historical_prices);
    """, conn)
    
    # Audit Alerts
    df_alerts = pd.read_sql_query("""
        SELECT id, alert_timestamp, metric_type, current_value, threshold_value, severity, status 
        FROM risk_alerts
        ORDER BY alert_timestamp DESC;
    """, conn)
    
    conn.close()
    return df_positions, df_prices, df_alerts

try:
    df_pos, df_prices, df_alerts = load_data()
    
    # Merge holdings with latest prices
    df_merged = pd.merge(df_pos, df_prices, on="asset_ticker")
    df_merged["close_price"] = pd.to_numeric(df_merged["close_price"])
    df_merged["valuation"] = df_merged["qty"] * df_merged["close_price"]
    
    total_aum = df_merged["valuation"].sum()
    
    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Assets Under Mgmt (AUM)", f"${total_aum:,.2f}")
    col2.metric("Active Assets Tracked", f"{len(df_merged)}")
    col3.metric("System Status", "ONLINE / SECURE", delta_color="normal")
    col4.metric("Logged Compliance Breaches", f"{len(df_alerts)}")
    
    st.divider()
    
    # Visual Layout
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("📊 Portfolio Asset Allocation")
        fig_pie = px.pie(
            df_merged, 
            values="valuation", 
            names="asset_ticker", 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with c2:
        st.subheader("💵 Position Exposure Breakdown (USD)")
        fig_bar = px.bar(
            df_merged.sort_values(by="valuation", ascending=False),
            x="asset_ticker",
            y="valuation",
            color="asset_ticker",
            labels={"valuation": "Valuation ($)", "asset_ticker": "Asset"},
            text_auto='.2s'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.divider()
    
    # Compliance Audit Log Section
    st.subheader("🚨 Immutable Compliance & Risk Alerts Log")
    if not df_alerts.empty:
        st.dataframe(
            df_alerts,
            use_container_width=True,
            column_config={
                "current_value": st.column_config.NumberColumn("Breached Value ($)", format="$%.2f"),
                "threshold_value": st.column_config.NumberColumn("Allowed Limit ($)", format="$%.2f"),
            }
        )
    else:
        st.success("No compliance alerts recorded. Portfolio parameters nominal.")
        
except Exception as e:
    st.error(f"Error connecting to database or loading dashboard data: {e}")
