import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location("portable_build", Path(__file__).parents[1] / "build" / "build.py")
assert SPEC is not None and SPEC.loader is not None
portable_build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(portable_build)


@pytest.mark.parametrize("value", ["x86_64", "AMD64", "x64"])
def test_x86_64_architecture_aliases(value):
    assert portable_build.canonical_architecture(value) == "x86_64"


@pytest.mark.parametrize("value", ["arm64", "aarch64"])
def test_arm64_architecture_aliases(value):
    assert portable_build.canonical_architecture(value) == "arm64"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Linux", "linux"), ("Windows", "windows"), ("Darwin", "macos"), ("macOS", "macos")],
)
def test_platform_aliases(value, expected):
    assert portable_build.canonical_platform(value) == expected


def test_unsupported_32_bit_architecture_is_explicit():
    with pytest.raises(RuntimeError, match="x86_64 and ARM64"):
        portable_build.canonical_architecture("i686")

