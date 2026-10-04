"""
Failure scenario tests: Checksum Mismatch (E06).

Verifies that if the uploaded file's content doesn't match the declared
SHA-256 hash, the worker rejects the upload, cleans up the file,
marks the job FAILED, and refuses to process it.
"""

import io
from starlette.testclient import TestClient
from worker.main import create_app
from worker.core.config import get_settings


def test_upload_checksum_mismatch():
    """Altered content upload must be rejected with an integrity error."""
    app = create_app()
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.auth_token}"}

    with TestClient(app) as client:
        # Create job with declared hash A
        declared_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        payload = {
            "filename": "corrupted.mp4",
            "size": 100,
            "sha256": declared_hash,
            "codec": "h264",
            "resolution": "1920x1080",
            "bitrate": "5M",
            "preset": "p4",
        }

        resp = client.post("/jobs", json=payload, headers=headers)
        assert resp.status_code == 201
        job_id = resp.json()["job_id"]

        # Upload different content whose hash does NOT match declared_hash
        fake_content = b"Corrupted video data stream that has a completely different hash"
        files = {"file": ("corrupted.mp4", io.BytesIO(fake_content), "video/mp4")}

        upload_resp = client.post(f"/jobs/{job_id}/upload", files=files, headers=headers)
        assert upload_resp.status_code in (400, 409, 422)

        # Verify job is now in FAILED state
        status_resp = client.get(f"/jobs/{job_id}", headers=headers)
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "FAILED"
