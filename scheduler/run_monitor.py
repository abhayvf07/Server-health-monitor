# ==============================================================================
# scheduler/run_monitor.py — Full pipeline orchestration.
#
# One execution pass: collect metrics → check thresholds → store to DB →
# fire alerts → generate trend charts for all monitored servers.
# ==============================================================================
import os
import sys
import logging
from datetime import datetime, UTC
from dotenv import load_dotenv

# Add project root to sys.path so imports work from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

from monitor.collector import collect
from monitor.thresholds import check_breach_detailed
from monitor.alerts import send_email_alert, send_slack_alert
from monitor.db import get_engine, init_db, insert_metrics, insert_alert, fetch_history
from monitor.charts import plot_trend

# ── Logging setup ────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "monitor.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ── Server list from env ─────────────────────────────────────────────────────
SERVERS = os.getenv("SERVERS", "sim-server-1,sim-server-2,sim-server-3").split(",")
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "charts_output")


def run():
    """Execute one full monitoring pass across all configured servers."""
    logger.info(f"{'='*60}")
    logger.info(f"Monitor run started at {datetime.now(UTC).isoformat()}")
    logger.info(f"Monitoring servers: {', '.join(SERVERS)}")
    logger.info(f"{'='*60}")

    engine = get_engine()
    init_db(engine)

    total_breaches = 0

    for server in SERVERS:
        server = server.strip()
        if not server:
            continue

        try:
            # ── 1. Collect metrics ───────────────────────────────────────────
            logger.info(f"Collecting metrics for {server}...")
            metrics = collect(server)

            # ── 2. Store metrics ─────────────────────────────────────────────
            insert_metrics(metrics, engine)

            # ── 3. Check thresholds ──────────────────────────────────────────
            breaches = check_breach_detailed(metrics)

            for breach in breaches:
                total_breaches += 1
                # ── 4. Fire alerts ───────────────────────────────────────────
                send_slack_alert(breach["message"])
                send_email_alert("🚨 Server Threshold Breach", breach["message"])
                # ── 5. Log alert to DB ───────────────────────────────────────
                insert_alert(metrics, breach, engine)

            if not breaches:
                logger.info(f"  [OK] {server}: All metrics within thresholds")

        except Exception as e:
            logger.error(f"  [ERROR] Failed to process {server}: {e}")
            continue

    # ── 6. Generate trend charts ─────────────────────────────────────────────
    logger.info("Generating trend charts...")
    os.makedirs(CHARTS_DIR, exist_ok=True)

    for server in SERVERS:
        server = server.strip()
        if not server:
            continue
        try:
            df = fetch_history(server, engine)
            plot_trend(df, server, out_dir=CHARTS_DIR)
        except Exception as e:
            logger.error(f"  Chart generation failed for {server}: {e}")

    logger.info(f"{'='*60}")
    logger.info(f"Run complete. Total breaches: {total_breaches}")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    run()
