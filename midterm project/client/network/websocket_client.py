"""
WebSocket client for receiving real-time job progress events.

Runs in a separate thread — emits Qt signals to update the GUI safely.
"""

from __future__ import annotations

import json
import logging
import time

from PyQt6.QtCore import QThread, pyqtSignal

from client.config import ClientConfig

logger = logging.getLogger("client")


class WebSocketClientThread(QThread):
    """
    Connects to /ws/jobs/{job_id} and emits progress signals.

    Automatically reconnects on disconnect (the job continues on the worker).
    """

    # Signals
    event_received = pyqtSignal(dict)       # raw parsed JSON event
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        config: ClientConfig,
        job_id: str,
        parent: object = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._job_id = job_id
        self._running = True

    def stop(self) -> None:
        """Signal the thread to stop."""
        self._running = False

    def run(self) -> None:
        """Thread entry point — connects and listens for events."""
        import websockets.sync.client as ws_sync

        url = f"{self._config.ws_url}/ws/jobs/{self._job_id}"
        retry_delay = 1.0

        while self._running:
            try:
                with ws_sync.connect(url, close_timeout=5) as ws:
                    self.connected.emit()
                    retry_delay = 1.0  # reset on successful connect

                    while self._running:
                        try:
                            message = ws.recv(timeout=5.0)
                            if isinstance(message, bytes):
                                message = message.decode("utf-8")

                            data = json.loads(message)
                            self.event_received.emit(data)

                            # Check for terminal events
                            event = data.get("event", "")
                            if event in (
                                "job.completed",
                                "job.failed",
                                "job.cancelled",
                                "job.timeout",
                            ):
                                self._running = False
                                break

                        except TimeoutError:
                            # Send ping to keep alive
                            try:
                                ws.send("ping")
                            except Exception:
                                break

            except Exception as exc:
                if self._running:
                    self.error_occurred.emit(str(exc))
                    self.disconnected.emit()
                    # Exponential backoff reconnect
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30.0)

        self.disconnected.emit()
