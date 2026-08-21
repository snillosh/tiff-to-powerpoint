"""Logical image pairing, duplicate validation, and slide pagination."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
import logging

from tiff_to_powerpoint.errors import DuplicateImageError
from tiff_to_powerpoint.models import (
    DuplicateConflict,
    ImagePair,
    PairingResult,
    PairKey,
    ParsedImage,
    SlideGroup,
)
from tiff_to_powerpoint.sorting import natural_sort_key


LOGGER = logging.getLogger(__name__)


def detect_duplicate_conflicts(images: Iterable[ParsedImage]) -> tuple[DuplicateConflict, ...]:
    slots: dict[tuple[PairKey, bool], list[ParsedImage]] = defaultdict(list)
    for image in images:
        key = PairKey(image.primary, image.sub_component, image.colour)
        slots[(key, image.is_volume_viewer)].append(image)

    conflicts = [
        DuplicateConflict(key, "volume_viewer" if is_vv else "normal", tuple(slot_images))
        for (key, is_vv), slot_images in slots.items()
        if len(slot_images) > 1
    ]
    return tuple(sorted(conflicts, key=lambda conflict: _pair_key_sort_key(conflict.key)))


def pair_images(images: Iterable[ParsedImage]) -> PairingResult:
    image_list = tuple(images)
    conflicts = detect_duplicate_conflicts(image_list)
    if conflicts:
        LOGGER.error("Pairing stopped because %d duplicate logical slots were found", len(conflicts))
        raise DuplicateImageError(conflicts)

    slots: dict[PairKey, dict[bool, ParsedImage]] = defaultdict(dict)
    for image in image_list:
        key = PairKey(image.primary, image.sub_component, image.colour)
        slots[key][image.is_volume_viewer] = image

    pairs = [
        ImagePair(key, normal_image=slot.get(False), volume_viewer_image=slot.get(True))
        for key, slot in slots.items()
    ]
    pairs.sort(key=lambda pair: _pair_key_sort_key(pair.key))
    result = PairingResult(tuple(pairs))
    LOGGER.info(
        "Paired %d logical columns across %d primaries (%d missing Volume Viewer, %d missing normal)",
        len(result.pairs),
        result.primary_count,
        len(result.unmatched_normals),
        len(result.unmatched_volume_viewers),
    )
    return result


def paginate_pairs(pairing: PairingResult, max_columns: int) -> tuple[SlideGroup, ...]:
    if max_columns <= 0:
        raise ValueError("max_columns must be greater than zero")

    by_primary: dict[str, list[ImagePair]] = defaultdict(list)
    for pair in pairing.pairs:
        by_primary[pair.key.primary].append(pair)

    groups: list[SlideGroup] = []
    for primary in sorted(by_primary, key=natural_sort_key):
        items = sorted(by_primary[primary], key=lambda pair: _within_primary_sort_key(pair.key))
        chunks = [items[index : index + max_columns] for index in range(0, len(items), max_columns)]
        for page_index, chunk in enumerate(chunks, start=1):
            groups.append(SlideGroup(primary, tuple(chunk), page_index, len(chunks)))
    return tuple(groups)


def _within_primary_sort_key(key: PairKey) -> tuple[object, ...]:
    # Colourless entries are deliberately first for a stable, documented order.
    colour_key = (0, ()) if key.colour is None else (1, natural_sort_key(key.colour))
    return key.sub_component, colour_key


def _pair_key_sort_key(key: PairKey) -> tuple[object, ...]:
    return natural_sort_key(key.primary), _within_primary_sort_key(key)
