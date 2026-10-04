"""
Worker entry point.

Boots the FastAPI application, detects hardware, initialises the job queue
and executor, then starts Uvicorn.
"""

from __future__ import annotations

import platform
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

# Ensure project root is in sys.path when invoked directly as `python worker/main.py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI

from shared.protocol import WSEventType
from worker.api import health, info, jobs, upload, download, websocket
from worker.api.websocket import broadcast_event
from worker.core.config import WorkerSettings, get_settings
from worker.core.logging_config import setup_logging
from worker.gpu.detector import GPUInfo, detect_gpu
from worker.gpu.nvenc import detect_ffmpeg_version, detect_ffprobe, detect_nvenc_encoders
from worker.jobs.executor import JobExecutor
from worker.jobs.manager import JobManager
from worker.jobs.queue import TaskQueue


def _ensure_directories(settings: WorkerSettings) -> None:
    """Create required data directories if they don't exist."""
    for p in (settings.input_path, settings.output_path, settings.temp_path):
        p.mkdir(parents=True, exist_ok=True)


def _print_banner(
    settings: WorkerSettings,
    gpu_info: GPUInfo,
    nvenc_encoders: list[str],
    ffmpeg_version: str,
    ffprobe_ok: bool,
) -> None:
    """Print the startup readiness banner."""
    local_ip = _get_local_ip()
    banner = f"""
=================================================
 Distributed GPU Worker
=================================================
 Host:       {platform.node()}
 IP:         {local_ip}
 Port:       {settings.worker_port}
 Python:     {sys.version.split()[0]}
 FFmpeg:     {ffmpeg_version}
 FFprobe:    {"detected" if ffprobe_ok else "NOT FOUND"}
 GPU:        {gpu_info.name if gpu_info.available else "NOT AVAILABLE"}
 NVENC:      {", ".join(nvenc_encoders) if nvenc_encoders else "NOT AVAILABLE"}
 Storage:    {_get_storage_gb(settings.input_path):.0f} GB available
 Queue max:  {settings.max_queue_size}
 Concurrent: {settings.max_concurrent_jobs}
 Status:     READY
=================================================
"""
    print(banner)


def _get_local_ip() -> str:
    """Best-effort local IP detection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_storage_gb(path: Path) -> float:
    """Return available storage in GB for the given path's drive."""
    import psutil
    path.mkdir(parents=True, exist_ok=True)
    usage = psutil.disk_usage(str(path))
    return usage.free / (1024 ** 3)


# ------------------------------------------------------------------
# Application Lifespan
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown lifecycle for the worker."""
    logger = setup_logging()
    settings = get_settings()
    app.state.settings = settings

    # Create directories
    _ensure_directories(settings)

    # Detect hardware
    gpu_info = detect_gpu()
    app.state.gpu_info = gpu_info

    nvenc_encoders = detect_nvenc_encoders()
    app.state.nvenc_encoders = nvenc_encoders

    ffmpeg_version = detect_ffmpeg_version()
    app.state.ffmpeg_version = ffmpeg_version

    ffprobe_ok = detect_ffprobe()

    # Initialise job manager
    job_manager = JobManager()
    job_manager.mark_interrupted_on_startup()
    app.state.job_manager = job_manager

    # Initialise executor
    executor = JobExecutor(
        input_dir=settings.input_path,
        output_dir=settings.output_path,
        temp_dir=settings.temp_path,
        max_duration_seconds=settings.max_job_duration_seconds,
    )

    # Wire up the progress callback to broadcast via WebSocket
    async def _progress_cb(
        job_id: str, progress: int, fps: float, speed: str
    ) -> None:
        await broadcast_event(
            job_id=job_id,
            event_type=WSEventType.JOB_PROGRESS,
            progress=progress,
            fps=fps,
            speed=speed,
        )

    executor.set_progress_callback(_progress_cb)
    app.state.executor = executor

    # Initialise task queue
    task_queue = TaskQueue(
        max_concurrent=settings.max_concurrent_jobs,
        max_size=settings.max_queue_size,
    )
    task_queue.set_executor(executor.execute)
    task_queue.start()
    app.state.task_queue = task_queue

    # Print banner
    _print_banner(settings, gpu_info, nvenc_encoders, ffmpeg_version, ffprobe_ok)

    yield  # ---- application runs ----

    # Shutdown
    await task_queue.stop()
    logger.info("Worker shut down cleanly")


# ------------------------------------------------------------------
# App Factory
# ------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Distributed GPU Worker",
        description="Remote video transcoding worker with NVIDIA NVENC",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register routes
    app.include_router(health.router)
    app.include_router(info.router)
    app.include_router(jobs.router)
    app.include_router(upload.router)
    app.include_router(download.router)
    app.include_router(websocket.router)

    return app


# ------------------------------------------------------------------
# Direct execution
# ------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    app = create_app()
    uvicorn.run(
        app,
        host=settings.worker_host,
        port=settings.worker_port,
        log_level="info",
    )
