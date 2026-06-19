# 🖥️ Server Health Monitor

A Python + Bash monitoring system that tracks CPU, memory, and disk usage across a simulated multi-server Docker cluster, persists metrics to PostgreSQL, fires email/Slack alerts on threshold breaches, generates matplotlib trend charts, and serves a real-time web dashboard.

---

## 📐 Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Docker       │     │  Bash Script      │     │  Python Modules   │
│  Containers   │────▶│  collect_metrics  │────▶│  collector.py     │
│  (sim-server) │     │  .sh              │     │  thresholds.py    │
└──────────────┘     └──────────────────┘     │  alerts.py        │
                                               │  db.py            │
                                               │  charts.py        │
                                               └────────┬─────────┘
                                                        │
                                    ┌───────────────────┼───────────────────┐
                                    ▼                   ▼                   ▼
                             ┌────────────┐     ┌────────────┐     ┌────────────┐
                             │ PostgreSQL  │     │ Email/Slack │     │ Matplotlib │
                             │ Storage     │     │ Alerts      │     │ Charts     │
                             └──────┬─────┘     └────────────┘     └────────────┘
                                    │
                                    ▼
                             ┌────────────┐
                             │ Flask       │
                             │ Dashboard   │
                             │ :5050       │
                             └────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **Docker Desktop** (for simulated servers + PostgreSQL)
- **Python 3.10+**
- **Bash** (Git Bash on Windows)

### 1. Clone & Install

```bash
cd server-health-monitor
pip install -r requirements.txt
cp .env.example .env
```

### 2. Start Infrastructure

```bash
cd docker
docker-compose up -d
```

This spins up:
- 3 simulated Ubuntu "servers" (`sim-server-1`, `sim-server-2`, `sim-server-3`)
- PostgreSQL 15 on port `5433` (auto-initializes the schema)

### 3. Run a Collection

```bash
# Single pass: collect → check → store → alert → chart
python scheduler/run_monitor.py
```

### 4. Launch the Dashboard

```bash
python dashboard/app.py
```

Open [http://localhost:5050](http://localhost:5050) in your browser.

### 5. (Optional) Continuous Monitoring

```bash
# Subprocess-based loop (every 5 min by default)
python scheduler/loop.py
```

---

## 🎯 Demo: Triggering Alerts

To demonstrate the alert pipeline live:

```bash
# Spike CPU on server 1 for 30 seconds
docker exec sim-server-1 apt-get update && docker exec sim-server-1 apt-get install -y stress-ng
docker exec sim-server-1 stress-ng --cpu 2 --timeout 30s &

# Run collection immediately
python scheduler/run_monitor.py
```

This will:
1. Detect CPU > 85% threshold
2. Log an alert to PostgreSQL
3. Send Slack/email alerts (if configured)
4. Update the dashboard with a red "Critical" badge and toast notification

---

## 📁 Project Structure

```
server-health-monitor/
├── docker/
│   └── docker-compose.yml      # Simulated cluster + PostgreSQL
├── scripts/
│   └── collect_metrics.sh      # Bash: docker stats + df per container
├── monitor/
│   ├── __init__.py
│   ├── collector.py            # subprocess wrapper around bash script
│   ├── thresholds.py           # Breach detection (configurable)
│   ├── alerts.py               # Email + Slack senders (graceful skip)
│   ├── db.py                   # SQLAlchemy connection + queries
│   └── charts.py               # matplotlib dark-themed trend plots
├── scheduler/
│   ├── run_monitor.py          # Full pipeline orchestration
│   └── loop.py                 # subprocess-based continuous scheduler
├── dashboard/
│   ├── app.py                  # Flask API + static server
│   └── static/
│       ├── index.html          # Dashboard page
│       ├── style.css           # Dark glassmorphic theme
│       └── app.js              # Frontend logic
├── sql/
│   └── schema.sql              # PostgreSQL table definitions
├── tests/
│   ├── test_thresholds.py      # Unit tests
│   ├── test_collector.py       # Mocked subprocess tests
│   └── test_db.py              # Integration tests (skip if no DB)
├── logs/                       # Auto-created log files
├── charts_output/              # Auto-generated trend PNGs
├── .env.example                # Environment variable template
├── requirements.txt
└── README.md
```

---

## ⚙️ Configuration

All settings are configurable via `.env`:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5433` | PostgreSQL port |
| `DB_NAME` | `server_monitor` | Database name |
| `SERVERS` | `sim-server-1,...` | Comma-separated container names |
| `THRESHOLD_CPU` | `85.0` | CPU breach threshold (%) |
| `THRESHOLD_MEM` | `90.0` | Memory breach threshold (%) |
| `THRESHOLD_DISK` | `90.0` | Disk breach threshold (%) |
| `SMTP_HOST` | *(empty)* | SMTP server (leave blank to skip email) |
| `SLACK_WEBHOOK_URL` | *(empty)* | Slack webhook (leave blank to skip) |
| `DASHBOARD_PORT` | `5050` | Dashboard web server port |

---

## 🔄 Scheduling: Cron vs Subprocess

This project implements **two scheduling approaches** deliberately:

### Cron (Production)
```
*/5 * * * * /usr/bin/python3 /path/scheduler/run_monitor.py >> logs/monitor.log 2>&1
```
- ✅ OS-managed → survives script crashes
- ✅ Lower resource usage when idle
- ❌ Requires cron access (not available everywhere)

### Subprocess Loop (Portable)
```bash
python scheduler/loop.py
```
- ✅ Portable across Windows, containers, cloud environments
- ✅ No OS-level scheduling dependency
- ❌ Must be restarted if it crashes
- ❌ Keeps a Python process running

**When to pick which**: Use cron in production Linux environments; use the subprocess loop in development, Docker containers, or Windows where cron isn't available.

---

## 🧪 Testing

```bash
# Unit tests (no Docker/DB needed)
python -m pytest tests/test_thresholds.py tests/test_collector.py -v

# Integration tests (requires running PostgreSQL)
python -m pytest tests/test_db.py -v

# All tests
python -m pytest tests/ -v
```

---

## 📝 Resume Bullet Points

- Built a Python + Bash monitoring system tracking CPU, memory, and disk usage across a simulated multi-server cluster in Docker, with metrics persisted to PostgreSQL
- Implemented automated email and Slack alerting on configurable resource thresholds, using `subprocess` to orchestrate Bash-based collection scripts
- Generated matplotlib trend charts with threshold overlays from historical metric data; built dual cron/subprocess-based scheduling for continuous unattended monitoring
- Developed a real-time web dashboard with glassmorphic dark theme, animated SVG gauges, auto-refresh, and REST API endpoints using Flask

---

## 📋 Tech Stack

| Layer | Technology |
|---|---|
| Simulated Fleet | Docker / docker-compose |
| Metric Collection | Bash (`docker stats`, `df`) via Python `subprocess` |
| Core Modules | `os`, `sys`, `subprocess`, `datetime`, `logging` |
| Storage | PostgreSQL via `psycopg2` / SQLAlchemy |
| Alerting | `smtplib` (email) + `requests` (Slack webhook) |
| Charts | `matplotlib` |
| Dashboard | Flask + vanilla HTML/CSS/JS |
| Scheduling | Cron + subprocess-based loop |
"# Server-health-monitor" 
