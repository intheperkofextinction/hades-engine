# 🛡️ Hades Quantitative Risk & Execution Engine

An institutional-grade portfolio risk engine built in Python and PostgreSQL. Features real-time Value at Risk (VaR) calculations, Geometric Brownian Motion (GBM) Monte Carlo simulations, automated limit breach detection, and stress testing.

## 🏗️ System Architecture
- **Database Engine:** PostgreSQL (Async append-only transactional ledger)
- **Quantitative Core:** NumPy & Pandas (10,000-path Monte Carlo VaR / CVaR)
- **Compliance Desk:** Automated Risk Sentinel & Rebalancing Execution Engine
- **Visualization:** Streamlit & Plotly Executive Command Dashboard

## 🚀 Modules
- `quant_engine/monte_carlo_engine.py` - Vectorized 30-day VaR/CVaR simulator
- `quant_engine/stress_tester.py` - Black Swan historical macro shock suite
- `compliance/risk_sentinel.py` - Automated limit breach detector & database auditor
- `database/execute_rebalance.py` - Risk-mitigation order execution desk
- `data_stream/live_stream.py` - Live WebSocket market price pipeline
- `dashboard/app.py` - Executive visual command center

## 🛠️ Quickstart
```bash
# Initialize Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run Dashboard
streamlit run dashboard/app.py
