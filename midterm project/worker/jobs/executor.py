"""
FFmpeg subprocess executor with real-time progress parsing.

Builds the FFmpeg command from validated parameters (never shell strings),
runs it as a managed subprocess, parses machine-readable progress,
supports cancellation and timeout.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional, Callable, Coroutine

from shared.constants import JobState
from worker.jobs.models import Job

from worker.gpu.nvenc import resolve_ffmpeg_path

logger = logging.getLogger("worker")

# Progress callback type: receives (job_id, progress%, fps, speed_str)
ProgressCallback = Callable[[str, int, float, str], Coroutine[None, None, None]]


class JobExecutor:
    """
    Executes FFmpeg transcoding as an async subprocess.

    One executor instance per worker — it manages one running process
    at a time (called by the TaskQueue consumer loop).
    """

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        temp_dir: Path,
        max_duration_seconds: int = 7200,
        ffmpeg_path: str = "ffmpeg",
    ) -> None:
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._temp_dir = temp_dir
        self._max_duration = max_duration_seconds
        self._ffmpeg_path = resolve_ffmpeg_path(ffmpeg_path)
        self._current_process: Optional[asyncio.subprocess.Process] = None
        self._current_job_id: Optional[str] = None
        self._progress_callback: Optional[ProgressCallback] = None

    def set_progress_callback(self, cb: ProgressCallback) -> None:
        self._progress_callback = cb

    # ------------------------------------------------------------------
    # FFmpeg command builder
    # ------------------------------------------------------------------

    def _build_command(self, job: Job, encoder_override: str | None = None) -> list[str]:
        """
        Build an FFmpeg argument list from validated job parameters.

        Never uses shell=True.  Never accepts raw user command strings.
        """
        input_path = str(Path(job.input_path) if job.input_path else "")
        output_dir = self._output_dir / job.job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / "output.mp4")
        job.output_path = output_path

        width, height = job.resolution.split("x")
        codec = encoder_override or job.output_codec

        cmd = [
            self._ffmpeg_path,
            "-y",                         # overwrite output
            "-i", input_path,
            "-c:v", codec,
        ]

        if "nvenc" in codec:
            cmd.extend(["-preset", job.preset])
        elif codec.startswith("libx"):
            cmd.extend(["-preset", "fast"])

        cmd.extend([
            "-b:v", job.bitrate,
            "-vf", f"scale={width}:{height}",
            "-progress", "pipe:1",        # machine-readable progress to stdout
            "-stats_period", "0.5",       # update every 0.5s
            output_path,
        ])
        return cmd

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, job: Job) -> None:
        """
        Run the full FFmpeg lifecycle for a job:
        QUEUED -> PROCESSING -> COMPLETED / FAILED / TIMEOUT
        """
        job.transition_to(JobState.PROCESSING)
        logger.info("processing.started", extra={"job_id": job.job_id})

        cmd = self._build_command(job)
        logger.info(
            f"ffmpeg.command: {' '.join(cmd)}",
            extra={"job_id": job.job_id},
        )

        start_time = time.monotonic()
        self._current_job_id = job.job_id

        try:
            self._current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Parse progress from stdout while FFmpeg runs
            await self._read_progress(job, start_time)

            # Wait for process to finish (with timeout)
            remaining_timeout = self._max_duration - (time.monotonic() - start_time)
            if remaining_timeout <= 0:
                await self._handle_timeout(job)
                return

            try:
                await asyncio.wait_for(
                    self._current_process.wait(),
                    timeout=max(remaining_timeout, 1),
                )
            except asyncio.TimeoutError:
                await self._handle_timeout(job)
                return

            # Check if NVENC driver mismatch occurred and attempt automatic hardware fallback
            if self._current_process.returncode != 0:
                stderr_bytes = await self._current_process.stderr.read() if self._current_process.stderr else b""
                stderr_text = stderr_bytes.decode("utf-8", errors="replace")
                is_nvenc_err = any(
                    x in stderr_text.lower()
                    for x in ["nvenc", "driver does not support", "function not implemented", "could not open encoder"]
                )
                if is_nvenc_err and "nvenc" in job.output_codec:
                    fallback_codec = "h264_mf" if "264" in job.output_codec else "hevc_mf"
                    logger.warning(
                        f"NVENC driver version mismatch detected. Retrying with system hardware encoder: {fallback_codec}",
                        extra={"job_id": job.job_id},
                    )
                    fallback_cmd = self._build_command(job, encoder_override=fallback_codec)
                    self._current_process = await asyncio.create_subprocess_exec(
                        *fallback_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await self._read_progress(job, start_time)
                    await asyncio.wait_for(
                        self._current_process.wait(),
                        timeout=max(self._max_duration, 1),
                    )

            elapsed = time.monotonic() - start_time
            job.elapsed_seconds = round(elapsed, 2)

            if self._current_process.returncode == 0:
                job.progress = 100
                # Measure output size
                if job.output_path and os.path.exists(job.output_path):
                    job.output_size = os.path.getsize(job.output_path)
                job.transition_to(JobState.COMPLETED)
                logger.info(
                    f"processing.completed elapsed={job.elapsed_seconds}s",
                    extra={"job_id": job.job_id},
                )
            else:
                stderr_bytes = await self._current_process.stderr.read() if self._current_process.stderr else b""
                stderr_text = stderr_bytes.decode("utf-8", errors="replace")[-500:]
                job.error_message = f"FFmpeg exit code {self._current_process.returncode}: {stderr_text}"
                job.transition_to(JobState.FAILED)
                logger.error(
                    f"processing.failed: {job.error_message}",
                    extra={"job_id": job.job_id},
                )
                self._cleanup_output(job)

        except asyncio.CancelledError:
            # Cancellation from outside
            await self._terminate_process()
            if job.status == JobState.PROCESSING:
                job.transition_to(JobState.CANCELLED)
            self._cleanup_output(job)
            logger.info("processing.cancelled", extra={"job_id": job.job_id})

        except Exception as exc:
            job.error_message = str(exc)
            if job.status == JobState.PROCESSING:
                job.transition_to(JobState.FAILED)
            self._cleanup_output(job)
            logger.error(
                f"processing.error: {exc}",
                extra={"job_id": job.job_id},
            )

        finally:
            self._current_process = None
            self._current_job_id = None

    # ------------------------------------------------------------------
    # Progress parsing
    # ------------------------------------------------------------------

    async def _read_progress(self, job: Job, start_time: float) -> None:
        """
        Read FFmpeg's machine-readable progress from stdout.

        Parses lines like:
            frame=1234
            fps=148.5
            out_time=00:01:23.456
            speed=3.1x
            progress=continue
        """
        if not self._current_process or not self._current_process.stdout:
            return

        current_fps: float = 0.0
        current_speed: str = ""

        while True:
            try:
                line_bytes = await asyncio.wait_for(
                    self._current_process.stdout.readline(),
                    timeout=2.0,
                )
            except asyncio.TimeoutError:
                # Check if process still running
                if self._current_process.returncode is not None:
                    break
                # Check overall timeout
                if (time.monotonic() - start_time) > self._max_duration:
                    break
                continue

            if not line_bytes:
                break

            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            if line.startswith("fps="):
                try:
                    current_fps = float(line.split("=", 1)[1].strip())
                except (ValueError, IndexError):
                    pass

            elif line.startswith("speed="):
                current_speed = line.split("=", 1)[1].strip()

            elif line.startswith("out_time="):
                out_time_str = line.split("=", 1)[1].strip()
                out_seconds = self._parse_time(out_time_str)
                if job.input_duration > 0 and out_seconds >= 0:
                    pct = min(int((out_seconds / job.input_duration) * 100), 99)
                    job.progress = pct
                    job.fps = current_fps
                    job.speed = current_speed
                    job.elapsed_seconds = round(
                        time.monotonic() - start_time, 2
                    )

                    if self._progress_callback:
                        await self._progress_callback(
                            job.job_id, pct, current_fps, current_speed
                        )

            elif line.startswith("progress="):
                val = line.split("=", 1)[1].strip()
                if val == "end":
                    break

    @staticmethod
    def _parse_time(time_str: str) -> float:
        """Parse FFmpeg out_time like '00:01:23.456789' into seconds."""
        match = re.match(
            r"(-?)(\d+):(\d+):(\d+(?:\.\d+)?)", time_str
        )
        if not match:
            return -1.0
        sign = -1 if match.group(1) == "-" else 1
        hours = int(match.group(2))
        minutes = int(match.group(3))
        seconds = float(match.group(4))
        return sign * (hours * 3600 + minutes * 60 + seconds)

    # ------------------------------------------------------------------
    # Timeout / cancellation
    # ------------------------------------------------------------------

    async def _handle_timeout(self, job: Job) -> None:
        """Kill the FFmpeg process and mark the job as TIMEOUT."""
        logger.warning(
            f"processing.timeout after {self._max_duration}s",
            extra={"job_id": job.job_id},
        )
        await self._terminate_process()
        if job.status == JobState.PROCESSING:
            job.transition_to(JobState.TIMEOUT)
        self._cleanup_output(job)

    async def cancel_current(self, job_id: str) -> bool:
        """
        Cancel the currently running job if it matches the given job_id.

        Returns True if the process was terminated.
        """
        if self._current_job_id == job_id and self._current_process:
            await self._terminate_process()
            return True
        return False

    async def _terminate_process(self) -> None:
        """Safely terminate the FFmpeg subprocess."""
        proc = self._current_process
        if proc is None:
            return

        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass  # already dead
        except Exception as exc:
            logger.error(f"Error terminating FFmpeg: {exc}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_output(self, job: Job) -> None:
        """Remove partial output files on failure/cancel/timeout."""
        if job.output_path and os.path.exists(job.output_path):
            try:
                os.remove(job.output_path)
                logger.info(
                    "cleanup.partial_output removed",
                    extra={"job_id": job.job_id},
                )
            except OSError as exc:
                logger.warning(
                    f"cleanup.failed: {exc}",
                    extra={"job_id": job.job_id},
                )
