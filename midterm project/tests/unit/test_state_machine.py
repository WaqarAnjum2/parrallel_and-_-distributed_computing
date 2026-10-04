"""
Unit tests for job state machine transitions.
"""

import pytest

from shared.constants import JobState, is_valid_transition, VALID_STATE_TRANSITIONS
from worker.core.exceptions import InvalidStateTransitionError
from worker.jobs.models import Job


class TestStateTransitions:
    """Verify allowed and forbidden state transitions."""

    def test_valid_transitions(self) -> None:
        """All defined valid transitions should be allowed."""
        for source, targets in VALID_STATE_TRANSITIONS.items():
            for target in targets:
                assert is_valid_transition(source, target), (
                    f"{source} -> {target} should be valid"
                )

    def test_invalid_transition_finished_to_processing(self) -> None:
        """FINISHED -> PROCESSING must be rejected."""
        assert not is_valid_transition(JobState.FINISHED, JobState.PROCESSING)

    def test_invalid_transition_failed_to_completed(self) -> None:
        """FAILED -> COMPLETED must be rejected."""
        assert not is_valid_transition(JobState.FAILED, JobState.COMPLETED)

    def test_invalid_transition_cancelled_to_processing(self) -> None:
        """CANCELLED -> PROCESSING must be rejected."""
        assert not is_valid_transition(JobState.CANCELLED, JobState.PROCESSING)

    def test_created_only_to_uploading(self) -> None:
        """CREATED can only transition to UPLOADING."""
        assert is_valid_transition(JobState.CREATED, JobState.UPLOADING)
        assert not is_valid_transition(JobState.CREATED, JobState.PROCESSING)
        assert not is_valid_transition(JobState.CREATED, JobState.COMPLETED)

    def test_processing_can_reach_four_states(self) -> None:
        """PROCESSING can go to COMPLETED, FAILED, CANCELLED, or TIMEOUT."""
        assert is_valid_transition(JobState.PROCESSING, JobState.COMPLETED)
        assert is_valid_transition(JobState.PROCESSING, JobState.FAILED)
        assert is_valid_transition(JobState.PROCESSING, JobState.CANCELLED)
        assert is_valid_transition(JobState.PROCESSING, JobState.TIMEOUT)

    def test_terminal_states_have_no_outgoing(self) -> None:
        """Terminal states must have zero outgoing transitions."""
        terminal = [
            JobState.FINISHED,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.TIMEOUT,
            JobState.INTERRUPTED,
        ]
        for state in terminal:
            assert VALID_STATE_TRANSITIONS.get(state) == set()


class TestJobModel:
    """Test Job.transition_to enforcement."""

    def test_valid_transition_updates_state(self) -> None:
        job = Job(job_id="JOB-TEST-001")
        assert job.status == JobState.CREATED
        job.transition_to(JobState.UPLOADING)
        assert job.status == JobState.UPLOADING

    def test_invalid_transition_raises(self) -> None:
        job = Job(job_id="JOB-TEST-002")
        with pytest.raises(InvalidStateTransitionError):
            job.transition_to(JobState.COMPLETED)

    def test_processing_sets_started_at(self) -> None:
        job = Job(job_id="JOB-TEST-003")
        assert job.started_at is None
        job.transition_to(JobState.UPLOADING)
        job.transition_to(JobState.UPLOADED)
        job.transition_to(JobState.QUEUED)
        job.transition_to(JobState.PROCESSING)
        assert job.started_at is not None

    def test_completed_sets_completed_at(self) -> None:
        job = Job(job_id="JOB-TEST-004")
        job.transition_to(JobState.UPLOADING)
        job.transition_to(JobState.UPLOADED)
        job.transition_to(JobState.QUEUED)
        job.transition_to(JobState.PROCESSING)
        assert job.completed_at is None
        job.transition_to(JobState.COMPLETED)
        assert job.completed_at is not None
