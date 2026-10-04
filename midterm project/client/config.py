"""
Client configuration loader.

Reads worker connection settings from .env or allows runtime override
from the PyQt6 GUI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClientConfig:
    """Client-side configuration for connecting to the worker."""

    worker_host: str = "192.168.1.10"
    worker_port: int = 8000
    auth_token: str = "change-me-to-a-secure-random-string"

    @property
    def base_url(self) -> str:
        return f"http://{self.worker_host}:{self.worker_port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.worker_host}:{self.worker_port}"

    def update(self, host: str, port: int, token: str) -> None:
        """Update connection settings (called from the GUI)."""
        self.worker_host = host.strip()
        self.worker_port = port
        self.auth_token = token.strip()


def load_config() -> ClientConfig:
    """
    Load client config from environment or return defaults.
    The GUI will override these at runtime.
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    return ClientConfig(
        worker_host=os.getenv("CLIENT_WORKER_HOST", "192.168.1.10"),
        worker_port=int(os.getenv("CLIENT_WORKER_PORT", "8000")),
        auth_token=os.getenv("CLIENT_AUTH_TOKEN", "change-me-to-a-secure-random-string"),
    )
