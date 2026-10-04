"""
Custom exception types for the worker.

Each maps to a specific HTTP error code and standardised error response.
"""

from fastapi import HTTPException, status


class JobNotFoundError(HTTPException):
    """Raised when a job_id does not exist in the registry."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Job '{job_id}' does not exist.",
            },
        )


class InvalidParameterError(HTTPException):
    """Raised when a client-provided parameter fails validation."""

    def __init__(self, message: str, field_errors: dict[str, list[str]] | None = None) -> None:
        detail: dict[str, object] = {
            "code": "INVALID_PARAMETER",
            "message": message,
        }
        if field_errors:
            detail["field_errors"] = field_errors
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class IntegrityError(HTTPException):
    """Raised when uploaded file checksum doesn't match the declared hash."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INTEGRITY_FAILURE",
                "message": "Input integrity verification failed.",
                "expected_sha256": expected,
                "actual_sha256": actual,
            },
        )


class InsufficientStorageError(HTTPException):
    """Raised when the worker doesn't have enough disk space."""

    def __init__(self, required_mb: float, available_mb: float) -> None:
        super().__init__(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail={
                "code": "INSUFFICIENT_STORAGE",
                "message": (
                    f"Insufficient worker storage. "
                    f"Required: {required_mb:.0f} MB, Available: {available_mb:.0f} MB."
                ),
            },
        )


class QueueFullError(HTTPException):
    """Raised when the job queue has reached its maximum capacity."""

    def __init__(self, max_size: int) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "QUEUE_FULL",
                "message": f"Job queue is full (max {max_size}). Try again later.",
            },
        )


class InvalidStateTransitionError(HTTPException):
    """Raised when an invalid job state transition is attempted."""

    def __init__(self, job_id: str, current: str, target: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": (
                    f"Cannot transition job '{job_id}' "
                    f"from {current} to {target}."
                ),
            },
        )


class FileTooLargeError(HTTPException):
    """Raised when the input file exceeds the configured maximum."""

    def __init__(self, size_mb: float, max_mb: int) -> None:
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": (
                    f"File size ({size_mb:.0f} MB) exceeds "
                    f"the configured maximum ({max_mb} MB)."
                ),
            },
        )
