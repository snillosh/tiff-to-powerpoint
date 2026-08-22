"""End-to-end diagnostic used to validate a packaged application."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PIL import Image
from pptx import Presentation

from tiff_to_powerpoint.generator import generate_presentation
from tiff_to_powerpoint.models import AppConfig
from tiff_to_powerpoint.pairing import pair_images
from tiff_to_powerpoint.scanner import scan_folder


LOGGER = logging.getLogger(__name__)


def run_packaged_self_test() -> None:
    """Exercise TIFF decoding and PowerPoint output without starting the GUI."""

    with tempfile.TemporaryDirectory(prefix="tiff-pptx-self-test-") as temporary:
        root = Path(temporary)
        normal = root / "G10_1H_2.tif"
        volume = root / "G10_1H_Volume_Viewer_2.tif"
        Image.new("RGB", (120, 60), (20, 80, 160)).save(normal, format="TIFF")
        Image.new("RGB", (120, 60), (160, 80, 20)).save(volume, format="TIFF")

        scan = scan_folder(root)
        if len(scan.parsed_images) != 2 or scan.parse_failures:
            raise RuntimeError("Packaged self-test could not scan and parse its sample TIFF files.")
        pairing = pair_images(scan.parsed_images)
        output = root / "self-test.pptx"
        result = generate_presentation(
            pairing,
            AppConfig(root_folder=root, image_width_cm=4.0, output_path=output),
        )
        if result.slide_count != 1 or not output.is_file():
            raise RuntimeError("Packaged self-test did not produce the expected presentation.")
        if len(Presentation(output).slides) != 1:
            raise RuntimeError("Packaged self-test could not reopen the generated presentation.")
        LOGGER.info("Packaged self-test completed successfully")
