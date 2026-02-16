"""Entry point for job execution."""
import asyncio
import sys
from moose.logging_setup import setup_logging
from moose.runner import run_all_jobs


def main() -> int:
    """
    Run all jobs and return exit code.
    
    Returns:
        0 if all jobs succeeded, 1 if any job failed
    """
    # Setup logging
    setup_logging()
    
    # Run jobs
    results = asyncio.run(run_all_jobs())
    
    # Determine exit code
    if all(r.success for r in results):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
