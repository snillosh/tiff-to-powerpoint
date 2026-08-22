"""Explicit staged parsing for TIFF filename metadata."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from tiff_to_powerpoint.colours import canonical_colour_name
from tiff_to_powerpoint.errors import FilenameParseError
from tiff_to_powerpoint.models import ParsedImage


PRIMARY_PATTERN = re.compile(r"[A-Z][0-9]+")
INTEGER_TOKEN_PATTERN = re.compile(r"[0-9]+")
VOLUME_MARKER_PARTS = ("Volume", "Viewer")


def parse_tiff_filename(file_path: str | Path, delimiter: str = "_") -> ParsedImage:
    """Parse one TIFF filename without assuming fixed token positions.

    Volume Viewer status and sub-component selection are independent. The former
    comes from adjacent ``Volume``/``Viewer`` tokens; the latter is the first token
    in filename order consisting entirely of ASCII digits.
    """

    path = Path(file_path)
    if not delimiter:
        raise FilenameParseError("Filename delimiter cannot be empty.")
    if path.suffix.casefold() != ".tif":
        raise FilenameParseError(f"'{path.name}' is not a .tif file.")

    stem = path.stem
    tokens = stem.split(delimiter)
    is_volume_viewer = contains_volume_viewer_sequence(tokens)

    primary_matches = list(PRIMARY_PATTERN.finditer(stem))
    if not primary_matches:
        raise FilenameParseError(f"'{path.name}' does not contain a primary such as E6 or Z100.")
    if len(primary_matches) > 1:
        values = ", ".join(match.group(0) for match in primary_matches)
        raise FilenameParseError(f"'{path.name}' contains multiple possible primary values: {values}.")

    primary_match = primary_matches[0]
    sub_component = find_first_standalone_integer(tokens)
    if sub_component is None:
        raise FilenameParseError(
            f"'{path.name}' does not contain a standalone integer sub-component separated by '{delimiter}'."
        )

    colour = _detect_colour(stem, delimiter, primary_match)
    return ParsedImage(
        file_path=path,
        file_name=path.name,
        primary=primary_match.group(0),
        sub_component=sub_component,
        colour=colour,
        is_volume_viewer=is_volume_viewer,
    )


def find_first_standalone_integer(tokens: Sequence[str]) -> int | None:
    """Return the first token made entirely of ASCII digits, if one exists."""

    for token in tokens:
        if INTEGER_TOKEN_PATTERN.fullmatch(token):
            return int(token)
    return None


def contains_volume_viewer_sequence(tokens: Sequence[str]) -> bool:
    """Detect adjacent Volume/Viewer tokens using the parser's existing case-insensitivity."""

    expected_volume, expected_viewer = (part.casefold() for part in VOLUME_MARKER_PARTS)
    return any(
        first.casefold() == expected_volume and second.casefold() == expected_viewer
        for first, second in zip(tokens, tokens[1:])
    )


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
