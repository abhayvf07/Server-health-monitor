# ==============================================================================
# monitor/charts.py — Matplotlib trend chart generation with dark theme
#                     and threshold reference lines.
# ==============================================================================
import os
import logging
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

logger = logging.getLogger(__name__)

# Dark color palette matching the dashboard theme
COLORS = {
    "bg": "#0f1923",
    "card": "#1a2736",
    "grid": "#2a3a4a",
    "cpu": "#00d4ff",
    "mem": "#a855f7",
    "disk": "#f97316",
    "threshold": "#ef4444",
    "text": "#e2e8f0",
    "text_muted": "#94a3b8",
}


def plot_trend(df: pd.DataFrame, server: str, out_dir: str = "charts_output"):
    """Generate a dark-themed trend chart for a server's resource metrics.

    Args:
        df:      pandas DataFrame with columns: ts, cpu_pct, mem_pct, disk_pct
        server:  Server/container name (used in title and filename)
        out_dir: Output directory for the PNG file

    Returns:
        str: Path to the generated chart image, or None on failure.
    """
    if df.empty:
        logger.warning(f"No data to plot for {server}")
        return None

    os.makedirs(out_dir, exist_ok=True)

    # ── Apply dark theme ─────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["card"])

    # ── Plot metric lines ────────────────────────────────────────────────────
    ax.plot(
        df["ts"], df["cpu_pct"],
        color=COLORS["cpu"], linewidth=2, label="CPU %", alpha=0.9,
    )
    ax.fill_between(df["ts"], df["cpu_pct"], alpha=0.1, color=COLORS["cpu"])

    ax.plot(
        df["ts"], df["mem_pct"],
        color=COLORS["mem"], linewidth=2, label="Memory %", alpha=0.9,
    )
    ax.fill_between(df["ts"], df["mem_pct"], alpha=0.1, color=COLORS["mem"])

    ax.plot(
        df["ts"], df["disk_pct"],
        color=COLORS["disk"], linewidth=2, label="Disk %", alpha=0.9,
    )
    ax.fill_between(df["ts"], df["disk_pct"], alpha=0.1, color=COLORS["disk"])

    # ── Threshold reference lines ────────────────────────────────────────────
    from monitor.thresholds import THRESHOLDS

    ax.axhline(
        THRESHOLDS["cpu_pct"],
        color=COLORS["threshold"], linestyle="--", linewidth=1,
        alpha=0.7, label=f"CPU Threshold ({THRESHOLDS['cpu_pct']}%)",
    )
    ax.axhline(
        THRESHOLDS["mem_pct"],
        color=COLORS["threshold"], linestyle=":",  linewidth=1,
        alpha=0.5, label=f"Mem Threshold ({THRESHOLDS['mem_pct']}%)",
    )

    # ── Styling ──────────────────────────────────────────────────────────────
    ax.set_title(
        f"  {server} — Resource Trends",
        color=COLORS["text"], fontsize=14, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Time", color=COLORS["text_muted"], fontsize=10)
    ax.set_ylabel("Usage %", color=COLORS["text_muted"], fontsize=10)
    ax.set_ylim(0, 105)
    ax.tick_params(colors=COLORS["text_muted"], labelsize=9)
    ax.grid(True, color=COLORS["grid"], alpha=0.3, linestyle="--")

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()

    # Legend
    legend = ax.legend(
        loc="upper right", fontsize=8,
        facecolor=COLORS["card"], edgecolor=COLORS["grid"],
        labelcolor=COLORS["text_muted"],
    )

    # Spine styling
    for spine in ax.spines.values():
        spine.set_color(COLORS["grid"])
        spine.set_linewidth(0.5)

    # ── Save ─────────────────────────────────────────────────────────────────
    out_path = os.path.join(out_dir, f"{server}_trend.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    logger.info(f"Chart saved: {out_path}")
    return out_path
