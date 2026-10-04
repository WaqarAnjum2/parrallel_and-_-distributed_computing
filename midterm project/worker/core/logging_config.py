"""
Structured logging configuration for the worker.

Produces human-readable logs with timestamp, level, event, and optional job_id.
"""

import logging
import sys
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Formatter that produces structured log lines."""

    def format(self, record: logging.LogRecord) -> str:
        job_id: Optional[str] = getattr(record, "job_id", None)
        base = f"{self.formatTime(record)} {record.levelname:<5} {record.getMessage()}"
        if job_id:
            base += f" job_id={job_id}"
        if record.exc_info and record.exc_info[1]:
            base += f" error={record.exc_info[1]}"
        return base


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root worker logger."""
    logger = logging.getLogger("worker")
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(StructuredFormatter(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))
        logger.addHandler(handler)

    return logger
