"""Explicit staged parsing for TIFF filename metadata."""

from __future__ import annotations

import re
from pathlib import Path

from tiff_to_powerpoint.colours import canonical_colour_name
from tiff_to_powerpoint.errors import FilenameParseError
from tiff_to_powerpoint.models import ParsedImage


PRIMARY_PATTERN = re.compile(r"[A-Z][0-9]+")
INTEGER_TOKEN_PATTERN = re.compile(r"[0-9]+")
VOLUME_MARKER_PARTS = ("Volume", "Viewer", "1")


def parse_tiff_filename(file_path: str | Path, delimiter: str = "_") -> ParsedImage:
    """Parse one TIFF filename without assuming fixed token positions.

    The Volume Viewer marker is removed before numeric-token analysis, preventing
    its trailing ``1`` from being interpreted as the sub-component.
    """

    path = Path(file_path)
    if not delimiter:
        raise FilenameParseError("Filename delimiter cannot be empty.")
    if path.suffix.casefold() != ".tif":
        raise FilenameParseError(f"'{path.name}' is not a .tif file.")

    raw_stem = path.stem
    stem, is_volume_viewer = _remove_volume_marker(raw_stem, delimiter)

    primary_matches = list(PRIMARY_PATTERN.finditer(stem))
    if not primary_matches:
        raise FilenameParseError(f"'{path.name}' does not contain a primary such as E6 or Z100.")
    if len(primary_matches) > 1:
        values = ", ".join(match.group(0) for match in primary_matches)
        raise FilenameParseError(f"'{path.name}' contains multiple possible primary values: {values}.")

    primary_match = primary_matches[0]
    tokens = [token.strip() for token in stem.split(delimiter) if token.strip()]
    numeric_tokens = [token for token in tokens if INTEGER_TOKEN_PATTERN.fullmatch(token)]
    if not numeric_tokens:
        raise FilenameParseError(
            f"'{path.name}' does not contain a standalone integer sub-component separated by '{delimiter}'."
        )
    if len(numeric_tokens) > 1:
        values = ", ".join(numeric_tokens)
        raise FilenameParseError(f"'{path.name}' contains ambiguous sub-component values: {values}.")

    colour = _detect_colour(stem, delimiter, primary_match)
    return ParsedImage(
        file_path=path,
        file_name=path.name,
        primary=primary_match.group(0),
        sub_component=int(numeric_tokens[0]),
        colour=colour,
        is_volume_viewer=is_volume_viewer,
    )


def _remove_volume_marker(stem: str, delimiter: str) -> tuple[str, bool]:
    configured_marker = delimiter.join(VOLUME_MARKER_PARTS)
    # Also accept the documented exact marker when a custom delimiter is in use.
    markers = tuple(dict.fromkeys((configured_marker, "Volume_Viewer_1")))
    found = False
    cleaned = stem
    for marker in markers:
        pattern = re.compile(re.escape(marker), re.IGNORECASE)
        if pattern.search(cleaned):
            found = True
            cleaned = pattern.sub("", cleaned)
    return cleaned, found


def _detect_colour(stem: str, delimiter: str, primary_match: re.Match[str]) -> str | None:
    candidates: list[str] = []

    # A colour can touch the primary, as in BlueE6 or E6Blue. Bound the adjacent
    # substring by the configured delimiter so colours are not found inside words.
    before = stem[: primary_match.start()]
    after = stem[primary_match.end() :]
    candidates.append(before.rsplit(delimiter, 1)[-1])
    candidates.append(after.split(delimiter, 1)[0])

    # Also inspect complete alphabetic tokens, supporting Sample_Blue_E8_1.
    candidates.extend(token for token in stem.split(delimiter) if token.isalpha())

    recognised: list[str] = []
    for candidate in candidates:
        canonical = canonical_colour_name(candidate.strip())
        if canonical is not None and canonical not in recognised:
            recognised.append(canonical)

    if len(recognised) > 1:
        raise FilenameParseError(
            f"Filename contains multiple recognised colours ({', '.join(recognised)}); colour is ambiguous."
        )
    return recognised[0] if recognised else None

