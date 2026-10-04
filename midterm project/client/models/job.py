"""
Client-side job data model.

Mirrors the server's job model but holds client-specific timing data
for benchmark calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from shared.constants import JobState


@dataclass
class ClientJob:
    """Client-side representation of a transcoding job with timing data."""

    job_id: str = ""
    status: JobState = JobState.CREATED

    # File info
    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    sha256: str = ""

    # Transcoding params
    codec: str = ""
    resolution: str = ""
    bitrate: str = ""
    preset: str = ""

    # Progress
    progress: int = 0
    fps: float = 0.0
    speed: str = ""

    # Timing (seconds) — measured values
    hash_time: float = 0.0
    upload_time: float = 0.0
    queue_wait_time: float = 0.0
    gpu_processing_time: float = 0.0
    download_time: float = 0.0
    local_encode_time: float = 0.0

    # Result
    output_path: Optional[str] = None
    output_size: Optional[int] = None
    error_message: Optional[str] = None

    # Input metadata
    duration_seconds: float = 0.0

    @property
    def download_path(self) -> Optional[str]:
        """Alias for output_path for compatibility with result page."""
        return self.output_path

    @download_path.setter
    def download_path(self, val: Optional[str]) -> None:
        self.output_path = val

    @property
    def remote_total_time(self) -> float:
        """T_remote = T_upload + T_gpu + T_download"""
        return self.upload_time + self.gpu_processing_time + self.download_time

    @property
    def speedup(self) -> float:
        """Speedup = T_local / T_remote"""
        if self.remote_total_time > 0:
            return round(self.local_encode_time / self.remote_total_time, 2)
        return 0.0

    @property
    def network_overhead_percent(self) -> float:
        """Network Overhead % = ((T_upload + T_download) / T_remote) * 100"""
        if self.remote_total_time > 0:
            return round(
                (self.upload_time + self.download_time) / self.remote_total_time * 100,
                1,
            )
        return 0.0
