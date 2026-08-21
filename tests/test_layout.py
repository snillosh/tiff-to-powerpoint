import pytest

from tiff_to_powerpoint.errors import LayoutValidationError
from tiff_to_powerpoint.layout import ImageGeometry, LayoutItem, LayoutSettings, calculate_slide_layout


def geometry(name: str, width: int = 200, height: int = 100) -> ImageGeometry:
    return ImageGeometry(name, width, height)


def test_columns_and_final_slide_are_centred():
    settings = LayoutSettings(image_width_cm=5.0, horizontal_gap_cm=0.5)
    items = tuple(LayoutItem(str(number), geometry(f"n{number}"), geometry(f"v{number}")) for number in range(2))
    layout = calculate_slide_layout(items, settings)

    occupied = 2 * 5.0 + 0.5
    usable = settings.slide_width_cm - settings.left_margin_cm - settings.right_margin_cm
    expected_start = settings.left_margin_cm + (usable - occupied) / 2
    assert layout.columns[0].x_cm == pytest.approx(expected_start)
    assert layout.columns[1].x_cm == pytest.approx(expected_start + 5.5)


def test_aspect_ratio_calculates_height_without_distortion():
    item = LayoutItem("1", geometry("normal", 400, 100), geometry("vv", 100, 300))
    layout = calculate_slide_layout((item,), LayoutSettings(image_width_cm=4.0))
    normal, volume = layout.images

    assert normal.height_cm == pytest.approx(1.0)
    assert volume.height_cm == pytest.approx(12.0)
    assert normal.width_cm == volume.width_cm == 4.0


def test_bottom_row_uses_tallest_normal_height_for_every_column():
    items = (
        LayoutItem("1", geometry("short", 200, 100), geometry("v1")),
        LayoutItem("2", geometry("tall", 100, 100), geometry("v2")),
    )
    settings = LayoutSettings(image_width_cm=4.0, vertical_gap_cm=0.4)
    layout = calculate_slide_layout(items, settings)
    volumes = [position for position in layout.images if position.slot == "volume_viewer"]

    assert layout.normal_row_height_cm == pytest.approx(4.0)
    assert all(position.y_cm == pytest.approx(layout.normal_row_y_cm + 4.4) for position in volumes)


def test_missing_normal_preserves_blank_top_slot():
    layout = calculate_slide_layout(
        (LayoutItem("1", None, geometry("vv", 200, 100)),),
        LayoutSettings(image_width_cm=4.0, vertical_gap_cm=0.4),
    )
    volume = layout.images[0]

    assert volume.slot == "volume_viewer"
    assert layout.normal_row_height_cm == pytest.approx(2.0)
    assert volume.y_cm == pytest.approx(layout.normal_row_y_cm + 2.4)


def test_horizontal_overflow_is_rejected_not_resized():
    items = tuple(LayoutItem(str(index), geometry(str(index)), None) for index in range(5))
    with pytest.raises(LayoutValidationError, match="5 columns require"):
        calculate_slide_layout(items, LayoutSettings(image_width_cm=7.0, horizontal_gap_cm=0.5))


def test_vertical_overflow_identifies_problem_image():
    item = LayoutItem("1", geometry("very-tall.tif", 100, 1000), None)
    with pytest.raises(LayoutValidationError, match="very-tall.tif") as captured:
        calculate_slide_layout((item,), LayoutSettings(image_width_cm=5.0))
    assert "available" in str(captured.value)
    assert "Reduce the image width" in str(captured.value)

