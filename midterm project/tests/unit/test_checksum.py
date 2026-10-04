"""
Unit tests for SHA-256 checksum computation.
"""

import hashlib
import os
import tempfile

from client.services.checksum import compute_sha256


class TestChecksum:
    """Test streaming SHA-256 hash computation."""

    def test_known_hash(self) -> None:
        """Verify hash of a known byte string."""
        content = b"Hello, Distributed GPU Worker!"
        expected = hashlib.sha256(content).hexdigest()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(content)
            path = f.name

        try:
            result = compute_sha256(path, total_size=len(content))
            assert result == expected
        finally:
            os.unlink(path)

    def test_empty_file(self) -> None:
        """Empty file should produce the SHA-256 of empty bytes."""
        expected = hashlib.sha256(b"").hexdigest()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            path = f.name

        try:
            result = compute_sha256(path)
            assert result == expected
        finally:
            os.unlink(path)

    def test_large_file_chunked(self) -> None:
        """Verify chunked hashing matches single-pass hashing for a larger file."""
        content = os.urandom(5 * 1024 * 1024)  # 5 MB
        expected = hashlib.sha256(content).hexdigest()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(content)
            path = f.name

        try:
            result = compute_sha256(path, total_size=len(content))
            assert result == expected
        finally:
            os.unlink(path)

    def test_progress_callback(self) -> None:
        """Verify progress callback is called during hashing."""
        content = b"x" * (3 * 1024 * 1024)  # 3 MB
        progress_calls: list[tuple[int, int]] = []

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(content)
            path = f.name

        try:
            compute_sha256(
                path,
                total_size=len(content),
                on_progress=lambda done, total: progress_calls.append((done, total)),
            )
            assert len(progress_calls) >= 1
            # Last call should have done == total
            assert progress_calls[-1][0] == len(content)
        finally:
            os.unlink(path)
