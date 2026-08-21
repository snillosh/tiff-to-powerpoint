"""Scan analysis used by both the GUI preview and validation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tiff_to_powerpoint.models import DuplicateConflict, PairingResult, ScanResult
from tiff_to_powerpoint.pairing import detect_duplicate_conflicts, pair_images


@dataclass(frozen=True, slots=True)
class ScanAnalysis:
    scan: ScanResult
    pairing: PairingResult | None
    duplicate_conflicts: tuple[DuplicateConflict, ...]

    @property
    def can_generate(self) -> bool:
        return self.pairing is not None and bool(self.pairing.pairs) and not self.duplicate_conflicts


def analyse_scan(scan: ScanResult) -> ScanAnalysis:
    conflicts = detect_duplicate_conflicts(scan.parsed_images)
    pairing = None if conflicts else pair_images(scan.parsed_images)
    return ScanAnalysis(scan, pairing, conflicts)


def pair_statuses(analysis: ScanAnalysis) -> dict[Path, str]:
    statuses: dict[Path, str] = {}
    for conflict in analysis.duplicate_conflicts:
        for image in conflict.images:
            statuses[image.file_path] = "Duplicate/conflict"
    if analysis.pairing is None:
        return statuses

    for pair in analysis.pairing.pairs:
        if pair.is_matched:
            status = "Matched"
        elif pair.normal_image is None:
            status = "Missing normal"
        else:
            status = "Missing Volume Viewer"
        for image in (pair.normal_image, pair.volume_viewer_image):
            if image is not None:
                statuses[image.file_path] = status
    return statuses

