# ==============================================================================
# scheduler/loop.py — Subprocess-based continuous scheduler.
#
# An alternative to cron that's portable across environments without cron
# access. Uses subprocess to invoke run_monitor.py at configurable intervals.
#
# Why this over cron?
#   - Portable: works on Windows, containers, any env without cron
#   - Self-contained: no OS-level scheduling dependency
#
# Why cron over this?
#   - OS-managed: survives script crashes automatically
#   - Lower resource footprint when idle
#   - Standard production approach on Linux
# ==============================================================================
import subprocess
import sys
import os
import time
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

INTERVAL = int(os.getenv("COLLECT_INTERVAL", "300"))  # seconds
MONITOR_SCRIPT = os.path.join(os.path.dirname(__file__), "run_monitor.py")


def main():
    """Run the monitoring pipeline in a continuous loop with configurable interval."""
    logger.info(f"Starting continuous monitor loop (interval: {INTERVAL}s)")
    logger.info(f"Script: {MONITOR_SCRIPT}")
    logger.info("Press Ctrl+C to stop.\n")

    iteration = 0
    while True:
        iteration += 1
        logger.info(f"── Iteration {iteration} ──")

        try:
            result = subprocess.run(
                [sys.executable, MONITOR_SCRIPT],
                cwd=os.path.dirname(MONITOR_SCRIPT),
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning(f"Monitor exited with code {result.returncode}")
        except subprocess.TimeoutExpired:
            logger.error("Monitor run timed out (60s limit)")
        except Exception as e:
            logger.error(f"Monitor run failed: {e}")

        logger.info(f"Sleeping {INTERVAL}s until next collection...\n")
        try:
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            logger.info("Loop stopped by user.")
            break


if __name__ == "__main__":
    main()
