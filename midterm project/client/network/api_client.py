"""
HTTP API client for communicating with the worker.

Uses httpx for async HTTP requests.  All methods are synchronous wrappers
suitable for calling from QThread (the GUI thread never calls these directly).
"""

from __future__ import annotations

import time
from typing import Optional

import httpx

from client.config import ClientConfig
from shared.schemas import (
    HealthResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
    LatencyResult,
    WorkerInfoResponse,
)


class APIClient:
    """Synchronous HTTP client for the worker REST API."""

    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        self._timeout = httpx.Timeout(connect=5.0, read=30.0, write=300.0, pool=5.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.auth_token}",
        }

    def _url(self, path: str) -> str:
        return f"{self._config.base_url}{path}"

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> HealthResponse:
        """GET /health — no auth required."""
        resp = httpx.get(
            self._url("/health"),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return HealthResponse(**resp.json())

    # ------------------------------------------------------------------
    # Worker Info
    # ------------------------------------------------------------------

    def worker_info(self) -> WorkerInfoResponse:
        """GET /worker/info — requires auth."""
        resp = httpx.get(
            self._url("/worker/info"),
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return WorkerInfoResponse(**resp.json())

    # ------------------------------------------------------------------
    # Latency Test
    # ------------------------------------------------------------------

    def latency_test(self, count: int = 5) -> LatencyResult:
        """Measure round-trip latency to the health endpoint."""
        times_ms: list[float] = []
        failed = 0

        for _ in range(count):
            try:
                start = time.perf_counter()
                httpx.get(self._url("/health"), timeout=httpx.Timeout(5.0))
                elapsed = (time.perf_counter() - start) * 1000
                times_ms.append(elapsed)
            except Exception:
                failed += 1

        if not times_ms:
            return LatencyResult(
                requests=count,
                successful=0,
                failed=count,
                min_ms=0.0,
                avg_ms=0.0,
                max_ms=0.0,
            )

        return LatencyResult(
            requests=count,
            successful=len(times_ms),
            failed=failed,
            min_ms=round(min(times_ms), 2),
            avg_ms=round(sum(times_ms) / len(times_ms), 2),
            max_ms=round(max(times_ms), 2),
        )

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def create_job(
        self,
        request: JobCreateRequest,
        idempotency_key: Optional[str] = None,
    ) -> JobCreateResponse:
        """POST /jobs — create a new transcoding job."""
        headers = self._headers()
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        resp = httpx.post(
            self._url("/jobs"),
            headers=headers,
            json=request.model_dump(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return JobCreateResponse(**resp.json())

    def get_job_status(self, job_id: str) -> JobStatusResponse:
        """GET /jobs/{id} — poll current job state."""
        resp = httpx.get(
            self._url(f"/jobs/{job_id}"),
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return JobStatusResponse(**resp.json())

    def cancel_job(self, job_id: str) -> JobStatusResponse:
        """POST /jobs/{id}/cancel."""
        resp = httpx.post(
            self._url(f"/jobs/{job_id}/cancel"),
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return JobStatusResponse(**resp.json())
