"""Recursive TIFF discovery and filename parsing."""

from __future__ import annotations

import os
import logging
from pathlib import Path

from tiff_to_powerpoint.errors import FilenameParseError
from tiff_to_powerpoint.models import ParseFailure, ProgressCallback, ScanResult
from tiff_to_powerpoint.parser import parse_tiff_filename
from tiff_to_powerpoint.sorting import natural_sort_key


LOGGER = logging.getLogger(__name__)


def scan_folder(root_folder: str | Path, delimiter: str = "_", progress: ProgressCallback | None = None) -> ScanResult:
    root = Path(root_folder)
    LOGGER.info("Scanning TIFF files recursively under %s", root)
    traversal_errors: list[str] = []

    def record_walk_error(error: OSError) -> None:
        traversal_errors.append(str(error))

    files: list[Path] = []
    for directory, _, names in os.walk(root, onerror=record_walk_error, followlinks=False):
        for name in names:
            path = Path(directory) / name
            if path.suffix.casefold() == ".tif":
                files.append(path)
    files.sort(key=lambda path: natural_sort_key(str(path.relative_to(root))))

    parsed = []
    failures = []
    total = len(files)
    for index, path in enumerate(files, start=1):
        if progress is not None:
            progress(index, total, f"Parsing {path.name}")
        try:
            parsed.append(parse_tiff_filename(path, delimiter))
        except FilenameParseError as exc:
            LOGGER.warning("Skipping unparseable TIFF %s: %s", path, exc)
            failures.append(ParseFailure(path, str(exc)))

    result = ScanResult(tuple(files), tuple(parsed), tuple(failures), tuple(traversal_errors))
    LOGGER.info(
        "Scan complete: %d found, %d parsed, %d skipped, %d traversal warnings",
        len(result.files_found),
        len(result.parsed_images),
        len(result.parse_failures),
        len(result.traversal_errors),
    )
    return result
