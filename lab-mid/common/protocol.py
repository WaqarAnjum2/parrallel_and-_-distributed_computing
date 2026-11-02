"""
Protocol definitions, schemas, and shared utilities for Distributed Task Offloading.
"""
from enum import Enum
import hashlib
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RECEIVING = "RECEIVING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class HandshakeRequest(BaseModel):
    client_id: str
    client_timestamp: float


class GPUInfo(BaseModel):
    available: bool = False
    name: str = "Unknown / None"
    driver_version: str = "N/A"
    cuda_version: str = "N/A"
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    nvenc_supported: bool = False


class HandshakeResponse(BaseModel):
    worker_id: str
    status: str = "READY"
    server_timestamp: float
    gpu: GPUInfo
    active_jobs: int = 0
    max_concurrent_jobs: int = 1


class RenderConfig(BaseModel):
    resolution: str = Field(default="1920x1080", description="Target video resolution e.g. 1920x1080, 1280x720, or original")
    bitrate: str = Field(default="5M", description="Target video bitrate e.g. 5M, 10M, 2M")
    preset: str = Field(default="p4", description="NVENC preset e.g. p1-p7 or x264 preset fast/medium/slow")
    codec: str = Field(default="h264_nvenc", description="Target encoder: h264_nvenc or libx264")
    fps: Optional[int] = Field(default=None, description="Target framerate, or None to keep original")
    input_sha256: Optional[str] = Field(default=None, description="SHA-256 checksum of input file for verification")
    # Video Editing Timeline & Filter Parameters
    trim_start: Optional[float] = Field(default=None, description="Trim start time in seconds")
    trim_end: Optional[float] = Field(default=None, description="Trim end time in seconds")
    filter_effect: str = Field(default="None", description="Visual filter: None, Grayscale, Sepia, Vignette, High Contrast, Invert")
    playback_speed: float = Field(default=1.0, description="Playback speed factor e.g. 0.5, 1.0, 1.5, 2.0")
    watermark_text: Optional[str] = Field(default=None, description="Text watermark stamped onto video")
    audio_mode: str = Field(default="Original", description="Audio mode: Original, Boost, Mute")


class ProgressUpdate(BaseModel):
    job_id: str
    status: JobStatus
    percent: float = 0.0
    current_frame: int = 0
    total_frames: int = 0
    fps: float = 0.0
    speed: str = "0x"
    eta_seconds: int = 0
    log_line: str = ""
    error_msg: Optional[str] = None
    output_sha256: Optional[str] = None


def compute_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file efficiently using chunked reads."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"

