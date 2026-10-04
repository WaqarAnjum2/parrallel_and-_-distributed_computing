"""
Job management endpoints.

POST /jobs          — create a new transcoding job
GET  /jobs/{id}     — get job status
POST /jobs/{id}/cancel — cancel a queued or processing job
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Request

from shared.constants import JobState
from shared.schemas import (
    CancelResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
)
from worker.core.exceptions import JobNotFoundError, QueueFullError
from worker.core.security import verify_token
from worker.validation.params import (
    validate_bitrate,
    validate_codec,
    validate_filename,
    validate_file_size,
    validate_preset,
    validate_resolution,
    validate_sha256,
)

router = APIRouter(tags=["Jobs"])


@router.post("/jobs", response_model=JobCreateResponse, status_code=201)
async def create_job(
    body: JobCreateRequest,
    request: Request,
    _token: str = Depends(verify_token),
    x_idempotency_key: Optional[str] = Header(None),
) -> JobCreateResponse:
    """
    Create a new transcoding job.

    Validates all parameters against whitelists before accepting.
    Supports idempotency via X-Idempotency-Key header.
    """
    state = request.app.state
    settings = state.settings

    # Queue capacity check
    if state.task_queue.is_full():
        raise QueueFullError(settings.max_queue_size)

    # Validate every client-controlled parameter
    validate_filename(body.filename)
    validate_file_size(body.size, settings.max_file_size_bytes)
    sha256 = validate_sha256(body.sha256)
    output_codec = validate_codec(body.codec)
    validate_resolution(body.resolution)
    validate_bitrate(body.bitrate)
    validate_preset(body.preset)

    # Create job in the registry
    job = state.job_manager.create_job(
        filename=body.filename,
        input_size=body.size,
        input_sha256=sha256,
        codec=body.codec,
        output_codec=output_codec,
        resolution=body.resolution,
        bitrate=body.bitrate,
        preset=body.preset,
        idempotency_key=x_idempotency_key,
    )

    return JobCreateResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    request: Request,
    _token: str = Depends(verify_token),
) -> JobStatusResponse:
    """Return the current status of a job."""
    job = request.app.state.job_manager.get_job(job_id)
    if job is None:
        raise JobNotFoundError(job_id)

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        fps=job.fps,
        speed=job.speed,
        elapsed_seconds=job.elapsed_seconds,
        filename=job.filename,
        input_size=job.input_size,
        output_size=job.output_size,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.post("/jobs/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(
    job_id: str,
    request: Request,
    _token: str = Depends(verify_token),
) -> CancelResponse:
    """
    Cancel a job.

    - If QUEUED: removed from queue, marked CANCELLED.
    - If PROCESSING: FFmpeg subprocess terminated, marked CANCELLED.
    - Otherwise: returns current state (no-op).
    """
    state = request.app.state
    job = state.job_manager.get_job(job_id)
    if job is None:
        raise JobNotFoundError(job_id)

    if job.status == JobState.CREATED:
        job.transition_to(JobState.CANCELLED)

    elif job.status == JobState.QUEUED:
        state.task_queue.remove_if_queued(job)

    elif job.status == JobState.PROCESSING:
        cancelled = await state.executor.cancel_current(job_id)
        if cancelled and job.status == JobState.PROCESSING:
            job.transition_to(JobState.CANCELLED)

    return CancelResponse(job_id=job.job_id, status=job.status)
