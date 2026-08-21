from pathlib import Path

import pytest

from tiff_to_powerpoint.errors import DuplicateImageError
from tiff_to_powerpoint.models import ParsedImage
from tiff_to_powerpoint.pairing import pair_images, paginate_pairs
from tiff_to_powerpoint.sorting import natural_sorted


def image(name: str, primary: str, sub: int, colour: str | None = None, vv: bool = False) -> ParsedImage:
    return ParsedImage(Path(name), name, primary, sub, colour, vv)


def test_natural_sorting():
    values = ["E10", "A10", "B8", "A2", "E9", "A1", "B1", "E6"]
    assert natural_sorted(values) == ["A1", "A2", "A10", "B1", "B8", "E6", "E9", "E10"]


def test_pairing_uses_primary_subcomponent_and_colour():
    result = pair_images(
        [
            image("blue-normal.tif", "E8", 1, "Blue"),
            image("blue-vv.tif", "E8", 1, "Blue", True),
            image("red-normal.tif", "E8", 1, "Red"),
            image("red-vv.tif", "E8", 1, "Red", True),
            image("colourless.tif", "E8", 1),
        ]
    )

    assert len(result.pairs) == 3
    assert [pair.key.colour for pair in result.pairs] == [None, "Blue", "Red"]
    assert result.pairs[1].is_matched
    assert len(result.unmatched_normals) == 1


def test_missing_normal_is_retained():
    result = pair_images([image("vv-only.tif", "E9", 2, vv=True)])
    assert result.pairs[0].normal_image is None
    assert result.pairs[0].volume_viewer_image is not None
    assert len(result.unmatched_volume_viewers) == 1


def test_duplicate_slot_fails_with_both_filenames():
    first = image("first.tif", "E9", 1)
    second = image("second.tif", "E9", 1)

    with pytest.raises(DuplicateImageError) as captured:
        pair_images([first, second])

    message = str(captured.value)
    assert "first.tif" in message
    assert "second.tif" in message


def test_pagination_occurs_after_numeric_sorting_and_never_mixes_primaries():
    images = [image(f"E9_{sub}.tif", "E9", sub) for sub in [12, 2, 1, 11, 3, 10, 4, 9, 8, 7, 6, 5]]
    images.extend(image(f"E8_{sub}.tif", "E8", sub) for sub in [3, 1, 2])
    groups = paginate_pairs(pair_images(images), 5)

    assert len(groups) == 4
    assert [group.primary for group in groups] == ["E8", "E9", "E9", "E9"]
    assert [[pair.key.sub_component for pair in group.items] for group in groups] == [
        [1, 2, 3],
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10],
        [11, 12],
    ]
    assert [(group.page_number, group.total_pages) for group in groups[1:]] == [(1, 3), (2, 3), (3, 3)]


def test_max_columns_must_be_positive():
    with pytest.raises(ValueError):
        paginate_pairs(pair_images([image("E1_1.tif", "E1", 1)]), 0)

