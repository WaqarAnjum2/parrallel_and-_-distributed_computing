"""
Integration tests for Worker Health & Info endpoints.
"""

import pytest
import httpx
from worker.main import create_app
from worker.core.config import get_settings


from starlette.testclient import TestClient
from worker.main import create_app
from worker.core.config import get_settings


def test_health_check_unauthenticated():
    """GET /health should succeed without any auth headers."""
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["ready"] is True
        assert "gpu_available" in data
        assert "nvenc_available" in data
        assert "queue_size" in data


def test_worker_info_requires_auth():
    """GET /worker/info without auth should return 401."""
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/worker/info")
        assert resp.status_code == 401


def test_worker_info_with_valid_auth():
    """GET /worker/info with valid Bearer token should return hardware info."""
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.auth_token}"}
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/worker/info", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "hostname" in data
        assert "platform" in data
        assert "cpu" in data
        assert "gpu" in data
        assert "max_concurrent_jobs" in data

