"""Moose - Self-updating async job runner with git-pull loop."""

import asyncio
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from moose.config import (
    GIT_PULL_TIMEOUT_SECONDS,
    POLL_INTERVAL_SECONDS,
)
from moose.logging_setup import setup_logging
from moose.models import JobsSpec
from moose.notifications import send_discord

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config/jobs.json")


def load_spec(config_path: Path) -> JobsSpec | None:
    """Load and validate JobsSpec from *config_path*. Returns None and logs on failure."""
    try:
        return JobsSpec.model_validate_json(config_path.read_text())
    except FileNotFoundError:
        logger.error(f"Config not found: {config_path}")
        return None
    except Exception as e:
        logger.error(f"Invalid config ({config_path}): {e}")
        return None


def run_git_pull() -> bool:
    """
    Run git pull --ff-only with timeout.

    Returns:
        True if successful, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            capture_output=True,
            text=True,
            timeout=GIT_PULL_TIMEOUT_SECONDS,
        )

        if result.returncode == 0:
            logger.info(f"Git pull successful: {result.stdout.strip()}")
            return True
        else:
            logger.warning(f"Git pull failed (exit {result.returncode}): {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Git pull timed out after {GIT_PULL_TIMEOUT_SECONDS}s")
        return False
    except Exception as e:
        logger.error(f"Git pull error: {e}")
        return False


def _get_eligible_spec(spec: JobsSpec, last_run: dict[str, float], now: float) -> JobsSpec:
    """Return a copy of *spec* containing only jobs eligible to run given *last_run* timestamps."""
    eligible = []
    for entry in spec.jobs:
        jid = str(entry.job_id)
        elapsed = now - last_run.get(jid, 0.0)
        if elapsed >= entry.min_interval_seconds:
            eligible.append(entry)
        else:
            remaining = entry.min_interval_seconds - elapsed
            logger.info(f"Skipping {jid}: next run in {remaining:.0f}s (min_interval={entry.min_interval_seconds}s)")
    return spec.model_copy(update={"jobs": eligible})


def run_jobs(eligible_spec: JobsSpec) -> bool:
    """
    Write *eligible_spec* to a temp file and invoke jobs.py against it.

    Returns:
        True if successful, False otherwise
    """
    total_timeout = (
        sum(e.timeout_seconds or eligible_spec.default_timeout_seconds for e in eligible_spec.jobs)
        + 30  # buffer for startup/shutdown
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        tf.write(eligible_spec.model_dump_json())
        tmp_path = Path(tf.name)

    try:
        result = subprocess.run(
            ["uv", "run", "jobs.py", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=total_timeout,
        )

        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                logger.info(f"[jobs.py] {line}")

        if result.returncode == 0:
            logger.info("Jobs completed successfully")
            return True
        else:
            logger.warning(f"Jobs failed with exit code {result.returncode}")
            if result.stderr:
                logger.error(f"[jobs.py stderr] {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Jobs timed out after {total_timeout}s")
        return False
    except Exception as e:
        logger.error(f"Jobs execution error: {e}")
        return False
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    """Main poll loop: git pull → run eligible jobs → sleep → repeat.

    Usage: main.py [config_path]  (default: config/jobs.json)
    """
    setup_logging()

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH

    # Fail fast if config is missing/invalid before entering the loop
    if load_spec(config_path) is None:
        sys.exit(1)

    logger.info("🦌 Moose started")
    asyncio.run(send_discord("🦌 Moose started", "info"))

    # In-memory state (intentionally resets on process restart)
    last_run: dict[str, float] = {}
    git_pull_failed_last_cycle = False

    try:
        while True:
            logger.info(f"Sleeping for {POLL_INTERVAL_SECONDS}s...")
            time.sleep(POLL_INTERVAL_SECONDS)
            logger.info("Starting poll cycle")

            if not run_git_pull():
                if not git_pull_failed_last_cycle:
                    asyncio.run(send_discord("⚠️ Git pull failed, skipping jobs this cycle", "warning"))
                git_pull_failed_last_cycle = True
                logger.info("Skipping jobs due to git pull failure")
                continue
            git_pull_failed_last_cycle = False

            # Re-read config after git pull so changes take effect immediately
            spec = load_spec(config_path)
            if spec is None:
                logger.warning("Skipping jobs due to config load failure")
                continue

            now = time.time()
            eligible_spec = _get_eligible_spec(spec, last_run, now)
            if not eligible_spec.jobs:
                logger.info("No eligible jobs this cycle")
                continue

            # Mark jobs as attempted before running (crash-safe)
            for entry in eligible_spec.jobs:
                last_run[str(entry.job_id)] = now

            run_jobs(eligible_spec)
            logger.info("Poll cycle complete")

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        asyncio.run(send_discord("🦌 Moose shutting down", "info"))


if __name__ == "__main__":
    main()
