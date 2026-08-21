# Native PyInstaller one-folder build for Linux, Windows, and macOS.
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files


project_root = Path(SPECPATH).parent
entry_point = project_root / "src" / "tiff_to_powerpoint" / "__main__.py"

datas = collect_data_files("pptx") + collect_data_files("PIL")
# The Pillow hook handles core image support; these explicit plugins guarantee
# the two formats this application reads/writes are retained by future hook changes.
hiddenimports = ["PIL.TiffImagePlugin", "PIL.PngImagePlugin"]

a = Analysis(
    [str(entry_point)],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Neither the application nor Pillow's TIFF/PNG path needs these optional
    # packages. Excluding them avoids accidentally bundling host-global modules.
    excludes=["numpy", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TIFFToPowerPoint",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TIFFToPowerPoint",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="TIFFToPowerPoint.app",
        icon=None,
        bundle_identifier="com.tifftopowerpoint.app",
    )
