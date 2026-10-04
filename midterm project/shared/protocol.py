"""
WebSocket event type constants.

Both client and worker import these to guarantee consistent event names.
"""


class WSEventType:
    """String constants for WebSocket event types."""

    JOB_CREATED = "job.created"
    UPLOAD_STARTED = "job.upload_started"
    UPLOAD_PROGRESS = "job.upload_progress"
    UPLOAD_COMPLETED = "job.upload_completed"
    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_LOG = "job.log"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    JOB_TIMEOUT = "job.timeout"
    DOWNLOAD_STARTED = "job.download_started"
    DOWNLOAD_PROGRESS = "job.download_progress"
    JOB_FINISHED = "job.finished"

    # Resource metrics pushed during processing
    RESOURCE_UPDATE = "worker.resource_update"
