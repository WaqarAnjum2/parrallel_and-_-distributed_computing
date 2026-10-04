"""
Integration tests for Job lifecycle endpoints (create, status, cancel).
"""

from starlette.testclient import TestClient
from worker.main import create_app
from worker.core.config import get_settings


def test_job_create_and_get_status():
    """Create a valid job and verify its status can be retrieved."""
    app = create_app()
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.auth_token}"}

    with TestClient(app) as client:
        payload = {
            "filename": "test_video.mp4",
            "size": 1024 * 1024 * 5,
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "codec": "h264",
            "resolution": "1920x1080",
            "bitrate": "5M",
            "preset": "p4",
        }

        resp = client.post("/jobs", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "CREATED"
        job_id = data["job_id"]

        # Retrieve status
        status_resp = client.get(f"/jobs/{job_id}", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] == "CREATED"


def test_job_create_invalid_parameters():
    """Attempting to create a job with invalid params should return 422 or 400."""
    app = create_app()
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.auth_token}"}

    with TestClient(app) as client:
        payload = {
            "filename": "malicious.sh",
            "size": 1024,
            "sha256": "bad_hash",
            "codec": "invalid_codec",
            "resolution": "9999x9999",
            "bitrate": "999M",
            "preset": "ultra_invalid",
        }

        resp = client.post("/jobs", json=payload, headers=headers)
        assert resp.status_code in (400, 422)


def test_job_create_idempotency():
    """Sending the same X-Idempotency-Key returns the cached response."""
    app = create_app()
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.auth_token}",
        "X-Idempotency-Key": "unique-idempotency-key-12345",
    }

    with TestClient(app) as client:
        payload = {
            "filename": "idempotent.mp4",
            "size": 1024 * 1024,
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "codec": "h264",
            "resolution": "1280x720",
            "bitrate": "3M",
            "preset": "p4",
        }

        resp1 = client.post("/jobs", json=payload, headers=headers)
        assert resp1.status_code == 201
        job_id1 = resp1.json()["job_id"]

        # Repeat with same key
        resp2 = client.post("/jobs", json=payload, headers=headers)
        assert resp2.status_code == 201
        job_id2 = resp2.json()["job_id"]
        assert job_id1 == job_id2


def test_job_cancellation():
    """Cancel a newly created job."""
    app = create_app()
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.auth_token}"}

    with TestClient(app) as client:
        payload = {
            "filename": "cancel_me.mp4",
            "size": 1024 * 1024,
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "codec": "h264",
            "resolution": "1920x1080",
            "bitrate": "5M",
            "preset": "p4",
        }

        create_resp = client.post("/jobs", json=payload, headers=headers)
        job_id = create_resp.json()["job_id"]

        cancel_resp = client.post(f"/jobs/{job_id}/cancel", headers=headers)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"
