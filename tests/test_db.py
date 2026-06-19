# ==============================================================================
# tests/test_db.py — Integration tests for the database module.
#
# These tests require a running PostgreSQL instance. They will skip gracefully
# if the database is unavailable.
# ==============================================================================
import sys
import os
import datetime
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def get_test_engine():
    """Try to create a DB engine; skip test if DB is unavailable."""
    try:
        from monitor.db import get_engine, init_db
        engine = get_engine()
        # Test the connection
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        init_db(engine)
        return engine
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


class TestDatabaseOperations:
    """Integration tests for DB insert and fetch operations."""

    def test_insert_and_fetch_metrics(self):
        """Insert a metric row and fetch it back."""
        from monitor.db import insert_metrics, fetch_latest
        engine = get_test_engine()

        metrics = {
            "server": "test-integration-server",
            "ts": datetime.datetime.now(datetime.UTC),
            "cpu_pct": 42.5,
            "mem_pct": 63.2,
            "disk_pct": 28.1,
        }
        insert_metrics(metrics, engine)

        latest = fetch_latest(engine)
        test_server = [s for s in latest if s["server"] == "test-integration-server"]
        assert len(test_server) > 0
        assert test_server[0]["cpu_pct"] == 42.5

    def test_insert_and_fetch_alert(self):
        """Insert an alert and verify it appears in fetch_alerts."""
        from monitor.db import insert_alert, fetch_alerts
        engine = get_test_engine()

        metrics = {
            "server": "test-alert-server",
            "ts": datetime.datetime.now(datetime.UTC),
        }
        breach = {
            "metric": "cpu_pct",
            "value": 95.0,
            "threshold": 85.0,
            "message": "test-alert-server: cpu_pct at 95.0% (limit 85.0%)",
        }
        insert_alert(metrics, breach, engine)

        alerts = fetch_alerts(engine, limit=10)
        test_alerts = [a for a in alerts if a["server"] == "test-alert-server"]
        assert len(test_alerts) > 0
        assert test_alerts[0]["metric"] == "cpu_pct"
        assert test_alerts[0]["value"] == 95.0

    def test_fetch_history_returns_dataframe(self):
        """fetch_history returns a DataFrame even with no data."""
        from monitor.db import fetch_history
        engine = get_test_engine()

        df = fetch_history("nonexistent-server", engine)
        assert list(df.columns) == ["ts", "cpu_pct", "mem_pct", "disk_pct"]
        assert len(df) == 0

    def test_fetch_latest_empty(self):
        """fetch_latest returns a list (possibly empty) without crashing."""
        from monitor.db import fetch_latest
        engine = get_test_engine()

        result = fetch_latest(engine)
        assert isinstance(result, list)
