"""
Remote Worker Node Server Daemon.
Provides REST and WebSocket endpoints for distributed rendering offload.
"""
import asyncio
import os
import sys
import time
from typing import Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from common.protocol import (
    HandshakeRequest,
    HandshakeResponse,
    JobStatus,
    ProgressUpdate,
    RenderConfig,
    compute_sha256
)
from server.task_queue import TaskQueueManager

app = FastAPI(title="Distributed GPU Render Worker Daemon", version="1.0.0")

# Enable CORS for local cross-origin connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

queue_mgr = TaskQueueManager()


@app.get("/")
async def root():
    return {
        "service": "GPU Render Worker Daemon",
        "status": "ONLINE",
        "gpu_available": queue_mgr.engine.gpu_info.available,
        "nvenc_supported": queue_mgr.engine.gpu_info.nvenc_supported
    }


@app.post("/api/handshake", response_model=HandshakeResponse)
async def handshake(req: HandshakeRequest):
    """
    Task 1: Handshake protocol endpoint.
    Returns GPU hardware specs, driver, VRAM, and server timestamp for latency RTT calculation.
    """
    gpu_status = queue_mgr.engine.get_gpu_status()
    active_count = sum(1 for j in queue_mgr.jobs.values() if j.status == JobStatus.PROCESSING)

    return HandshakeResponse(
        worker_id="worker-node-01",
        status="READY" if active_count == 0 else "BUSY",
        server_timestamp=time.time(),
        gpu=gpu_status,
        active_jobs=active_count,
        max_concurrent_jobs=1
    )


@app.post("/api/upload")
async def upload_asset(
    file: UploadFile = File(...),
    sha256_checksum: Optional[str] = Form(None)
):
    """
    Task 2 & 4: Upload video asset with chunked streaming and SHA-256 validation.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    job = queue_mgr.create_job(file.filename)
    queue_mgr.append_log(job.job_id, f"Receiving file '{file.filename}'...")

    total_bytes = 0
    try:
        with open(job.input_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunk
                out_file.write(chunk)
                total_bytes += len(chunk)
    except Exception as e:
        queue_mgr.cleanup_job(job.job_id)
        raise HTTPException(status_code=500, detail=f"File write failed: {str(e)}")

    if total_bytes == 0:
        queue_mgr.cleanup_job(job.job_id)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Verify input integrity
    calc_hash = compute_sha256(job.input_path)
    if sha256_checksum and sha256_checksum.lower() != calc_hash.lower():
        queue_mgr.cleanup_job(job.job_id)
        raise HTTPException(
            status_code=422,
            detail=f"Integrity check failed: Expected {sha256_checksum}, got {calc_hash}"
        )

    queue_mgr.append_log(job.job_id, f"File received ({total_bytes / (1024*1024):.2f} MB). SHA-256 verified.")
    job.status = JobStatus.QUEUED

    return {
        "job_id": job.job_id,
        "bytes_received": total_bytes,
        "sha256": calc_hash,
        "status": "QUEUED"
    }


@app.post("/api/jobs/{job_id}/start")
async def start_job(job_id: str, config: RenderConfig):
    """
    Task 2: Start transcoding job using supplied configuration.
    """
    job = queue_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status not in [JobStatus.QUEUED, JobStatus.RECEIVING]:
        raise HTTPException(status_code=400, detail=f"Job cannot be started in state {job.status}")

    # Launch background rendering task
    asyncio.create_task(queue_mgr.execute_job(job_id, config))

    return {"job_id": job_id, "status": "PROCESSING", "message": "Job initiated."}


@app.get("/api/jobs/{job_id}/status")
async def job_status(job_id: str):
    """Poll job status and recent logs."""
    job = queue_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "current_frame": job.current_frame,
        "fps": job.fps,
        "speed": job.speed,
        "logs": job.logs[-20:],
        "error": job.error,
        "output_sha256": job.output_sha256
    }


@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    Task 4: Asynchronous real-time WebSocket progress and log streaming.
    """
    await websocket.accept()
    job = queue_mgr.get_job(job_id)
    if not job:
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    q: asyncio.Queue[ProgressUpdate] = asyncio.Queue()
    queue_mgr.ws_subscribers.setdefault(job_id, []).append(q)

    # Immediately send existing logs
    for line in job.logs[-10:]:
        await websocket.send_json({"type": "log", "line": line, "percent": job.progress})

    try:
        while True:
            # Check if queue has update
            try:
                update = await asyncio.wait_for(q.get(), timeout=1.0)
                await websocket.send_json({
                    "type": "progress",
                    "status": update.status,
                    "percent": update.percent,
                    "current_frame": update.current_frame,
                    "fps": update.fps,
                    "speed": update.speed,
                    "log_line": update.log_line,
                    "error_msg": update.error_msg,
                    "output_sha256": update.output_sha256
                })
                if update.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    break
            except asyncio.TimeoutError:
                # Keep-alive heartbeat
                await websocket.send_json({"type": "ping", "percent": job.progress, "status": job.status})
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if job_id in queue_mgr.ws_subscribers and q in queue_mgr.ws_subscribers[job_id]:
            queue_mgr.ws_subscribers[job_id].remove(q)


@app.get("/api/jobs/{job_id}/download")
async def download_output(job_id: str):
    """
    Download rendered output video file with SHA-256 header.
    """
    job = queue_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != JobStatus.COMPLETED or not os.path.exists(job.output_path):
        raise HTTPException(status_code=400, detail="Output file not ready or render failed.")

    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
        filename=f"rendered_{job_id}.mp4",
        headers={"X-File-SHA256": job.output_sha256 or ""}
    )


@app.delete("/api/jobs/{job_id}")
async def cancel_or_delete_job(job_id: str):
    """Cancel and delete job resources."""
    success = queue_mgr.cancel_job(job_id)
    queue_mgr.cleanup_job(job_id)
    return {"job_id": job_id, "cancelled": success}


def start_server(host: str = "0.0.0.0", port: int = 8500):
    print(f"Starting Remote GPU Render Daemon on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Distributed GPU Worker Daemon")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8500, help="Port (default: 8500)")
    args = parser.parse_args()
    start_server(args.host, args.port)

