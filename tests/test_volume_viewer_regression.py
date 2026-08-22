from pathlib import Path

from tiff_to_powerpoint.analysis import analyse_scan
from tiff_to_powerpoint.scanner import scan_folder


def test_three_normal_and_volume_viewer_files_form_three_pairs_without_conflicts(tmp_path: Path):
    filenames = [
        "G6_1H_1.tif",
        "G6_1H_Volume_Viewer_1.tif",
        "G6_1H_2.tif",
        "G6_1H_Volume_Viewer_2.tif",
        "G6_1H_3.tif",
        "G6_1H_Volume_Viewer_3.tif",
    ]
    for filename in filenames:
        (tmp_path / filename).touch()

    analysis = analyse_scan(scan_folder(tmp_path))

    assert len(analysis.scan.files_found) == 6
    assert len(analysis.scan.parsed_images) == 6
    assert not analysis.scan.parse_failures
    assert not analysis.duplicate_conflicts
    assert analysis.pairing is not None
    assert len(analysis.pairing.pairs) == 3
    assert [pair.key.sub_component for pair in analysis.pairing.pairs] == [1, 2, 3]
    assert all(pair.normal_image is not None for pair in analysis.pairing.pairs)
    assert all(pair.volume_viewer_image is not None for pair in analysis.pairing.pairs)

