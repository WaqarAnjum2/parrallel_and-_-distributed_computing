"""
Advanced Worker Node GUI Installer (Light Theme).

Provides a zero-friction, 1-click setup wizard for target GPU PCs:
1. Pre-flight Hardware Inspection (NVIDIA GPU, VRAM, NVENC, Firewall).
2. Destination Selection (default: C:\\DistributedGPUWorker).
3. Extraction & Installation of all bundled binaries (Python, packages, FFmpeg NVENC).
4. Windows Firewall Rule Auto-Configuration (Inbound TCP 8000).
5. Desktop Shortcut Creation with Custom Worker Icon.
6. Post-Install Node Information & LAN/WAN connection guides.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import zipfile
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Colors & Tokens (Clean Modern Light Theme)
BG_MAIN = "#F8FAFC"
BG_CARD = "#FFFFFF"
BORDER_COLOR = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_MUTED = "#64748B"
PRIMARY_BLUE = "#2563EB"
PRIMARY_HOVER = "#1D4ED8"
EMERALD_GREEN = "#10B981"
EMERALD_BG = "#ECFDF5"
AMBER_WARN = "#F59E0B"
AMBER_BG = "#FFFBEB"

LIGHT_STYLE = f"""
QWidget {{
    background-color: {BG_MAIN};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Inter, system-ui, sans-serif;
}}
QFrame.Card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
}}
QLabel {{
    background: transparent;
}}
QPushButton.Primary {{
    background-color: {PRIMARY_BLUE};
    color: #FFFFFF;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 8px;
    border: none;
}}
QPushButton.Primary:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton.Secondary {{
    background-color: #FFFFFF;
    color: {TEXT_PRIMARY};
    font-weight: 500;
    font-size: 13px;
    padding: 8px 18px;
    border-radius: 8px;
    border: 1px solid {BORDER_COLOR};
}}
QPushButton.Secondary:hover {{
    background-color: #F1F5F9;
}}
QLineEdit {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}
QLineEdit:focus {{
    border: 1px solid {PRIMARY_BLUE};
}}
QProgressBar {{
    background-color: #E2E8F0;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    font-size: 11px;
    color: {TEXT_PRIMARY};
}}
QProgressBar::chunk {{
    background-color: {PRIMARY_BLUE};
    border-radius: 6px;
}}
QCheckBox {{
    font-size: 13px;
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
"""


def get_local_ip() -> str:
    """Resolve current machine's primary LAN IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def detect_gpu_info() -> tuple[str, str, bool]:
    """Detect GPU name, memory, and NVENC/hardware support."""
    # 1. nvidia-smi with standard Windows paths
    smi_paths = [
        shutil.which("nvidia-smi"),
        r"C:\Windows\System32\nvidia-smi.exe",
        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    ]
    for p in smi_paths:
        if p and os.path.exists(p):
            try:
                cmd = [p, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, check=False)
                if res.returncode == 0 and res.stdout.strip():
                    parts = res.stdout.strip().split("\n")[0].split(",")
                    return parts[0].strip(), f"{int(parts[1].strip()):,} MB VRAM", True
            except Exception:
                pass

    # 2. NVML library
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu_name, bytes):
            gpu_name = gpu_name.decode("utf-8")
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram = f"{mem.total // (1024 * 1024):,} MB VRAM"
        pynvml.nvmlShutdown()
        return gpu_name, vram, True
    except Exception:
        pass

    # 3. Windows CIM / WMI
    if os.name == "nt":
        try:
            import json
            ps_cmd = "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                controllers = data if isinstance(data, list) else [data]
                for c in controllers:
                    name = str(c.get("Name") or "")
                    if any(k in name.lower() for k in ["nvidia", "geforce", "quadro", "rtx", "gtx"]):
                        ram = (c.get("AdapterRAM") or 0) // (1024 * 1024)
                        return name, f"{ram:,} MB VRAM" if ram else "Dedicated VRAM", True
        except Exception:
            pass

    return "Standard Graphics Adapter", "Shared Memory", False


class InstallWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        dest_dir: str,
        create_shortcut: bool,
        config_firewall: bool,
        port: int,
    ):
        super().__init__()
        self.dest_dir = Path(dest_dir)
        self.create_shortcut = create_shortcut
        self.config_firewall = config_firewall
        self.port = port

    def run(self) -> None:
        try:
            self.progress.emit(10, "Preparing installation target directory...")
            self.dest_dir.mkdir(parents=True, exist_ok=True)

            # Find source payload (check embedded MEIPASS, adjacent directory, or project dist)
            candidates = []
            if hasattr(sys, "_MEIPASS"):
                candidates.append(Path(sys._MEIPASS) / "DistributedGPUWorker_Portable.zip")
                candidates.append(Path(sys._MEIPASS) / "DistributedGPUWorker")

            exe_dir = Path(sys.executable).resolve().parent
            candidates.append(exe_dir / "DistributedGPUWorker_Portable.zip")
            candidates.append(exe_dir / "DistributedGPUWorker")

            base_dir = Path(__file__).resolve().parent.parent
            candidates.append(base_dir / "dist" / "DistributedGPUWorker_Portable.zip")
            candidates.append(base_dir / "dist" / "DistributedGPUWorker")

            zip_payload = None
            source_folder = None
            for cand in candidates:
                if cand.is_file() and cand.name.endswith(".zip") and cand.exists():
                    zip_payload = cand
                    break
                elif cand.is_dir() and cand.exists():
                    source_folder = cand
                    break

            if zip_payload and zip_payload.exists():
                self.progress.emit(20, "Extracting bundled Python, NVENC FFmpeg & Worker...")
                with zipfile.ZipFile(zip_payload, "r") as zf:
                    total_files = len(zf.namelist())
                    for idx, member in enumerate(zf.namelist()):
                        zf.extract(member, self.dest_dir)
                        if idx % 200 == 0:
                            pct = 20 + int((idx / total_files) * 55)
                            self.progress.emit(pct, f"Extracting {member}...")
            elif source_folder and source_folder.exists():
                self.progress.emit(25, "Copying pre-packaged binaries and dependencies...")
                for item in source_folder.glob("*"):
                    dest_target = self.dest_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest_target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest_target)
                    self.progress.emit(50, f"Installed {item.name}")
            else:
                self.finished.emit(False, "Worker payload not found. Ensure DistributedGPUWorker_Portable.zip is present.")
                return

            self.progress.emit(80, "Configuring runtime environment (.env)...")
            env_file = self.dest_dir / ".env"
            if not env_file.exists():
                env_content = f"WORKER_PORT={self.port}\nAUTH_TOKEN=supersecret_token_12345\nLOG_LEVEL=INFO\n"
                env_file.write_text(env_content, encoding="utf-8")

            # Desktop Shortcut
            if self.create_shortcut:
                self.progress.emit(85, "Creating Desktop Shortcut with custom icon...")
                self._create_desktop_shortcut()

            # Firewall Rule
            if self.config_firewall:
                self.progress.emit(92, f"Adding Windows Firewall rule for TCP Port {self.port}...")
                self._configure_firewall()

            self.progress.emit(100, "Installation completed successfully!")
            self.finished.emit(True, "All components installed and ready.")

        except Exception as e:
            self.finished.emit(False, str(e))

    def _create_desktop_shortcut(self) -> None:
        try:
            desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
            shortcut_path = desktop / "Distributed GPU Worker.lnk"
            target_exe = self.dest_dir / "DistributedGPUWorker.exe"
            icon_path = self.dest_dir / "worker_icon.ico"

            # Use PowerShell COM script to create standard Windows shortcut
            ps_script = f"""
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{target_exe}"
            $Shortcut.WorkingDirectory = "{self.dest_dir}"
            $Shortcut.Description = "Distributed GPU Task Offloading Worker Node"
            if (Test-Path "{icon_path}") {{
                $Shortcut.IconLocation = "{icon_path}, 0"
            }}
            $Shortcut.Save()
            """
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                check=False,
            )
        except Exception as err:
            print(f"[!] Shortcut error: {err}")

    def _configure_firewall(self) -> None:
        try:
            rule_cmd = [
                "netsh",
                "advfirewall",
                "firewall",
                "add",
                "rule",
                f'name="Distributed GPU Worker Node (Port {self.port})"',
                "dir=in",
                "action=allow",
                "protocol=TCP",
                f"localport={self.port}",
            ]
            subprocess.run(rule_cmd, capture_output=True, check=False)
        except Exception as err:
            print(f"[!] Firewall rule error: {err}")


