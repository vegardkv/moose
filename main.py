"""Moose - Self-updating async job runner with git-pull loop."""
import asyncio
import logging
import subprocess
import time
from moose.config import (
    POLL_INTERVAL_SECONDS,
    GIT_PULL_TIMEOUT_SECONDS,
    DEFAULT_JOB_TIMEOUT_SECONDS,
)
from moose.logging_setup import setup_logging
from moose.notifications import send_discord

logger = logging.getLogger(__name__)


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


def run_jobs() -> bool:
    """
    Run jobs.py with timeout.
    
    Returns:
        True if successful, False otherwise
    """
    job_timeout = DEFAULT_JOB_TIMEOUT_SECONDS + 30  # Add buffer for startup/shutdown
    
    try:
        result = subprocess.run(
            ["uv", "run", "jobs.py"],
            capture_output=True,
            text=True,
            timeout=job_timeout,
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
        logger.error(f"Jobs timed out after {job_timeout}s")
        return False
    except Exception as e:
        logger.error(f"Jobs execution error: {e}")
        return False


def main() -> None:
    """Main poll loop: git pull → run jobs → sleep → repeat."""
    # Setup logging
    setup_logging()
    
    # Send startup notification
    logger.info("🦌 Moose started")
    asyncio.run(send_discord("🦌 Moose started", "info"))
    
    # Track git pull failures to avoid noisy loops
    git_pull_failed_last_cycle = False
    
    try:
        while True:
            logger.info(f"Sleeping for {POLL_INTERVAL_SECONDS}s...")
            time.sleep(POLL_INTERVAL_SECONDS)
            
            logger.info("Starting poll cycle")
            
            # Step 1: Git pull
            git_pull_success = run_git_pull()
            
            if not git_pull_success:
                # Alert once per failure (not every cycle)
                if not git_pull_failed_last_cycle:
                    asyncio.run(send_discord(
                        "⚠️ Git pull failed, skipping jobs this cycle",
                        "warning"
                    ))
                git_pull_failed_last_cycle = True
                logger.info("Skipping jobs due to git pull failure")
                continue
            
            # Reset failure flag if pull succeeded
            git_pull_failed_last_cycle = False
            
            # Step 2: Run jobs
            run_jobs()
            
            logger.info("Poll cycle complete")
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        asyncio.run(send_discord("🦌 Moose shutting down", "info"))


if __name__ == "__main__":
    main()
