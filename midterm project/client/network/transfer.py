"""
Streaming file transfer (upload & download) with progress reporting.

Uses httpx for chunked HTTP streaming.  Never loads full files into RAM.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable, Optional

import httpx

from client.config import ClientConfig
from shared.constants import CHUNK_SIZE_BYTES

# Progress callback: (bytes_transferred, total_bytes)
ProgressCallback = Callable[[int, int], None]


class ProgressFileReader:
    """File reader wrapper that tracks read progress for HTTP multipart streaming."""

    def __init__(
        self,
        file_path: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> None:
        self._file = open(file_path, "rb")
        self._total_size = os.path.getsize(file_path)
        self._bytes_read = 0
        self._on_progress = on_progress

    def read(self, size: int = -1) -> bytes:
        data = self._file.read(size)
        if data:
            self._bytes_read += len(data)
            if self._on_progress and self._total_size > 0:
                self._on_progress(self._bytes_read, self._total_size)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._file.seek(offset, whence)

    def tell(self) -> int:
        return self._file.tell()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> ProgressFileReader:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()


def upload_file(
    config: ClientConfig,
    job_id: str,
    file_path: str,
    on_progress: Optional[ProgressCallback] = None,
) -> dict[str, object]:
    """
    Stream-upload a file to the worker.

    Returns the parsed JSON response from the upload endpoint.
    """
    filename = os.path.basename(file_path)
    timeout = httpx.Timeout(600.0, connect=10.0, read=600.0, write=600.0, pool=10.0)

    with ProgressFileReader(file_path, on_progress) as reader:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{config.base_url}/jobs/{job_id}/upload",
                headers={"Authorization": f"Bearer {config.auth_token}"},
                files={"file": (filename, reader, "application/octet-stream")},
            )
            resp.raise_for_status()
            return resp.json()



def download_file(
    config: ClientConfig,
    job_id: str,
    dest_path: str,
    on_progress: Optional[ProgressCallback] = None,
) -> str:
    """
    Stream-download the job result to a local file.

    Returns the path to the downloaded file.
    """
    url = f"{config.base_url}/jobs/{job_id}/result"
    headers = {"Authorization": f"Bearer {config.auth_token}"}

    with httpx.stream("GET", url, headers=headers, timeout=httpx.Timeout(600.0)) as resp:
        resp.raise_for_status()

        # Get total size from Content-Length if available
        total_size = int(resp.headers.get("content-length", 0))
        bytes_received = 0

        # Ensure destination directory exists
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=CHUNK_SIZE_BYTES):
                f.write(chunk)
                bytes_received += len(chunk)
                if on_progress and total_size > 0:
                    on_progress(bytes_received, total_size)

    return dest_path
