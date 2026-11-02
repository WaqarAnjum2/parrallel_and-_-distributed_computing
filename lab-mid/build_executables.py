"""
Automated Build Script to compile Standalone Windows .EXE files
for both Client and Server using PyInstaller.
Resulting executables run on any Windows machine without installing Python or dependencies!
"""
import os
import shutil
import subprocess
import sys


def build_app(script_path: str, exe_name: str, extra_collects: list = None):
    print("\n" + "=" * 60)
    print(f"Building optimized standalone executable: {exe_name}.exe...")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name", exe_name,
        "--onefile",
        "--clean",
        "--collect-all", "customtkinter",
        "--collect-all", "PIL",
        # Exclude massive unused libraries to keep build fast and exe lightweight
        "--exclude-module", "PyQt6",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "tensorflow",
        "--exclude-module", "torch",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "notebook",
    ]

    if extra_collects:
        for c in extra_collects:
            cmd.extend(["--collect-all", c])

    cmd.append(script_path)

    res = subprocess.run(cmd)
    if res.returncode == 0:
        dist_exe = os.path.join("dist", f"{exe_name}.exe")
        if os.path.exists(dist_exe):
            sz_mb = os.path.getsize(dist_exe) / (1024 * 1024)
            print(f"[SUCCESS] Generated: {dist_exe} ({sz_mb:.1f} MB)")
            return True
    print(f"[ERROR] Failed to build {exe_name}.exe")
    return False


def main():
    os.makedirs("dist", exist_ok=True)

    # 1. Build Client Desktop App (CustomTkinter + Requests + WebSockets)
    ok_client = build_app(
        os.path.join("client", "app.py"),
        "Cobalt_Client_App",
        extra_collects=["websockets"]
    )

    # 2. Build GPU Worker Node GUI (Server + FastAPI + Uvicorn + WebSockets)
    ok_server = build_app(
        os.path.join("server", "worker_gui.py"),
        "Cobalt_GPU_Worker_Node",
        extra_collects=["uvicorn", "fastapi", "websockets"]
    )

    if ok_client and ok_server:
        print("\n" + "=" * 60)
        print("ALL STANDALONE EXECUTABLES SUCCESSFULLY CREATED IN 'dist/'!")
        print("1. dist/Cobalt_Client_App.exe      (Run on Laptop 1 - Client)")
        print("2. dist/Cobalt_GPU_Worker_Node.exe (Run on Laptop 2 - GPU Worker)")
        print("Zero installation required on target machines!")
        print("=" * 60)


if __name__ == "__main__":
    main()
