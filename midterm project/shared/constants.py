"""
Shared constants for the Distributed GPU Task Offloading system.

Whitelists for codecs, resolutions, bitrates, presets, and file types
used by both client and worker for validation.
"""

from enum import Enum

# ---------------------------------------------------------------------------
# Job States
# ---------------------------------------------------------------------------

class JobState(str, Enum):
    """Explicit job state machine states."""
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    DOWNLOADING = "DOWNLOADING"
    FINISHED = "FINISHED"
    INTERRUPTED = "INTERRUPTED"


# Valid state transitions: source -> set of allowed targets
VALID_STATE_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.CREATED: {JobState.UPLOADING, JobState.CANCELLED},
    JobState.UPLOADING: {JobState.UPLOADED, JobState.FAILED},
    JobState.UPLOADED: {JobState.QUEUED},
    JobState.QUEUED: {JobState.PROCESSING, JobState.CANCELLED},
    JobState.PROCESSING: {
        JobState.COMPLETED,
        JobState.FAILED,
        JobState.CANCELLED,
        JobState.TIMEOUT,
    },
    JobState.COMPLETED: {JobState.DOWNLOADING},
    JobState.DOWNLOADING: {JobState.FINISHED, JobState.FAILED},
    # Terminal states — no outgoing transitions
    JobState.FINISHED: set(),
    JobState.FAILED: set(),
    JobState.CANCELLED: set(),
    JobState.TIMEOUT: set(),
    JobState.INTERRUPTED: set(),
}


def is_valid_transition(current: JobState, target: JobState) -> bool:
    """Check whether a state transition is permitted."""
    allowed = VALID_STATE_TRANSITIONS.get(current, set())
    return target in allowed


# ---------------------------------------------------------------------------
# Allowed Codecs
# ---------------------------------------------------------------------------

ALLOWED_CODECS: dict[str, str] = {
    "h264": "h264_nvenc",
    "hevc": "hevc_nvenc",
}

# ---------------------------------------------------------------------------
# Allowed Presets (NVENC)
# ---------------------------------------------------------------------------

ALLOWED_PRESETS: list[str] = [
    "p1",
    "p2",
    "p3",
    "p4",
    "p5",
    "p6",
    "p7",
]

# ---------------------------------------------------------------------------
# Allowed Resolutions
# ---------------------------------------------------------------------------

ALLOWED_RESOLUTIONS: list[str] = [
    "3840x2160",
    "2560x1440",
    "1920x1080",
    "1280x720",
    "854x480",
    "640x360",
]

# ---------------------------------------------------------------------------
# Allowed Bitrates
# ---------------------------------------------------------------------------

ALLOWED_BITRATES: list[str] = [
    "1M",
    "2M",
    "3M",
    "5M",
    "8M",
    "10M",
    "12M",
    "15M",
    "20M",
]

# ---------------------------------------------------------------------------
# File Type Whitelist
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: set[str] = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".ts",
    ".m4v",
}

# ---------------------------------------------------------------------------
# Transfer / Hashing
# ---------------------------------------------------------------------------

CHUNK_SIZE_BYTES: int = 1_048_576  # 1 MB streaming chunk
HASH_ALGORITHM: str = "sha256"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_PORT: int = 8000
DEFAULT_HOST: str = "0.0.0.0"
DEFAULT_MAX_FILE_SIZE_MB: int = 4096
DEFAULT_MAX_JOB_DURATION_SECONDS: int = 7200
DEFAULT_MAX_QUEUE_SIZE: int = 20
DEFAULT_MAX_CONCURRENT_JOBS: int = 1

LATENCY_TEST_COUNT: int = 5
