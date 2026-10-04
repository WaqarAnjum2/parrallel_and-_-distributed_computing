"""
Unit tests for FFmpeg command builder.
"""

from pathlib import Path

from worker.jobs.executor import JobExecutor
from worker.jobs.models import Job


class TestFFmpegBuilder:
    """Verify that the executor builds safe FFmpeg argument lists."""

    def _make_executor(self) -> JobExecutor:
        return JobExecutor(
            input_dir=Path("./data/inputs"),
            output_dir=Path("./data/outputs"),
            temp_dir=Path("./data/temp"),
        )

    def test_basic_h264_command(self) -> None:
        """Verify correct argument list for H.264 NVENC encoding."""
        executor = self._make_executor()
        job = Job(
            job_id="JOB-TEST-001",
            input_path="./data/inputs/JOB-TEST-001/input.mp4",
            output_codec="h264_nvenc",
            resolution="1920x1080",
            bitrate="5M",
            preset="p4",
        )
        cmd = executor._build_command(job)

        assert "ffmpeg" in cmd[0].lower()
        assert "-y" in cmd
        assert "-i" in cmd
        assert "h264_nvenc" in cmd
        assert "p4" in cmd
        assert "5M" in cmd
        assert "scale=1920:1080" in " ".join(cmd)
        assert "-progress" in cmd
        assert "pipe:1" in cmd
        # Must NOT contain shell=True related strings
        assert "shell" not in str(cmd).lower()

    def test_hevc_command(self) -> None:
        """Verify HEVC encoder is used when requested."""
        executor = self._make_executor()
        job = Job(
            job_id="JOB-TEST-002",
            input_path="./data/inputs/JOB-TEST-002/input.mkv",
            output_codec="hevc_nvenc",
            resolution="3840x2160",
            bitrate="20M",
            preset="p2",
        )
        cmd = executor._build_command(job)
        assert "hevc_nvenc" in cmd
        assert "20M" in cmd
        assert "scale=3840:2160" in " ".join(cmd)

    def test_output_path_set(self) -> None:
        """The build_command method must set job.output_path."""
        executor = self._make_executor()
        job = Job(
            job_id="JOB-TEST-003",
            input_path="./data/inputs/JOB-TEST-003/input.mp4",
            output_codec="h264_nvenc",
            resolution="1280x720",
            bitrate="2M",
            preset="p4",
        )
        executor._build_command(job)
        assert job.output_path is not None
        assert "JOB-TEST-003" in job.output_path


class TestProgressParser:
    """Test the FFmpeg progress time parser."""

    def test_normal_time(self) -> None:
        result = JobExecutor._parse_time("00:01:23.456789")
        assert abs(result - 83.456789) < 0.001

    def test_zero_time(self) -> None:
        result = JobExecutor._parse_time("00:00:00.000000")
        assert result == 0.0

    def test_hours(self) -> None:
        result = JobExecutor._parse_time("02:30:00.000000")
        assert abs(result - 9000.0) < 0.001

    def test_invalid_format(self) -> None:
        result = JobExecutor._parse_time("invalid")
        assert result == -1.0

    def test_negative_time(self) -> None:
        result = JobExecutor._parse_time("-00:00:01.000000")
        assert result < 0
