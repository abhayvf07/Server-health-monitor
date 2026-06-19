# ==============================================================================
# dashboard/app.py — Flask API + static file server for the monitoring dashboard.
# ==============================================================================
import os
import sys
import logging
from flask import Flask, jsonify, request, send_from_directory, send_file
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

from monitor.db import get_engine, init_db, fetch_latest, fetch_alerts, fetch_history
from monitor.charts import plot_trend

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "charts_output")
os.makedirs(CHARTS_DIR, exist_ok=True)

# Lazy engine initialization
_engine = None


def get_db_engine():
    """Lazy-initialize and return the database engine."""
    global _engine
    if _engine is None:
        _engine = get_engine()
        init_db(_engine)
    return _engine


# ── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the dashboard HTML page."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/servers")
def api_servers():
    """Return the latest metrics for all monitored servers."""
    try:
        engine = get_db_engine()
        servers = fetch_latest(engine)
        return jsonify({"status": "ok", "servers": servers})
    except Exception as e:
        logger.error(f"API /servers error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/alerts")
def api_alerts():
    """Return recent alerts (last 50 by default)."""
    try:
        limit = request.args.get("limit", 50, type=int)
        engine = get_db_engine()
        alerts = fetch_alerts(engine, limit=limit)
        return jsonify({"status": "ok", "alerts": alerts})
    except Exception as e:
        logger.error(f"API /alerts error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/history/<server>")
def api_history(server):
    """Return historical metric data for a specific server."""
    try:
        hours = request.args.get("hours", 24, type=int)
        engine = get_db_engine()
        df = fetch_history(server, engine, hours=hours)
        data = df.to_dict(orient="records")
        # Convert timestamps to ISO strings
        for row in data:
            if row.get("ts"):
                row["ts"] = row["ts"].isoformat()
        return jsonify({"status": "ok", "server": server, "history": data})
    except Exception as e:
        logger.error(f"API /history/{server} error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/charts/<server>")
def api_chart(server):
    """Serve a generated trend chart PNG for a server."""
    chart_path = os.path.join(CHARTS_DIR, f"{server}_trend.png")
    if os.path.exists(chart_path):
        return send_file(chart_path, mimetype="image/png")

    # Try generating on the fly
    try:
        engine = get_db_engine()
        df = fetch_history(server, engine)
        result = plot_trend(df, server, out_dir=CHARTS_DIR)
        if result and os.path.exists(result):
            return send_file(result, mimetype="image/png")
        return jsonify({"status": "error", "message": "No data to chart"}), 404
    except Exception as e:
        logger.error(f"API /charts/{server} error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/collect", methods=["POST"])
def api_collect():
    """Trigger an immediate collection run across all servers."""
    try:
        import subprocess
        run_script = os.path.join(os.path.dirname(__file__), "..", "scheduler", "run_monitor.py")
        result = subprocess.run(
            [sys.executable, run_script],
            capture_output=True, text=True, timeout=120,
        )
        return jsonify({
            "status": "ok" if result.returncode == 0 else "error",
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Collection timed out"}), 504
    except Exception as e:
        logger.error(f"API /collect error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", "5050"))
    logger.info(f"Starting dashboard on {host}:{port}")
    app.run(host=host, port=port, debug=True)
