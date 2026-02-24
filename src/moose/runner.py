"""Job orchestrator with timeout and error isolation."""

import asyncio
import logging
import time

from moose.job import Job, JobResult
from moose.modules.example_job import ExampleJob
from moose.modules.finn_cars_job import FinnCarsJob
from moose.notifications import send_discord

logger = logging.getLogger(__name__)

# Job registry - add your jobs here
JOBS: list[Job] = [
    FinnCarsJob(),
    ExampleJob(),
]


async def run_all_jobs() -> list[JobResult]:
    """
    Run all registered jobs with timeout and error isolation.

    Returns:
        List of JobResult for each job executed
    """
    results: list[JobResult] = []

    logger.info(f"Starting job run with {len(JOBS)} job(s)")

    for job in JOBS:
        logger.info(f"Running job: {job.name} (timeout: {job.timeout}s)")
        start_time = time.time()

        try:
            # Run job with timeout
            await asyncio.wait_for(job.run(), timeout=job.timeout)

            # Success
            duration = time.time() - start_time
            logger.info(f"Job {job.name} completed in {duration:.2f}s")
            results.append(
                JobResult(
                    job_name=job.name,
                    success=True,
                    duration=duration,
                )
            )

        except TimeoutError:
            # Job timed out
            duration = time.time() - start_time
            error_msg = f"Job {job.name} timed out after {job.timeout}s"
            logger.error(error_msg)
            results.append(
                JobResult(
                    job_name=job.name,
                    success=False,
                    duration=duration,
                    error="Timeout",
                )
            )

        except Exception as e:
            # Job raised exception
            duration = time.time() - start_time
            error_msg = f"Job {job.name} failed: {type(e).__name__}: {e}"
            logger.error(error_msg)
            results.append(
                JobResult(
                    job_name=job.name,
                    success=False,
                    duration=duration,
                    error=str(e),
                )
            )

    # Send summary to Discord
    await _send_summary(results)

    return results


async def _send_summary(results: list[JobResult]) -> None:
    """Send job execution summary to Discord."""
    total = len(results)
    succeeded = sum(1 for r in results if r.success)
    failed = total - succeeded

    if failed == 0:
        summary = f"✅ All {total} job(s) completed successfully"
        level = "info"
    else:
        summary = f"⚠️ Job run complete: {succeeded}/{total} succeeded, {failed} failed\n\n"
        summary += "Failed jobs:\n"
        for r in results:
            if not r.success:
                summary += f"- {r.job_name}: {r.error}\n"
        level = "warning"

    await send_discord(summary, level)
