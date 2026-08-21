"""Domain models shared by scanning, pairing, layout, and presentation code."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal


ProgressCallback = Callable[[int, int, str], None]


@dataclass(frozen=True, slots=True)
class ParsedImage:
    file_path: Path
    file_name: str
    primary: str
    sub_component: int
    colour: str | None
    is_volume_viewer: bool


@dataclass(frozen=True, slots=True)
class ParseFailure:
    file_path: Path
    reason: str


@dataclass(frozen=True, slots=True)
class ScanResult:
    files_found: tuple[Path, ...]
    parsed_images: tuple[ParsedImage, ...]
    parse_failures: tuple[ParseFailure, ...]
    traversal_errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PairKey:
    primary: str
    sub_component: int
    colour: str | None

    @property
    def display_label(self) -> str:
        return str(self.sub_component) if self.colour is None else f"{self.sub_component} - {self.colour}"


@dataclass(frozen=True, slots=True)
class ImagePair:
    key: PairKey
    normal_image: ParsedImage | None
    volume_viewer_image: ParsedImage | None

    @property
    def is_matched(self) -> bool:
        return self.normal_image is not None and self.volume_viewer_image is not None


@dataclass(frozen=True, slots=True)
class DuplicateConflict:
    key: PairKey
    slot: Literal["normal", "volume_viewer"]
    images: tuple[ParsedImage, ...]

    @property
    def slot_label(self) -> str:
        return "Volume Viewer" if self.slot == "volume_viewer" else "normal"


@dataclass(frozen=True, slots=True)
class PairingResult:
    pairs: tuple[ImagePair, ...]

    @property
    def unmatched_normals(self) -> tuple[ImagePair, ...]:
        return tuple(pair for pair in self.pairs if pair.normal_image is not None and pair.volume_viewer_image is None)

    @property
    def unmatched_volume_viewers(self) -> tuple[ImagePair, ...]:
        return tuple(pair for pair in self.pairs if pair.normal_image is None and pair.volume_viewer_image is not None)

    @property
    def primary_count(self) -> int:
        return len({pair.key.primary for pair in self.pairs})


@dataclass(frozen=True, slots=True)
class SlideGroup:
    primary: str
    items: tuple[ImagePair, ...]
    page_number: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class AppConfig:
    root_folder: Path
    delimiter: str = "_"
    image_width_cm: float = 5.5
    horizontal_gap_cm: float = 0.3
    vertical_gap_cm: float = 0.3
    max_columns_per_slide: int = 5
    output_path: Path | None = None
    show_labels: bool = True


@dataclass(frozen=True, slots=True)
class GenerationResult:
    output_path: Path
    slide_count: int
    converted_image_count: int

