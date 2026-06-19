# ==============================================================================
# monitor/collector.py — Subprocess wrapper around the bash metric collection
#                        script. Calls collect_metrics.sh per container.
#
# On Windows, converts paths to Git Bash-compatible format automatically.
# ==============================================================================
import subprocess
import os
import sys
import datetime
import logging
import pathlib

logger = logging.getLogger(__name__)

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "collect_metrics.sh")


def _bash_path(win_path: str) -> str:
    """Convert a Windows path to a Git Bash-compatible path.

    Example: D:\\Server Health Monitor\\scripts\\collect.sh
          -> /d/Server Health Monitor/scripts/collect.sh
    """
    p = str(pathlib.Path(win_path).resolve()).replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        return "/" + p[0].lower() + p[2:]
    return p


def collect(container: str) -> dict:
    """Collect CPU, memory, and disk metrics from a Docker container.

    Runs the bash collection script via subprocess and parses its CSV output.

    Args:
        container: Name of the Docker container to collect metrics from.

    Returns:
        dict with keys: server, ts, cpu_pct, mem_pct, disk_pct

    Raises:
        subprocess.CalledProcessError: If the bash script exits with non-zero.
        SystemExit: If the script times out (30-second limit).
    """
    # Convert path for Git Bash on Windows
    script_path = _bash_path(SCRIPT) if os.name == "nt" else SCRIPT

    # Use Git Bash explicitly on Windows to avoid WSL Docker issues
    bash_cmd = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else "bash"
    
    # Prevent Git Bash from converting '/' to Windows paths (fixes 'df -h /' in docker)
    env = os.environ.copy()
    if os.name == "nt":
        env["MSYS_NO_PATHCONV"] = "1"

    try:
        result = subprocess.run(
            [bash_cmd, script_path, container],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        output = result.stdout.strip()
        if not output:
            logger.error(f"Empty output from collection script for {container}")
            raise ValueError(f"No metrics returned for {container}")

        name, cpu, mem, disk = output.split(",")
        metrics = {
            "server": name,
            "ts": datetime.datetime.now(datetime.UTC),
            "cpu_pct": float(cpu),
            "mem_pct": float(mem),
            "disk_pct": float(disk),
        }
        logger.info(
            f"Collected: {name} -- CPU={cpu}%, MEM={mem}%, DISK={disk}%"
        )
        return metrics

    except subprocess.CalledProcessError as e:
        logger.error(f"Collection failed for {container}: {e.stderr}")
        raise

    except subprocess.TimeoutExpired:
        logger.error(f"Timed out collecting metrics for {container}")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Parse error for {container}: {e}")
        raise
