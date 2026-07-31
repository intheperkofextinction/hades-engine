import sys
import os
import asyncio
import logging
import psycopg

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CONN_INFO

# Define institutional compliance risk thresholds
MAX_VAR_PCT = -0.05   # Maximum allowed 30-Day 95% VaR (-5.0%)
MAX_CVAR_PCT = -0.08  # Maximum allowed 30-Day 95% CVaR (-8.0%)


async def audit_compliance_limits(var_95: float, cvar_95: float, portfolio_value: float = None):
    """
    Audits pre-calculated portfolio VaR and CVaR metrics against policy limits.
    Persists policy breach logs to PostgreSQL risk_alerts table.

    :param var_95: 30-Day 95% Value at Risk (float, e.g. -0.0861)
    :param cvar_95: 30-Day 95% Conditional Value at Risk (float, e.g. -0.1047)
    :param portfolio_value: Total portfolio market value in USD (used for audit context only)
    :return: list of breach description strings (empty if no breaches)
    """
    logging.info("[🛡️ Sentinel] Auditing risk metrics against compliance thresholds...")

    # Each tuple: (metric_type label, current value, threshold limit)
    checks = [
        ("VAR_95", var_95, MAX_VAR_PCT),
        ("CVAR_95", cvar_95, MAX_CVAR_PCT),
    ]

    # VaR and CVaR are negative losses: a MORE negative number means a LARGER loss
    breaches = [
        (metric_type, current_val, limit_val)
        for metric_type, current_val, limit_val in checks
        if current_val < limit_val
    ]

    if not breaches:
        logging.info("[🛡️ Sentinel] ✅ All risk metrics within compliance thresholds.")
        return []

    logging.warning(f"[⚠️ RISK BREACH DETECTED] {len(breaches)} policy breach(es) identified!")
    for metric_type, current_val, limit_val in breaches:
        logging.warning(
            f"    • {metric_type} Limit Breach: {current_val:.2%} "
            f"(Policy Limit: {limit_val:.2%})"
        )

    # Persist breach logs to database
    try:
        async with await psycopg.AsyncConnection.connect(CONN_INFO) as conn:
            async with conn.cursor() as cur:
                for metric_type, current_val, limit_val in breaches:
                    await cur.execute(
                        """
                        INSERT INTO risk_alerts
                            (alert_timestamp, metric_type, current_value, threshold_value,
                             portfolio_valuation, severity, status)
                        VALUES (NOW(), %s, %s, %s, %s, 'CRITICAL', 'OPEN');
                        """,
                        (metric_type, current_val, limit_val, portfolio_value or 0),
                    )
                await conn.commit()
        logging.info("[🛡️ Sentinel] Breach events logged to PostgreSQL 'risk_alerts' table.")
    except Exception as e:
        logging.error(f"[🛡️ Sentinel] Could not record breach to DB table: {e}")

    return [
        f"{metric_type} Limit Breach: {current_val:.2%} (Policy Limit: {limit_val:.2%})"
        for metric_type, current_val, limit_val in breaches
    ]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Test execution with sample metrics (should trigger both breaches)
    asyncio.run(audit_compliance_limits(var_95=-0.0861, cvar_95=-0.1047, portfolio_value=125000.0))
