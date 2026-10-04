"""
Failure scenario tests: Job Timeout (E13).

Verifies that jobs exceeding max allowed duration transition to TIMEOUT.
"""

import pytest
from pathlib import Path
from shared.constants import JobState
from worker.jobs.models import Job
from worker.jobs.executor import JobExecutor


@pytest.mark.asyncio
async def test_job_timeout_transition(tmp_path: Path):
    """Executor transitions job to TIMEOUT on duration expiry."""
    executor = JobExecutor(
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        temp_dir=tmp_path / "temp",
        max_duration_seconds=1,
    )
    job = Job(
        job_id="JOB-TIMEOUT-001",
        filename="video.mp4",
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

    await executor._handle_timeout(job)
    assert job.status == JobState.TIMEOUT
