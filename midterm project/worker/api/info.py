"""
Worker information endpoint.

GET /worker/info — returns hardware and software metadata.
Does not expose unnecessary sensitive OS information.
"""

from __future__ import annotations

import platform

import psutil
from fastapi import APIRouter, Depends, Request

from shared.schemas import WorkerInfoResponse
from worker.core.security import verify_token

router = APIRouter(tags=["Worker"])


@router.get("/worker/info", response_model=WorkerInfoResponse)
async def worker_info(
    request: Request,
    _token: str = Depends(verify_token),
) -> WorkerInfoResponse:
    """Return worker hardware and software metadata."""
    state = request.app.state
    settings = state.settings

    # CPU info (basic label, not full system details)
    cpu_brand = platform.processor() or "Unknown CPU"

    return WorkerInfoResponse(
        hostname=platform.node(),
        platform=platform.system(),
        cpu=cpu_brand,
        gpu=state.gpu_info.name,
        gpu_memory_mb=state.gpu_info.memory_mb,
        ffmpeg_version=state.ffmpeg_version,
        encoders=state.nvenc_encoders,
        max_concurrent_jobs=settings.max_concurrent_jobs,
    )
