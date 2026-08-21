"""Validation of user-controlled application settings."""

from __future__ import annotations

import os
from pathlib import Path

from tiff_to_powerpoint.errors import ConfigurationError
from tiff_to_powerpoint.models import AppConfig


def validate_scan_settings(root_folder: str | Path, delimiter: str) -> None:
    root = Path(root_folder)
    if not str(root_folder).strip():
        raise ConfigurationError("Choose a root image folder.")
    if not root.exists():
        raise ConfigurationError(f"Root image folder does not exist: {root}")
    if not root.is_dir():
        raise ConfigurationError(f"Root image folder is not a directory: {root}")
    if not delimiter:
        raise ConfigurationError("Filename delimiter cannot be empty.")


def validate_generation_config(config: AppConfig) -> None:
    validate_scan_settings(config.root_folder, config.delimiter)
    if config.image_width_cm <= 0:
        raise ConfigurationError("Image width must be greater than zero.")
    if config.horizontal_gap_cm < 0 or config.vertical_gap_cm < 0:
        raise ConfigurationError("Image gap cannot be negative.")
    if not isinstance(config.max_columns_per_slide, int) or config.max_columns_per_slide <= 0:
        raise ConfigurationError("Max columns per slide must be a whole number greater than zero.")
    if config.output_path is None or not str(config.output_path).strip():
        raise ConfigurationError("Choose an output PowerPoint file.")
    output = config.output_path
    if output.suffix.casefold() != ".pptx":
        raise ConfigurationError("Output PowerPoint path must end in .pptx.")
    parent = output.parent
    if not parent.exists() or not parent.is_dir():
        raise ConfigurationError(f"Output folder does not exist: {parent}")
    if output.exists() and not output.is_file():
        raise ConfigurationError(f"Output path is not a file: {output}")
    target_for_access = output if output.exists() else parent
    if not os.access(target_for_access, os.W_OK):
        raise ConfigurationError(f"Output location is not writable: {target_for_access}")

