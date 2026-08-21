"""Lossless temporary conversion of the first TIFF frame to PNG."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from tiff_to_powerpoint.errors import ImageConversionError


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConvertedImage:
    source_path: Path
    png_path: Path
    pixel_width: int
    pixel_height: int


class TiffConverter:
    """Convert each source at most once within a generation run."""

    def __init__(self, temporary_directory: Path) -> None:
        self._temporary_directory = temporary_directory
        self._cache: dict[Path, ConvertedImage] = {}

    def convert(self, source_path: str | Path) -> ConvertedImage:
        source = Path(source_path).resolve()
        cached = self._cache.get(source)
        if cached is not None:
            return cached

        digest = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:16]
        destination = self._temporary_directory / f"{digest}.png"
        LOGGER.debug("Converting TIFF %s to %s", source, destination)
        try:
            with Image.open(source) as opened:
                opened.seek(0)
                first_frame = ImageOps.exif_transpose(opened.copy())
                first_frame.load()
                output = _powerpoint_compatible_image(first_frame)
                save_options: dict[str, object] = {"format": "PNG", "compress_level": 6}
                dpi = opened.info.get("dpi")
                if isinstance(dpi, tuple) and len(dpi) == 2:
                    save_options["dpi"] = dpi
                output.save(destination, **save_options)
                width, height = output.size
                if output is not first_frame:
                    output.close()
                first_frame.close()
        except (UnidentifiedImageError, OSError, ValueError, EOFError) as exc:
            LOGGER.exception("TIFF conversion failed for %s", source)
            raise ImageConversionError(source, str(exc)) from exc

        converted = ConvertedImage(source, destination, width, height)
        self._cache[source] = converted
        return converted

    @property
    def conversion_count(self) -> int:
        return len(self._cache)


def _powerpoint_compatible_image(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"}:
        return image.convert("RGBA")
    if image.mode == "P" and "transparency" in image.info:
        return image.convert("RGBA")
    if image.mode == "RGB":
        return image
    return image.convert("RGB")

