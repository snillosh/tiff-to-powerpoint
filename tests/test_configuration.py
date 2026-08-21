from pathlib import Path

import pytest

from tiff_to_powerpoint.configuration import validate_generation_config, validate_scan_settings
from tiff_to_powerpoint.errors import ConfigurationError
from tiff_to_powerpoint.models import AppConfig


def test_empty_root_and_delimiter_are_rejected():
    with pytest.raises(ConfigurationError, match="Choose a root"):
        validate_scan_settings("", "_")
    with pytest.raises(ConfigurationError, match="delimiter"):
        validate_scan_settings(Path.cwd(), "")


@pytest.mark.parametrize(
    ("width", "gap", "columns", "message"),
    [
        (0.0, 0.3, 5, "width"),
        (5.5, -0.1, 5, "gap"),
        (5.5, 0.3, 0, "columns"),
    ],
)
def test_invalid_numeric_generation_settings(tmp_path: Path, width, gap, columns, message):
    config = AppConfig(
        root_folder=tmp_path,
        image_width_cm=width,
        horizontal_gap_cm=gap,
        vertical_gap_cm=gap,
        max_columns_per_slide=columns,
        output_path=tmp_path / "output.pptx",
    )
    with pytest.raises(ConfigurationError, match=message):
        validate_generation_config(config)


def test_output_must_be_pptx(tmp_path: Path):
    config = AppConfig(root_folder=tmp_path, output_path=tmp_path / "output.pdf")
    with pytest.raises(ConfigurationError, match="must end in .pptx"):
        validate_generation_config(config)

