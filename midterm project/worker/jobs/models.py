"""
Job data model and state machine for the worker.

Each job tracks its lifecycle from CREATED through to FINISHED/FAILED/CANCELLED.
State transitions are enforced — invalid transitions raise errors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from shared.constants import JobState, is_valid_transition
from worker.core.exceptions import InvalidStateTransitionError

logger = logging.getLogger("worker")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    """In-memory representation of a transcoding job."""

    job_id: str
    status: JobState = JobState.CREATED

    # Client-declared metadata
    filename: str = ""
    input_size: int = 0
    input_sha256: str = ""
    codec: str = ""
    output_codec: str = ""
    resolution: str = ""
    bitrate: str = ""
    preset: str = ""

    # Paths (worker-side, generated internally)
    input_path: Optional[str] = None
    output_path: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=_now_utc)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Processing metrics
    progress: int = 0
    fps: float = 0.0
    speed: str = ""
    elapsed_seconds: float = 0.0
    output_size: Optional[int] = None

    # Error info
    error_message: Optional[str] = None

    # Idempotency
    idempotency_key: Optional[str] = None

    # Input duration (seconds) — set after ffprobe on upload
    input_duration: float = 0.0

    def transition_to(self, new_state: JobState) -> None:
        """
        Transition the job to a new state.

        Raises InvalidStateTransitionError if the transition is not allowed
        by the state machine defined in shared/constants.py.
        """
        if not is_valid_transition(self.status, new_state):
            raise InvalidStateTransitionError(
                self.job_id, self.status.value, new_state.value
            )

        old_state = self.status
        self.status = new_state

        # Update timestamps on key transitions
        if new_state == JobState.PROCESSING:
            self.started_at = datetime.now(timezone.utc)
        elif new_state in (
            JobState.COMPLETED,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.TIMEOUT,
        ):
            self.completed_at = datetime.now(timezone.utc)

        logger.info(
            f"job.state_change {old_state.value} -> {new_state.value}",
            extra={"job_id": self.job_id},
        )
