from pathlib import Path

import pytest

from tiff_to_powerpoint.errors import FilenameParseError
from tiff_to_powerpoint.parser import (
    contains_volume_viewer_sequence,
    find_first_standalone_integer,
    parse_tiff_filename,
)


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
        ("F10_30MIN_Volume_Viewer_1.tif", "F10", 1, None, True),
        ("G10_1H_3.tif", "G10", 3, None, False),
        ("G10_1H_Volume_Viewer_2.tif", "G10", 2, None, True),
        ("BlueE8_100_Volume_Viewer_1.tif", "E8", 100, "Blue", True),
        ("E8_30MIN_100.tif", "E8", 100, None, False),
        ("E8_1H_20MIN_7.tif", "E8", 7, None, False),
        ("E8_100_Test_200_Volume_Viewer_300.tif", "E8", 100, None, True),
        ("E8_1_Volume_Viewer.tif", "E8", 1, None, True),
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
    ("filename", "expected_sub_component", "expected_colour"),
    [
        ("G10-1H-Volume-Viewer-2.tif", 2, None),
        ("BlueE6-30MIN-1-Volume-Viewer-9.tif", 1, "Blue"),
    ],
)
def test_hyphen_delimiter_uses_first_integer_and_adjacent_volume_viewer_tokens(
    filename, expected_sub_component, expected_colour
):
    parsed = parse_tiff_filename(filename, "-")

    assert parsed.sub_component == expected_sub_component
    assert parsed.colour == expected_colour
    assert parsed.is_volume_viewer is True


def test_volume_viewer_detection_uses_only_the_configured_delimiter():
    parsed = parse_tiff_filename("G10-2-Volume_Viewer.tif", "-")

    assert parsed.sub_component == 2
    assert parsed.is_volume_viewer is False


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (["G10", "1H", "3"], 3),
        (["E8", "100", "Test", "200", "Volume", "Viewer", "300"], 100),
        (["E8", "30MIN", "1H", "H1", "ABC12", "12ABC"], None),
        (["E8", "001", "2"], 1),
    ],
)
def test_find_first_standalone_integer(tokens, expected):
    assert find_first_standalone_integer(tokens) == expected


def test_volume_viewer_helper_requires_adjacent_tokens_and_is_case_insensitive():
    assert contains_volume_viewer_sequence(["G10", "volume", "VIEWER", "2"])
    assert not contains_volume_viewer_sequence(["G10", "Volume", "Other", "Viewer", "2"])


@pytest.mark.parametrize(
    ("filename", "primary", "sub_component", "colour", "delimiter"),
    [
        ("G6_1H_Volume_Viewer_1.tif", "G6", 1, None, "_"),
        ("G6_1H_Volume_Viewer_2.tif", "G6", 2, None, "_"),
        ("G6_1H_Volume_Viewer_3.tif", "G6", 3, None, "_"),
        ("F6_30MIN_Volume_Viewer_1.tif", "F6", 1, None, "_"),
        ("F6_30MIN_Volume_Viewer_2.tif", "F6", 2, None, "_"),
        ("E6_Volume_Viewer_1.tif", "E6", 1, None, "_"),
        ("BlueE6_30MIN_1_Volume_Viewer_1.tif", "E6", 1, "Blue", "_"),
        ("BlueE6_30MIN_100_Volume_Viewer_1.tif", "E6", 100, "Blue", "_"),
        ("BlueE6_30MIN_1_Volume_Viewer_9.tif", "E6", 1, "Blue", "_"),
        ("G6-1H-Volume-Viewer-3.tif", "G6", 3, None, "-"),
    ],
)
def test_volume_viewer_type_is_independent_of_trailing_number(
    filename, primary, sub_component, colour, delimiter
):
    parsed = parse_tiff_filename(filename, delimiter)

    assert parsed.primary == primary
    assert parsed.sub_component == sub_component
    assert parsed.colour == colour
    assert parsed.is_volume_viewer is True


@pytest.mark.parametrize(
    "filename",
    [
        "no_primary_1.tif",
        "E8_no_subcomponent.tif",
        "E8_30MIN_Volume_Viewer.tif",
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


def test_first_numeric_token_wins_instead_of_being_ambiguous():
    parsed = parse_tiff_filename("E8_1_2.tif")
    assert parsed.sub_component == 1
