"""
Health check endpoint.

GET /health — returns worker readiness, GPU/NVENC status, and queue size.
No authentication required (allows connectivity testing).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from shared.schemas import HealthResponse

if TYPE_CHECKING:
    pass

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """
    Return worker health status.

    This endpoint is intentionally unauthenticated so that the client
    can test connectivity before configuring credentials.
    """
    state = request.app.state
    return HealthResponse(
        status="online",
        ready=True,
        gpu_available=state.gpu_info.available,
        nvenc_available=len(state.nvenc_encoders) > 0,
        queue_size=state.task_queue.size,
    )
