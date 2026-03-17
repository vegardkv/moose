"""Entry point for job execution."""

import asyncio
import logging
import sys
from pathlib import Path

from moose.logging_setup import setup_logging
from moose.models import JobsSpec
from moose.runner import run_all_jobs

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("config/jobs.json")


def load_spec(config_path: Path) -> JobsSpec:
    """Load and validate JobsSpec from *config_path*. Exits on any failure."""
    if not config_path.exists():
        sys.exit(f"Config not found: {config_path}")
    try:
        return JobsSpec.model_validate_json(config_path.read_text())
    except Exception as e:
        sys.exit(f"Invalid config ({config_path}): {e}")


def main() -> int:
    """
    Run all jobs defined in the config and return exit code.

    Usage: jobs.py [config_path]  (default: config/jobs.json)

    Returns:
        0 if all jobs succeeded, 1 if any job failed
    """
    setup_logging()

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG
    spec = load_spec(config_path)

    if not spec.jobs:
        logger.warning("No jobs to run")
        return 0

    results = asyncio.run(run_all_jobs(spec))
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
