"""
Client entry point — launches the PyQt6 desktop application.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when invoked directly as `python client/main.py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication

from client.config import load_config
from client.ui.main_window import MainWindow


def main() -> None:
    """Launch the Distributed GPU Task Offloading client."""
    app = QApplication(sys.argv)
    app.setApplicationName("GPU Task Offloading Client")
    app.setStyle("Fusion")

    config = load_config()
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
