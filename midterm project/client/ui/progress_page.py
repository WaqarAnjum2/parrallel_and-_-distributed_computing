"""
Advanced Multi-Stage Progress Page — Real-Time Hardware Transcode Monitor.

Visualises the 4-phase pipeline (Upload -> Queue -> NVENC Transcoding -> Download)
with live gauges for FPS, encoding speed factor, elapsed time, and ETA.
Includes an interactive color-coded terminal log viewer and graceful cancellation.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor, QCursor, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProgressPage(QWidget):
    """High-tech 4-stage job pipeline progress monitor."""

    def __init__(self, on_cancel: callable | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_cancel = on_cancel
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # -------------------------------------------------------------
        # Section 1: Hero Pipeline Stage Status Banner
        # -------------------------------------------------------------
        header_box = QHBoxLayout()
        self._stage_badge = QLabel("● IDLE / STANDBY")
        self._stage_badge.setStyleSheet("""
            QLabel {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
        """)
        header_box.addWidget(self._stage_badge)

        header_box.addStretch()

        # Cancel Job Button
        self._cancel_btn = QPushButton("✖ ABORT JOB")
        self._cancel_btn.setFixedSize(130, 36)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEE2E2;
                color: #EF4444;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: white;
            }
            QPushButton:disabled {
                background-color: #F1F5F9;
                color: #94A3B8;
                border-color: #E2E8F0;
            }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        header_box.addWidget(self._cancel_btn)

        layout.addLayout(header_box)

        # -------------------------------------------------------------
        # Section 2: 4-Stage Visual Pipeline Cards
        # -------------------------------------------------------------
        pipeline_group = QGroupBox("⚡ 4-STAGE DISTRIBUTED OFFLOADING PIPELINE")
        pipeline_layout = QVBoxLayout()
        pipeline_layout.setSpacing(10)

        # Phase 1: Upload
        p1_box = QHBoxLayout()
        p1_lbl = QLabel("1. Streaming Upload:")
        p1_lbl.setStyleSheet("color: #0284C7; font-weight: 700; width: 140px;")
        p1_lbl.setFixedWidth(150)
        p1_box.addWidget(p1_lbl)
        self._upload_bar = self._create_progress_bar("#0284C7", "#38BDF8")
        p1_box.addWidget(self._upload_bar)
        self._upload_text = QLabel("0%")
        self._upload_text.setStyleSheet("color: #0284C7; font-family: Consolas; font-weight: 700;")
        self._upload_text.setFixedWidth(50)
        p1_box.addWidget(self._upload_text)
        pipeline_layout.addLayout(p1_box)

        # Phase 2: NVENC Hardware Transcode
        p2_box = QHBoxLayout()
        p2_lbl = QLabel("2. NVENC GPU Transcode:")
        p2_lbl.setStyleSheet("color: #059669; font-weight: 700;")
        p2_lbl.setFixedWidth(150)
        p2_box.addWidget(p2_lbl)
        self._processing_bar = self._create_progress_bar("#059669", "#10B981")
        p2_box.addWidget(self._processing_bar)
        self._processing_text = QLabel("0%")
        self._processing_text.setStyleSheet("color: #059669; font-family: Consolas; font-weight: 700;")
        self._processing_text.setFixedWidth(50)
        p2_box.addWidget(self._processing_text)
        pipeline_layout.addLayout(p2_box)

        # Live GPU Telemetry sub-row
        gpu_telemetry_box = QHBoxLayout()
        gpu_telemetry_box.setContentsMargins(155, 0, 0, 0)
        
        self._fps_label = QLabel("Encoding Speed: — FPS")
        self._fps_label.setStyleSheet("color: #7C3AED; font-family: Consolas; font-weight: 700; font-size: 12px;")
        gpu_telemetry_box.addWidget(self._fps_label)

        self._speed_label = QLabel("Realtime Factor: —x")
        self._speed_label.setStyleSheet("color: #059669; font-family: Consolas; font-weight: 700; font-size: 12px;")
        gpu_telemetry_box.addWidget(self._speed_label)

        self._elapsed_label = QLabel("Elapsed: —s")
        self._elapsed_label.setStyleSheet("color: #D97706; font-family: Consolas; font-weight: 700; font-size: 12px;")
        gpu_telemetry_box.addWidget(self._elapsed_label)
        
        gpu_telemetry_box.addStretch()
        pipeline_layout.addLayout(gpu_telemetry_box)

        # Phase 3: Result Download
        p3_box = QHBoxLayout()
        p3_lbl = QLabel("3. Stream Download:")
        p3_lbl.setStyleSheet("color: #D97706; font-weight: 700;")
        p3_lbl.setFixedWidth(150)
        p3_box.addWidget(p3_lbl)
        self._download_bar = self._create_progress_bar("#D97706", "#F59E0B")
        p3_box.addWidget(self._download_bar)
        self._download_text = QLabel("0%")
        self._download_text.setStyleSheet("color: #D97706; font-family: Consolas; font-weight: 700;")
        self._download_text.setFixedWidth(50)
        p3_box.addWidget(self._download_text)
        pipeline_layout.addLayout(p3_box)

        pipeline_group.setLayout(pipeline_layout)
        layout.addWidget(pipeline_group)

        # -------------------------------------------------------------
        # Section 3: Interactive Monospace Terminal Console
        # -------------------------------------------------------------
        term_header = QHBoxLayout()
        term_title = QLabel("📟 LIVE EVENT & TELEMETRY STREAM CONSOLE")
        term_title.setStyleSheet("color: #475569; font-weight: 700; font-size: 12px;")
        term_header.addWidget(term_title)
        term_header.addStretch()

        copy_btn = QPushButton("📋 Copy Logs")
        copy_btn.setFixedHeight(24)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 11px;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        copy_btn.clicked.connect(self._copy_terminal)
        term_header.addWidget(copy_btn)

        clear_btn = QPushButton("🧹 Clear")
        clear_btn.setFixedHeight(24)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 11px;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        clear_btn.clicked.connect(self._clear_terminal)
        term_header.addWidget(clear_btn)

        layout.addLayout(term_header)

        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setFont(QFont("Consolas", 10))
        self._log_area.setStyleSheet("""
            QTextEdit {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self._log_area.setMinimumHeight(200)
        layout.addWidget(self._log_area)

    # ------------------------------------------------------------------
    # UI Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_progress_bar(start_color: str, end_color: str) -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(18)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E2E8F0;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start_color}, stop:1 {end_color});
                border-radius: 3px;
            }}
        """)
        return bar

    # ------------------------------------------------------------------
    # Public Slot Handlers (invoked by signals from Worker Thread)
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._upload_bar.setValue(0)
        self._upload_text.setText("0%")
        self._processing_bar.setValue(0)
        self._processing_text.setText("0%")
        self._download_bar.setValue(0)
        self._download_text.setText("0%")
        self._fps_label.setText("Encoding Speed: — FPS")
        self._speed_label.setText("Realtime Factor: —x")
        self._elapsed_label.setText("Elapsed: —s")
        self._cancel_btn.setEnabled(True)
        self._stage_badge.setText("● PREPARING OFFLOAD PIPELINE...")
        self._stage_badge.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.15);
            color: #38BDF8;
            border: 1px solid #38BDF8;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 800;
        """)

    def set_stage(self, stage: str, progress: int = 0) -> None:
        self._stage_badge.setText(f"● {stage.upper()}")

    def set_upload_progress(self, percent: int) -> None:
        self._upload_bar.setValue(percent)
        self._upload_text.setText(f"{percent}%")
        self._stage_badge.setText(f"● UPLOADING INPUT VIDEO ({percent}%)")
        self._stage_badge.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.15);
            color: #38BDF8;
            border: 1px solid #38BDF8;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 800;
        """)

    def set_processing_progress(self, percent: int, fps: float, speed: str) -> None:
        self._processing_bar.setValue(percent)
        self._processing_text.setText(f"{percent}%")
        self._fps_label.setText(f"Encoding Speed: {fps:.1f} FPS")
        self._speed_label.setText(f"Realtime Factor: {speed}")
        self._stage_badge.setText(f"● NVIDIA NVENC PROCESSING ({percent}%)")
        self._stage_badge.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #10B981;
            border: 1px solid #10B981;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 800;
        """)

    def set_download_progress(self, percent: int) -> None:
        self._download_bar.setValue(percent)
        self._download_text.setText(f"{percent}%")
        self._stage_badge.setText(f"● DOWNLOADING ENCODED STREAM ({percent}%)")
        self._stage_badge.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.15);
            color: #F59E0B;
            border: 1px solid #F59E0B;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 800;
        """)

    def set_cancel_enabled(self, enabled: bool) -> None:
        self._cancel_btn.setEnabled(enabled)

    def append_log(self, text: str) -> None:
        # Syntax highlighting for log tokens on light background
        color = "#0F172A"
        if "[ERROR]" in text or "FAILED" in text or "IntegrityError" in text:
            color = "#DC2626"
        elif "[GPU]" in text or "NVENC" in text or "Completed" in text:
            color = "#059669"
        elif "[UPLOAD]" in text or "Transfer" in text:
            color = "#0284C7"
        elif "[WARNING]" in text:
            color = "#D97706"

        html_line = f"<span style='color: {color};'>{text}</span>"
        self._log_area.append(html_line)
        self._log_area.moveCursor(QTextCursor.MoveOperation.End)

    def _copy_terminal(self) -> None:
        QApplication.clipboard().setText(self._log_area.toPlainText())

    def _clear_terminal(self) -> None:
        self._log_area.clear()

    def _on_cancel_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm Cancellation",
            "Are you sure you want to abort and terminate the remote GPU transcoding job?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._cancel_btn.setEnabled(False)
            self._stage_badge.setText("● ABORTING JOB...")
            if self._on_cancel:
                self._on_cancel()
