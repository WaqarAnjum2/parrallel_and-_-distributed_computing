"""
Whitelist validators for transcoding parameters.

The worker NEVER accepts arbitrary FFmpeg commands from the client.
All parameters are validated against strict whitelists.
"""

from __future__ import annotations

import os
import re

from shared.constants import (
    ALLOWED_BITRATES,
    ALLOWED_CODECS,
    ALLOWED_EXTENSIONS,
    ALLOWED_PRESETS,
    ALLOWED_RESOLUTIONS,
)
from worker.core.exceptions import InvalidParameterError


def validate_codec(codec: str) -> str:
    """Validate and return the NVENC encoder name for the requested codec."""
    if codec not in ALLOWED_CODECS:
        raise InvalidParameterError(
            f"Unsupported codec: '{codec}'",
            field_errors={"codec": [f"Must be one of: {list(ALLOWED_CODECS.keys())}"]},
        )
    return ALLOWED_CODECS[codec]


def validate_resolution(resolution: str) -> str:
    """Validate the resolution is in the whitelist."""
    if resolution not in ALLOWED_RESOLUTIONS:
        raise InvalidParameterError(
            f"Unsupported resolution: '{resolution}'",
            field_errors={"resolution": [f"Must be one of: {ALLOWED_RESOLUTIONS}"]},
        )
    return resolution


def validate_bitrate(bitrate: str) -> str:
    """Validate the bitrate is in the whitelist."""
    if bitrate not in ALLOWED_BITRATES:
        raise InvalidParameterError(
            f"Unsupported bitrate: '{bitrate}'",
            field_errors={"bitrate": [f"Must be one of: {ALLOWED_BITRATES}"]},
        )
    return bitrate


def validate_preset(preset: str) -> str:
    """Validate the NVENC preset is in the whitelist."""
    if preset not in ALLOWED_PRESETS:
        raise InvalidParameterError(
            f"Unsupported preset: '{preset}'",
            field_errors={"preset": [f"Must be one of: {ALLOWED_PRESETS}"]},
        )
    return preset


def validate_filename(filename: str) -> str:
    """
    Validate the filename is safe (no path traversal) and has an allowed extension.

    The worker generates its own internal storage path — this only validates
    the original filename the client declares.
    """
    # Block path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise InvalidParameterError(
            "Filename contains illegal path characters.",
            field_errors={"filename": ["Must not contain '..', '/', or '\\\\'"]},
        )

    # Block absolute paths
    if os.path.isabs(filename):
        raise InvalidParameterError(
            "Filename must be a relative name, not an absolute path.",
        )

    # Validate extension
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidParameterError(
            f"Unsupported file type: '{ext}'",
            field_errors={"filename": [f"Must be one of: {sorted(ALLOWED_EXTENSIONS)}"]},
        )

    return filename


def validate_file_size(size_bytes: int, max_bytes: int) -> None:
    """Raise if the declared file size exceeds the configured limit."""
    if size_bytes <= 0:
        raise InvalidParameterError("File size must be positive.")

    if size_bytes > max_bytes:
        size_mb = size_bytes / (1024 * 1024)
        max_mb = max_bytes // (1024 * 1024)
        from worker.core.exceptions import FileTooLargeError
        raise FileTooLargeError(size_mb, max_mb)


def validate_sha256(sha256: str) -> str:
    """Validate that the SHA-256 hash looks valid (64 hex chars)."""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
        raise InvalidParameterError(
            "Invalid SHA-256 hash format.",
            field_errors={"sha256": ["Must be exactly 64 hexadecimal characters"]},
        )
    return sha256.lower()
