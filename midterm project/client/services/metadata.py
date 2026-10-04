"""
Video file metadata extraction using FFprobe.

Provides input duration, resolution, and codec info needed for
progress calculation and benchmark setup.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoMetadata:
    """Extracted video file metadata."""
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    codec_name: str = ""
    bitrate_kbps: int = 0
    file_size_bytes: int = 0
    format_name: str = ""
    fps_val: float = 30.0

    @property
    def duration(self) -> float:
        return self.duration_seconds

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"

    @property
    def codec(self) -> str:
        return self.codec_name or "Unknown"

    @property
    def fps(self) -> float:
        return self.fps_val

    @property
    def valid(self) -> bool:
        return self.duration_seconds > 0 or (self.width > 0 and self.height > 0)


from worker.gpu.nvenc import resolve_ffprobe_path


def probe_video(file_path: str, ffprobe_path: str = "ffprobe") -> Optional[VideoMetadata]:
    """
    Run ffprobe and extract video metadata.

    Returns None if ffprobe fails or the file is not a valid video.
    """
    resolved_path = resolve_ffprobe_path(ffprobe_path)
    try:
        result = subprocess.run(
            [
                resolved_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])

        # Find the first video stream
        video_stream: dict[str, object] = {}
        for stream in streams:
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        duration = float(fmt.get("duration", 0))
        file_size = int(fmt.get("size", 0))
        bitrate = int(fmt.get("bit_rate", 0)) // 1000  # to kbps

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        codec_name = str(video_stream.get("codec_name", ""))

        return VideoMetadata(
            duration_seconds=duration,
            width=width,
            height=height,
            codec_name=codec_name,
            bitrate_kbps=bitrate,
            file_size_bytes=file_size,
            format_name=str(fmt.get("format_name", "")),
        )

    except Exception:
        return None
