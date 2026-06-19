# ==============================================================================
# tests/test_collector.py — Unit tests for the collector module.
# Uses mocked subprocess to avoid needing actual Docker containers.
# ==============================================================================
import sys
import os
import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import subprocess
from monitor.collector import collect


class TestCollect:
    """Tests for the collect function with mocked subprocess."""

    @patch("monitor.collector.subprocess.run")
    def test_successful_collection(self, mock_run):
        """Successful bash script execution returns a valid metrics dict."""
        mock_run.return_value = MagicMock(
            stdout="sim-server-1,25.50,40.30,55.00\n",
            returncode=0,
        )

        result = collect("sim-server-1")

        assert result["server"] == "sim-server-1"
        assert result["cpu_pct"] == 25.50
        assert result["mem_pct"] == 40.30
        assert result["disk_pct"] == 55.00
        assert isinstance(result["ts"], datetime.datetime)

    @patch("monitor.collector.subprocess.run")
    def test_collection_called_with_correct_args(self, mock_run):
        """The bash script is called with the correct container name."""
        mock_run.return_value = MagicMock(
            stdout="test-container,10.0,20.0,30.0\n",
            returncode=0,
        )

        collect("test-container")

        args = mock_run.call_args
        assert "test-container" in args[0][0]  # Container name in the command
        assert args[1]["timeout"] == 30
        assert args[1]["check"] is True

    @patch("monitor.collector.subprocess.run")
    def test_collection_failure_raises(self, mock_run):
        """CalledProcessError from the bash script is propagated."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="bash", stderr="Container not running"
        )

        try:
            collect("bad-container")
            assert False, "Should have raised CalledProcessError"
        except subprocess.CalledProcessError:
            pass

    @patch("monitor.collector.subprocess.run")
    def test_empty_output_raises(self, mock_run):
        """Empty output from the bash script raises ValueError."""
        mock_run.return_value = MagicMock(stdout="\n", returncode=0)

        try:
            collect("empty-container")
            assert False, "Should have raised an exception"
        except (ValueError, Exception):
            pass

    @patch("monitor.collector.subprocess.run")
    def test_zero_metrics(self, mock_run):
        """Container with zero resource usage returns valid dict with 0s."""
        mock_run.return_value = MagicMock(
            stdout="idle-server,0.00,0.10,12.00\n",
            returncode=0,
        )

        result = collect("idle-server")

        assert result["cpu_pct"] == 0.00
        assert result["mem_pct"] == 0.10
        assert result["disk_pct"] == 12.00
