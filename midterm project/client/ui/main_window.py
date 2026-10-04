"""
Main Window — Tab-based shell containing all pages.

Orchestrates the job submission pipeline by wiring page signals
to worker threads and inter-page navigation.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from client.config import ClientConfig
from client.models.job import ClientJob
from client.ui.connection_page import ConnectionPage
from client.ui.job_page import JobPage
from client.ui.progress_page import ProgressPage
from client.ui.result_page import ResultPage
from client.workers.threads import JobSubmitThread


class MainWindow(QMainWindow):
    """Main application window with tabbed navigation."""

    def __init__(self, config: ClientConfig) -> None:
        super().__init__()
        self._config = config
        self._submit_thread: JobSubmitThread | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Distributed GPU Task Offloading — Client")
        self.setMinimumSize(720, 700)
        self.resize(840, 780)

        # Apply crisp modern Light theme
        from client.ui.theme import LIGHT_THEME_QSS
        self.setStyleSheet(LIGHT_THEME_QSS)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title_label = self._create_title()
        main_layout.addWidget(title_label)

        # Tab widget
        self._tabs = QTabWidget()

        self._connection_page = ConnectionPage(self._config)
        self._tabs.addTab(self._connection_page, "🔌 Connection")

        self._job_page = JobPage(self._config, on_submit=self._on_job_submit)
        self._tabs.addTab(self._job_page, "⚙ Job")

        self._progress_page = ProgressPage(on_cancel=self._on_cancel)
        self._tabs.addTab(self._progress_page, "📊 Progress")

        self._result_page = ResultPage(self._config)
        self._tabs.addTab(self._result_page, "📈 Results")

        main_layout.addWidget(self._tabs)

        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet("color: #64748B; font-weight: 500;")
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready — configure worker connection to begin")

    @staticmethod
    def _create_title() -> QWidget:
        from PyQt6.QtWidgets import QLabel
        label = QLabel("🖥️ Distributed GPU Task Offloading")
        label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        label.setStyleSheet("color: #3B5BFF; margin-bottom: 8px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    # ------------------------------------------------------------------
    # Job Pipeline
    # ------------------------------------------------------------------

    def _on_job_submit(self, job: ClientJob) -> None:
        """Called when the user clicks 'Start Remote Processing'."""
        self._job_page.set_submit_enabled(False)
        self._progress_page.reset()
        self._tabs.setCurrentWidget(self._progress_page)

        self._submit_thread = JobSubmitThread(self._config, job)
        self._submit_thread.stage_changed.connect(self._progress_page.set_stage)
        self._submit_thread.upload_progress.connect(self._progress_page.set_upload_progress)
        self._submit_thread.processing_progress.connect(self._progress_page.set_processing_progress)
        self._submit_thread.download_progress.connect(self._progress_page.set_download_progress)
        self._submit_thread.log_message.connect(self._progress_page.append_log)
        self._submit_thread.job_created.connect(
            lambda jid: self._status_bar.showMessage(f"Job {jid} created")
        )
        self._submit_thread.completed.connect(self._on_job_completed)
        self._submit_thread.failed.connect(self._on_job_failed)
        self._submit_thread.finished.connect(self._on_thread_finished)
        self._submit_thread.start()

    def _on_job_completed(self, job: ClientJob) -> None:
        self._progress_page.set_stage("✅ Job Completed!", 100)
        self._progress_page.set_cancel_enabled(False)
        self._progress_page.append_log("Job completed successfully!")

        self._result_page.show_results(job)
        self._tabs.setCurrentWidget(self._result_page)
        self._status_bar.showMessage(f"Job {job.job_id} completed — {job.remote_total_time:.1f}s remote")

    def _on_job_failed(self, error: str) -> None:
        self._progress_page.set_stage("❌ Job Failed")
        self._progress_page.append_log(f"ERROR: {error}")
        self._progress_page.set_cancel_enabled(False)
        self._status_bar.showMessage("Job failed")

        QMessageBox.critical(self, "Job Failed", error)

    def _on_thread_finished(self) -> None:
        self._job_page.set_submit_enabled(True)

    def _on_cancel(self) -> None:
        if self._submit_thread:
            self._submit_thread.cancel()
        self._status_bar.showMessage("Cancellation requested...")
