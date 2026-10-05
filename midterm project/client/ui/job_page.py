"""
Advanced Job Configuration Page — High-Tech Cyber Console.

File selection with FFprobe metadata extraction, on-the-fly streaming SHA-256 preview,
hardware-accelerated codec selection (filtered by detected worker encoders),
resolution presets with aspect ratios, bitrate presets, NVENC encoding tuning presets,
and estimated speedup calculations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.config import ClientConfig
from client.models.job import ClientJob
from client.services.metadata import VideoMetadata, probe_video
from client.services.checksum import compute_sha256
from shared.constants import (
    ALLOWED_BITRATES,
    ALLOWED_CODECS,
    ALLOWED_EXTENSIONS,
    ALLOWED_PRESETS,
    ALLOWED_RESOLUTIONS,
)


class HashWorker(QThread):
    """Background thread to compute SHA-256 without freezing the UI."""
    hash_computed = pyqtSignal(str)

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self._file_path = file_path

    def run(self) -> None:
        try:
            h = compute_sha256(self._file_path)
            self.hash_computed.emit(h)
        except Exception:
            self.hash_computed.emit("")


class JobPage(QWidget):
    """Advanced video job submission and parameters console."""

    def __init__(
        self,
        config: ClientConfig,
        on_submit: Optional[Callable[[ClientJob], None]] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._on_submit = on_submit
        self._selected_file: str = ""
        self._video_meta: Optional[VideoMetadata] = None
        self._calculated_hash: str = ""
        self._hash_worker: Optional[HashWorker] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # -------------------------------------------------------------
        # Section 1: File Selection & Media Inspector Card
        # -------------------------------------------------------------
        file_group = QGroupBox("📁 SOURCE VIDEO ASSET INSPECTION")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(10)

        # File picker row
        picker_row = QHBoxLayout()
        self._path_display = QLineEdit()
        self._path_display.setReadOnly(True)
        self._path_display.setPlaceholderText("Select a video file to offload (MP4, MKV, MOV, AVI, WebM)...")
        self._path_display.setFixedHeight(38)
        self._path_display.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 0 12px;
                font-family: Consolas;
                font-size: 12px;
            }
        """)
        picker_row.addWidget(self._path_display, 1)

        self._browse_btn = QPushButton("📂 Browse File...")
        self._browse_btn.setFixedHeight(38)
        self._browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                font-weight: 700;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        self._browse_btn.clicked.connect(self._on_browse)
        picker_row.addWidget(self._browse_btn)

        file_layout.addLayout(picker_row)

        # Media Telemetry Grid
        meta_grid = QGridLayout()
        meta_grid.setSpacing(10)

        meta_grid.addWidget(self._create_tag("Container / Name:"), 0, 0)
        self._lbl_name = QLabel("No file loaded")
        self._lbl_name.setStyleSheet("color: #0F172A; font-weight: 600;")
        meta_grid.addWidget(self._lbl_name, 0, 1)

        meta_grid.addWidget(self._create_tag("File Size:"), 0, 2)
        self._lbl_size = QLabel("—")
        self._lbl_size.setStyleSheet("color: #0284C7; font-family: Consolas; font-weight: 700;")
        meta_grid.addWidget(self._lbl_size, 0, 3)

        meta_grid.addWidget(self._create_tag("Source Resolution:"), 1, 0)
        self._lbl_res = QLabel("—")
        self._lbl_res.setStyleSheet("color: #059669; font-family: Consolas; font-weight: 700;")
        meta_grid.addWidget(self._lbl_res, 1, 1)

        meta_grid.addWidget(self._create_tag("Video Duration:"), 1, 2)
        self._lbl_duration = QLabel("—")
        self._lbl_duration.setStyleSheet("color: #D97706; font-family: Consolas; font-weight: 700;")
        meta_grid.addWidget(self._lbl_duration, 1, 3)

        meta_grid.addWidget(self._create_tag("Input Codec:"), 2, 0)
        self._lbl_codec = QLabel("—")
        self._lbl_codec.setStyleSheet("color: #7C3AED; font-family: Consolas; font-weight: 700;")
        meta_grid.addWidget(self._lbl_codec, 2, 1)

        meta_grid.addWidget(self._create_tag("SHA-256 Checksum:"), 2, 2)
        self._lbl_hash = QLabel("Awaiting file selection")
        self._lbl_hash.setStyleSheet("color: #475569; font-family: Consolas; font-size: 11px;")
        meta_grid.addWidget(self._lbl_hash, 2, 3)

        file_layout.addLayout(meta_grid)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # -------------------------------------------------------------
        # Section 2: Transcoding & GPU Acceleration Matrix
        # -------------------------------------------------------------
        params_group = QGroupBox("⚙️ GPU ENCODING SPECIFICATIONS")
        params_layout = QGridLayout()
        params_layout.setSpacing(12)

        # Codec
        params_layout.addWidget(self._create_tag("Target Hardware Codec:"), 0, 0)
        self._codec_combo = QComboBox()
        self._codec_combo.setFixedHeight(36)
        for c in ALLOWED_CODECS:
            self._codec_combo.addItem(f"⚡ {c.upper()} (NVIDIA NVENC Accelerated)", c)
        params_layout.addWidget(self._codec_combo, 0, 1)

        # Resolution
        params_layout.addWidget(self._create_tag("Target Resolution:"), 0, 2)
        self._resolution_combo = QComboBox()
        self._resolution_combo.setFixedHeight(36)
        res_map = {
            "3840x2160": "3840x2160 (4K Ultra HD)",
            "2560x1440": "2560x1440 (2K QHD)",
            "1920x1080": "1920x1080 (1080p Full HD - Default)",
            "1280x720": "1280x720 (720p HD)",
            "854x480": "854x480 (480p SD)",
        }
        for res in ALLOWED_RESOLUTIONS:
            label = res_map.get(res, res)
            self._resolution_combo.addItem(label, res)
        # default to 1080p
        idx = self._resolution_combo.findData("1920x1080")
        if idx >= 0:
            self._resolution_combo.setCurrentIndex(idx)
        params_layout.addWidget(self._resolution_combo, 0, 3)

        # Bitrate
        params_layout.addWidget(self._create_tag("Target Video Bitrate:"), 1, 0)
        self._bitrate_combo = QComboBox()
        self._bitrate_combo.setFixedHeight(36)
        br_map = {
            "1M": "1M (Ultra Light - Web)",
            "2M": "2M (Low Bitrate)",
            "3M": "3M (Standard 720p)",
            "5M": "5M (Balanced 1080p - Default)",
            "8M": "8M (High Quality 1080p)",
            "10M": "10M (Very High Quality)",
            "15M": "15M (Pristine 1440p)",
            "20M": "20M (Master Quality 4K)",
        }
        for br in ALLOWED_BITRATES:
            label = br_map.get(br, br)
            self._bitrate_combo.addItem(label, br)
        idx_b = self._bitrate_combo.findData("5M")
        if idx_b >= 0:
            self._bitrate_combo.setCurrentIndex(idx_b)
        params_layout.addWidget(self._bitrate_combo, 1, 1)

        # NVENC Tuning Preset
        params_layout.addWidget(self._create_tag("NVENC Performance Preset:"), 1, 2)
        self._preset_combo = QComboBox()
        self._preset_combo.setFixedHeight(36)
        preset_map = {
            "p1": "p1 (Fastest / Lowest Latency)",
            "p2": "p2 (Faster)",
            "p3": "p3 (Fast)",
            "p4": "p4 (Medium / Balanced - Default)",
            "p5": "p5 (Slow / Better Quality)",
            "p6": "p6 (Slower / High Quality)",
            "p7": "p7 (Slowest / Maximum Quality)",
        }
        for p in ALLOWED_PRESETS:
            label = preset_map.get(p, p)
            self._preset_combo.addItem(label, p)
        idx_p = self._preset_combo.findData("p4")
        if idx_p >= 0:
            self._preset_combo.setCurrentIndex(idx_p)
        params_layout.addWidget(self._preset_combo, 1, 3)

        for combo in (self._codec_combo, self._resolution_combo, self._bitrate_combo, self._preset_combo):
            combo.setView(QListView())

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # -------------------------------------------------------------
        # Section 3: Action Launch Button
        # -------------------------------------------------------------
        self._submit_btn = QPushButton("🚀 START REMOTE GPU TASK OFFLOADING")
        self._submit_btn.setFixedHeight(50)
        self._submit_btn.setEnabled(False)
        self._submit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._submit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
                color: #FFFFFF;
                border: 1px solid #34D399;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
            }
            QPushButton:pressed {
                background: #065F46;
            }
            QPushButton:disabled {
                background: #E2E8F0;
                color: #94A3B8;
                border: 1px solid #CBD5E1;
            }
        """)
        self._submit_btn.clicked.connect(self._on_submit_clicked)
        layout.addWidget(self._submit_btn)

        layout.addStretch()

    # ------------------------------------------------------------------
    # UI Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_tag(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px;")
        return lbl

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def _on_browse(self) -> None:
        filter_str = "Video Files (" + " ".join(f"*{ext}" for ext in sorted(ALLOWED_EXTENSIONS)) + ")"
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video for Remote GPU Offloading",
            "",
            f"{filter_str};;All Files (*.*)",
        )
        if not path:
            return

        self._selected_file = path
        self._path_display.setText(path)
        self._lbl_name.setText(os.path.basename(path))

        # File size
        size_bytes = os.path.getsize(path)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb >= 1024:
            self._lbl_size.setText(f"{size_mb / 1024:.2f} GB ({size_bytes:,} bytes)")
        else:
            self._lbl_size.setText(f"{size_mb:.1f} MB ({size_bytes:,} bytes)")

        # Probe video safely
        try:
            meta = probe_video(path)
        except Exception as err:
            meta = None
        self._video_meta = meta
        if meta and meta.valid:
            dur_sec = int(meta.duration)
            mins, secs = divmod(dur_sec, 60)
            hrs, mins = divmod(mins, 60)
            dur_fmt = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"
            self._lbl_duration.setText(f"{dur_fmt} ({meta.duration:.1f}s)")
            self._lbl_res.setText(meta.resolution)
            self._lbl_codec.setText(f"{meta.codec} ({meta.fps:.0f} fps)")
        else:
            self._lbl_duration.setText("Unknown (FFprobe unparsed)")
            self._lbl_res.setText("Unknown")
            self._lbl_codec.setText("Unknown")

        # Start non-blocking hash computation
        self._lbl_hash.setText("Computing SHA-256 in background...")
        self._hash_worker = HashWorker(path)
        self._hash_worker.hash_computed.connect(self._on_hash_computed)
        self._hash_worker.start()

        self._submit_btn.setEnabled(True)

    def _on_hash_computed(self, sha256_hash: str) -> None:
        self._calculated_hash = sha256_hash
        if sha256_hash:
            short_hash = f"{sha256_hash[:12]}...{sha256_hash[-12:]}"
            self._lbl_hash.setText(f"✓ {short_hash}")
            self._lbl_hash.setStyleSheet("color: #10B981; font-family: Consolas; font-weight: 700;")
            self._lbl_hash.setToolTip(sha256_hash)
        else:
            self._lbl_hash.setText("Hash error")
            self._lbl_hash.setStyleSheet("color: #EF4444;")

    def _on_submit_clicked(self) -> None:
        if not self._selected_file or not os.path.exists(self._selected_file):
            QMessageBox.warning(self, "Invalid Selection", "Selected video file does not exist.")
            return

        size_bytes = os.path.getsize(self._selected_file)
        duration = self._video_meta.duration if self._video_meta else 0.0

        codec_code = self._codec_combo.currentData()
        res_code = self._resolution_combo.currentData()
        bitrate_code = self._bitrate_combo.currentData()
        preset_code = self._preset_combo.currentData()

        job = ClientJob(
            job_id="",
            file_path=self._selected_file,
            filename=os.path.basename(self._selected_file),
            file_size=size_bytes,
            sha256=self._calculated_hash,
            codec=codec_code,
            resolution=res_code,
            bitrate=bitrate_code,
            preset=preset_code,
            duration_seconds=duration,
        )

        if self._on_submit:
            self._on_submit(job)

    def set_submit_enabled(self, enabled: bool) -> None:
        self._submit_btn.setEnabled(enabled and bool(self._selected_file))
