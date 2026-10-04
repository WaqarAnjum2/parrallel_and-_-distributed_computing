"""
Build script to compile the GUI Installer into a standalone Setup executable:
dist/Worker_Node_Setup.exe
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def build_installer() -> None:
    print("=======================================================")
    print(" Compiling Worker Node GUI Installer (Worker_Node_Setup.exe) ")
    print("=======================================================")

    import PyInstaller.__main__

    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build_installer"
    entry_script = PROJECT_ROOT / "installer" / "installer_gui.py"
    icon_file = PROJECT_ROOT / "installer" / "worker_icon.ico"

    args = [
        str(entry_script),
        "--name=Worker_Node_Setup",
        "--onefile",
        "--clean",
        "-y",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--icon={icon_file}",
        f"--add-data={icon_file};installer",
        # Include PyQt6 modules
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--noconsole",
    ]

    print("[*] Running PyInstaller for GUI Installer...")
    PyInstaller.__main__.run(args)

    setup_exe = dist_dir / "Worker_Node_Setup.exe"
    if setup_exe.exists():
        print("\n=======================================================")
        print(" [✓] INSTALLER EXECUTABLE READY!")
        print(f" File: {setup_exe}")
        print(" Users can run this installer on ANY PC to set up the Worker Node!")
        print("=======================================================\n")
    else:
        print("[!] Setup compilation failed.")

if __name__ == "__main__":
    build_installer()
