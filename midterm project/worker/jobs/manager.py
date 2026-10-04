"""
In-memory job registry.

Thread-safe dictionary holding all active jobs.  The initial implementation
does NOT persist jobs across worker restarts (per PRD §31 Scenario C).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from shared.constants import JobState
from worker.jobs.models import Job

logger = logging.getLogger("worker")


class JobManager:
    """
    Central registry for all jobs known to this worker process.

    Uses a threading.Lock for safe concurrent access from the FastAPI
    async handlers and the background executor task.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._counter: int = 0
        self._idempotency_cache: dict[str, str] = {}  # key -> job_id

    # ------------------------------------------------------------------
    # Job ID generation
    # ------------------------------------------------------------------

    def _next_id(self) -> str:
        self._counter += 1
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"JOB-{date_str}-{self._counter:06d}"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_job(
        self,
        filename: str,
        input_size: int,
        input_sha256: str,
        codec: str,
        output_codec: str,
        resolution: str,
        bitrate: str,
        preset: str,
        idempotency_key: Optional[str] = None,
    ) -> Job:
        """Create a new job and register it."""
        with self._lock:
            # Idempotency check
            if idempotency_key and idempotency_key in self._idempotency_cache:
                existing_id = self._idempotency_cache[idempotency_key]
                existing = self._jobs.get(existing_id)
                if existing is not None:
                    logger.info(
                        f"Idempotent duplicate — returning existing {existing_id}",
                        extra={"job_id": existing_id},
                    )
                    return existing

            job_id = self._next_id()
            job = Job(
                job_id=job_id,
                filename=filename,
                input_size=input_size,
                input_sha256=input_sha256,
                codec=codec,
                output_codec=output_codec,
                resolution=resolution,
                bitrate=bitrate,
                preset=preset,
                idempotency_key=idempotency_key,
            )
            self._jobs[job_id] = job

            if idempotency_key:
                self._idempotency_cache[idempotency_key] = job_id

            logger.info("job.created", extra={"job_id": job_id})
            return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Return the job or None."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        """Return a snapshot of all jobs."""
        with self._lock:
            return list(self._jobs.values())

    def count_active(self) -> int:
        """Count jobs that are not in a terminal state."""
        terminal = {
            JobState.FINISHED,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.TIMEOUT,
            JobState.INTERRUPTED,
        }
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status not in terminal)

    def queue_size(self) -> int:
        """Count jobs currently in QUEUED or PROCESSING state."""
        with self._lock:
            return sum(
                1
                for j in self._jobs.values()
                if j.status in (JobState.QUEUED, JobState.PROCESSING)
            )

    # ------------------------------------------------------------------
    # Startup recovery
    # ------------------------------------------------------------------

    def mark_interrupted_on_startup(self) -> None:
        """
        On worker restart, mark any PROCESSING jobs as INTERRUPTED.

        The initial implementation does not persist jobs, so this is a
        no-op in practice — but the method exists for correctness.
        """
        with self._lock:
            for job in self._jobs.values():
                if job.status == JobState.PROCESSING:
                    job.status = JobState.INTERRUPTED
                    job.completed_at = datetime.utcnow()
                    logger.warning(
                        "job.interrupted (startup recovery)",
                        extra={"job_id": job.job_id},
                    )