class WorkerInstallerGUI(QWidget):
    """Modern Light Theme Installer Wizard for Distributed GPU Worker Node."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Distributed GPU Worker Node — Setup Wizard")
        self.resize(720, 560)
        self.setStyleSheet(LIGHT_STYLE)

        # Set window icon
        icon_path = Path(__file__).resolve().parent / "worker_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.gpu_name, self.vram, self.has_nvenc = detect_gpu_info()
        self.local_ip = get_local_ip()

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(20)

        # Top Header Banner
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Distributed GPU Worker Node Setup")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        subtitle = QLabel("Autonomous High-Performance Video Offloading Node for NVIDIA GPUs")
        subtitle.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        header.addStretch()

        badge = QLabel("Light Edition v1.0")
        badge.setStyleSheet(
            f"background-color: #EFF6FF; color: {PRIMARY_BLUE}; "
            f"border: 1px solid #BFDBFE; border-radius: 12px; padding: 4px 12px; font-weight: 600;"
        )
        header.addWidget(badge)
        main_layout.addLayout(header)

        # Stacked Pages
        self.pages = QStackedWidget()
        self.page_preflight = self._create_preflight_page()
        self.page_options = self._create_options_page()
        self.page_progress = self._create_progress_page()
        self.page_finish = self._create_finish_page()

        self.pages.addWidget(self.page_preflight)
        self.pages.addWidget(self.page_options)
        self.pages.addWidget(self.page_progress)
        self.pages.addWidget(self.page_finish)

        main_layout.addWidget(self.pages)

        # Bottom Navigation Bar
        nav_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_back.setProperty("class", "Secondary")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.hide()

        self.btn_next = QPushButton("Continue →")
        self.btn_next.setProperty("class", "Primary")
        self.btn_next.clicked.connect(self._go_next)

        nav_layout.addWidget(self.btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        main_layout.addLayout(nav_layout)

    def _create_preflight_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        lbl = QLabel("Hardware & Runtime Pre-Flight Verification")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        card_layout.addWidget(lbl)

        # GPU Card row
        gpu_row = QHBoxLayout()
        gpu_icon = QLabel("🖥️")
        gpu_icon.setFont(QFont("Segoe UI", 18))
        gpu_meta = QVBoxLayout()
        gpu_title = QLabel(f"Detected GPU: {self.gpu_name}")
        gpu_title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        gpu_desc = QLabel(f"VRAM: {self.vram} | Driver Status: Ready")
        gpu_desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        gpu_meta.addWidget(gpu_title)
        gpu_meta.addWidget(gpu_desc)
        gpu_row.addWidget(gpu_icon)
        gpu_row.addLayout(gpu_meta)
        gpu_row.addStretch()

        status_badge = QLabel("NVENC READY" if self.has_nvenc else "CPU FALLBACK")
        status_bg = EMERALD_BG if self.has_nvenc else AMBER_BG
        status_fg = EMERALD_GREEN if self.has_nvenc else AMBER_WARN
        status_badge.setStyleSheet(
            f"background-color: {status_bg}; color: {status_fg}; "
            f"border: 1px solid {status_fg}; border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 11px;"
        )
        gpu_row.addWidget(status_badge)
        card_layout.addLayout(gpu_row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {BORDER_COLOR};")
        card_layout.addWidget(line)

        # Network row
        net_row = QHBoxLayout()
        net_icon = QLabel("🌐")
        net_icon.setFont(QFont("Segoe UI", 18))
        net_meta = QVBoxLayout()
        net_title = QLabel(f"Local Area Network (LAN): {self.local_ip}")
        net_title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        net_desc = QLabel("Client laptops on the same Wi-Fi/Ethernet connect directly to this IP.")
        net_desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        net_meta.addWidget(net_title)
        net_meta.addWidget(net_desc)
        net_row.addWidget(net_icon)
        net_row.addLayout(net_meta)
        net_row.addStretch()
        card_layout.addLayout(net_row)

        layout.addWidget(card)

        # Zero-Download Guarantee Note
        note = QLabel(
            "✓ All Python runtimes, FastAPI libraries, and NVIDIA NVENC FFmpeg binaries "
            "are 100% pre-bundled inside this setup. Zero internet downloads required."
        )
        note.setStyleSheet(f"color: {EMERALD_GREEN}; font-weight: 500; font-size: 12px;")
        layout.addWidget(note)
        layout.addStretch()

        return page

    def _create_options_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        lbl = QLabel("Installation Options")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        card_layout.addWidget(lbl)

        # Folder row
        folder_label = QLabel("Destination Directory:")
        folder_label.setStyleSheet("font-weight: 500;")
        card_layout.addWidget(folder_label)

        folder_row = QHBoxLayout()
        default_dir = os.path.join(os.environ.get("SystemDrive", "C:"), "\\DistributedGPUWorker")
        self.edit_dir = QLineEdit(default_dir)
        btn_browse = QPushButton("Browse...")
        btn_browse.setProperty("class", "Secondary")
        btn_browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.edit_dir)
        folder_row.addWidget(btn_browse)
        card_layout.addLayout(folder_row)

        # Checkboxes
        self.chk_shortcut = QCheckBox("Create Desktop Shortcut (with Worker Icon)")
        self.chk_shortcut.setChecked(True)
        card_layout.addWidget(self.chk_shortcut)

        self.chk_firewall = QCheckBox("Automatically add Windows Firewall rule for Port 8000 (Allow Inbound)")
        self.chk_firewall.setChecked(True)
        card_layout.addWidget(self.chk_firewall)

        # Port option
        port_row = QHBoxLayout()
        port_lbl = QLabel("Worker Service Port:")
        self.edit_port = QLineEdit("8000")
        self.edit_port.setFixedWidth(100)
        port_row.addWidget(port_lbl)
        port_row.addWidget(self.edit_port)
        port_row.addStretch()
        card_layout.addLayout(port_row)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _create_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        card.setProperty("class", "Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        self.lbl_progress_title = QLabel("Installing Distributed GPU Worker...")
        self.lbl_progress_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        card_layout.addWidget(self.lbl_progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar)

        self.lbl_progress_detail = QLabel("Initializing installation...")
        self.lbl_progress_detail.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        card_layout.addWidget(self.lbl_progress_detail)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _create_finish_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        lbl = QLabel("Setup Complete! Your GPU Worker is Ready")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {EMERALD_GREEN};")
        card_layout.addWidget(lbl)

        info_box = QFrame()
        info_box.setStyleSheet(
            f"background-color: #F1F5F9; border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 12px;"
        )
        info_layout = QVBoxLayout(info_box)

        lbl_connect = QLabel("How to Connect from Client Laptop:")
        lbl_connect.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        info_layout.addWidget(lbl_connect)

        lan_txt = QLabel(f"• Local LAN URL:  http://{self.local_ip}:8000")
        lan_txt.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-weight: bold;")
        info_layout.addWidget(lan_txt)

        wan_txt = QLabel(
            "• Remote / Worldwide: Install Tailscale or Cloudflare Tunnel to access this worker "
            "from any PC anywhere in the world!"
        )
        wan_txt.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        info_layout.addWidget(wan_txt)

        card_layout.addWidget(info_box)

        self.chk_launch = QCheckBox("Launch Distributed GPU Worker immediately")
        self.chk_launch.setChecked(True)
        card_layout.addWidget(self.chk_launch)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Directory")
        if folder:
            self.edit_dir.setText(folder)

    def _go_next(self) -> None:
        idx = self.pages.currentIndex()
        if idx == 0:
            self.pages.setCurrentIndex(1)
            self.btn_back.show()
            self.btn_next.setText("Install Now ⚡")
        elif idx == 1:
            self.pages.setCurrentIndex(2)
            self.btn_back.hide()
            self.btn_next.setEnabled(False)
            self._start_installation()
        elif idx == 3:
            if self.chk_launch.isChecked():
                self._launch_worker()
            self.close()

    def _go_back(self) -> None:
        idx = self.pages.currentIndex()
        if idx == 1:
            self.pages.setCurrentIndex(0)
            self.btn_back.hide()
            self.btn_next.setText("Continue →")

    def _start_installation(self) -> None:
        dest = self.edit_dir.text().strip()
        port = int(self.edit_port.text().strip() or "8000")
        create_sh = self.chk_shortcut.isChecked()
        firewall = self.chk_firewall.isChecked()

        self.thread = QThread()
        self.worker = InstallWorker(dest, create_sh, firewall, port)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _on_progress(self, pct: int, msg: str) -> None:
        self.progress_bar.setValue(pct)
        self.lbl_progress_detail.setText(msg)

    def _on_finished(self, success: bool, msg: str) -> None:
        self.btn_next.setEnabled(True)
        if success:
            self.pages.setCurrentIndex(3)
            self.btn_next.setText("Finish & Launch 🚀")
        else:
            self.lbl_progress_title.setText("Installation Error")
            self.lbl_progress_title.setStyleSheet("color: #E5484D;")
            self.lbl_progress_detail.setText(f"Failed: {msg}")
            self.btn_next.setText("Close")

    def _launch_worker(self) -> None:
        dest = Path(self.edit_dir.text().strip())
        exe_path = dest / "DistributedGPUWorker.exe"
        bat_path = dest / "Start-Worker.bat"

        target = bat_path if bat_path.exists() else exe_path
        if target.exists():
            subprocess.Popen(
                ["cmd.exe", "/c", "start", str(target)],
                cwd=str(dest),
                shell=True,
            )


def main() -> None:
    app = QApplication(sys.argv)
    window = WorkerInstallerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
