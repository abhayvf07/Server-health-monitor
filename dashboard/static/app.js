// =============================================================================
// Server Health Monitor — Dashboard JavaScript
// Fetches metrics from the Flask API, renders animated gauge cards, charts,
// and alert history with auto-refresh and toast notifications.
// =============================================================================

const API_BASE = '';
const REFRESH_INTERVAL = 30; // seconds

// ── State ────────────────────────────────────────────────────────────────────
let autoRefresh = true;
let countdown = REFRESH_INTERVAL;
let countdownTimer = null;
let previousAlertIds = new Set();

// ── Gauge SVG constants ──────────────────────────────────────────────────────
const GAUGE_RADIUS = 33;
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * GAUGE_RADIUS;

// ── Color helpers ────────────────────────────────────────────────────────────
const METRIC_COLORS = {
    cpu_pct:  { color: '#00d4ff', label: 'CPU',    icon: '⚡' },
    mem_pct:  { color: '#a855f7', label: 'Memory', icon: '🧠' },
    disk_pct: { color: '#f97316', label: 'Disk',   icon: '💾' },
};

const THRESHOLDS = {
    cpu_pct:  85,
    mem_pct:  90,
    disk_pct: 90,
};

function getStatusColor(value, metric) {
    const threshold = THRESHOLDS[metric] || 85;
    if (value >= threshold) return '#ef4444';
    if (value >= threshold * 0.8) return '#eab308';
    return METRIC_COLORS[metric]?.color || '#00d4ff';
}

function getServerStatus(server) {
    for (const [key, threshold] of Object.entries(THRESHOLDS)) {
        if ((server[key] || 0) >= threshold) return 'critical';
    }
    for (const [key, threshold] of Object.entries(THRESHOLDS)) {
        if ((server[key] || 0) >= threshold * 0.8) return 'warning';
    }
    return 'healthy';
}

// ── DOM Helpers ──────────────────────────────────────────────────────────────

function formatTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDateTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleString('en-US', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
}

function timeAgo(isoString) {
    if (!isoString) return 'never';
    const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (seconds < 10) return 'just now';
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
}

// ── Toast Notifications ──────────────────────────────────────────────────────

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'}</span>
        <span>${message}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Gauge Rendering ──────────────────────────────────────────────────────────

function createGaugeSVG(value, metric) {
    const color = getStatusColor(value, metric);
    const offset = GAUGE_CIRCUMFERENCE - (value / 100) * GAUGE_CIRCUMFERENCE;

    return `
        <div class="gauge">
            <div class="gauge-ring">
                <svg viewBox="0 0 80 80">
                    <circle class="bg-ring" cx="40" cy="40" r="${GAUGE_RADIUS}"/>
                    <circle class="value-ring"
                        cx="40" cy="40" r="${GAUGE_RADIUS}"
                        stroke="${color}"
                        stroke-dasharray="${GAUGE_CIRCUMFERENCE}"
                        stroke-dashoffset="${offset}"
                    />
                </svg>
                <div class="gauge-value">
                    ${value.toFixed(1)}<span class="unit">%</span>
                </div>
            </div>
            <span class="gauge-label">${METRIC_COLORS[metric]?.label || metric}</span>
        </div>
    `;
}

// ── Server Card Rendering ────────────────────────────────────────────────────

function renderServerCard(server) {
    const status = getServerStatus(server);
    const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);

    return `
        <div class="glass-card server-card" id="server-${server.server}">
            <div class="server-card-header">
                <div class="server-name">
                    <div class="server-icon">
                        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                            <rect x="2" y="3" width="14" height="4.5" rx="1" stroke="#00d4ff" stroke-width="1.2"/>
                            <rect x="2" y="10.5" width="14" height="4.5" rx="1" stroke="#00d4ff" stroke-width="1.2"/>
                            <circle cx="5" cy="5.25" r="0.8" fill="#00d4ff"/>
                            <circle cx="5" cy="12.75" r="0.8" fill="#00d4ff"/>
                        </svg>
                    </div>
                    ${server.server}
                </div>
                <span class="server-status-badge ${status}">
                    <span class="status-dot"></span>
                    ${statusLabel}
                </span>
            </div>
            <div class="gauges">
                ${createGaugeSVG(server.cpu_pct || 0, 'cpu_pct')}
                ${createGaugeSVG(server.mem_pct || 0, 'mem_pct')}
                ${createGaugeSVG(server.disk_pct || 0, 'disk_pct')}
            </div>
            <div class="server-card-footer">
                <span>Last update: ${timeAgo(server.ts)}</span>
                <span>${formatTime(server.ts)}</span>
            </div>
        </div>
    `;
}

// ── Chart Rendering ──────────────────────────────────────────────────────────

function renderChartCard(serverName) {
    const timestamp = Date.now();
    return `
        <div class="glass-card chart-card" id="chart-${serverName}">
            <div class="chart-card-title">📊 ${serverName}</div>
            <img
                src="/api/charts/${serverName}?t=${timestamp}"
                alt="${serverName} trend chart"
                onload="this.classList.add('loaded')"
                onerror="this.parentElement.querySelector('.chart-placeholder').style.display='flex'; this.style.display='none';"
            />
            <div class="chart-placeholder" style="display:none;">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" opacity="0.3">
                    <polyline points="4,24 10,16 16,20 22,10 28,14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
                </svg>
                <p>No chart data yet — run a collection first</p>
            </div>
        </div>
    `;
}

// ── Alert Row Rendering ──────────────────────────────────────────────────────

