"""
Streaming file upload receiver.

POST /jobs/{id}/upload — receives the input video as a streaming body,
writes to disk in chunks, computes SHA-256 on-the-fly, and verifies
integrity before transitioning to UPLOADED.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import json
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends, Request, UploadFile, File

from shared.constants import CHUNK_SIZE_BYTES, JobState
from shared.schemas import UploadResponse
from worker.core.exceptions import (
    InsufficientStorageError,
    IntegrityError,
    JobNotFoundError,
)
from worker.core.security import verify_token

from worker.gpu.nvenc import resolve_ffprobe_path

logger = logging.getLogger("worker")
router = APIRouter(tags=["Upload"])


def _check_disk_space(path: Path, required_bytes: int) -> None:
    """Raise InsufficientStorageError if there isn't enough disk space."""
    usage = psutil.disk_usage(str(path))
    available = usage.free
    # Require the input size + 50% safety margin for the output
    total_required = int(required_bytes * 2.5)
    if available < total_required:
        raise InsufficientStorageError(
            required_mb=total_required / (1024 * 1024),
            available_mb=available / (1024 * 1024),
        )


def _probe_duration(filepath: str) -> float:
    """
    Use ffprobe to get the input video duration in seconds.
    Returns 0.0 if ffprobe fails.
    """
    bin_path = resolve_ffprobe_path("ffprobe")
    try:
        result = subprocess.run(
            [
                bin_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        duration_str = data.get("format", {}).get("duration", "0")
        return float(duration_str)
    except Exception as exc:
        logger.warning(f"ffprobe duration detection failed: {exc}")
        return 0.0


@router.post("/jobs/{job_id}/upload", response_model=UploadResponse)
async def upload_file(
    job_id: str,
    request: Request,
    file: UploadFile = File(...),
    _token: str = Depends(verify_token),
) -> UploadResponse:
    """
    Receive streaming file upload for a job.

    1. Validate job exists and is in CREATED state
    2. Check disk space
    3. Stream body to disk in chunks (never load full file into RAM)
    4. Compute SHA-256 on-the-fly
    5. Verify checksum against client-declared hash
    6. Probe input duration via ffprobe
    7. Transition to UPLOADED
    """
    state = request.app.state
    settings = state.settings
    job = state.job_manager.get_job(job_id)

    if job is None:
        raise JobNotFoundError(job_id)

    # Transition CREATED -> UPLOADING
    job.transition_to(JobState.UPLOADING)

    # Prepare storage path
    input_dir = settings.input_path / job_id
    input_dir.mkdir(parents=True, exist_ok=True)
    dest_path = input_dir / f"input{os.path.splitext(job.filename)[1]}"

    # Check disk space
    _check_disk_space(settings.input_path, job.input_size)

    # Stream to disk + hash
    sha256_hash = hashlib.sha256()
    bytes_written = 0

    try:
        with open(dest_path, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                f.write(chunk)
                sha256_hash.update(chunk)
                bytes_written += len(chunk)

    except Exception as exc:
        # Clean up partial upload
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        job.error_message = f"Upload failed: {exc}"
        job.transition_to(JobState.FAILED)
        logger.error(f"upload.failed: {exc}", extra={"job_id": job_id})
        raise

    actual_sha256 = sha256_hash.hexdigest()

    # Integrity check
    if actual_sha256 != job.input_sha256:
        # Clean up the corrupted file
        dest_path.unlink(missing_ok=True)
        job.error_message = "Integrity verification failed"
        job.transition_to(JobState.FAILED)
        logger.error(
            f"upload.integrity_failure expected={job.input_sha256} actual={actual_sha256}",
            extra={"job_id": job_id},
        )
        raise IntegrityError(expected=job.input_sha256, actual=actual_sha256)

    # Store the path and probe duration
    job.input_path = str(dest_path)
    job.input_duration = _probe_duration(str(dest_path))

    # Transition UPLOADING -> UPLOADED
    job.transition_to(JobState.UPLOADED)
    logger.info(
        f"upload.completed bytes={bytes_written} sha256_verified=True",
        extra={"job_id": job_id},
    )

    # Auto-enqueue for processing
    await state.task_queue.enqueue(job)

    return UploadResponse(
        job_id=job.job_id,
        status=job.status,
        sha256_verified=True,
    )
