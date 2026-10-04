"""
Async task queue for the worker.

Uses asyncio.Queue with a background consumer loop that processes
one job at a time (max_concurrent_jobs = 1 by default).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Coroutine

from shared.constants import JobState

if TYPE_CHECKING:
    from worker.jobs.models import Job

logger = logging.getLogger("worker")


class TaskQueue:
    """
    Async FIFO queue that dequeues QUEUED jobs and delegates them
    to the executor callback.
    """

    def __init__(
        self,
        max_concurrent: int = 1,
        max_size: int = 20,
    ) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=max_size)
        self._max_concurrent = max_concurrent
        self._running = False
        self._consumer_task: asyncio.Task[None] | None = None
        self._executor_callback: Callable[[Job], Coroutine[None, None, None]] | None = None

    def set_executor(
        self, callback: Callable[[Job], Coroutine[None, None, None]]
    ) -> None:
        """Register the async function that will execute each job."""
        self._executor_callback = callback

    async def enqueue(self, job: Job) -> None:
        """Add a job to the queue.  The job must already be in UPLOADED state."""
        job.transition_to(JobState.QUEUED)
        await self._queue.put(job)
        logger.info("job.queued", extra={"job_id": job.job_id})

    def is_full(self) -> bool:
        """Return True if the queue has no room for new jobs."""
        return self._queue.full()

    @property
    def size(self) -> int:
        return self._queue.qsize()

    # ------------------------------------------------------------------
    # Consumer loop
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background consumer loop."""
        if self._running:
            return
        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_loop())
        logger.info("Task queue consumer started")

    async def stop(self) -> None:
        """Gracefully stop the consumer loop."""
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Task queue consumer stopped")

    async def _consume_loop(self) -> None:
        """
        Continuously dequeue jobs and execute them one at a time.
        """
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if job.status == JobState.CANCELLED:
                logger.info(
                    "job.skipped (cancelled before execution)",
                    extra={"job_id": job.job_id},
                )
                self._queue.task_done()
                continue

            if self._executor_callback is not None:
                try:
                    await self._executor_callback(job)
                except Exception as exc:
                    logger.error(
                        f"job.execution_error: {exc}",
                        extra={"job_id": job.job_id},
                    )
                    if job.status == JobState.PROCESSING:
                        job.transition_to(JobState.FAILED)
                        job.error_message = str(exc)

            self._queue.task_done()

    # ------------------------------------------------------------------
    # Cancellation support
    # ------------------------------------------------------------------

    def remove_if_queued(self, job: Job) -> bool:
        """
        Attempt to cancel a QUEUED job before it starts processing.

        Returns True if the job was successfully cancelled.
        """
        if job.status == JobState.QUEUED:
            job.transition_to(JobState.CANCELLED)
            logger.info("job.cancelled (from queue)", extra={"job_id": job.job_id})
            return True
        return False
