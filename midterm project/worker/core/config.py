"""
Worker configuration loaded from environment variables.

Uses pydantic-settings for typed, validated config that fails fast
if a required variable is missing at startup.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """All worker configuration — sourced from .env or environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    worker_host: str = "0.0.0.0"
    worker_port: int = 8000

    # Authentication
    auth_token: str = "change-me-to-a-secure-random-string"

    # Storage paths
    input_directory: str = "./data/inputs"
    output_directory: str = "./data/outputs"
    temp_directory: str = "./data/temp"

    # Resource limits
    max_file_size_mb: int = 4096
    max_job_duration_seconds: int = 7200
    max_queue_size: int = 20
    max_concurrent_jobs: int = 1

    # Derived properties -----------------------------------------------

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def input_path(self) -> Path:
        return Path(self.input_directory)

    @property
    def output_path(self) -> Path:
        return Path(self.output_directory)

    @property
    def temp_path(self) -> Path:
        return Path(self.temp_directory)


def get_settings() -> WorkerSettings:
    """Create and return a validated WorkerSettings instance."""
    return WorkerSettings()
