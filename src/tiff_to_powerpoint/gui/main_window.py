"""Main application window and scan/generate workflow."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThreadPool
from PySide6.QtGui import QCloseEvent, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tiff_to_powerpoint.analysis import ScanAnalysis, analyse_scan, pair_statuses
from tiff_to_powerpoint.configuration import validate_generation_config, validate_scan_settings
from tiff_to_powerpoint.errors import ConfigurationError
from tiff_to_powerpoint.generator import generate_presentation
from tiff_to_powerpoint.gui.workers import FunctionWorker
from tiff_to_powerpoint.models import AppConfig, GenerationResult
from tiff_to_powerpoint.scanner import scan_folder


LOGGER = logging.getLogger(__name__)
TABLE_HEADERS = ("Filename", "Primary", "Sub-component", "Colour", "Type", "Pair status")


class MainWindow(QMainWindow):
    def __init__(self, log_path: Path) -> None:
        super().__init__()
        self._log_path = log_path
        self._thread_pool = QThreadPool.globalInstance()
        self._analysis: ScanAnalysis | None = None
        self._scan_signature: tuple[str, str] | None = None
        self._busy = False
        self._operation_failed = False
        self._worker: FunctionWorker | None = None
        self._settings = QSettings("TIFFToPowerPoint", "TIFFToPowerPoint")

        self.setWindowTitle("TIFF to PowerPoint Generator")
        self.setMinimumSize(980, 700)
        self.resize(1200, 820)
        self._build_ui()
        self._restore_settings()
        self._append_status(f"Ready. Developer log: {self._log_path}")

    def _build_ui(self) -> None:
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)
        self.setCentralWidget(central)

        heading = QLabel("TIFF to PowerPoint Generator")
        heading.setStyleSheet("font-size: 20px; font-weight: 600;")
        root_layout.addWidget(heading)

        settings_group = QGroupBox("Input and layout")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setColumnStretch(1, 1)

        self.root_edit = QLineEdit()
        self.root_edit.setPlaceholderText("Choose the folder containing TIFF images")
        self.root_browse_button = QPushButton("Browse...")
        self.root_browse_button.clicked.connect(self._browse_root)
        settings_layout.addWidget(QLabel("Root image folder"), 0, 0)
        settings_layout.addWidget(self.root_edit, 0, 1)
        settings_layout.addWidget(self.root_browse_button, 0, 2)

        self.delimiter_edit = QLineEdit("_")
        self.delimiter_edit.setMaximumWidth(120)
        settings_layout.addWidget(QLabel("Filename delimiter"), 1, 0)
        settings_layout.addWidget(self.delimiter_edit, 1, 1)

        self.image_width_spin = QDoubleSpinBox()
        self.image_width_spin.setRange(0.01, 100.0)
        self.image_width_spin.setDecimals(2)
        self.image_width_spin.setSingleStep(0.1)
        self.image_width_spin.setValue(5.5)
        self.image_width_spin.setSuffix(" cm")
        settings_layout.addWidget(QLabel("Image width (cm)"), 2, 0)
        settings_layout.addWidget(self.image_width_spin, 2, 1)

        self.gap_spin = QDoubleSpinBox()
        self.gap_spin.setRange(0.0, 100.0)
        self.gap_spin.setDecimals(2)
        self.gap_spin.setSingleStep(0.1)
        self.gap_spin.setValue(0.3)
        self.gap_spin.setSuffix(" cm")
        self.gap_spin.setToolTip("Used for both horizontal column spacing and vertical row spacing")
        settings_layout.addWidget(QLabel("Image gap (cm)"), 3, 0)
        settings_layout.addWidget(self.gap_spin, 3, 1)

        self.max_columns_spin = QSpinBox()
        self.max_columns_spin.setRange(1, 100)
        self.max_columns_spin.setValue(5)
        settings_layout.addWidget(QLabel("Max columns per slide"), 4, 0)
        settings_layout.addWidget(self.max_columns_spin, 4, 1)

        self.labels_check = QCheckBox("Show image labels")
        self.labels_check.setChecked(True)
        settings_layout.addWidget(self.labels_check, 5, 1)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Choose the destination .pptx file")
        self.output_browse_button = QPushButton("Browse...")
        self.output_browse_button.clicked.connect(self._browse_output)
        settings_layout.addWidget(QLabel("Output PowerPoint"), 6, 0)
        settings_layout.addWidget(self.output_edit, 6, 1)
        settings_layout.addWidget(self.output_browse_button, 6, 2)
        root_layout.addWidget(settings_group)

        button_row = QHBoxLayout()
        self.scan_button = QPushButton("Scan Images")
        self.scan_button.clicked.connect(self._start_scan)
        self.generate_button = QPushButton("Generate PowerPoint")
        self.generate_button.clicked.connect(self._start_generation)
        self.generate_button.setEnabled(False)
        button_row.addWidget(self.scan_button)
        button_row.addWidget(self.generate_button)
        button_row.addStretch(1)
        root_layout.addLayout(button_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(QLabel("Scan results"))
        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(TABLE_HEADERS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_container)

        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_label = QLabel("No scan has been run.")
        self.summary_label.setWordWrap(True)
        status_layout.addWidget(self.summary_label)
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setMaximumHeight(170)
        status_layout.addWidget(self.status_log)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)
        splitter.addWidget(status_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, 1)

        self.root_edit.textChanged.connect(self._mark_scan_stale)
        self.delimiter_edit.textChanged.connect(self._mark_scan_stale)

    def _browse_root(self) -> None:
        initial = self.root_edit.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Choose root image folder", initial)
        if selected:
            self.root_edit.setText(selected)
            if not self.output_edit.text().strip():
                self.output_edit.setText(str(Path(selected) / "TIFF Presentation.pptx"))

    def _browse_output(self) -> None:
        initial = self.output_edit.text().strip()
        if not initial:
            root = self.root_edit.text().strip()
            initial = str(Path(root) / "TIFF Presentation.pptx") if root else str(Path.home() / "TIFF Presentation.pptx")
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Save PowerPoint presentation",
            initial,
            "PowerPoint presentation (*.pptx)",
        )
        if selected:
            path = Path(selected)
            if path.suffix.casefold() != ".pptx":
                path = path.with_suffix(".pptx")
            self.output_edit.setText(str(path))

    def _start_scan(self) -> None:
        try:
            root_text = self.root_edit.text().strip()
            delimiter = self.delimiter_edit.text()
            validate_scan_settings(root_text, delimiter)
        except ConfigurationError as exc:
            self._show_expected_error(str(exc))
            return
        root = Path(root_text)

        self._analysis = None
        self._scan_signature = None
        self.table.setRowCount(0)
        self.generate_button.setEnabled(False)
        self._append_status(f"Scanning {root} recursively...")
        self._set_busy(True)

        def task(progress):
            return analyse_scan(scan_folder(root, delimiter, progress))

        self._run_worker(task, self._scan_complete)

    def _scan_complete(self, analysis: ScanAnalysis) -> None:
        self._analysis = analysis
        root, delimiter = self._scan_values()
        self._scan_signature = (str(root.resolve()), delimiter)
        self._populate_table(analysis)

        scan = analysis.scan
        parsed_count = len(scan.parsed_images)
        failure_count = len(scan.parse_failures)
        if analysis.pairing is None:
            pair_text = "generation blocked by duplicate conflicts"
        else:
            pairing = analysis.pairing
            pair_text = (
                f"{len(pairing.pairs)} logical columns across {pairing.primary_count} primaries; "
                f"{len(pairing.unmatched_normals)} missing Volume Viewer; "
                f"{len(pairing.unmatched_volume_viewers)} missing normal"
            )
        summary = f"{len(scan.files_found)} TIFF files found; {parsed_count} parsed; {failure_count} skipped; {pair_text}."
        self.summary_label.setText(summary)
        self._append_status(summary)

        for failure in scan.parse_failures:
            self._append_status(f"Skipped {failure.file_path.name}: {failure.reason}", warning=True)
        for error in scan.traversal_errors:
            self._append_status(f"Folder access warning: {error}", warning=True)
        for conflict in analysis.duplicate_conflicts:
            names = ", ".join(image.file_name for image in conflict.images)
            self._append_status(
                f"Duplicate {conflict.slot_label} slot for {conflict.key.display_label} / {conflict.key.primary}: {names}",
                warning=True,
            )
        if analysis.pairing is not None:
            for pair in analysis.pairing.unmatched_normals:
                self._append_status(f"Missing Volume Viewer: {pair.normal_image.file_name}", warning=True)
            for pair in analysis.pairing.unmatched_volume_viewers:
                self._append_status(f"Missing normal image: {pair.volume_viewer_image.file_name}", warning=True)
        self.generate_button.setEnabled(analysis.can_generate and not self._busy)

    def _start_generation(self) -> None:
        if self._analysis is None or not self._analysis.can_generate or self._analysis.pairing is None:
            self._show_expected_error("Scan the image folder successfully before generating.")
            return
        root, delimiter = self._scan_values()
        signature = (str(root.resolve()), delimiter)
        if signature != self._scan_signature:
            self._show_expected_error("The root folder or filename delimiter changed. Scan the images again.")
            return

        output_text = self.output_edit.text().strip()
        if not output_text:
            self._show_expected_error("Choose an output PowerPoint file.")
            return
        config = AppConfig(
            root_folder=root,
            delimiter=delimiter,
            image_width_cm=self.image_width_spin.value(),
            horizontal_gap_cm=self.gap_spin.value(),
            vertical_gap_cm=self.gap_spin.value(),
            max_columns_per_slide=self.max_columns_spin.value(),
            output_path=Path(output_text),
            show_labels=self.labels_check.isChecked(),
        )
        try:
            validate_generation_config(config)
        except ConfigurationError as exc:
            self._show_expected_error(str(exc))
            return
        if config.output_path is not None and config.output_path.exists():
            answer = QMessageBox.question(
                self,
                "Replace existing presentation?",
                f"The output file already exists:\n{config.output_path}\n\nReplace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self._save_settings()
        self._append_status("Starting TIFF conversion and PowerPoint generation...")
        self._set_busy(True)
        pairing = self._analysis.pairing

        def task(progress):
            return generate_presentation(pairing, config, progress)

        self._run_worker(task, self._generation_complete)

    def _generation_complete(self, result: GenerationResult) -> None:
        message = (
            f"PowerPoint generated successfully: {result.slide_count} slides, "
            f"{result.converted_image_count} TIFF files converted.\n{result.output_path}"
        )
        self._append_status(message)
        QMessageBox.information(self, "Generation complete", message)

    def _run_worker(self, function, on_result) -> None:
        self._operation_failed = False
        worker = FunctionWorker(function)
        self._worker = worker
        worker.signals.progress.connect(self._update_progress)
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(self._worker_error)
        worker.signals.finished.connect(self._worker_finished)
        self._thread_pool.start(worker)

    def _worker_error(self, message: str, technical_detail: str) -> None:
        self._operation_failed = True
        LOGGER.error("Background operation failed: %s\n%s", message, technical_detail)
        self._append_status(f"Error: {message}", warning=True)
        QMessageBox.critical(
            self,
            "Operation failed",
            f"{message}\n\nTechnical details were written to:\n{self._log_path}",
        )

    def _worker_finished(self) -> None:
        self._set_busy(False)
        if not self._operation_failed:
            self.progress_bar.setValue(100)
        self._worker = None

    def _update_progress(self, current: int, total: int, message: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0 if total <= 0 else round(current * 100 / total))
        self.progress_bar.setFormat(f"%p% — {message}")

    def _populate_table(self, analysis: ScanAnalysis) -> None:
        statuses = pair_statuses(analysis)
        parsed = analysis.scan.parsed_images
        failures = analysis.scan.parse_failures
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(parsed) + len(failures))
        for row, image in enumerate(parsed):
            values = (
                image.file_name,
                image.primary,
                str(image.sub_component),
                image.colour or "",
                "Volume Viewer" if image.is_volume_viewer else "Normal",
                statuses.get(image.file_path, ""),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 2:
                    item.setData(Qt.ItemDataRole.UserRole, image.sub_component)
                self.table.setItem(row, column, item)
        start = len(parsed)
        for offset, failure in enumerate(failures):
            row = start + offset
            self.table.setItem(row, 0, QTableWidgetItem(failure.file_path.name))
            for column in range(1, 5):
                self.table.setItem(row, column, QTableWidgetItem(""))
            self.table.setItem(row, 5, QTableWidgetItem(f"Unparseable: {failure.reason}"))
        self.table.setSortingEnabled(True)

    def _scan_values(self) -> tuple[Path, str]:
        return Path(self.root_edit.text().strip()), self.delimiter_edit.text()

    def _mark_scan_stale(self) -> None:
        if self._analysis is not None:
            self._analysis = None
            self._scan_signature = None
            self.generate_button.setEnabled(False)
            self.summary_label.setText("Folder or delimiter changed; scan again to refresh the preview.")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.scan_button.setEnabled(not busy)
        self.generate_button.setEnabled(not busy and self._analysis is not None and self._analysis.can_generate)
        for widget in (
            self.root_edit,
            self.root_browse_button,
            self.delimiter_edit,
            self.image_width_spin,
            self.gap_spin,
            self.max_columns_spin,
            self.labels_check,
            self.output_edit,
            self.output_browse_button,
        ):
            widget.setEnabled(not busy)
        if busy:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("Working...")

    def _append_status(self, message: str, warning: bool = False) -> None:
        cursor = self.status_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if self.status_log.toPlainText():
            cursor.insertText("\n")
        cursor.insertText(message)
        self.status_log.setTextCursor(cursor)
        self.status_log.ensureCursorVisible()
        if warning:
            LOGGER.warning(message)
        else:
            LOGGER.info(message)

    def _show_expected_error(self, message: str) -> None:
        self._append_status(message, warning=True)
        QMessageBox.warning(self, "Check settings", message)

    def _restore_settings(self) -> None:
        self.root_edit.setText(str(self._settings.value("root_folder", "")))
        self.delimiter_edit.setText(str(self._settings.value("delimiter", "_")))
        self.image_width_spin.setValue(float(self._settings.value("image_width_cm", 5.5)))
        self.gap_spin.setValue(float(self._settings.value("gap_cm", 0.3)))
        self.max_columns_spin.setValue(int(self._settings.value("max_columns", 5)))
        self.labels_check.setChecked(str(self._settings.value("show_labels", "true")).casefold() == "true")
        self.output_edit.setText(str(self._settings.value("output_path", "")))

    def _save_settings(self) -> None:
        self._settings.setValue("root_folder", self.root_edit.text().strip())
        self._settings.setValue("delimiter", self.delimiter_edit.text())
        self._settings.setValue("image_width_cm", self.image_width_spin.value())
        self._settings.setValue("gap_cm", self.gap_spin.value())
        self._settings.setValue("max_columns", self.max_columns_spin.value())
        self._settings.setValue("show_labels", self.labels_check.isChecked())
        self._settings.setValue("output_path", self.output_edit.text().strip())
        self._settings.sync()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API name
        if self._busy:
            QMessageBox.information(self, "Operation in progress", "Wait for the current operation to finish before closing.")
            event.ignore()
            return
        self._save_settings()
        event.accept()
