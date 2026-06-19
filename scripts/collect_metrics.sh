#!/bin/bash
# ==============================================================================
# collect_metrics.sh — Collects CPU, memory, and disk metrics from a Docker
#                      container using 'docker stats' and 'docker exec df'.
#
# Usage:  ./collect_metrics.sh <container_name>
# Output: <container_name>,<cpu_%>,<mem_%>,<disk_%>
# ==============================================================================

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <container_name>" >&2
    exit 1
fi

CONTAINER="$1"

# Verify the container is running
if ! docker inspect --format='{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q "true"; then
    echo "Error: Container '$CONTAINER' is not running." >&2
    exit 1
fi

# ── Collect CPU and Memory via docker stats ──────────────────────────────────
STATS=$(docker stats "$CONTAINER" --no-stream --format "{{.CPUPerc}},{{.MemPerc}}")
CPU=$(echo "$STATS" | cut -d',' -f1 | tr -d '%')
MEM=$(echo "$STATS" | cut -d',' -f2 | tr -d '%')

# ── Collect Disk usage via df inside the container ───────────────────────────
DISK=$(docker exec "$CONTAINER" df -h / 2>/dev/null | awk 'NR==2 {print $5}' | tr -d '%')

# Default to 0 if any metric is empty
CPU=${CPU:-0}
MEM=${MEM:-0}
DISK=${DISK:-0}

echo "${CONTAINER},${CPU},${MEM},${DISK}"
