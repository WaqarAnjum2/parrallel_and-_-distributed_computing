"""
Unit tests for benchmark calculations.
"""

from client.services.benchmark import calculate_speedup
from shared.schemas import BenchmarkRecord


class TestBenchmarkCalculations:
    """Verify speedup and network overhead formulas."""

    def test_speedup_calculation(self) -> None:
        """Speedup = T_local / T_remote"""
        remote_total, speedup, overhead = calculate_speedup(
            local_time=300.0,
            upload_time=20.0,
            gpu_time=80.0,
            download_time=10.0,
        )
        # T_remote = 20 + 80 + 10 = 110
        assert remote_total == 110.0
        # Speedup = 300 / 110 ≈ 2.73
        assert abs(speedup - 2.73) < 0.01

    def test_network_overhead(self) -> None:
        """Overhead% = ((T_upload + T_download) / T_remote) * 100"""
        _, _, overhead = calculate_speedup(
            local_time=300.0,
            upload_time=30.0,
            gpu_time=60.0,
            download_time=10.0,
        )
        # Overhead = (30 + 10) / 100 * 100 = 40%
        assert abs(overhead - 40.0) < 0.1

    def test_zero_remote_time(self) -> None:
        """When remote time is zero, speedup should be 0 (not divide by zero)."""
        remote_total, speedup, overhead = calculate_speedup(
            local_time=100.0,
            upload_time=0.0,
            gpu_time=0.0,
            download_time=0.0,
        )
        assert remote_total == 0.0
        assert speedup == 0.0
        assert overhead == 0.0

    def test_remote_slower_than_local(self) -> None:
        """When remote is slower, speedup should be < 1."""
        _, speedup, _ = calculate_speedup(
            local_time=50.0,
            upload_time=30.0,
            gpu_time=40.0,
            download_time=20.0,
        )
        # T_remote = 90, Speedup = 50/90 ≈ 0.56
        assert speedup < 1.0

    def test_benchmark_record_creation(self) -> None:
        """BenchmarkRecord should hold all fields."""
        record = BenchmarkRecord(
            test_id="B01",
            input_size_mb=100.5,
            resolution="1280x720",
            duration_seconds=120.0,
            local_time_seconds=200.0,
            upload_seconds=10.0,
            gpu_seconds=50.0,
            download_seconds=8.0,
            remote_total_seconds=68.0,
            speedup=2.94,
            network_overhead_percent=26.5,
        )
        assert record.test_id == "B01"
        assert record.speedup == 2.94
