"""Application log setup for source and packaged execution."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def application_data_directory() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "TIFFToPowerPoint"


def configure_logging() -> Path:
    log_directory = application_data_directory() / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / "application.log"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    logging.getLogger(__name__).info("Application logging started: %s", log_path)
    return log_path
