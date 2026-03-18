"""Entry point for job execution."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from moose.logging_setup import setup_logging
from moose.models import JobId, JobsSpec
from moose.runner import run_all_jobs

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("config/jobs.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run moose jobs.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        metavar="PATH",
        help=f"Path to jobs config file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "job_ids",
        nargs="*",
        metavar="JOB_ID",
        help="Job IDs to run. Runs all configured jobs if omitted.",
    )
    return parser.parse_args()


def load_spec(config_path: Path, job_ids: list[str] | None = None) -> JobsSpec:
    """Load and validate JobsSpec from *config_path*, optionally filtered to *job_ids*.

    Exits the process on any failure.
    """
    if not config_path.exists():
        sys.exit(f"Config not found: {config_path}")
    try:
        spec = JobsSpec.model_validate_json(config_path.read_text())
    except Exception as e:
        sys.exit(f"Invalid config ({config_path}): {e}")

    if job_ids:
        requested = {JobId(jid) for jid in job_ids}
        spec = spec.model_copy(update={"jobs": [e for e in spec.jobs if e.job_id in requested]})

    return spec


def main() -> int:
    """
    Run jobs and return exit code.

    Returns:
        0 if all jobs succeeded, 1 if any job failed
    """
    setup_logging()
    args = parse_args()
    spec = load_spec(args.config, args.job_ids or None)

    if not spec.jobs:
        logger.warning("No jobs to run")
        return 0

    results = asyncio.run(run_all_jobs(spec))
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
