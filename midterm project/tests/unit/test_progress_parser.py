"""
Unit tests for FFmpeg progress parser.
"""

from pathlib import Path

from worker.jobs.executor import JobExecutor
from worker.jobs.models import Job


class TestProgressParser:
    """Test parsing FFmpeg out_time strings into seconds."""

    def test_parse_time_standard(self) -> None:
        assert JobExecutor._parse_time("00:01:23.456789") == 83.456789

    def test_parse_time_zero(self) -> None:
        assert JobExecutor._parse_time("00:00:00.000000") == 0.0

    def test_parse_time_hours(self) -> None:
        assert JobExecutor._parse_time("02:30:15.500000") == 2 * 3600 + 30 * 60 + 15.5

    def test_parse_time_negative(self) -> None:
        val = JobExecutor._parse_time("-00:00:01.500000")
        assert val == -1.5

    def test_parse_time_invalid(self) -> None:
        assert JobExecutor._parse_time("invalid_time") == -1.0
        assert JobExecutor._parse_time("N/A") == -1.0
