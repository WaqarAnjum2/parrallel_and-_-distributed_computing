"""
Advanced Connection Page — High-Tech Cyber-Industrial Console.

Worker IP/Port configuration, fast presets, credential management,
live hardware telemetry (GPU/NVENC/Storage), and real-time latency ping analysis.
All network calls run strictly in background QThreads to prevent UI blocking.
"""

from __future__ import annotations

import socket
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from client.config import ClientConfig
from client.workers.threads import ConnectionTestThread


class ConnectionPage(QWidget):
    """High-tech worker connection configuration & telemetry console."""

    def __init__(self, config: ClientConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._test_thread: Optional[ConnectionTestThread] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # -------------------------------------------------------------
        # Section 1: Server Connection Configuration Card
        # -------------------------------------------------------------
        conn_group = QGroupBox("🌐 WORKER ENDPOINT & CREDENTIALS")
        conn_layout = QVBoxLayout()
        conn_layout.setSpacing(10)

        form_layout = QGridLayout()
        form_layout.setSpacing(10)

        # Worker IP
        ip_label = QLabel("Worker Host / IP:")
        ip_label.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px;")
        self._host_input = QLineEdit(self._config.worker_host)
        self._host_input.setPlaceholderText("e.g. 192.168.1.10 or 127.0.0.1")
        self._host_input.setFixedHeight(36)
        form_layout.addWidget(ip_label, 0, 0)
        form_layout.addWidget(self._host_input, 0, 1)

        # Port
        port_label = QLabel("Port:")
        port_label.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px;")
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(self._config.worker_port)
        self._port_input.setFixedHeight(36)
        form_layout.addWidget(port_label, 0, 2)
        form_layout.addWidget(self._port_input, 0, 3)

        # Auth Token
        token_label = QLabel("Worker Auth Token:")
        token_label.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px;")
        
        token_box = QHBoxLayout()
        self._token_input = QLineEdit(self._config.auth_token)
        self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_input.setPlaceholderText("Bearer token (from worker .env)")
        self._token_input.setFixedHeight(36)
        
        self._toggle_token_btn = QPushButton("👁")
        self._toggle_token_btn.setFixedSize(36, 36)
        self._toggle_token_btn.setToolTip("Show/Hide Token")
        self._toggle_token_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                color: #334155;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        self._toggle_token_btn.clicked.connect(self._toggle_token_visibility)
        token_box.addWidget(self._token_input)
        token_box.addWidget(self._toggle_token_btn)

        form_layout.addWidget(token_label, 1, 0)
        form_layout.addLayout(token_box, 1, 1, 1, 3)

        conn_layout.addLayout(form_layout)

        # Quick Preset Buttons
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)

        preset_local_btn = QPushButton("⚡ This PC (192.168.100.8)")
        preset_local_btn.setFixedHeight(28)
        preset_local_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #1D4ED8;
                border: 1px solid #93C5FD;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #DBEAFE; color: #1E40AF; }
        """)
        preset_local_btn.clicked.connect(lambda: self._set_host_preset("192.168.100.8"))
        presets_layout.addWidget(preset_local_btn)

        preset_lan_btn = QPushButton("🔍 Auto-Detect Local IP")
        preset_lan_btn.setFixedHeight(28)
        preset_lan_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F3FF;
                color: #6D28D9;
                border: 1px solid #C4B5FD;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #EDE9FE; color: #5B21B6; }
        """)
        preset_lan_btn.clicked.connect(self._detect_local_ip)
        presets_layout.addWidget(preset_lan_btn)
        presets_layout.addStretch()

        conn_layout.addLayout(presets_layout)

        # Test Connection Button
        self._test_btn = QPushButton("⚡ CONNECT & RUN TELEMETRY DIAGNOSTIC")
        self._test_btn.setFixedHeight(44)
        self._test_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._test_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #4F46E5);
                color: #FFFFFF;
                border: 1px solid #60A5FA;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #4338CA);
            }
            QPushButton:pressed {
                background: #1E3A8A;
            }
            QPushButton:disabled {
                background: #334155;
                color: #64748B;
                border-color: #475569;
            }
        """)
        self._test_btn.clicked.connect(self._on_test_connection)
        conn_layout.addWidget(self._test_btn)

        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # -------------------------------------------------------------
        # Section 2: Worker Hardware & Capabilities Telemetry
        # -------------------------------------------------------------
        telemetry_group = QGroupBox("🖥️ WORKER HARDWARE & ENVIRONMENT TELEMETRY")
        telemetry_layout = QGridLayout()
        telemetry_layout.setSpacing(12)

        # Status badge
        telemetry_layout.addWidget(self._create_header_label("Node Status:"), 0, 0)
        self._status_badge = QLabel("● DISCONNECTED")
        self._status_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
                font-size: 12px;
            }
        """)
        telemetry_layout.addWidget(self._status_badge, 0, 1)

        # Server Node Name
        telemetry_layout.addWidget(self._create_header_label("Worker Hostname:"), 0, 2)
        self._hostname_label = QLabel("—")
        self._hostname_label.setStyleSheet("color: #0F172A; font-family: Consolas; font-weight: 600;")
        telemetry_layout.addWidget(self._hostname_label, 0, 3)

        # GPU Hardware
        telemetry_layout.addWidget(self._create_header_label("NVIDIA GPU:"), 1, 0)
        self._gpu_label = QLabel("Not detected")
        self._gpu_label.setStyleSheet("color: #64748B; font-weight: 600;")
        telemetry_layout.addWidget(self._gpu_label, 1, 1)

        # VRAM / Memory
        telemetry_layout.addWidget(self._create_header_label("GPU VRAM:"), 1, 2)
        self._vram_label = QLabel("—")
        self._vram_label.setStyleSheet("color: #64748B; font-family: Consolas; font-weight: 600;")
        telemetry_layout.addWidget(self._vram_label, 1, 3)

        # NVENC Hardware Encoders
        telemetry_layout.addWidget(self._create_header_label("NVENC Encoders:"), 2, 0)
        self._nvenc_label = QLabel("Not detected")
        self._nvenc_label.setStyleSheet("color: #64748B; font-weight: 600;")
        telemetry_layout.addWidget(self._nvenc_label, 2, 1)

        # FFmpeg Version
        telemetry_layout.addWidget(self._create_header_label("FFmpeg Build:"), 2, 2)
        self._ffmpeg_label = QLabel("—")
        self._ffmpeg_label.setStyleSheet("color: #64748B; font-family: Consolas; font-weight: 600;")
        telemetry_layout.addWidget(self._ffmpeg_label, 2, 3)

        # Queue Occupancy & Limits
        telemetry_layout.addWidget(self._create_header_label("Queue Occupancy:"), 3, 0)
        self._queue_label = QLabel("0 active jobs (Max concurrency: 1)")
        self._queue_label.setStyleSheet("color: #64748B; font-weight: 600;")
        telemetry_layout.addWidget(self._queue_label, 3, 1)

        # Worker CPU
        telemetry_layout.addWidget(self._create_header_label("Worker CPU:"), 3, 2)
        self._cpu_label = QLabel("—")
        self._cpu_label.setStyleSheet("color: #64748B; font-weight: 600;")
        telemetry_layout.addWidget(self._cpu_label, 3, 3)

        telemetry_group.setLayout(telemetry_layout)
        layout.addWidget(telemetry_group)

        # -------------------------------------------------------------
        # Section 3: Real-Time Network Latency Benchmark Card
        # -------------------------------------------------------------
        latency_group = QGroupBox("📡 REAL-TIME NETWORK LATENCY & QUALITY")
        latency_layout = QGridLayout()
        latency_layout.setSpacing(12)

        # Latency tier pill
        latency_layout.addWidget(self._create_header_label("Connection Quality:"), 0, 0)
        self._quality_badge = QLabel("— UNTESTED")
        self._quality_badge.setStyleSheet("""
            QLabel {
                background-color: #F1F5F9;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
                font-size: 11px;
            }
        """)
        latency_layout.addWidget(self._quality_badge, 0, 1)

        latency_layout.addWidget(self._create_header_label("Packet Reliability:"), 0, 2)
        self._lat_success = QLabel("— / — (0% loss)")
        self._lat_success.setStyleSheet("color: #0F172A; font-family: Consolas; font-weight: 600;")
        latency_layout.addWidget(self._lat_success, 0, 3)

        # Latency metrics
        latency_layout.addWidget(self._create_header_label("Minimum Latency:"), 1, 0)
        self._lat_min = QLabel("—")
        self._lat_min.setStyleSheet("color: #0284C7; font-family: Consolas; font-weight: 700; font-size: 13px;")
        latency_layout.addWidget(self._lat_min, 1, 1)

        latency_layout.addWidget(self._create_header_label("Average Latency:"), 1, 2)
        self._lat_avg = QLabel("—")
        self._lat_avg.setStyleSheet("color: #059669; font-family: Consolas; font-weight: 700; font-size: 13px;")
        latency_layout.addWidget(self._lat_avg, 1, 3)

        latency_layout.addWidget(self._create_header_label("Maximum Latency:"), 2, 0)
        self._lat_max = QLabel("—")
        self._lat_max.setStyleSheet("color: #D97706; font-family: Consolas; font-weight: 700; font-size: 13px;")
        latency_layout.addWidget(self._lat_max, 2, 1)

        latency_layout.addWidget(self._create_header_label("Offloading Viability:"), 2, 2)
        self._viability_label = QLabel("Awaiting diagnostic")
        self._viability_label.setStyleSheet("color: #64748B; font-weight: 600;")
        latency_layout.addWidget(self._viability_label, 2, 3)

        latency_group.setLayout(latency_layout)
        layout.addWidget(latency_group)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Helper UI Builders
    # ------------------------------------------------------------------

    @staticmethod
    def _create_header_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px;")
        return lbl

    def _toggle_token_visibility(self) -> None:
        if self._token_input.echoMode() == QLineEdit.EchoMode.Password:
            self._token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_token_btn.setText("🔒")
        else:
            self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_token_btn.setText("👁")

    def _set_host_preset(self, host: str) -> None:
        self._host_input.setText(host)

    def _detect_local_ip(self) -> None:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            self._host_input.setText(local_ip)
        except Exception:
            self._host_input.setText("127.0.0.1")

    # ------------------------------------------------------------------
    # Actions & Signal Handlers
    # ------------------------------------------------------------------

    def _on_test_connection(self) -> None:
        """Spawn background ConnectionTestThread to evaluate worker."""
        self._config.update(
            host=self._host_input.text().strip(),
            port=self._port_input.value(),
            token=self._token_input.text().strip(),
        )

        self._test_btn.setEnabled(False)
        self._test_btn.setText("⏳ RUNNING DIAGNOSTICS & PING TESTS...")

        self._status_badge.setText("● CONNECTING...")
        self._status_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(245, 158, 11, 0.15);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
                font-size: 12px;
            }
        """)

        self._test_thread = ConnectionTestThread(self._config)
        self._test_thread.success.connect(self._on_test_success)
        self._test_thread.failed.connect(self._on_test_failed)
        self._test_thread.finished.connect(self._on_test_finished)
        self._test_thread.start()

    def _on_test_success(self, data: dict) -> None:
        health = data["health"]
        info = data["info"]
        latency = data["latency"]

        # 1. Update Status Badge
        self._status_badge.setText("● READY & ONLINE")
        self._status_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(16, 185, 129, 0.15);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.5);
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
                font-size: 12px;
            }
        """)

        # 2. Hostname & CPU
        self._hostname_label.setText(info.get("hostname", "Unknown Host"))
        self._cpu_label.setText(info.get("cpu", "Unknown CPU"))

        # 3. GPU Status
        gpu_name = info.get("gpu", "NVIDIA GPU")
        gpu_mem = info.get("gpu_memory_mb", 0)
        if health.get("gpu_available"):
            self._gpu_label.setText(f"✓ {gpu_name}")
            self._gpu_label.setStyleSheet("color: #10B981; font-weight: 700;")
            self._vram_label.setText(f"{gpu_mem:,} MB Dedicated")
            self._vram_label.setStyleSheet("color: #10B981; font-family: Consolas; font-weight: 700;")
        else:
            self._gpu_label.setText("✗ NOT AVAILABLE")
            self._gpu_label.setStyleSheet("color: #EF4444; font-weight: 700;")
            self._vram_label.setText("None")

        # 4. NVENC Encoders
        encoders = info.get("encoders", [])
        if encoders:
            self._nvenc_label.setText(" | ".join(encoders).upper())
            self._nvenc_label.setStyleSheet("color: #38BDF8; font-weight: 700;")
        else:
            self._nvenc_label.setText("✗ NO NVENC FOUND")
            self._nvenc_label.setStyleSheet("color: #EF4444; font-weight: 700;")

        # 5. FFmpeg
        self._ffmpeg_label.setText(info.get("ffmpeg_version", "Detected"))

        # 6. Queue
        q_size = health.get("queue_size", 0)
        max_jobs = info.get("max_concurrent_jobs", 1)
        self._queue_label.setText(f"{q_size} jobs waiting (Max concurrent: {max_jobs})")

        # 7. Latency Metrics
        min_ms = latency.get("min_ms", 0.0)
        avg_ms = latency.get("avg_ms", 0.0)
        max_ms = latency.get("max_ms", 0.0)
        success = latency.get("successful", 0)
        total = latency.get("requests", 5)

        self._lat_min.setText(f"{min_ms:.1f} ms")
        self._lat_avg.setText(f"{avg_ms:.1f} ms")
        self._lat_max.setText(f"{max_ms:.1f} ms")
        loss_pct = int(((total - success) / total) * 100) if total > 0 else 0
        self._lat_success.setText(f"{success}/{total} packets ({loss_pct}% loss)")

        # Connection Quality categorization
        if avg_ms < 5.0:
            self._quality_badge.setText("● ULTRA-FAST LAN (<5ms)")
            self._quality_badge.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.2);
                color: #10B981;
                border: 1px solid #10B981;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
            """)
            self._viability_label.setText("Excellent (Near-zero network penalty)")
            self._viability_label.setStyleSheet("color: #10B981; font-weight: 600;")
        elif avg_ms < 25.0:
            self._quality_badge.setText("● HIGH-SPEED WI-FI (<25ms)")
            self._quality_badge.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.2);
                color: #38BDF8;
                border: 1px solid #38BDF8;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
            """)
            self._viability_label.setText("High Offload Advantage")
            self._viability_label.setStyleSheet("color: #38BDF8; font-weight: 600;")
        else:
            self._quality_badge.setText("● ELEVATED LATENCY (>25ms)")
            self._quality_badge.setStyleSheet("""
                background-color: rgba(245, 158, 11, 0.2);
                color: #F59E0B;
                border: 1px solid #F59E0B;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
            """)
            self._viability_label.setText("Viable for large/complex videos")
            self._viability_label.setStyleSheet("color: #F59E0B; font-weight: 600;")

    def _on_test_failed(self, error_msg: str) -> None:
        self._status_badge.setText("● CONNECTION FAILED")
        self._status_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(239, 68, 68, 0.2);
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 700;
                font-size: 12px;
            }
        """)

        self._quality_badge.setText("● UNREACHABLE")
        self._quality_badge.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.2);
            color: #EF4444;
            border: 1px solid #EF4444;
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: 700;
        """)
        self._viability_label.setText("Cannot connect to remote node")
        self._viability_label.setStyleSheet("color: #EF4444; font-weight: 600;")

        QMessageBox.warning(
            self,
            "Worker Connection Diagnostic",
            f"Unable to establish connection to worker:\n\n{error_msg}\n\n"
            "Please check:\n"
            "1. Worker process is running (python worker/main.py)\n"
            "2. Windows Firewall allows inbound TCP 8000 on worker\n"
            "3. Client and Worker are on the same Wi-Fi/LAN network\n"
            "4. Authentication token matches worker configuration",
        )

    def _on_test_finished(self) -> None:
        self._test_btn.setEnabled(True)
        self._test_btn.setText("⚡ CONNECT & RUN TELEMETRY DIAGNOSTIC")

    def _set_host_preset(self, host: str) -> None:
        """Set host from a quick preset button."""
        self._host_input.setText(host)

    def _detect_local_ip(self) -> None:
        """Auto-detect machine's active LAN IP and set as host."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._host_input.setText(ip)
        except Exception:
            self._host_input.setText("192.168.100.8")

