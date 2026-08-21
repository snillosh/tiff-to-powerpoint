"""Expected application exceptions with user-facing messages."""

from __future__ import annotations

from pathlib import Path

from tiff_to_powerpoint.models import DuplicateConflict


class TiffToPowerPointError(Exception):
    """Base class for errors that can be shown directly to a user."""


class FilenameParseError(TiffToPowerPointError):
    """A filename does not contain unambiguous required metadata."""


class ConfigurationError(TiffToPowerPointError):
    """Application settings are invalid."""


class LayoutValidationError(TiffToPowerPointError):
    """The requested fixed-width layout cannot fit on the slide."""


class ImageConversionError(TiffToPowerPointError):
    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        super().__init__(f"Could not decode TIFF '{path.name}': {detail}")


class DuplicateImageError(TiffToPowerPointError):
    def __init__(self, conflicts: tuple[DuplicateConflict, ...]) -> None:
        self.conflicts = conflicts
        lines = ["Duplicate logical image slots were found:"]
        for conflict in conflicts:
            identity = f"{conflict.key.primary} / {conflict.key.sub_component} / {conflict.key.colour or 'no colour'}"
            files = ", ".join(image.file_name for image in conflict.images)
            lines.append(f"- {identity} ({conflict.slot_label}): {files}")
        lines.append("Resolve these conflicts and scan again before generating.")
        super().__init__("\n".join(lines))