function renderAlertRow(alert, isNew = false) {
    const value = alert.value || 0;
    const threshold = alert.threshold || 0;
    const severity = value >= threshold * 1.1 ? 'critical' : 'warning';
    const valueClass = severity === 'critical' ? 'high' : 'medium';

    return `
        <tr class="${isNew ? 'new-alert' : ''}">
            <td class="cell-mono">${formatDateTime(alert.ts)}</td>
            <td>${alert.server}</td>
            <td>${METRIC_COLORS[alert.metric]?.label || alert.metric}</td>
            <td class="cell-value ${valueClass}">${value.toFixed(1)}%</td>
            <td class="cell-mono">${threshold.toFixed(1)}%</td>
            <td><span class="severity-badge ${severity}">● ${severity}</span></td>
        </tr>
    `;
}

// ── API Calls ────────────────────────────────────────────────────────────────

async function fetchServers() {
    try {
        const res = await fetch(`${API_BASE}/api/servers`);
        const data = await res.json();

        if (data.status === 'ok' && data.servers.length > 0) {
            const grid = document.getElementById('serverGrid');
            grid.innerHTML = data.servers.map(renderServerCard).join('');

            // Also update charts section
            const chartsGrid = document.getElementById('chartsGrid');
            chartsGrid.innerHTML = data.servers.map(s => renderChartCard(s.server)).join('');

            updateStatus('online', `${data.servers.length} servers monitored`);
            document.getElementById('lastUpdated').textContent = `Updated ${new Date().toLocaleTimeString()}`;
        } else if (data.status === 'ok' && data.servers.length === 0) {
            updateStatus('online', 'No metric data yet');
            showPlaceholderCards();
        } else {
            updateStatus('error', 'API error');
        }
    } catch (e) {
        console.error('Failed to fetch servers:', e);
        updateStatus('error', 'Connection failed');
        showPlaceholderCards();
    }
}

async function fetchAlerts() {
    try {
        const res = await fetch(`${API_BASE}/api/alerts?limit=50`);
        const data = await res.json();

        if (data.status === 'ok') {
            const tbody = document.getElementById('alertsBody');
            const emptyState = document.getElementById('alertsEmpty');
            const countBadge = document.getElementById('alertCount');

            countBadge.textContent = data.alerts.length;
            countBadge.className = data.alerts.length === 0 ? 'badge zero' : 'badge';

            if (data.alerts.length === 0) {
                tbody.innerHTML = '';
                emptyState.style.display = 'flex';
                document.querySelector('.alerts-table').style.display = 'none';
            } else {
                emptyState.style.display = 'none';
                document.querySelector('.alerts-table').style.display = 'table';

                // Detect new alerts for animation
                const newAlertIds = new Set(data.alerts.map(a => a.id));
                tbody.innerHTML = data.alerts.map(alert => {
                    const isNew = !previousAlertIds.has(alert.id) && previousAlertIds.size > 0;
                    if (isNew) {
                        showToast(`🚨 ${alert.server}: ${METRIC_COLORS[alert.metric]?.label || alert.metric} at ${alert.value?.toFixed(1)}%`, 'error');
                    }
                    return renderAlertRow(alert, isNew);
                }).join('');
                previousAlertIds = newAlertIds;
            }
        }
    } catch (e) {
        console.error('Failed to fetch alerts:', e);
    }
}

function showPlaceholderCards() {
    const grid = document.getElementById('serverGrid');
    const servers = ['sim-server-1', 'sim-server-2', 'sim-server-3'];
    grid.innerHTML = servers.map(name => renderServerCard({
        server: name, cpu_pct: 0, mem_pct: 0, disk_pct: 0, ts: null,
    })).join('');

    const chartsGrid = document.getElementById('chartsGrid');
    chartsGrid.innerHTML = servers.map(renderChartCard).join('');
}

function updateStatus(status, text) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    indicator.className = `status-indicator ${status}`;
    statusText.textContent = text;
}

// ── Collect Now Button ───────────────────────────────────────────────────────

async function triggerCollect() {
    const btn = document.getElementById('collectBtn');
    btn.classList.add('loading');
    btn.disabled = true;

    showToast('Starting metric collection...', 'info');

    try {
        const res = await fetch(`${API_BASE}/api/collect`, { method: 'POST' });
        const data = await res.json();

        if (data.status === 'ok') {
            showToast('Collection complete!', 'success');
            await refreshAll();
        } else {
            showToast(`Collection failed: ${data.message || 'Unknown error'}`, 'error');
        }
    } catch (e) {
        showToast('Collection request failed', 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// ── Auto-refresh ─────────────────────────────────────────────────────────────

function startCountdown() {
    stopCountdown();
    countdown = REFRESH_INTERVAL;
    updateCountdownDisplay();

    countdownTimer = setInterval(() => {
        countdown--;
        updateCountdownDisplay();

        if (countdown <= 0) {
            refreshAll();
            countdown = REFRESH_INTERVAL;
        }
    }, 1000);
}

function stopCountdown() {
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
    document.getElementById('countdown').textContent = '';
}

function updateCountdownDisplay() {
    document.getElementById('countdown').textContent = `${countdown}s`;
}

function toggleAutoRefresh() {
    const toggle = document.getElementById('autoRefreshToggle');
    autoRefresh = !autoRefresh;
    toggle.classList.toggle('active', autoRefresh);

    if (autoRefresh) {
        startCountdown();
    } else {
        stopCountdown();
    }
}

// ── Refresh All Data ─────────────────────────────────────────────────────────

async function refreshAll() {
    await Promise.all([fetchServers(), fetchAlerts()]);
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Set up auto-refresh toggle
    const toggle = document.getElementById('autoRefreshToggle');
    toggle.addEventListener('click', toggleAutoRefresh);
    toggle.classList.add('active');

    // Initial data load
    refreshAll();

    // Start auto-refresh countdown
    startCountdown();
});
