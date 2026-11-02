"""
GPU Hardware Detection and FFmpeg NVENC/CPU Execution Engine.
Handles real-time progress parsing, sub-process lifecycle, and codec fallback.
"""
import json
import logging
import os
import re
import shutil
import subprocess
import time
from typing import Callable, Dict, Optional, Tuple

from common.protocol import GPUInfo, RenderConfig

logger = logging.getLogger("gpu_engine")


class GPUEngine:
    def __init__(self):
        self.ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe_path = shutil.which("ffprobe") or "ffprobe"
        self.gpu_info = self._detect_gpu()
        self._check_nvenc_support()

    def _detect_gpu(self) -> GPUInfo:
        """Detect GPU hardware using pynvml or nvidia-smi."""
        info = GPUInfo()
        # Try pynvml first
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                driver = pynvml.nvmlSystemGetDriverVersion()
                if isinstance(driver, bytes):
                    driver = driver.decode("utf-8")

                info.available = True
                info.name = name
                info.driver_version = driver
                info.vram_total_mb = int(mem_info.total / (1024 * 1024))
                info.vram_used_mb = int(mem_info.used / (1024 * 1024))
                info.vram_free_mb = int(mem_info.free / (1024 * 1024))
                pynvml.nvmlShutdown()
                return info
        except Exception as e:
            logger.debug(f"pynvml detection skipped: {e}")

        # Fallback to nvidia-smi CLI
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                if len(parts) >= 5:
                    info.available = True
                    info.name = parts[0]
                    info.driver_version = parts[1]
                    info.vram_total_mb = int(float(parts[2]))
                    info.vram_used_mb = int(float(parts[3]))
                    info.vram_free_mb = int(float(parts[4]))
                    return info
        except Exception as e:
            logger.debug(f"nvidia-smi query skipped: {e}")

        return info

    def _check_nvenc_support(self):
        """Verify whether ffmpeg binary supports NVENC or MediaFoundation GPU hardware encoder."""
        if not self.gpu_info.available:
            self.gpu_info.nvenc_supported = False
            return

        try:
            cmd = [self.ffmpeg_path, "-encoders"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            # Check if NVENC or MF hardware encoder is compiled
            if "h264_nvenc" in res.stdout or "h264_mf" in res.stdout:
                self.gpu_info.nvenc_supported = True
            else:
                self.gpu_info.nvenc_supported = False
        except Exception:
            self.gpu_info.nvenc_supported = False

    def get_gpu_status(self) -> GPUInfo:
        """Fetch real-time GPU memory metrics."""
        fresh = self._detect_gpu()
        fresh.nvenc_supported = self.gpu_info.nvenc_supported
        return fresh

    def get_video_duration(self, file_path: str) -> float:
        """Extract video duration in seconds via ffprobe."""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            val = float(res.stdout.strip())
            return val if val > 0 else 1.0
        except Exception as e:
            logger.warning(f"Could not probe video duration: {e}. Defaulting to 1.0s.")
            return 1.0

    def build_ffmpeg_cmd(
        self,
        input_path: str,
        output_path: str,
        config: RenderConfig,
        use_gpu: bool = True
    ) -> Tuple[list, str]:
        """Build command array for FFmpeg execution with editing filters and hardware encoder."""
        actual_codec = config.codec if use_gpu else "libx264"
        if use_gpu and not self.gpu_info.nvenc_supported:
            actual_codec = "libx264"

        cmd = [
            self.ffmpeg_path,
            "-y",                     # Overwrite output
            "-nostats",
            "-loglevel", "error",
        ]

        # Trimming edit points (Start and End times)
        if config.trim_start is not None and config.trim_start > 0:
            cmd.extend(["-ss", str(config.trim_start)])
        if config.trim_end is not None and config.trim_end > 0:
            cmd.extend(["-to", str(config.trim_end)])

        cmd.extend(["-i", input_path])
        cmd.extend(["-c:v", actual_codec])

        # Assemble Video Filter Pipeline
        vf_filters = []

        # Resolution scaling
        if config.resolution and config.resolution.lower() != "original":
            if "x" in config.resolution:
                w, h = config.resolution.split("x")
                vf_filters.append(f"scale={w}:{h}")

        # Creative Visual Filters
        eff = config.filter_effect.lower() if config.filter_effect else "none"
        if "grayscale" in eff or "b&w" in eff:
            vf_filters.append("hue=s=0")
        elif "sepia" in eff:
            vf_filters.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        elif "vignette" in eff:
            vf_filters.append("vignette=PI/4")
        elif "contrast" in eff or "pop" in eff:
            vf_filters.append("eq=contrast=1.3:saturation=1.4")
        elif "invert" in eff or "negative" in eff:
            vf_filters.append("negate")

        # Playback speed factor (video pts)
        if config.playback_speed and config.playback_speed != 1.0:
            pts_ratio = 1.0 / config.playback_speed
            vf_filters.append(f"setpts={pts_ratio:.4f}*PTS")

        # Watermark Text Overlay
        if config.watermark_text and config.watermark_text.strip():
            safe_text = config.watermark_text.replace("'", "").replace(":", "-")
            vf_filters.append(f"drawtext=text='{safe_text}':x=(w-text_w)/2:y=h-th-25:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6")

        if vf_filters:
            cmd.extend(["-vf", ",".join(vf_filters)])

        # Target Bitrate
        if config.bitrate:
            cmd.extend(["-b:v", config.bitrate])

        # Presets
        if actual_codec == "h264_nvenc":
            nv_preset = config.preset if config.preset.startswith("p") else "p4"
            cmd.extend(["-preset", nv_preset])
        elif actual_codec == "libx264":
            cpu_preset = config.preset if not config.preset.startswith("p") else "medium"
            cmd.extend(["-preset", cpu_preset])

        # Framerate
        if config.fps:
            cmd.extend(["-r", str(config.fps)])

        # Audio Pipeline
        if config.audio_mode == "Mute":
            cmd.append("-an")
        else:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
            af_filters = []
            if config.playback_speed and config.playback_speed != 1.0:
                af_filters.append(f"atempo={config.playback_speed}")
            if config.audio_mode == "Boost":
                af_filters.append("volume=1.6")
            if af_filters:
                cmd.extend(["-af", ",".join(af_filters)])

        # Real-time progress output to stdout
        cmd.extend([
            "-progress", "pipe:1",
            output_path
        ])

        return cmd, actual_codec

    def run_transcode(
        self,
        input_path: str,
        output_path: str,
        config: RenderConfig,
        progress_callback: Callable[[float, int, float, str, str], None],
        log_callback: Callable[[str], None],
        stop_check: Callable[[], bool]
    ) -> Tuple[bool, str, str]:
        """
        Executes FFmpeg with real-time stdout progress interception.
        Returns (success: bool, used_codec: str, error_message: str).
        """
        total_duration = self.get_video_duration(input_path)
        log_callback(f"[Engine] Input duration: {total_duration:.2f}s")

        use_gpu = (config.codec == "h264_nvenc")
        cmd, chosen_codec = self.build_ffmpeg_cmd(input_path, output_path, config, use_gpu=use_gpu)
        log_callback(f"[Engine] Selected Encoder: {chosen_codec} (GPU={use_gpu and self.gpu_info.nvenc_supported})")
        log_callback(f"[Engine] Command: {' '.join(cmd)}")

        process = None
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            current_frame = 0
            current_fps = 0.0
            current_speed = "0x"
            out_time_sec = 0.0

            # Parse ffmpeg key=value stdout stream
            for line in process.stdout:
                if stop_check():
                    process.terminate()
                    log_callback("[Engine] Job cancelled by user/client.")
                    return False, chosen_codec, "Cancelled"

                line_str = line.strip()
                if not line_str:
                    continue

                if "=" in line_str:
                    key, val = line_str.split("=", 1)
                    key = key.strip()
                    val = val.strip()

                    if key == "frame":
                        current_frame = int(val) if val.isdigit() else current_frame
                    elif key == "fps":
                        try:
                            current_fps = float(val)
                        except ValueError:
                            pass
                    elif key == "speed":
                        current_speed = val
                    elif key == "out_time_us":
                        try:
                            out_time_sec = float(val) / 1000000.0
                        except ValueError:
                            pass
                    elif key == "progress":
                        # Compute percentage
                        pct = min(100.0, max(0.0, (out_time_sec / total_duration) * 100.0))
                        if val == "end":
                            pct = 100.0
                        progress_callback(pct, current_frame, current_fps, current_speed, f"Rendered frame {current_frame} ({pct:.1f}%)")

            process.wait()
            _, stderr_data = process.communicate()

            if process.returncode != 0:
                err_summary = stderr_data[-500:] if stderr_data else "Unknown error"
                # Check if NVENC failed and we can fallback to CPU
                if chosen_codec == "h264_nvenc":
                    log_callback(f"[Engine Warning] NVENC failed ({err_summary}). Retrying with CPU libx264...")
                    cmd_cpu, cpu_codec = self.build_ffmpeg_cmd(input_path, output_path, config, use_gpu=False)
                    return self._run_cpu_fallback(cmd_cpu, total_duration, progress_callback, log_callback, stop_check)
                return False, chosen_codec, err_summary

            progress_callback(100.0, current_frame, current_fps, current_speed, "Rendering finished successfully.")
            return True, chosen_codec, ""

        except Exception as ex:
            if process:
                process.kill()
            return False, chosen_codec, str(ex)

    def _run_cpu_fallback(
        self,
        cmd: list,
        total_duration: float,
        progress_callback: Callable,
        log_callback: Callable,
        stop_check: Callable
    ) -> Tuple[bool, str, str]:
        """Fallback path when NVENC is unavailable or throws a runtime error."""
        try:
            log_callback(f"[Fallback CPU] Command: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            out_time_sec = 0.0
            cur_frame = 0
            cur_fps = 0.0
            cur_spd = "0x"

            for line in proc.stdout:
                if stop_check():
                    proc.terminate()
                    return False, "libx264", "Cancelled"
                line_str = line.strip()
                if "=" in line_str:
                    k, v = line_str.split("=", 1)
                    if k == "out_time_us":
                        try:
                            out_time_sec = float(v) / 1000000.0
                        except ValueError:
                            pass
                    elif k == "frame" and v.isdigit():
                        cur_frame = int(v)
                    elif k == "fps":
                        try:
                            cur_fps = float(v)
                        except ValueError:
                            pass
                    elif k == "speed":
                        cur_spd = v
                    elif k == "progress":
                        pct = min(100.0, max(0.0, (out_time_sec / total_duration) * 100.0))
                        if v == "end":
                            pct = 100.0
                        progress_callback(pct, cur_frame, cur_fps, cur_spd, f"CPU Render: {pct:.1f}%")

            proc.wait()
            if proc.returncode != 0:
                _, err = proc.communicate()
                return False, "libx264", err[-400:] if err else "Fallback failed"
            return True, "libx264", ""
        except Exception as e:
            return False, "libx264", str(e)

