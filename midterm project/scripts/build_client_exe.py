"""
Standalone Executable & Portable Package Builder for Distributed GPU Client.

Bundles Python runtime, PyQt6, Matplotlib, HTTPX, WebSockets, Pydantic,
and local FFprobe/FFmpeg binaries for video analysis & local CPU benchmarking.
Produces:
1. dist/DistributedGPUClient/ (Self-contained directory)
2. dist/DistributedGPUClient_Portable.zip (Portable all-in-one client package)
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


def build_client() -> None:
    print("=======================================================")
    print(" Building Standalone Distributed GPU Client Package    ")
    print("=======================================================")

    # 1. Locate FFmpeg & FFprobe (for local metadata probe & CPU benchmark)
    ffmpeg_exe = resolve_ffmpeg_path()
    ffprobe_exe = resolve_ffprobe_path()

    print(f"[*] Local FFmpeg binary:  {ffmpeg_exe}")
    print(f"[*] Local FFprobe binary: {ffprobe_exe}")

    import PyInstaller.__main__

    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build_client"
    entry_script = PROJECT_ROOT / "client" / "main.py"
    icon_file = PROJECT_ROOT / "installer" / "client_icon.ico"

    args = [
        str(entry_script),
        "--name=DistributedGPUClient",
        "--onedir",
        "--clean",
        "-y",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--icon={icon_file}",
        # Add shared modules & icons
        f"--add-data={PROJECT_ROOT / 'shared'};shared",
        f"--add-data={icon_file};installer",
        # Include hidden Qt & matplotlib imports
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=matplotlib",
        "--hidden-import=matplotlib.backends.backend_qtagg",
        "--hidden-import=httpx",
        "--hidden-import=websockets",
        "--hidden-import=pydantic",
        "--noconsole",
    ]

    print("[*] Running PyInstaller compilation for Client...")
    PyInstaller.__main__.run(args)

    output_folder = dist_dir / "DistributedGPUClient"
    if not output_folder.exists():
        print("[!] PyInstaller client build failed!")
        sys.exit(1)

    # Copy FFmpeg & FFprobe into client folder for offline metadata & CPU benchmark
    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        print("[*] Bundling local FFmpeg & FFprobe with client for benchmarks...")
        shutil.copy2(ffmpeg_exe, output_folder / "ffmpeg.exe")
        shutil.copy2(ffprobe_exe, output_folder / "ffprobe.exe")

    # Copy .env
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        shutil.copy2(env_file, output_folder / ".env")
    else:
        shutil.copy2(PROJECT_ROOT / ".env.example", output_folder / ".env")

    # Copy icon
    if icon_file.exists():
        shutil.copy2(icon_file, output_folder / "client_icon.ico")

    # Launcher script
    launcher_content = """@echo off
title Distributed GPU Task Client
cd /d "%~dp0"
start "" "DistributedGPUClient.exe"
"""
    with open(output_folder / "Start-Client.bat", "w", encoding="utf-8") as f:
        f.write(launcher_content)

    # Create Desktop shortcut for the Client
    try:
        desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        shortcut_path = desktop / "Distributed GPU Client.lnk"
        target_exe = output_folder / "DistributedGPUClient.exe"
        icon_path = output_folder / "client_icon.ico"

        import subprocess
        ps_script = f"""
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{target_exe}"
        $Shortcut.WorkingDirectory = "{output_folder}"
        $Shortcut.Description = "Distributed GPU Task Offloading Client Controller"
        if (Test-Path "{icon_path}") {{
            $Shortcut.IconLocation = "{icon_path}, 0"
        }}
        $Shortcut.Save()
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, check=False)
        print(f"[✓] Created Desktop Shortcut: {shortcut_path}")
    except Exception as err:
        print(f"[!] Desktop shortcut notice: {err}")

    # Create portable ZIP package
    zip_path = dist_dir / "DistributedGPUClient_Portable.zip"
    print(f"[*] Packaging into all-in-one ZIP: {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(output_folder)
                zipf.write(file_path, arcname)

    print("\n=======================================================")
    print(" [✓] STANDALONE CLIENT PACKAGE READY!")
    print(f" Folder: {output_folder}")
    print(f" Executable: {output_folder / 'DistributedGPUClient.exe'}")
    print(f" Archive: {zip_path}")
    print(" Desktop shortcut created: 'Distributed GPU Client'")
    print("=======================================================")


if __name__ == "__main__":
    build_client()
