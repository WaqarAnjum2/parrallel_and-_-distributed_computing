"""
Output file download endpoint.

GET /jobs/{id}/result — streams the completed output video to the client.
Only serves files for jobs in COMPLETED state.
Does not expose arbitrary filesystem paths.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from shared.constants import JobState
from worker.core.exceptions import JobNotFoundError
from worker.core.security import verify_token

router = APIRouter(tags=["Download"])


@router.get("/jobs/{job_id}/result")
async def download_result(
    job_id: str,
    request: Request,
    _token: str = Depends(verify_token),
) -> FileResponse:
    """
    Stream the completed output video.

    The job must be in COMPLETED state.  Transitions to DOWNLOADING
    when the response starts.
    """
    job = request.app.state.job_manager.get_job(job_id)

    if job is None:
        raise JobNotFoundError(job_id)

    if job.status not in (JobState.COMPLETED, JobState.DOWNLOADING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "JOB_NOT_READY",
                "message": (
                    f"Job '{job_id}' is in state {job.status.value}. "
                    "Download is only available for COMPLETED jobs."
                ),
            },
        )

    output_path = job.output_path
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "OUTPUT_NOT_FOUND",
                "message": f"Output file for job '{job_id}' not found on disk.",
            },
        )

    # Transition to DOWNLOADING
    if job.status == JobState.COMPLETED:
        job.transition_to(JobState.DOWNLOADING)

    filename = f"{job_id}_output.mp4"

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
