"""Job abstract base class and result dataclass."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from moose.config import DEFAULT_JOB_TIMEOUT_SECONDS


@dataclass
class JobResult:
    """Result of a job execution."""
    job_name: str
    success: bool
    duration: float
    error: str | None = None


class Job(ABC):
    """Abstract base class for all jobs."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this job."""
        pass
    
    @property
    def timeout(self) -> int:
        """Timeout in seconds for this job. Override to customize."""
        return DEFAULT_JOB_TIMEOUT_SECONDS
    
    @abstractmethod
    async def run(self) -> None:
        """Execute the job. Raise exceptions on failure."""
        pass
