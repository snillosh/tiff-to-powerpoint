"""Deterministic natural sorting helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TypeVar


_T = TypeVar("_T")
_NATURAL_PARTS = re.compile(r"([0-9]+)")


def natural_sort_key(value: str) -> tuple[tuple[int, int | str], ...]:
    """Return a comparison-safe key where digit runs are compared numerically."""

    parts: list[tuple[int, int | str]] = []
    for part in _NATURAL_PARTS.split(value.casefold()):
        if not part:
            continue
        parts.append((0, int(part)) if part.isdigit() else (1, part))
    return tuple(parts)


def natural_sorted(values: Iterable[_T], key=lambda value: value) -> list[_T]:
    return sorted(values, key=lambda value: natural_sort_key(str(key(value))))

