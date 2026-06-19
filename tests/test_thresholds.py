# ==============================================================================
# tests/test_thresholds.py — Unit tests for breach detection logic.
# ==============================================================================
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from monitor.thresholds import check_breach, check_breach_detailed, THRESHOLDS


class TestCheckBreach:
    """Tests for the simple check_breach function."""

    def test_no_breach_all_below(self):
        """All metrics well below thresholds → empty list."""
        metrics = {"server": "test-server", "cpu_pct": 10.0, "mem_pct": 20.0, "disk_pct": 30.0}
        result = check_breach(metrics)
        assert result == []

    def test_cpu_breach(self):
        """CPU above threshold → exactly one breach."""
        metrics = {"server": "test-server", "cpu_pct": 95.0, "mem_pct": 20.0, "disk_pct": 30.0}
        result = check_breach(metrics)
        assert len(result) == 1
        assert "cpu_pct" in result[0]
        assert "95.0%" in result[0]

    def test_all_breach(self):
        """All metrics above thresholds → three breaches."""
        metrics = {"server": "test-server", "cpu_pct": 99.0, "mem_pct": 95.0, "disk_pct": 99.0}
        result = check_breach(metrics)
        assert len(result) == 3

    def test_exactly_at_threshold(self):
        """Metric exactly at threshold → counts as breach (>=)."""
        metrics = {
            "server": "test-server",
            "cpu_pct": THRESHOLDS["cpu_pct"],
            "mem_pct": 0.0,
            "disk_pct": 0.0,
        }
        result = check_breach(metrics)
        assert len(result) == 1

    def test_just_below_threshold(self):
        """Metric just below threshold → no breach."""
        metrics = {
            "server": "test-server",
            "cpu_pct": THRESHOLDS["cpu_pct"] - 0.01,
            "mem_pct": 0.0,
            "disk_pct": 0.0,
        }
        result = check_breach(metrics)
        assert result == []

    def test_zero_values(self):
        """All zeros → no breach."""
        metrics = {"server": "test-server", "cpu_pct": 0.0, "mem_pct": 0.0, "disk_pct": 0.0}
        result = check_breach(metrics)
        assert result == []

    def test_server_name_in_message(self):
        """Breach message includes the server name."""
        metrics = {"server": "my-server-42", "cpu_pct": 99.0, "mem_pct": 0.0, "disk_pct": 0.0}
        result = check_breach(metrics)
        assert "my-server-42" in result[0]


class TestCheckBreachDetailed:
    """Tests for the structured check_breach_detailed function."""

    def test_no_breach_returns_empty(self):
        metrics = {"server": "test", "ts": "2024-01-01", "cpu_pct": 10.0, "mem_pct": 10.0, "disk_pct": 10.0}
        result = check_breach_detailed(metrics)
        assert result == []

    def test_breach_structure(self):
        """Each breach dict has the correct keys."""
        metrics = {"server": "test", "ts": "2024-01-01", "cpu_pct": 99.0, "mem_pct": 10.0, "disk_pct": 10.0}
        result = check_breach_detailed(metrics)
        assert len(result) == 1
        breach = result[0]
        assert breach["metric"] == "cpu_pct"
        assert breach["value"] == 99.0
        assert breach["threshold"] == THRESHOLDS["cpu_pct"]
        assert "message" in breach

    def test_multiple_breaches(self):
        metrics = {"server": "test", "ts": "2024-01-01", "cpu_pct": 99.0, "mem_pct": 99.0, "disk_pct": 99.0}
        result = check_breach_detailed(metrics)
        assert len(result) == 3
        metrics_breached = {b["metric"] for b in result}
        assert metrics_breached == {"cpu_pct", "mem_pct", "disk_pct"}
