"""Native, repeatable PyInstaller build for Linux, Windows, and macOS."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = PROJECT_ROOT / "build" / "TIFFToPowerPoint.spec"
BUILD_OUTPUT = PROJECT_ROOT / "build-output"
RELEASES = PROJECT_ROOT / "releases"


def canonical_platform(system: str | None = None) -> str:
    value = (system or platform.system()).casefold()
    aliases = {"linux": "linux", "windows": "windows", "darwin": "macos", "macos": "macos"}
    try:
        return aliases[value]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported build platform: {value}") from exc


def canonical_architecture(machine: str | None = None) -> str:
    value = (machine or platform.machine()).casefold()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    try:
        return aliases[value]
    except KeyError as exc:
        raise RuntimeError(
            f"Unsupported build architecture: {value}. Supported architectures are x86_64 and ARM64."
        ) from exc


def project_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def build(*, run_tests: bool = True, create_archive: bool = True) -> tuple[Path, Path | None]:
    target_platform = canonical_platform()
    target_arch = canonical_architecture()
    tag = f"{target_platform}-{target_arch}"
    dist_path = BUILD_OUTPUT / tag
    work_path = BUILD_OUTPUT / "work" / tag

    if run_tests:
        run([sys.executable, "-m", "pytest"])
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(dist_path),
            "--workpath",
            str(work_path),
            str(SPEC_PATH),
        ]
    )

    bundle = (
        dist_path / "TIFFToPowerPoint.app"
        if target_platform == "macos"
        else dist_path / "TIFFToPowerPoint"
    )
    executable = _packaged_executable(bundle, target_platform)
    if not executable.is_file():
        raise RuntimeError(f"Expected packaged executable was not created: {executable}")
    _run_packaged_self_test(executable)

    archive = _create_archive(bundle, tag) if create_archive else None
    print(f"Portable bundle: {bundle}")
    if archive is not None:
        print(f"Release archive: {archive}")
    return bundle, archive


def _packaged_executable(bundle: Path, target_platform: str) -> Path:
    if target_platform == "windows":
        return bundle / "TIFFToPowerPoint.exe"
    if target_platform == "macos":
        return bundle / "Contents" / "MacOS" / "TIFFToPowerPoint"
    return bundle / "TIFFToPowerPoint"


def _run_packaged_self_test(executable: Path) -> None:
    print(f"Running packaged self-test: {executable}", flush=True)
    with tempfile.TemporaryDirectory(prefix="tiff-pptx-package-test-") as temporary:
        environment = os.environ.copy()
        if canonical_platform() == "linux":
            environment["XDG_STATE_HOME"] = temporary
        subprocess.run(
            [str(executable), "--self-test"],
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
            timeout=60,
        )


def _create_archive(bundle: Path, tag: str) -> Path:
    RELEASES.mkdir(parents=True, exist_ok=True)
    artifact_base = RELEASES / f"TIFFToPowerPoint-{project_version()}-{tag}"
    archive_format = "zip" if canonical_platform() == "windows" else "gztar"
    archive = Path(
        shutil.make_archive(
            str(artifact_base),
            archive_format,
            root_dir=bundle.parent,
            base_dir=bundle.name,
        )
    )
    hasher = hashlib.sha256()
    with archive.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    checksum = archive.with_name(f"{archive.name}.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="Skip the source test suite before packaging")
    parser.add_argument("--no-archive", action="store_true", help="Leave the portable directory without an archive")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    build(run_tests=not arguments.skip_tests, create_archive=not arguments.no_archive)
