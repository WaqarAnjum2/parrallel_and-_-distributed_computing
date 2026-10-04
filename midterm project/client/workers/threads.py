"""
QThread worker classes for non-blocking GUI operations.

Every long-running operation (network, file I/O, hashing) runs in a
QThread and communicates results via Qt signals.  The GUI thread
NEVER performs blocking I/O.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from client.config import ClientConfig
from client.models.job import ClientJob
from client.network.api_client import APIClient
from client.network.transfer import download_file, upload_file
from client.services.checksum import compute_sha256
from shared.constants import JobState
from shared.schemas import JobCreateRequest


class ConnectionTestThread(QThread):
    """Test connectivity to the worker."""

    success = pyqtSignal(dict)     # health + worker info combined
    failed = pyqtSignal(str)       # error message

    def __init__(self, config: ClientConfig, parent: object = None) -> None:
        super().__init__()
        self._config = config

    def run(self) -> None:
        try:
            client = APIClient(self._config)
            health = client.health()
            info = client.worker_info()
            latency = client.latency_test()

            self.success.emit({
                "health": health.model_dump(),
                "info": info.model_dump(),
                "latency": latency.model_dump(),
            })
        except Exception as exc:
            self.failed.emit(_friendly_error(exc))


class JobSubmitThread(QThread):
    """
    Full job submission pipeline:
    1. Hash the input file
    2. Create the job on the worker
    3. Upload the file
    4. Listen for completion via polling

    Each stage emits progress signals.
    """

    stage_changed = pyqtSignal(str, int)      # (stage_name, progress_pct)
    job_created = pyqtSignal(str)              # job_id
    upload_progress = pyqtSignal(int)          # percent
    processing_progress = pyqtSignal(int, float, str)  # (pct, fps, speed)
    download_progress = pyqtSignal(int)        # percent
    completed = pyqtSignal(object)             # ClientJob with all timing
    failed = pyqtSignal(str)                   # error message
    log_message = pyqtSignal(str)              # log line

    def __init__(
        self,
        config: ClientConfig,
        job: ClientJob,
        parent: object = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._job = job
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            client = APIClient(self._config)
            job = self._job

            # --- Stage 1: Hash ---
            self.stage_changed.emit("Calculating SHA-256...", 0)
            self.log_message.emit(f"Hashing {job.filename}...")
            t0 = time.monotonic()
            sha256 = compute_sha256(
                job.file_path,
                total_size=job.file_size,
                on_progress=lambda done, total: self.stage_changed.emit(
                    "Hashing...", int(done / total * 100) if total else 0
                ),
            )
            job.sha256 = sha256
            job.hash_time = round(time.monotonic() - t0, 2)
            self.log_message.emit(f"SHA-256: {sha256[:16]}... ({job.hash_time}s)")

            if self._cancelled:
                return

            # --- Stage 2: Create Job ---
            self.stage_changed.emit("Creating job...", 0)
            req = JobCreateRequest(
                filename=job.filename,
                size=job.file_size,
                sha256=sha256,
                codec=job.codec,
                resolution=job.resolution,
                bitrate=job.bitrate,
                preset=job.preset,
            )
            resp = client.create_job(req, idempotency_key=str(uuid.uuid4()))
            job.job_id = resp.job_id
            job.status = resp.status
            self.job_created.emit(job.job_id)
            self.log_message.emit(f"Job created: {job.job_id}")

            if self._cancelled:
                client.cancel_job(job.job_id)
                return

            # --- Stage 3: Upload ---
            self.stage_changed.emit("Uploading...", 0)
            t1 = time.monotonic()
            upload_file(
                config=self._config,
                job_id=job.job_id,
                file_path=job.file_path,
                on_progress=lambda sent, total: self.upload_progress.emit(
                    int(sent / total * 100) if total else 0
                ),
            )
            job.upload_time = round(time.monotonic() - t1, 2)
            self.log_message.emit(f"Upload complete ({job.upload_time}s)")

            if self._cancelled:
                client.cancel_job(job.job_id)
                return

            # --- Stage 4: Wait for processing ---
            self.stage_changed.emit("Processing on GPU...", 0)
            t2 = time.monotonic()
            while not self._cancelled:
                time.sleep(1.0)
                status_resp = client.get_job_status(job.job_id)
                job.status = status_resp.status
                job.progress = status_resp.progress

                if status_resp.status == JobState.PROCESSING:
                    self.processing_progress.emit(
                        status_resp.progress,
                        status_resp.fps,
                        status_resp.speed,
                    )
                elif status_resp.status == JobState.QUEUED:
                    self.stage_changed.emit("Queued...", 0)
                elif status_resp.status == JobState.COMPLETED:
                    job.gpu_processing_time = round(time.monotonic() - t2, 2)
                    self.log_message.emit(
                        f"GPU processing complete ({job.gpu_processing_time}s)"
                    )
                    break
                elif status_resp.status in (
                    JobState.FAILED,
                    JobState.CANCELLED,
                    JobState.TIMEOUT,
                ):
                    job.error_message = status_resp.error_message or status_resp.status.value
                    self.failed.emit(job.error_message)
                    return

            if self._cancelled:
                client.cancel_job(job.job_id)
                return

            # --- Stage 5: Download ---
            self.stage_changed.emit("Downloading result...", 0)
            dest_dir = os.path.join(os.path.dirname(job.file_path), "output")
            dest_path = os.path.join(dest_dir, f"{job.job_id}_output.mp4")

            t3 = time.monotonic()
            download_file(
                config=self._config,
                job_id=job.job_id,
                dest_path=dest_path,
                on_progress=lambda recv, total: self.download_progress.emit(
                    int(recv / total * 100) if total else 0
                ),
            )
            job.download_time = round(time.monotonic() - t3, 2)
            job.output_path = dest_path
            job.output_size = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
            job.status = JobState.FINISHED
            self.log_message.emit(f"Download complete ({job.download_time}s)")

            self.completed.emit(job)

        except Exception as exc:
            self.failed.emit(_friendly_error(exc))


class LocalBenchmarkThread(QThread):
    """Run a local CPU encode for benchmark comparison."""

    progress = pyqtSignal(str)
    completed = pyqtSignal(float)   # local_time_seconds
    failed = pyqtSignal(str)

    def __init__(
        self,
        file_path: str,
        codec: str,
        resolution: str,
        bitrate: str,
        parent: object = None,
    ) -> None:
        super().__init__()
        self._file_path = file_path
        self._codec = codec
        self._resolution = resolution
        self._bitrate = bitrate

    def run(self) -> None:
        try:
            from client.services.benchmark import run_local_encode

            self.progress.emit("Running local CPU encode...")
            elapsed = run_local_encode(
                input_path=self._file_path,
                codec=self._codec,
                resolution=self._resolution,
                bitrate=self._bitrate,
            )
            self.completed.emit(elapsed)
        except Exception as exc:
            self.failed.emit(str(exc))


def _friendly_error(exc: Exception) -> str:
    """Convert technical exceptions to user-friendly messages."""
    msg = str(exc)

    if "ConnectionRefusedError" in msg or "10061" in msg:
        return (
            "Unable to connect to the worker.\n\n"
            "Check:\n"
            "• Worker IP address\n"
            "• Worker port number\n"
            "• Worker application is running\n"
            "• Windows Firewall allows the connection\n"
            "• Both computers are on the same network"
        )
    if "TimeoutError" in msg or "timed out" in msg.lower():
        return (
            "Connection timed out.\n\n"
            "The worker may be unreachable or the network is slow.\n"
            "Verify the IP address and firewall settings."
        )
    if "401" in msg or "Unauthorized" in msg:
        return (
            "Authentication failed.\n\n"
            "The auth token does not match the worker's configured token."
        )
    if "413" in msg:
        return "File exceeds the worker's configured maximum size."
    if "507" in msg:
        return "The worker does not have enough disk space."
    if "503" in msg:
        return "The worker's job queue is full. Try again later."

    return f"An error occurred: {msg}"
