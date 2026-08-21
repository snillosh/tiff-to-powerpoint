"""Pure slide layout calculations and fixed-width overflow validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tiff_to_powerpoint.errors import LayoutValidationError


WIDESCREEN_WIDTH_CM = 33.8667
WIDESCREEN_HEIGHT_CM = 19.05


@dataclass(frozen=True, slots=True)
class LayoutSettings:
    slide_width_cm: float = WIDESCREEN_WIDTH_CM
    slide_height_cm: float = WIDESCREEN_HEIGHT_CM
    left_margin_cm: float = 0.7
    right_margin_cm: float = 0.7
    top_margin_cm: float = 0.45
    bottom_margin_cm: float = 0.5
    title_height_cm: float = 1.15
    label_height_cm: float = 0.6
    image_width_cm: float = 5.5
    horizontal_gap_cm: float = 0.3
    vertical_gap_cm: float = 0.3
    show_labels: bool = True


@dataclass(frozen=True, slots=True)
class ImageGeometry:
    source_label: str
    pixel_width: int
    pixel_height: int

    def rendered_height(self, target_width_cm: float) -> float:
        if self.pixel_width <= 0 or self.pixel_height <= 0:
            raise LayoutValidationError(f"Image '{self.source_label}' has invalid pixel dimensions.")
        return target_width_cm * self.pixel_height / self.pixel_width


@dataclass(frozen=True, slots=True)
class LayoutItem:
    label: str
    normal: ImageGeometry | None
    volume_viewer: ImageGeometry | None


@dataclass(frozen=True, slots=True)
class PositionedImage:
    column_index: int
    slot: Literal["normal", "volume_viewer"]
    source_label: str
    x_cm: float
    y_cm: float
    width_cm: float
    height_cm: float


@dataclass(frozen=True, slots=True)
class ColumnPosition:
    index: int
    label: str
    x_cm: float
    label_y_cm: float
    width_cm: float


@dataclass(frozen=True, slots=True)
class SlideLayout:
    columns: tuple[ColumnPosition, ...]
    images: tuple[PositionedImage, ...]
    title_x_cm: float
    title_y_cm: float
    title_width_cm: float
    title_height_cm: float
    normal_row_y_cm: float
    normal_row_height_cm: float
    volume_row_y_cm: float
    required_vertical_cm: float
    available_vertical_cm: float


def calculate_slide_layout(items: tuple[LayoutItem, ...], settings: LayoutSettings) -> SlideLayout:
    """Calculate positions without resizing, cropping, or touching source files."""

    count = len(items)
    if count <= 0:
        raise LayoutValidationError("Cannot calculate a slide layout with no columns.")
    if settings.image_width_cm <= 0:
        raise LayoutValidationError("Image width must be greater than zero.")
    if settings.horizontal_gap_cm < 0 or settings.vertical_gap_cm < 0:
        raise LayoutValidationError("Image gaps cannot be negative.")

    usable_width = settings.slide_width_cm - settings.left_margin_cm - settings.right_margin_cm
    occupied_width = count * settings.image_width_cm + (count - 1) * settings.horizontal_gap_cm
    if occupied_width > usable_width + 1e-9:
        raise LayoutValidationError(
            f"With an image width of {settings.image_width_cm:.2f} cm and a horizontal gap of "
            f"{settings.horizontal_gap_cm:.2f} cm, {count} columns require {occupied_width:.2f} cm "
            f"but only {usable_width:.2f} cm is available on the 16:9 slide. Reduce the image width, "
            "gap, or maximum columns per slide."
        )

    block_x = settings.left_margin_cm + (usable_width - occupied_width) / 2
    label_height = settings.label_height_cm if settings.show_labels else 0.0
    normal_y = settings.top_margin_cm + settings.title_height_cm + label_height

    normal_heights = [
        item.normal.rendered_height(settings.image_width_cm) if item.normal is not None else 0.0
        for item in items
    ]
    volume_heights = [
        item.volume_viewer.rendered_height(settings.image_width_cm) if item.volume_viewer is not None else 0.0
        for item in items
    ]
    max_normal_height = max(normal_heights, default=0.0)
    max_volume_height = max(volume_heights, default=0.0)
    has_volume_row = any(height > 0 for height in volume_heights)

    # When every normal is missing, reserve a real blank top slot instead of
    # moving Volume Viewer images into the normal row.
    normal_row_height = max_normal_height
    if normal_row_height == 0 and has_volume_row:
        normal_row_height = max_volume_height
    row_gap = settings.vertical_gap_cm if has_volume_row else 0.0
    volume_y = normal_y + normal_row_height + row_gap
    required_vertical = normal_row_height + row_gap + max_volume_height
    available_vertical = settings.slide_height_cm - settings.bottom_margin_cm - normal_y

    if required_vertical > available_vertical + 1e-9:
        tallest_normal = _tallest_source(items, normal_heights, "normal")
        tallest_volume = _tallest_source(items, volume_heights, "volume_viewer")
        contributors = ", ".join(name for name in (tallest_normal, tallest_volume) if name) or "unknown image"
        raise LayoutValidationError(
            f"The image rows for {contributors} require {required_vertical:.2f} cm of vertical space at "
            f"the configured width, but only {available_vertical:.2f} cm is available. Reduce the image width."
        )

    columns: list[ColumnPosition] = []
    positioned: list[PositionedImage] = []
    label_y = settings.top_margin_cm + settings.title_height_cm
    for index, item in enumerate(items):
        x = block_x + index * (settings.image_width_cm + settings.horizontal_gap_cm)
        columns.append(ColumnPosition(index, item.label, x, label_y, settings.image_width_cm))
        if item.normal is not None:
            positioned.append(
                PositionedImage(index, "normal", item.normal.source_label, x, normal_y, settings.image_width_cm, normal_heights[index])
            )
        if item.volume_viewer is not None:
            positioned.append(
                PositionedImage(
                    index,
                    "volume_viewer",
                    item.volume_viewer.source_label,
                    x,
                    volume_y,
                    settings.image_width_cm,
                    volume_heights[index],
                )
            )

    return SlideLayout(
        columns=tuple(columns),
        images=tuple(positioned),
        title_x_cm=settings.left_margin_cm,
        title_y_cm=settings.top_margin_cm,
        title_width_cm=usable_width,
        title_height_cm=settings.title_height_cm,
        normal_row_y_cm=normal_y,
        normal_row_height_cm=normal_row_height,
        volume_row_y_cm=volume_y,
        required_vertical_cm=required_vertical,
        available_vertical_cm=available_vertical,
    )


def _tallest_source(items: tuple[LayoutItem, ...], heights: list[float], slot: str) -> str | None:
    if not heights or max(heights, default=0.0) <= 0:
        return None
    index = max(range(len(heights)), key=heights.__getitem__)
    geometry = items[index].normal if slot == "normal" else items[index].volume_viewer
    if geometry is None:
        return None
    return f"'{geometry.source_label}' ({heights[index]:.2f} cm high)"

