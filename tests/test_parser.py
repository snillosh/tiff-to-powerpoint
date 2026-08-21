from pathlib import Path

import pytest

from tiff_to_powerpoint.errors import FilenameParseError
from tiff_to_powerpoint.parser import parse_tiff_filename


@pytest.mark.parametrize(
    ("filename", "primary", "sub_component", "colour", "is_volume_viewer"),
    [
        ("B8_1.tif", "B8", 1, None, False),
        ("B8_1_Volume_Viewer_1.tif", "B8", 1, None, True),
        ("E6_30MIN_1.tif", "E6", 1, None, False),
        ("E6_30MIN_1_Volume_Viewer_1.tif", "E6", 1, None, True),
        ("BlueE6_30MIN_1.tif", "E6", 1, "Blue", False),
        ("BlueE6_30MIN_1_Volume_Viewer_1.tif", "E6", 1, "Blue", True),
        ("BlueE8_30MIN_100.tif", "E8", 100, "Blue", False),
        ("RedE8_30MIN_100_Volume_Viewer_1.tif", "E8", 100, "Red", True),
        ("Z100_11.tif", "Z100", 11, None, False),
        ("Sample_Blue_E8_100_processed.tif", "E8", 100, "Blue", False),
        ("unrelated_prefix_E8_2_rendered.TIF", "E8", 2, None, False),
        ("darkblueE8_3.tif", "E8", 3, "DarkBlue", False),
    ],
)
def test_filename_examples(filename, primary, sub_component, colour, is_volume_viewer):
    parsed = parse_tiff_filename(Path("somewhere") / filename)

    assert parsed.primary == primary
    assert parsed.sub_component == sub_component
    assert parsed.colour == colour
    assert parsed.is_volume_viewer is is_volume_viewer


def test_configurable_delimiter_is_literal_and_applies_to_volume_marker():
    parsed = parse_tiff_filename("BlueE8.30MIN.100.Volume.Viewer.1.tif", ".")

    assert parsed.primary == "E8"
    assert parsed.sub_component == 100
    assert parsed.colour == "Blue"
    assert parsed.is_volume_viewer is True


def test_hyphen_delimiter():
    parsed = parse_tiff_filename("Sample-Red-E8-12-Volume-Viewer-1.tif", "-")

    assert (parsed.primary, parsed.sub_component, parsed.colour, parsed.is_volume_viewer) == (
        "E8",
        12,
        "Red",
        True,
    )


@pytest.mark.parametrize(
    "filename",
    [
        "no_primary_1.tif",
        "E8_no_subcomponent.tif",
        "E8_1_2.tif",
        "E8_1.jpg",
        "E8_A1_1.tif",
    ],
)
def test_invalid_or_ambiguous_filename(filename):
    with pytest.raises(FilenameParseError):
        parse_tiff_filename(filename)


def test_empty_delimiter_is_invalid():
    with pytest.raises(FilenameParseError, match="cannot be empty"):
        parse_tiff_filename("E8_1.tif", "")


def test_arbitrary_text_is_not_a_colour():
    parsed = parse_tiff_filename("SampleE8_100.tif")
    assert parsed.colour is None


def test_multiple_recognised_colours_are_rejected_as_ambiguous():
    with pytest.raises(FilenameParseError, match="multiple recognised colours"):
        parse_tiff_filename("Blue_Red_E8_1.tif")

