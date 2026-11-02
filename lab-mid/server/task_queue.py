"""
Thread-safe task queue and job lifecycle manager for distributed task offloading.
"""
import asyncio
from dataclasses import dataclass, field
import os
import shutil
import sys
import time
from typing import Dict, List, Optional
import uuid

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.protocol import JobStatus, ProgressUpdate, RenderConfig, compute_sha256
from server.gpu_engine import GPUEngine


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    config: Optional[RenderConfig] = None
    input_path: str = ""
    output_path: str = ""
    input_sha256: Optional[str] = None
    output_sha256: Optional[str] = None
    progress: float = 0.0
    current_frame: int = 0
    fps: float = 0.0
    speed: str = "0x"
    logs: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    cancelled: bool = False
    error: Optional[str] = None
    codec_used: str = ""


class TaskQueueManager:
    def __init__(self, workspace_dir: str = "server_workspace"):
        self.workspace_dir = os.path.abspath(workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.jobs: Dict[str, JobRecord] = {}
        self.engine = GPUEngine()
        self.active_lock = asyncio.Lock()
        self.ws_subscribers: Dict[str, List[asyncio.Queue]] = {}

    def create_job(self, original_filename: str) -> JobRecord:
        """Register a new job in the queue."""
        job_id = str(uuid.uuid4())[:8]
        job_dir = os.path.join(self.workspace_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        ext = os.path.splitext(original_filename)[1] or ".mp4"
        input_path = os.path.join(job_dir, f"input{ext}")
        output_path = os.path.join(job_dir, "rendered_output.mp4")

        record = JobRecord(
            job_id=job_id,
            input_path=input_path,
            output_path=output_path,
            status=JobStatus.RECEIVING
        )
        self.jobs[job_id] = record
        self.ws_subscribers[job_id] = []
        return record

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return self.jobs.get(job_id)

    async def broadcast_update(self, job_id: str, update: ProgressUpdate):
        """Broadcast real-time progress update to all active WebSocket listeners."""
        queues = self.ws_subscribers.get(job_id, [])
        for q in queues:
            await q.put(update)

    def append_log(self, job_id: str, message: str):
        job = self.jobs.get(job_id)
        if job:
            timestamp = time.strftime("%H:%M:%S")
            line = f"[{timestamp}] {message}"
            job.logs.append(line)
            # Cap log history to last 200 lines to avoid memory leak
            if len(job.logs) > 200:
                job.logs = job.logs[-200:]

    async def execute_job(self, job_id: str, config: RenderConfig):
        """Asynchronous execution worker that triggers the GPUEngine."""
        job = self.jobs.get(job_id)
        if not job:
            return

        async with self.active_lock:
            job.status = JobStatus.PROCESSING
            job.started_at = time.time()
            job.config = config
            self.append_log(job_id, f"Job {job_id} scheduled on GPU/CPU engine.")

            # Validate input file existence and SHA-256
            if not os.path.exists(job.input_path) or os.path.getsize(job.input_path) == 0:
                job.status = JobStatus.FAILED
                job.error = "Input file missing or empty on worker node."
                self.append_log(job_id, f"ERROR: {job.error}")
                await self.broadcast_update(job_id, ProgressUpdate(
                    job_id=job_id, status=JobStatus.FAILED, error_msg=job.error, log_line=job.error
                ))
                return

            if config.input_sha256:
                actual_hash = compute_sha256(job.input_path)
                job.input_sha256 = actual_hash
                if actual_hash != config.input_sha256:
                    job.status = JobStatus.FAILED
                    job.error = f"SHA-256 hash mismatch! Sent: {config.input_sha256[:10]}..., Got: {actual_hash[:10]}..."
                    self.append_log(job_id, f"ERROR: {job.error}")
                    await self.broadcast_update(job_id, ProgressUpdate(
                        job_id=job_id, status=JobStatus.FAILED, error_msg=job.error, log_line=job.error
                    ))
                    return
                self.append_log(job_id, f"SHA-256 Checksum Verified: {actual_hash[:16]}... OK")

            # Callbacks for sync engine
            loop = asyncio.get_running_loop()

            def sync_progress_cb(pct: float, frame: int, fps: float, speed: str, msg: str):
                job.progress = pct
                job.current_frame = frame
                job.fps = fps
                job.speed = speed
                self.append_log(job_id, msg)
                update = ProgressUpdate(
                    job_id=job_id,
                    status=JobStatus.PROCESSING,
                    percent=pct,
                    current_frame=frame,
                    fps=fps,
                    speed=speed,
                    log_line=msg
                )
                asyncio.run_coroutine_threadsafe(self.broadcast_update(job_id, update), loop)

            def sync_log_cb(msg: str):
                self.append_log(job_id, msg)
                update = ProgressUpdate(
                    job_id=job_id,
                    status=job.status,
                    percent=job.progress,
                    log_line=msg
                )
                asyncio.run_coroutine_threadsafe(self.broadcast_update(job_id, update), loop)

            def stop_check() -> bool:
                return job.cancelled

            # Run in worker thread so we don't block asyncio event loop
            success, used_codec, err = await asyncio.to_thread(
                self.engine.run_transcode,
                job.input_path,
                job.output_path,
                config,
                sync_progress_cb,
                sync_log_cb,
                stop_check
            )

            job.finished_at = time.time()
            job.codec_used = used_codec

            if success and os.path.exists(job.output_path):
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                out_hash = compute_sha256(job.output_path)
                job.output_sha256 = out_hash
                elapsed = job.finished_at - job.started_at
                self.append_log(job_id, f"Render finished in {elapsed:.2f}s using {used_codec}. Out SHA-256: {out_hash[:16]}...")
                await self.broadcast_update(job_id, ProgressUpdate(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    percent=100.0,
                    output_sha256=out_hash,
                    log_line="Render complete! Output ready for download."
                ))
            elif job.cancelled:
                job.status = JobStatus.CANCELLED
                await self.broadcast_update(job_id, ProgressUpdate(
                    job_id=job_id, status=JobStatus.CANCELLED, log_line="Job was cancelled."
                ))
            else:
                job.status = JobStatus.FAILED
                job.error = err
                self.append_log(job_id, f"Render failed: {err}")
                await self.broadcast_update(job_id, ProgressUpdate(
                    job_id=job_id, status=JobStatus.FAILED, error_msg=err, log_line=f"Failure: {err}"
                ))

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job and job.status in [JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.RECEIVING]:
            job.cancelled = True
            job.status = JobStatus.CANCELLED
            return True
        return False

    def cleanup_job(self, job_id: str):
        """Remove temporary files for a completed or cancelled job."""
        job = self.jobs.pop(job_id, None)
        if job:
            job_dir = os.path.dirname(job.input_path)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
            self.ws_subscribers.pop(job_id, None)

