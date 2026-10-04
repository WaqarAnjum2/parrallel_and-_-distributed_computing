"""
Pydantic request / response models shared between client and worker.

Every API payload is strictly typed — no arbitrary dicts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from shared.constants import JobState


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """GET /health response."""
    status: str = "online"
    ready: bool = True
    gpu_available: bool = False
    nvenc_available: bool = False
    queue_size: int = 0


# ---------------------------------------------------------------------------
# Worker Info
# ---------------------------------------------------------------------------

class WorkerInfoResponse(BaseModel):
    """GET /worker/info response."""
    hostname: str
    platform: str
    cpu: str
    gpu: str = "Not detected"
    gpu_memory_mb: int = 0
    ffmpeg_version: str = "Not detected"
    encoders: list[str] = Field(default_factory=list)
    max_concurrent_jobs: int = 1


# ---------------------------------------------------------------------------
# Job Create
# ---------------------------------------------------------------------------

class JobCreateRequest(BaseModel):
    """POST /jobs request body."""
    filename: str
    size: int = Field(gt=0, description="Input file size in bytes")
    sha256: str = Field(min_length=64, max_length=64)
    codec: str
    resolution: str
    bitrate: str
    preset: str


class JobCreateResponse(BaseModel):
    """POST /jobs response body."""
    job_id: str
    status: JobState = JobState.CREATED


# ---------------------------------------------------------------------------
# Job Status
# ---------------------------------------------------------------------------

class JobStatusResponse(BaseModel):
    """GET /jobs/{id} response body."""
    job_id: str
    status: JobState
    progress: int = 0
    fps: float = 0.0
    speed: str = ""
    elapsed_seconds: float = 0.0
    filename: Optional[str] = None
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    """POST /jobs/{id}/upload response body."""
    job_id: str
    status: JobState
    sha256_verified: bool


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

class CancelResponse(BaseModel):
    """POST /jobs/{id}/cancel response body."""
    job_id: str
    status: JobState


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standardised API error envelope."""
    error: ErrorDetail


class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: Optional[dict[str, list[str]]] = None


# ---------------------------------------------------------------------------
# WebSocket Event
# ---------------------------------------------------------------------------

class WSEvent(BaseModel):
    """WebSocket progress / status event pushed to the client."""
    event: str
    job_id: str
    progress: int = 0
    fps: float = 0.0
    speed: str = ""
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------

class LatencyResult(BaseModel):
    """Result of a multi-ping latency test."""
    requests: int
    successful: int
    failed: int
    min_ms: float
    avg_ms: float
    max_ms: float


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

class BenchmarkRecord(BaseModel):
    """Single benchmark measurement."""
    test_id: str
    input_size_mb: float
    resolution: str
    duration_seconds: float
    local_time_seconds: float
    upload_seconds: float
    gpu_seconds: float
    download_seconds: float
    remote_total_seconds: float
    speedup: float
    network_overhead_percent: float
    cpu_usage_percent: Optional[float] = None
    gpu_usage_percent: Optional[float] = None
    ram_usage_mb: Optional[float] = None
    network_throughput_mbps: Optional[float] = None
