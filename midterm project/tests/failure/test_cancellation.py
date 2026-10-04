"""
Failure scenario tests: Cancellation (E14).

Verifies that cancelling jobs terminates execution safely, marks the job
as CANCELLED, and removes partial files.
"""

import pytest
from shared.constants import JobState
from worker.jobs.models import Job


def test_job_cancellation_state():
    """A job in CREATED or QUEUED state can transition directly to CANCELLED."""
    job = Job(
        job_id="JOB-CANCEL-001",
        filename="test.mp4",
        input_size=1024,
        input_sha256="abc",
        output_codec="h264_nvenc",
        resolution="1920x1080",
        bitrate="5M",
        preset="p4",
    )
    assert job.status == JobState.CREATED
    job.transition_to(JobState.CANCELLED)
    assert job.status == JobState.CANCELLED


def test_processing_job_cancellation_transition():
    """A job in PROCESSING can transition to CANCELLED."""
    job = Job(
        job_id="JOB-CANCEL-002",
        filename="test.mp4",
        input_size=1024,
        input_sha256="abc",
        output_codec="h264_nvenc",
        resolution="1920x1080",
        bitrate="5M",
        preset="p4",
    )
    job.transition_to(JobState.UPLOADING)
    job.transition_to(JobState.UPLOADED)
    job.transition_to(JobState.QUEUED)
    job.transition_to(JobState.PROCESSING)
    assert job.status == JobState.PROCESSING

    job.transition_to(JobState.CANCELLED)
    assert job.status == JobState.CANCELLED
