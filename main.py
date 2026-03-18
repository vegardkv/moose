"""Moose - Self-updating async job runner with git-pull loop."""

import argparse
import asyncio
import logging
import subprocess
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

DEFAULT_CONFIG = Path("config/jobs.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Moose job runner daemon.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        metavar="PATH",
        help=f"Path to jobs config file (default: {DEFAULT_CONFIG})",
    )
    return parser.parse_args()


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


def _get_eligible_ids(spec: JobsSpec, last_run: dict[str, float], now: float) -> list[str]:
    """Return job IDs from *spec* that are eligible to run given *last_run* timestamps."""
    eligible = []
    for entry in spec.jobs:
        jid = str(entry.job_id)
        elapsed = now - last_run.get(jid, 0.0)
        if elapsed >= entry.min_interval_seconds:
            eligible.append(jid)
        else:
            remaining = entry.min_interval_seconds - elapsed
            logger.info(
                f"Skipping {jid}: next run in {remaining:.0f}s"
                f" (min_interval={entry.min_interval_seconds}s)"
            )
    return eligible


def run_jobs(config_path: Path, spec: JobsSpec, job_ids: list[str]) -> bool:
    """
    Invoke jobs.py for *job_ids* with a timeout derived from *spec*.

    Returns:
        True if successful, False otherwise
    """
    entries = {e.job_id: e for e in spec.jobs}
    total_timeout = (
        sum(
            entries[jid].timeout_seconds or spec.default_timeout_seconds
            for jid in job_ids
            if jid in entries
        )
        + 30  # buffer for startup/shutdown
    )

    try:
        result = subprocess.run(
            ["uv", "run", "jobs.py", "--config", str(config_path), *job_ids],
            capture_output=True,
            text=True,
            timeout=total_timeout,
        )

        # Log output regardless of success/failure
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


def main() -> None:
    """Main poll loop: git pull → run eligible jobs → sleep → repeat.

    Usage: main.py [--config PATH]  (default: config/jobs.json)
    """
    setup_logging()
    args = parse_args()
    config_path: Path = args.config

    # Fail fast before entering the loop
    if load_spec(config_path) is None:
        return

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
                continue
            git_pull_failed_last_cycle = False

            # Re-read config after git pull so changes take effect immediately
            spec = load_spec(config_path)
            if spec is None:
                logger.warning("Skipping jobs due to config load failure")
                continue

            now = time.time()
            eligible_ids = _get_eligible_ids(spec, last_run, now)
            if not eligible_ids:
                logger.info("No eligible jobs this cycle")
                continue

            # Mark as attempted before running (crash-safe)
            for jid in eligible_ids:
                last_run[jid] = now

            run_jobs(config_path, spec, eligible_ids)
            logger.info("Poll cycle complete")

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        asyncio.run(send_discord("🦌 Moose shutting down", "info"))


if __name__ == "__main__":
    main()
