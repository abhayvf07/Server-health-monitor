# ==============================================================================
# monitor/db.py — Database connection, inserts, and queries via SQLAlchemy.
# ==============================================================================
import os
import logging
import pandas as pd
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_engine():
    """Create and return a SQLAlchemy engine from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5433")
    name = os.getenv("DB_NAME", "server_monitor")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")

    url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    engine = create_engine(url, pool_pre_ping=True)
    logger.info(f"Database engine created: {host}:{port}/{name}")
    return engine


def init_db(engine):
    """Run the schema.sql file to initialize database tables."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
    try:
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        with engine.begin() as conn:
            conn.execute(text(schema_sql))
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


def insert_metrics(metrics: dict, engine):
    """Insert a single metrics snapshot into the server_metrics table.

    Args:
        metrics: dict with keys: server, ts, cpu_pct, mem_pct, disk_pct
        engine: SQLAlchemy engine
    """
    query = text("""
        INSERT INTO server_metrics (server, ts, cpu_pct, mem_pct, disk_pct)
        VALUES (:server, :ts, :cpu_pct, :mem_pct, :disk_pct)
    """)
    try:
        with engine.begin() as conn:
            conn.execute(query, metrics)
        logger.info(f"Metrics inserted for {metrics['server']}")
    except Exception as e:
        logger.error(f"Failed to insert metrics for {metrics['server']}: {e}")
        raise


def insert_alert(metrics: dict, breach_info: dict, engine):
    """Insert an alert record into the alerts table.

    Args:
        metrics:     dict with keys: server, ts
        breach_info: dict with keys: metric, value, threshold, message
        engine:      SQLAlchemy engine
    """
    query = text("""
        INSERT INTO alerts (server, ts, metric, value, threshold, message)
        VALUES (:server, :ts, :metric, :value, :threshold, :message)
    """)
    record = {
        "server": metrics["server"],
        "ts": metrics["ts"],
        "metric": breach_info["metric"],
        "value": breach_info["value"],
        "threshold": breach_info["threshold"],
        "message": breach_info["message"],
    }
    try:
        with engine.begin() as conn:
            conn.execute(query, record)
        logger.info(f"Alert inserted for {metrics['server']}: {breach_info['metric']}")
    except Exception as e:
        logger.error(f"Failed to insert alert: {e}")
        raise


def fetch_history(server: str, engine, hours: int = 24) -> pd.DataFrame:
    """Fetch metric history for a specific server.

    Args:
        server: Container/server name
        engine: SQLAlchemy engine
        hours:  Number of hours of history to retrieve (default 24)

    Returns:
        pandas DataFrame with columns: ts, cpu_pct, mem_pct, disk_pct
    """
    query = text("""
        SELECT ts, cpu_pct, mem_pct, disk_pct
        FROM server_metrics
        WHERE server = :server AND ts >= :since
        ORDER BY ts ASC
    """)
    since = datetime.now(UTC) - timedelta(hours=hours)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"server": server, "since": since})
            df = pd.DataFrame(result.fetchall(), columns=["ts", "cpu_pct", "mem_pct", "disk_pct"])
        return df
    except Exception as e:
        logger.error(f"Failed to fetch history for {server}: {e}")
        return pd.DataFrame(columns=["ts", "cpu_pct", "mem_pct", "disk_pct"])


def fetch_latest(engine) -> list[dict]:
    """Fetch the most recent metric row for each server.

    Returns:
        List of dicts, each with: server, ts, cpu_pct, mem_pct, disk_pct
    """
    query = text("""
        SELECT DISTINCT ON (server) server, ts, cpu_pct, mem_pct, disk_pct
        FROM server_metrics
        ORDER BY server, ts DESC
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
        return [
            {
                "server": r[0],
                "ts": r[1].isoformat() if r[1] else None,
                "cpu_pct": float(r[2]) if r[2] is not None else 0,
                "mem_pct": float(r[3]) if r[3] is not None else 0,
                "disk_pct": float(r[4]) if r[4] is not None else 0,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Failed to fetch latest metrics: {e}")
        return []


def fetch_alerts(engine, limit: int = 50) -> list[dict]:
    """Fetch the most recent alerts across all servers.

    Args:
        engine: SQLAlchemy engine
        limit:  Max number of alerts to return (default 50)

    Returns:
        List of dicts with: id, server, ts, metric, value, threshold, message
    """
    query = text("""
        SELECT id, server, ts, metric, value, threshold, message
        FROM alerts
        ORDER BY ts DESC
        LIMIT :limit
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"limit": limit})
            rows = result.fetchall()
        return [
            {
                "id": r[0],
                "server": r[1],
                "ts": r[2].isoformat() if r[2] else None,
                "metric": r[3],
                "value": float(r[4]) if r[4] is not None else 0,
                "threshold": float(r[5]) if r[5] is not None else 0,
                "message": r[6],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {e}")
        return []
