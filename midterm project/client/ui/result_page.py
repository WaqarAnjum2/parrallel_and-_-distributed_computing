"""
Advanced Results Page — Academic Performance Benchmarking & Analytics.

Displays empirical timing metrics (Upload, NVENC GPU, Download, Remote Total, Local CPU),
calculates exact Speedup factor and Network Overhead %, visualises execution breakdown,
and enables one-click video preview, folder opening, and JSON/CSV dataset export.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from client.config import ClientConfig
from client.models.job import ClientJob
from client.services.benchmark import create_benchmark_record, export_benchmarks
from client.workers.threads import LocalBenchmarkThread
from shared.schemas import BenchmarkRecord


class ResultPage(QWidget):
    """Advanced benchmark evaluation, speedup analysis, and export console."""

    def __init__(self, config: ClientConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._current_job: Optional[ClientJob] = None
        self._benchmark_records: list[BenchmarkRecord] = []
        self._benchmark_thread: Optional[LocalBenchmarkThread] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # -------------------------------------------------------------
        # Section 1: Hero Analytics Cards (Speedup & Overhead)
        # -------------------------------------------------------------
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        # Speedup Card
        speedup_card = QFrame()
        speedup_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        sp_layout = QVBoxLayout(speedup_card)
        sp_title = QLabel("ACCELERATION SPEEDUP FACTOR")
        sp_title.setStyleSheet("color: #64748B; font-weight: 700; font-size: 11px;")
        self._lbl_speedup = QLabel("—")
        self._lbl_speedup.setStyleSheet("color: #10B981; font-family: Consolas; font-weight: 900; font-size: 26px;")
        self._lbl_speedup_desc = QLabel("Run local benchmark to calculate real speedup")
        self._lbl_speedup_desc.setStyleSheet("color: #64748B; font-size: 11px;")
        sp_layout.addWidget(sp_title)
        sp_layout.addWidget(self._lbl_speedup)
        sp_layout.addWidget(self._lbl_speedup_desc)
        kpi_row.addWidget(speedup_card)

        # Network Overhead Card
        overhead_card = QFrame()
        overhead_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        ov_layout = QVBoxLayout(overhead_card)
        ov_title = QLabel("NETWORK TRANSMISSION OVERHEAD")
        ov_title.setStyleSheet("color: #64748B; font-weight: 700; font-size: 11px;")
        self._lbl_overhead = QLabel("—")
        self._lbl_overhead.setStyleSheet("color: #2563EB; font-family: Consolas; font-weight: 900; font-size: 26px;")
        self._lbl_overhead_desc = QLabel("(Upload + Download) / Total Remote Time")
        self._lbl_overhead_desc.setStyleSheet("color: #64748B; font-size: 11px;")
        ov_layout.addWidget(ov_title)
        ov_layout.addWidget(self._lbl_overhead)
        ov_layout.addWidget(self._lbl_overhead_desc)
        kpi_row.addWidget(overhead_card)

        layout.addLayout(kpi_row)

        # -------------------------------------------------------------
        # Section 2: Detailed Performance Table
        # -------------------------------------------------------------
        summary_group = QGroupBox("📊 MEASURED PERFORMANCE METRICS")
        summary_layout = QVBoxLayout()

        self._table = QTableWidget(11, 2)
        self._table.setHorizontalHeaderLabels(["Performance Parameter", "Measured Telemetry Value"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 260)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                color: #0F172A;
                gridline-color: #E2E8F0;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #475569;
                padding: 8px;
                font-weight: 700;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
        """)

        metrics = [
            ("Source Video Asset", "—"),
            ("Input Asset Size", "—"),
            ("Encoded Output Size", "—"),
            ("Streaming Upload Duration (T_upload)", "—"),
            ("Worker NVENC GPU Encode Duration (T_gpu)", "—"),
            ("Streaming Download Duration (T_download)", "—"),
            ("Total Remote Turnaround Time (T_remote)", "—"),
            ("Local CPU Transcode Duration (T_local)", "Awaiting local benchmark"),
            ("Speedup Ratio (T_local / T_remote)", "—"),
            ("Network Transmission Overhead %", "—"),
            ("Downloaded File Output Path", "—"),
        ]
        for i, (name, val) in enumerate(metrics):
            item_name = QTableWidgetItem(name)
            item_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            item_val = QTableWidgetItem(val)
            item_val.setFont(QFont("Consolas", 10))
            self._table.setItem(i, 0, item_name)
            self._table.setItem(i, 1, item_val)

        summary_layout.addWidget(self._table)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # -------------------------------------------------------------
        # Section 3: Action Toolbar (Preview, Folder, Local Benchmark, Export)
        # -------------------------------------------------------------
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        # Play Result Video
        self._play_btn = QPushButton("🎬 Play Encoded Video")
        self._play_btn.setFixedHeight(38)
        self._play_btn.setEnabled(False)
        self._play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._play_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                font-weight: 700;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #DBEAFE; }
            QPushButton:disabled { background-color: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }
        """)
        self._play_btn.clicked.connect(self._on_play_video)
        actions_layout.addWidget(self._play_btn)

        # Open Output Folder
        self._open_folder_btn = QPushButton("📁 Open Output Folder")
        self._open_folder_btn.setFixedHeight(38)
        self._open_folder_btn.setEnabled(False)
        self._open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 700;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #F8FAFC; }
            QPushButton:disabled { background-color: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }
        """)
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        actions_layout.addWidget(self._open_folder_btn)

        # Local CPU Benchmark
        self._local_bench_btn = QPushButton("⏱ Run Local CPU Benchmark")
        self._local_bench_btn.setFixedHeight(38)
        self._local_bench_btn.setEnabled(False)
        self._local_bench_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._local_bench_btn.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #6D28D9; }
            QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }
        """)
        self._local_bench_btn.clicked.connect(self._on_run_local_benchmark)
        actions_layout.addWidget(self._local_bench_btn)

        # Export CSV/JSON
        self._export_btn = QPushButton("💾 Export Dataset (CSV / JSON)")
        self._export_btn.setFixedHeight(38)
        self._export_btn.setEnabled(False)
        self._export_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._export_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
                color: white;
                border: 1px solid #1D4ED8;
                border-radius: 6px;
                font-weight: 700;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: #1D4ED8;
            }
            QPushButton:disabled { background: #E2E8F0; color: #94A3B8; border-color: #E2E8F0; }
        """)
        self._export_btn.clicked.connect(self._on_export)
        actions_layout.addWidget(self._export_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Status note
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(self._status_label)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Data Presentation
    # ------------------------------------------------------------------

    def show_results(self, job: ClientJob) -> None:
        self._current_job = job

        size_mb = job.file_size / (1024 * 1024) if job.file_size else 0
        out_mb = job.output_size / (1024 * 1024) if job.output_size else 0

        # KPI labels
        if job.local_encode_time > 0 and job.remote_total_time > 0:
            speedup = job.speedup
            self._lbl_speedup.setText(f"{speedup:.2f}x FASTER")
            pct_saved = ((job.local_encode_time - job.remote_total_time) / job.local_encode_time) * 100
            self._lbl_speedup_desc.setText(f"Offloading saved {pct_saved:.1f}% time compared to Local CPU")
        else:
            self._lbl_speedup.setText("Pending")
            self._lbl_speedup_desc.setText("Click 'Run Local CPU Benchmark' to compare")

        if job.remote_total_time > 0:
            self._lbl_overhead.setText(f"{job.network_overhead_percent:.1f}%")
            net_time = job.upload_time + job.download_time
            self._lbl_overhead_desc.setText(f"Network time: {net_time:.2f}s | GPU time: {job.gpu_processing_time:.2f}s")

        # Table rows
        values = [
            job.filename,
            f"{size_mb:.2f} MB",
            f"{out_mb:.2f} MB",
            f"{job.upload_time:.2f} s",
            f"{job.gpu_processing_time:.2f} s",
            f"{job.download_time:.2f} s",
            f"{job.remote_total_time:.2f} s",
            f"{job.local_encode_time:.2f} s" if job.local_encode_time > 0 else "Not benchmarked yet",
            f"{job.speedup:.2f}x" if job.local_encode_time > 0 else "—",
            f"{job.network_overhead_percent:.1f}%" if job.remote_total_time > 0 else "—",
            job.download_path or "—",
        ]

        for i, val in enumerate(values):
            item = self._table.item(i, 1)
            if item:
                item.setText(val)

        self._play_btn.setEnabled(bool(job.download_path and os.path.exists(job.download_path)))
        self._open_folder_btn.setEnabled(bool(job.download_path and os.path.exists(job.download_path)))
        self._local_bench_btn.setEnabled(True)
        self._export_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_play_video(self) -> None:
        if self._current_job and self._current_job.download_path and os.path.exists(self._current_job.download_path):
            try:
                os.startfile(self._current_job.download_path)
            except Exception as exc:
                QMessageBox.warning(self, "Player Error", f"Unable to launch media player: {exc}")

    def _on_open_folder(self) -> None:
        if self._current_job and self._current_job.download_path:
            folder = os.path.dirname(os.path.abspath(self._current_job.download_path))
            try:
                os.startfile(folder)
            except Exception:
                subprocess.run(["explorer", folder])

    def _on_run_local_benchmark(self) -> None:
        if not self._current_job:
            return

        self._local_bench_btn.setEnabled(False)
        self._status_label.setText("Running local CPU FFmpeg encode benchmark (libx264)... please wait.")

        self._benchmark_thread = LocalBenchmarkThread(
            file_path=self._current_job.file_path,
            codec=self._current_job.codec,
            resolution=self._current_job.resolution,
            bitrate=self._current_job.bitrate,
        )
        self._benchmark_thread.completed.connect(self._on_local_benchmark_done)
        self._benchmark_thread.failed.connect(self._on_local_benchmark_failed)
        self._benchmark_thread.start()

    def _on_local_benchmark_done(self, local_time: float) -> None:
        if self._current_job:
            self._current_job.local_encode_time = local_time
            self.show_results(self._current_job)

        self._local_bench_btn.setEnabled(True)
        self._status_label.setText(f"Local benchmark complete: {local_time:.2f}s")

    def _on_local_benchmark_failed(self, error: str) -> None:
        self._local_bench_btn.setEnabled(True)
        self._status_label.setText(f"Local benchmark failed: {error}")
        QMessageBox.warning(self, "Benchmark Warning", f"Local FFmpeg benchmark could not complete:\n{error}")

    def _on_export(self) -> None:
        if not self._current_job:
            return

        job = self._current_job
        record = create_benchmark_record(
            test_id=job.job_id,
            input_path=job.file_path,
            resolution=job.resolution,
            duration_seconds=job.duration_seconds,
            local_time=job.local_encode_time,
            upload_time=job.upload_time,
            gpu_time=job.gpu_processing_time,
            download_time=job.download_time,
        )
        self._benchmark_records.append(record)

        default_dir = os.path.abspath("benchmarks/results")
        os.makedirs(default_dir, exist_ok=True)

        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory to Save Benchmark Dataset", default_dir
        )
        if not dir_path:
            return

        try:
            json_path = export_benchmarks(self._benchmark_records, dir_path, "json")
            csv_path = export_benchmarks(self._benchmark_records, dir_path, "csv")
            self._status_label.setText(f"Exported successfully to {dir_path}")
            QMessageBox.information(
                self,
                "Export Complete",
                f"Benchmark report data successfully exported:\n\n• JSON: {json_path}\n• CSV: {csv_path}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", str(exc))
