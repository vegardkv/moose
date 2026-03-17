"""Pydantic models for job configuration."""

from enum import StrEnum

from pydantic import BaseModel


class JobId(StrEnum):
    """Explicit registry of all known job identifiers."""

    FINN_CARS = "finn_cars"
    EXAMPLE_JOB = "example_job"


class JobEntry(BaseModel):
    """Configuration for a single job within a JobsSpec."""

    job_id: JobId
    timeout_seconds: int | None = None
    """Override the job's built-in timeout. Falls back to spec default_timeout_seconds, then Job.timeout."""
    min_interval_seconds: int = 0
    """Minimum seconds that must elapse since the last run before this job is eligible again."""


class JobsSpec(BaseModel):
    """Specification of which jobs to run and their shared settings."""

    jobs: list[JobEntry]
    default_timeout_seconds: int = 300
    """Fallback timeout for any job whose JobEntry.timeout_seconds is None."""
