"""Example job demonstrating the Job pattern."""

import asyncio
import logging

from moose.job import Job

logger = logging.getLogger(__name__)


class ExampleJob(Job):
    """A simple example job that sleeps for 2 seconds."""

    @property
    def name(self) -> str:
        return "example_job"

    async def run(self) -> None:
        """Execute the example job."""
        logger.info("ExampleJob starting...")
        await asyncio.sleep(2)
        logger.info("ExampleJob completed successfully!")
