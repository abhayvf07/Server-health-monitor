-- ==============================================================================
-- Server Health Monitor — Database Schema
-- PostgreSQL 15+
-- ==============================================================================

-- ── Metrics table ─────────────────────────────────────────────────────────────
-- Stores periodic CPU, memory, and disk snapshots per server.
CREATE TABLE IF NOT EXISTS server_metrics (
    id        SERIAL PRIMARY KEY,
    server    VARCHAR(50)   NOT NULL,
    ts        TIMESTAMP     NOT NULL DEFAULT NOW(),
    cpu_pct   NUMERIC(5,2),
    mem_pct   NUMERIC(5,2),
    disk_pct  NUMERIC(5,2)
);

CREATE INDEX IF NOT EXISTS idx_metrics_server_ts ON server_metrics (server, ts DESC);

-- ── Alerts table ──────────────────────────────────────────────────────────────
-- Logs every threshold breach for audit and dashboard display.
CREATE TABLE IF NOT EXISTS alerts (
    id        SERIAL PRIMARY KEY,
    server    VARCHAR(50)   NOT NULL,
    ts        TIMESTAMP     NOT NULL DEFAULT NOW(),
    metric    VARCHAR(20),
    value     NUMERIC(5,2),
    threshold NUMERIC(5,2),
    message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_server_ts ON alerts (server, ts DESC);
