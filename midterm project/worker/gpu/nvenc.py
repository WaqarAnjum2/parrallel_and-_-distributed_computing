"""
NVENC encoder discovery by querying FFmpeg.

Runs `ffmpeg -encoders` and parses the output to find available
NVENC hardware encoders on this machine.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("worker")

# Encoders we care about
_NVENC_ENCODER_NAMES: list[str] = [
    "h264_nvenc",
    "hevc_nvenc",
    "av1_nvenc",
]


def resolve_ffmpeg_path(custom_path: str = "ffmpeg") -> str:
    """
    Resolve full path to ffmpeg binary, checking:
    1. PyInstaller bundle temp directory (_MEIPASS)
    2. Directory adjacent to the running executable / script
    3. System PATH
    4. WinGet standard installation directories
    """
    if custom_path != "ffmpeg" and os.path.exists(custom_path):
        return custom_path

    # Check PyInstaller onefile temp bundle
    if hasattr(sys, "_MEIPASS"):
        bundle_bin = Path(sys._MEIPASS) / "ffmpeg.exe"
        if bundle_bin.exists():
            return str(bundle_bin)

    # Check next to executable or script
    for base in (Path(sys.executable).parent, Path(__file__).resolve().parent.parent.parent):
        if (base / "ffmpeg.exe").exists():
            return str(base / "ffmpeg.exe")
        if (base / "bin" / "ffmpeg.exe").exists():
            return str(base / "bin" / "ffmpeg.exe")

    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_packages.exists():
            for p in winget_packages.glob("**/ffmpeg.exe"):
                return str(p)
        winget_links = Path(local_app_data) / "Microsoft" / "WinGet" / "Links"
        if (winget_links / "ffmpeg.exe").exists():
            return str(winget_links / "ffmpeg.exe")

    return "ffmpeg"


def resolve_ffprobe_path(custom_path: str = "ffprobe") -> str:
    """
    Resolve full path to ffprobe binary, checking:
    1. PyInstaller bundle temp directory (_MEIPASS)
    2. Directory adjacent to the running executable / script
    3. System PATH
    4. WinGet standard installation directories
    """
    if custom_path != "ffprobe" and os.path.exists(custom_path):
        return custom_path

    # Check PyInstaller onefile temp bundle
    if hasattr(sys, "_MEIPASS"):
        bundle_bin = Path(sys._MEIPASS) / "ffprobe.exe"
        if bundle_bin.exists():
            return str(bundle_bin)

    # Check next to executable or script
    for base in (Path(sys.executable).parent, Path(__file__).resolve().parent.parent.parent):
        if (base / "ffprobe.exe").exists():
            return str(base / "ffprobe.exe")
        if (base / "bin" / "ffprobe.exe").exists():
            return str(base / "bin" / "ffprobe.exe")

    which_path = shutil.which("ffprobe")
    if which_path:
        return which_path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_packages.exists():
            for p in winget_packages.glob("**/ffprobe.exe"):
                return str(p)
        winget_links = Path(local_app_data) / "Microsoft" / "WinGet" / "Links"
        if (winget_links / "ffprobe.exe").exists():
            return str(winget_links / "ffprobe.exe")

    return "ffprobe"


def detect_nvenc_encoders(ffmpeg_path: str | None = None) -> list[str]:
    """
    Run ``ffmpeg -encoders`` and return the list of available NVENC encoders.

    Returns an empty list if FFmpeg is missing or no NVENC encoders are found.
    """
    bin_path = resolve_ffmpeg_path(ffmpeg_path or "ffmpeg")
    try:
        result = subprocess.run(
            [bin_path, "-encoders"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout + result.stderr
        found: list[str] = []

        for encoder_name in _NVENC_ENCODER_NAMES:
            if encoder_name in output:
                found.append(encoder_name)
                logger.info(f"NVENC encoder available: {encoder_name}")

        if not found:
            logger.warning("No NVENC encoders found in FFmpeg output")

        return found

    except FileNotFoundError:
        logger.error(f"FFmpeg not found at '{bin_path}'")
        return []

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg encoder detection timed out")
        return []

    except Exception as exc:
        logger.error(f"NVENC detection failed: {exc}")
        return []


def detect_ffmpeg_version(ffmpeg_path: str | None = None) -> str:
    """
    Return the FFmpeg version string, or 'Not detected' on failure.
    """
    bin_path = resolve_ffmpeg_path(ffmpeg_path or "ffmpeg")
    try:
        result = subprocess.run(
            [bin_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        first_line = result.stdout.strip().split("\n")[0]
        return first_line

    except Exception:
        return "Not detected"


def detect_ffprobe(ffprobe_path: str | None = None) -> bool:
    """Return True if ffprobe is available on PATH or WinGet."""
    bin_path = resolve_ffprobe_path(ffprobe_path or "ffprobe")
    try:
        subprocess.run(
            [bin_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except Exception:
        return False
