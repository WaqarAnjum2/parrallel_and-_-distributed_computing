"""
Failure scenario tests: Worker Offline (E01).

Verifies that connecting to an unreachable host or closed port
yields friendly, descriptive errors rather than uncaught exceptions.
"""

import httpx
import pytest
from client.config import ClientConfig
from client.network.api_client import APIClient


def test_offline_worker_connection_refused():
    """Connecting to a non-existent port should raise ConnectError or return empty latency."""
    config = ClientConfig(
        worker_host="127.0.0.1",
        worker_port=59999,  # closed port
        auth_token="dummy_token",
    )
    client = APIClient(config)
    with pytest.raises(httpx.ConnectError):
        client.health()

    latency_result = client.latency_test(count=2)
    assert latency_result.successful == 0
    assert latency_result.failed == 2
    assert latency_result.avg_ms == 0.0
