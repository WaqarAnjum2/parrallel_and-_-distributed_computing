"""
Standalone Executable & Portable Package Builder for Distributed GPU Worker.

Bundles Python runtime, FastAPI, Uvicorn, Pydantic, all dependencies,
plus the full FFmpeg and FFprobe binaries with NVIDIA NVENC support.
Produces:
1. dist/DistributedGPUWorker/ (Self-contained directory)
2. dist/DistributedGPUWorker.zip (Portable all-in-one package for other PCs)
"""

import os
import shutil
import sys
import zipfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from worker.gpu.nvenc import resolve_ffmpeg_path, resolve_ffprobe_path


def build() -> None:
    print("=======================================================")
    print(" Building Standalone Distributed GPU Worker Package    ")
    print("=======================================================")

    # 1. Locate FFmpeg & FFprobe
    ffmpeg_exe = resolve_ffmpeg_path()
    ffprobe_exe = resolve_ffprobe_path()

    print(f"[*] FFmpeg binary:  {ffmpeg_exe}")
    print(f"[*] FFprobe binary: {ffprobe_exe}")

    if not os.path.exists(ffmpeg_exe) or not os.path.exists(ffprobe_exe):
        print("[!] ERROR: ffmpeg.exe or ffprobe.exe not found on this system!")
        sys.exit(1)

    # 2. PyInstaller arguments
    import PyInstaller.__main__

    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"
    entry_script = PROJECT_ROOT / "worker" / "main.py"

    args = [
        str(entry_script),
        f"--name=DistributedGPUWorker",
        "--onedir",
        "--clean",
        "-y",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        # Add shared modules
        f"--add-data={PROJECT_ROOT / 'shared'};shared",
        # Include hidden Uvicorn and FastAPI dependencies
        "--hidden-import=uvicorn",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespans",
        "--hidden-import=uvicorn.lifespans.on",
        "--hidden-import=pydantic_settings",
        "--hidden-import=pynvml",
        "--hidden-import=nvidia_ml_py",
        "--hidden-import=multipart",
        "--hidden-import=python_multipart",
    ]

    print("[*] Running PyInstaller compilation...")
    PyInstaller.__main__.run(args)

    output_folder = dist_dir / "DistributedGPUWorker"
    if not output_folder.exists():
        print("[!] PyInstaller build failed!")
        sys.exit(1)

    # 3. Copy FFmpeg & FFprobe directly into the output folder
    print("[*] Bundling FFmpeg & FFprobe with NVENC hardware support...")
    shutil.copy2(ffmpeg_exe, output_folder / "ffmpeg.exe")
    shutil.copy2(ffprobe_exe, output_folder / "ffprobe.exe")

    # 4. Copy default .env configuration
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        shutil.copy2(env_file, output_folder / ".env")
    else:
        shutil.copy2(PROJECT_ROOT / ".env.example", output_folder / ".env")

    # 5. Create a convenient 1-Click Launcher script
    launcher_content = """@echo off
title Distributed GPU Worker Node
echo ========================================================
echo  Launching Distributed GPU Worker Node
echo ========================================================
cd /d "%~dp0"
DistributedGPUWorker.exe
pause
"""
    with open(output_folder / "Start-Worker.bat", "w", encoding="utf-8") as f:
        f.write(launcher_content)

    # 6. Create portable ZIP package
    zip_path = dist_dir / "DistributedGPUWorker_Portable.zip"
    print(f"[*] Packaging into all-in-one ZIP: {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(output_folder)
                zipf.write(file_path, arcname)

    print("\n=======================================================")
    print(" [✓] STANDALONE WORKER PACKAGE READY!")
    print(f" Folder: {output_folder}")
    print(f" Archive: {zip_path}")
    print(" Copy this folder or ZIP to ANY GPU PC — double click 'Start-Worker.bat'")
    print(" No Python, no pip, no FFmpeg installation needed on the other PC!")
    print("=======================================================")


if __name__ == "__main__":
    build()
