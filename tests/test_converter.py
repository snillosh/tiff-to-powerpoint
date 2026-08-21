from pathlib import Path

from PIL import Image

from tiff_to_powerpoint.converter import TiffConverter


def test_converter_uses_first_frame_caches_result_and_does_not_modify_source(tmp_path: Path):
    source = tmp_path / "E8_1.tif"
    first = Image.new("RGB", (40, 20), (255, 0, 0))
    second = Image.new("RGB", (10, 30), (0, 0, 255))
    first.save(source, format="TIFF", save_all=True, append_images=[second])
    original_bytes = source.read_bytes()
    converted_directory = tmp_path / "converted"
    converted_directory.mkdir()
    converter = TiffConverter(converted_directory)

    converted = converter.convert(source)
    cached = converter.convert(source)

    assert converted == cached
    assert converter.conversion_count == 1
    assert (converted.pixel_width, converted.pixel_height) == (40, 20)
    with Image.open(converted.png_path) as png:
        assert png.size == (40, 20)
        assert png.getpixel((0, 0))[:3] == (255, 0, 0)
    assert source.read_bytes() == original_bytes

