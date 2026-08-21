"""Small reusable Qt thread-pool adapter for long-running operations."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progress = Signal(int, int, str)
    result = Signal(object)
    error = Signal(str, str)
    finished = Signal()


class FunctionWorker(QRunnable):
    """Run ``function(progress_callback)`` in a QThreadPool."""

    def __init__(self, function: Callable[[Callable[[int, int, str], None]], Any]) -> None:
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            result = self.function(self.signals.progress.emit)
        except Exception as exc:  # The main thread presents and logs full details.
            self.signals.error.emit(str(exc), traceback.format_exc())
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

