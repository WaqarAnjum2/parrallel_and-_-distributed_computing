"""
Client-side Networking and Communication Module.
Handles HTTP, WebSocket streaming, SHA-256 checksums, and latency measurement.
"""
import asyncio
import json
import os
import sys
import time
from typing import Any, Callable, Dict, Optional, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
import websockets

from common.protocol import HandshakeRequest, HandshakeResponse, ProgressUpdate, RenderConfig, compute_sha256


class NetworkClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8500, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    def handshake(self) -> Tuple[bool, float, Optional[HandshakeResponse], str]:
        """
        Task 1: Performs initial handshake and computes Round-Trip Time (RTT) latency in ms.
        Returns: (success, latency_ms, HandshakeResponse, error_message)
        """
        req_obj = HandshakeRequest(client_id="client-laptop-gui", client_timestamp=time.time())
        url = f"{self.base_url}/api/handshake"
        t_start = time.perf_counter()

        try:
            resp = requests.post(url, json=req_obj.model_dump(), timeout=self.timeout)
            t_end = time.perf_counter()
            latency_ms = (t_end - t_start) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                parsed = HandshakeResponse(**data)
                return True, round(latency_ms, 2), parsed, ""
            else:
                return False, 0.0, None, f"Server responded with code {resp.status_code}: {resp.text}"
        except requests.exceptions.ConnectionError:
            return False, 0.0, None, f"Could not connect to {self.base_url}. Verify server is running and IP is correct."
        except requests.exceptions.Timeout:
            return False, 0.0, None, f"Connection to {self.base_url} timed out ({self.timeout}s)."
        except Exception as ex:
            return False, 0.0, None, str(ex)

    def upload_file(
        self,
        file_path: str,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[bool, str, str, str]:
        """
        Uploads local video file with SHA-256 validation.
        Returns: (success, job_id, sha256_hash, error_msg)
        """
        if not os.path.exists(file_path):
            return False, "", "", f"File '{file_path}' does not exist."

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "", "", "Selected file is empty (0 bytes)."

        if progress_cb:
            progress_cb(0.0, "Computing SHA-256 checksum...")

        try:
            file_hash = compute_sha256(file_path)
        except Exception as e:
            return False, "", "", f"Hashing failed: {e}"

        if progress_cb:
            progress_cb(5.0, f"SHA-256: {file_hash[:16]}... Uploading file...")

        url = f"{self.base_url}/api/upload"

        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "video/mp4")}
                data = {"sha256_checksum": file_hash}
                resp = requests.post(url, files=files, data=data, timeout=60)

            if resp.status_code == 200:
                res_data = resp.json()
                job_id = res_data.get("job_id", "")
                if progress_cb:
                    progress_cb(10.0, f"Uploaded! Job ID: {job_id}")
                return True, job_id, file_hash, ""
            else:
                return False, "", file_hash, f"Upload error {resp.status_code}: {resp.text}"
        except Exception as ex:
            return False, "", file_hash, f"Network upload failure: {str(ex)}"

    def start_job(self, job_id: str, config: RenderConfig) -> Tuple[bool, str]:
        """Triggers execution on worker daemon."""
        url = f"{self.base_url}/api/jobs/{job_id}/start"
        try:
            resp = requests.post(url, json=config.model_dump(), timeout=self.timeout)
            if resp.status_code == 200:
                return True, ""
            return False, f"Failed to start job ({resp.status_code}): {resp.text}"
        except Exception as ex:
            return False, str(ex)

    async def listen_progress_ws(
        self,
        job_id: str,
        on_progress: Callable[[float, float, str, str], None],
        on_log: Callable[[str], None],
        stop_check: Callable[[], bool]
    ) -> Tuple[bool, Optional[str]]:
        """
        Task 4: Connects to server WebSocket and listens for live rendering progress and logs.
        Returns: (success, output_sha256)
        """
        ws_url = f"{self.ws_url}/ws/progress/{job_id}"
        output_sha256 = None

        try:
            async with websockets.connect(ws_url, close_timeout=5) as ws:
                while not stop_check():
                    try:
                        msg_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        data = json.loads(msg_raw)
                        msg_type = data.get("type")

                        if msg_type == "log":
                            on_log(data.get("line", ""))
                        elif msg_type == "progress":
                            pct = float(data.get("percent", 0.0))
                            fps = float(data.get("fps", 0.0))
                            spd = data.get("speed", "0x")
                            log_line = data.get("log_line", "")
                            if log_line:
                                on_log(log_line)
                            on_progress(pct, fps, spd, log_line)

                            if data.get("output_sha256"):
                                output_sha256 = data.get("output_sha256")

                            status = data.get("status")
                            if status == "COMPLETED":
                                return True, output_sha256
                            elif status in ["FAILED", "CANCELLED"]:
                                err = data.get("error_msg") or "Job terminated abnormally"
                                on_log(f"[Error] {err}")
                                return False, None
                        elif msg_type == "ping":
                            pct = float(data.get("percent", 0.0))
                            on_progress(pct, 0.0, "", "")
                    except asyncio.TimeoutError:
                        if stop_check():
                            break
                        continue
        except Exception as e:
            on_log(f"[Network] WebSocket disconnected ({e}). Falling back to HTTP polling...")
            return self._poll_status_http(job_id, on_progress, on_log, stop_check)

        return True, output_sha256

    def _poll_status_http(
        self,
        job_id: str,
        on_progress: Callable,
        on_log: Callable,
        stop_check: Callable
    ) -> Tuple[bool, Optional[str]]:
        """Fallback polling when WebSocket encounters unexpected disconnects."""
        url = f"{self.base_url}/api/jobs/{job_id}/status"
        seen_logs = set()

        while not stop_check():
            try:
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    pct = float(data.get("progress", 0.0))
                    fps = float(data.get("fps", 0.0))
                    spd = data.get("speed", "0x")
                    on_progress(pct, fps, spd, f"Status: {status}")

                    for l in data.get("logs", []):
                        if l not in seen_logs:
                            seen_logs.add(l)
                            on_log(l)

                    if status == "COMPLETED":
                        return True, data.get("output_sha256")
                    elif status in ["FAILED", "CANCELLED"]:
                        return False, None
                time.sleep(1.0)
            except Exception:
                time.sleep(1.5)
        return False, None

    def download_file(
        self,
        job_id: str,
        dest_path: str,
        expected_sha256: Optional[str] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Downloads rendered video file and validates SHA-256 checksum.
        """
        url = f"{self.base_url}/api/jobs/{job_id}/download"
        try:
            if progress_cb:
                progress_cb(0.0, "Initiating download...")

            resp = requests.get(url, stream=True, timeout=60)
            if resp.status_code != 200:
                return False, f"Download failed with code {resp.status_code}: {resp.text}"

            server_hash = resp.headers.get("X-File-SHA256") or expected_sha256
            total_length = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_length > 0 and progress_cb:
                            pct = (downloaded / total_length) * 100.0
                            progress_cb(pct, f"Downloaded {downloaded / (1024*1024):.1f} MB / {total_length / (1024*1024):.1f} MB")

            # Check integrity
            if server_hash:
                local_hash = compute_sha256(dest_path)
                if local_hash.lower() != server_hash.lower():
                    return False, f"Downloaded file checksum mismatch! Server: {server_hash[:16]}, Local: {local_hash[:16]}"

            if progress_cb:
                progress_cb(100.0, "Download complete and verified!")
            return True, ""
        except Exception as ex:
            return False, f"Download error: {str(ex)}"

    def cancel_job(self, job_id: str) -> bool:
        """Sends abort signal to worker node."""
        try:
            resp = requests.delete(f"{self.base_url}/api/jobs/{job_id}", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

