# ==============================================================================
# monitor/thresholds.py — Configurable resource thresholds and breach detection.
# ==============================================================================
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Thresholds are configurable via environment variables, with sensible defaults.
THRESHOLDS = {
    "cpu_pct": float(os.getenv("THRESHOLD_CPU", "85.0")),
    "mem_pct": float(os.getenv("THRESHOLD_MEM", "90.0")),
    "disk_pct": float(os.getenv("THRESHOLD_DISK", "90.0")),
}


def check_breach(metrics: dict) -> list[str]:
    """Check if any metric exceeds its configured threshold.

    Args:
        metrics: dict with keys including server, cpu_pct, mem_pct, disk_pct

    Returns:
        List of human-readable breach messages (empty if no breaches).
    """
    return [
        f"{metrics['server']}: {key} at {metrics[key]}% (limit {limit}%)"
        for key, limit in THRESHOLDS.items()
        if metrics.get(key, 0) >= limit
    ]


def check_breach_detailed(metrics: dict) -> list[dict]:
    """Check for threshold breaches and return structured data for DB storage.

    Args:
        metrics: dict with keys including server, ts, cpu_pct, mem_pct, disk_pct

    Returns:
        List of dicts, each with: metric, value, threshold, message
    """
    breaches = []
    for key, limit in THRESHOLDS.items():
        value = metrics.get(key, 0)
        if value >= limit:
            breach = {
                "metric": key,
                "value": value,
                "threshold": limit,
                "message": f"{metrics['server']}: {key} at {value}% (limit {limit}%)",
            }
            breaches.append(breach)
            logger.warning(breach["message"])
    return breaches
