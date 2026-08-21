from pathlib import Path

from tiff_to_powerpoint.scanner import scan_folder


def test_scanner_is_recursive_case_insensitive_and_skips_unrelated_files(tmp_path: Path):
    nested = tmp_path / "nested" / "deeper"
    nested.mkdir(parents=True)
    (tmp_path / "E8_1.tif").touch()
    (nested / "BlueE8_2.TIF").touch()
    (nested / "not-an-image.txt").touch()
    (nested / "invalid.tif").touch()

    result = scan_folder(tmp_path)

    assert len(result.files_found) == 3
    assert [(image.primary, image.sub_component) for image in result.parsed_images] == [("E8", 1), ("E8", 2)]
    assert len(result.parse_failures) == 1
    assert result.parse_failures[0].file_path.name == "invalid.tif"

