"""
Streaming SHA-256 checksum calculator.

Computes the hash in chunks to avoid loading large video files into RAM.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Optional

from shared.constants import CHUNK_SIZE_BYTES

# Progress callback: (bytes_processed, total_bytes)
ProgressCallback = Callable[[int, int], None]


def compute_sha256(
    file_path: str,
    total_size: int = 0,
    on_progress: Optional[ProgressCallback] = None,
) -> str:
    """
    Compute the SHA-256 hash of a file using streaming chunks.

    Args:
        file_path: Absolute path to the file.
        total_size: Total file size (for progress reporting).
        on_progress: Optional callback receiving (bytes_read, total).

    Returns:
        The lowercase hexadecimal SHA-256 digest.
    """
    sha256 = hashlib.sha256()
    bytes_read = 0

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE_BYTES)
            if not chunk:
                break
            sha256.update(chunk)
            bytes_read += len(chunk)
            if on_progress and total_size > 0:
                on_progress(bytes_read, total_size)

    return sha256.hexdigest()
