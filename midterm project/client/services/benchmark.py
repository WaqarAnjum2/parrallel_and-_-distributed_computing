"""
Benchmark service — local encoding timer and speedup calculations.

Runs a local FFmpeg encode (CPU-only) for comparison against remote
GPU processing.  All values are measured, never fabricated.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from shared.schemas import BenchmarkRecord


def run_local_encode(
    input_path: str,
    codec: str,
    resolution: str,
    bitrate: str,
    preset: str = "medium",
    ffmpeg_path: str = "ffmpeg",
) -> float:
    """
    Run a local FFmpeg encode using CPU codec (libx264 / libx265)
    and return the elapsed wall-clock seconds.

    The output is written to a temp file and deleted after timing.
    """
    # Map GPU codec request to CPU equivalent for fair comparison
    cpu_codec_map = {
        "h264": "libx264",
        "hevc": "libx265",
    }
    cpu_codec = cpu_codec_map.get(codec, "libx264")

    # CPU presets are different from NVENC presets
    cpu_preset = "medium"

    width, height = resolution.split("x")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        output_path = tmp.name

    cmd = [
        ffmpeg_path,
        "-y",
        "-i", input_path,
        "-c:v", cpu_codec,
        "-preset", cpu_preset,
        "-b:v", bitrate,
        "-vf", f"scale={width}:{height}",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path,
    ]

    try:
        start = time.monotonic()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hour max
        )
        elapsed = time.monotonic() - start

        if result.returncode != 0:
            raise RuntimeError(
                f"Local FFmpeg failed (exit {result.returncode}): "
                f"{result.stderr[-300:]}"
            )

        return round(elapsed, 2)

    finally:
        # Clean up temp output
        if os.path.exists(output_path):
            os.unlink(output_path)


def calculate_speedup(
    local_time: float,
    upload_time: float,
    gpu_time: float,
    download_time: float,
) -> tuple[float, float, float]:
    """
    Calculate speedup and network overhead.

    Returns:
        (remote_total, speedup, network_overhead_percent)
    """
    remote_total = upload_time + gpu_time + download_time
    speedup = local_time / remote_total if remote_total > 0 else 0.0
    overhead_pct = (
        ((upload_time + download_time) / remote_total * 100)
        if remote_total > 0
        else 0.0
    )
    return (
        round(remote_total, 2),
        round(speedup, 2),
        round(overhead_pct, 1),
    )


def create_benchmark_record(
    test_id: str,
    input_path: str,
    resolution: str,
    duration_seconds: float,
    local_time: float,
    upload_time: float,
    gpu_time: float,
    download_time: float,
) -> BenchmarkRecord:
    """Create a fully populated benchmark record."""
    input_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    remote_total, speedup, overhead_pct = calculate_speedup(
        local_time, upload_time, gpu_time, download_time
    )

    return BenchmarkRecord(
        test_id=test_id,
        input_size_mb=round(input_size_mb, 1),
        resolution=resolution,
        duration_seconds=round(duration_seconds, 1),
        local_time_seconds=local_time,
        upload_seconds=upload_time,
        gpu_seconds=gpu_time,
        download_seconds=download_time,
        remote_total_seconds=remote_total,
        speedup=speedup,
        network_overhead_percent=overhead_pct,
    )


def export_benchmarks(
    records: list[BenchmarkRecord],
    output_dir: str,
    format: str = "json",
) -> str:
    """
    Export benchmark records to a file.

    Returns the path to the exported file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if format == "json":
        path = os.path.join(output_dir, "benchmark_results.json")
        with open(path, "w") as f:
            json.dump(
                [r.model_dump() for r in records],
                f,
                indent=2,
                default=str,
            )
    elif format == "csv":
        import csv
        path = os.path.join(output_dir, "benchmark_results.csv")
        if records:
            fieldnames = list(records[0].model_dump().keys())
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in records:
                    writer.writerow(r.model_dump())
    else:
        raise ValueError(f"Unsupported format: {format}")

    return path
