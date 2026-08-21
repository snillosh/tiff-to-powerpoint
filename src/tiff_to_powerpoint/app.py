"""GUI application entry point."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from tiff_to_powerpoint.gui.main_window import MainWindow
from tiff_to_powerpoint.logging_config import configure_logging


LOGGER = logging.getLogger(__name__)


def main() -> int:
    log_path = configure_logging()
    if "--self-test" in sys.argv[1:]:
        try:
            from tiff_to_powerpoint.self_test import run_packaged_self_test

            run_packaged_self_test()
        except Exception:
            LOGGER.exception("Packaged self-test failed")
            return 1
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("TIFF to PowerPoint")
    app.setOrganizationName("TIFFToPowerPoint")
    app.setStyle("Fusion")

    def handle_unexpected(exc_type, exc_value, exc_traceback) -> None:
        LOGGER.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        QMessageBox.critical(
            None,
            "Unexpected error",
            f"An unexpected error occurred: {exc_value}\n\nTechnical details were written to:\n{log_path}",
        )

    sys.excepthook = handle_unexpected
    window = MainWindow(log_path)
    window.show()
    LOGGER.info("Application started")
    return app.exec()
