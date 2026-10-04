"""
WebSocket endpoint for real-time job progress streaming.

/ws/jobs/{job_id} — sends JSON events as the job progresses through
its lifecycle.  A disconnected client does NOT terminate the job.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.constants import JobState
from shared.protocol import WSEventType

logger = logging.getLogger("worker")
router = APIRouter(tags=["WebSocket"])

# Registry of active WebSocket connections: job_id -> set of WebSocket
_ws_connections: dict[str, set[WebSocket]] = {}


async def broadcast_event(
    job_id: str,
    event_type: str,
    progress: int = 0,
    fps: float = 0.0,
    speed: str = "",
    message: str = "",
) -> None:
    """
    Broadcast a WebSocket event to all connected clients for a given job.

    This is called from the executor / queue when job state changes.
    """
    connections = _ws_connections.get(job_id, set())
    if not connections:
        return

    payload = json.dumps({
        "event": event_type,
        "job_id": job_id,
        "progress": progress,
        "fps": fps,
        "speed": speed,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    dead: list[WebSocket] = []
    for ws in connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)

    # Clean up dead connections
    for ws in dead:
        connections.discard(ws)


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str) -> None:
    """
    WebSocket endpoint for live job progress.

    The client connects, receives events until the job finishes or
    the connection drops.  Dropping the connection does NOT cancel the job.
    """
    await websocket.accept()

    # Register connection
    if job_id not in _ws_connections:
        _ws_connections[job_id] = set()
    _ws_connections[job_id].add(websocket)

    logger.info(f"ws.connected", extra={"job_id": job_id})

    try:
        # Optionally authenticate via first message
        # For simplicity, we accept the connection and verify via query param
        # or skip auth on WS (the job_id itself is the access scope).

        # Send current state immediately
        job = websocket.app.state.job_manager.get_job(job_id)
        if job:
            await websocket.send_text(json.dumps({
                "event": "job.status",
                "job_id": job_id,
                "status": job.status.value,
                "progress": job.progress,
                "fps": job.fps,
                "speed": job.speed,
                "timestamp": datetime.utcnow().isoformat(),
            }))

        # Keep the connection alive — we mostly send, rarely receive
        while True:
            try:
                # Wait for client messages (ping/pong/close)
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0
                )
                # Client can send "ping" to keep alive
                if data.strip().lower() == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))

            except asyncio.TimeoutError:
                # Send a heartbeat to keep the connection alive
                try:
                    await websocket.send_text(json.dumps({
                        "event": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat(),
                    }))
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("ws.disconnected", extra={"job_id": job_id})

    except Exception as exc:
        logger.warning(f"ws.error: {exc}", extra={"job_id": job_id})

    finally:
        # Unregister connection — job continues regardless
        conns = _ws_connections.get(job_id, set())
        conns.discard(websocket)
        if not conns:
            _ws_connections.pop(job_id, None)
