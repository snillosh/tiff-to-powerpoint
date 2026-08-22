# TIFF to PowerPoint Generator

A local desktop application that recursively scans TIFF files, previews metadata
parsed from their filenames, pairs ordinary and Volume Viewer images, and creates
a widescreen `.pptx` presentation. Microsoft PowerPoint is not used to construct
the file and is not required on the generation computer.

## Technology choice

- **Python 3.12** keeps the parsing, grouping, and layout code compact and testable.
- **PySide6 Essentials (Qt 6)** provides a native desktop GUI, preview table, dialogs, saved settings, and worker threads without bundling unused Qt add-on modules.
- **Pillow** decodes TIFF locally and converts the first frame to lossless temporary PNG files.
- **python-pptx** writes Office Open XML `.pptx` files directly without COM automation or Microsoft Office.
- **PyInstaller one-folder mode** bundles Python, Qt, Pillow TIFF support, python-pptx, and native libraries into native Linux, Windows, and macOS applications.

The finished application performs no network calls. CSS named-colour data is
bundled in the source and packaged executable.

## Features

- Recursive, case-insensitive `.tif`/`.TIF` discovery
- Explicit staged filename parser with a configurable literal delimiter
- Offline recognition of the standard CSS named-colour set
- Duplicate slot validation with every conflicting filename reported
- Preview table with filename, primary, sub-component, colour, type, and pair status
- Natural primary ordering and numeric sub-component ordering
- Pair identity of `(primary, sub-component, colour)`
- One primary per slide, with deterministic pagination by logical columns
- Normal image above its corresponding Volume Viewer image
- Fixed user-selected image width with aspect-ratio-derived height—no crop, stretch, or auto-shrink
- Centred partial continuation slides
- Horizontal and vertical fit validation before output is written
- First-frame TIFF-to-PNG conversion cached in a temporary directory and always cleaned up
- GUI work runs on a thread pool so scanning and generation do not freeze the window
- Saved GUI settings, rotating developer logs, and readable user-facing errors
- Direct `.pptx` generation; no Microsoft Office dependency

## Filename convention

The required values are:

- **Primary:** one capital letter immediately followed by one or more digits, such as `A1`, `E9`, or `Z100`.
- **Sub-component:** the first delimiter-separated token, scanning left to right, whose entire value consists only of digits.
- **Colour:** optional recognised CSS colour name, compared case-insensitively and stored in canonical form.
- **Volume Viewer:** true when adjacent tokens equal `Volume` and `Viewer` (case-insensitively). The configured delimiter determines token boundaries, so `_` recognises `Volume_Viewer` and `-` recognises `Volume-Viewer`.

Examples using the default `_` delimiter:

| Filename | Primary | Sub-component | Colour | Volume Viewer |
|---|---:|---:|---|---|
| `B8_1.tif` | B8 | 1 | — | No |
| `B8_1_Volume_Viewer_1.tif` | B8 | 1 | — | Yes |
| `E6_30MIN_1.tif` | E6 | 1 | — | No |
| `E6_30MIN_1_Volume_Viewer_1.tif` | E6 | 1 | — | Yes |
| `BlueE6_30MIN_1.tif` | E6 | 1 | Blue | No |
| `BlueE6_30MIN_1_Volume_Viewer_1.tif` | E6 | 1 | Blue | Yes |
| `BlueE8_30MIN_100.tif` | E8 | 100 | Blue | No |
| `RedE8_30MIN_100_Volume_Viewer_1.tif` | E8 | 100 | Red | Yes |
| `F10_30MIN_Volume_Viewer_1.tif` | F10 | 1 | — | Yes |
| `G10_1H_Volume_Viewer_2.tif` | G10 | 2 | — | Yes |
| `E8_100_Test_200_Volume_Viewer_300.tif` | E8 | 100 | — | Yes |

Tokens such as `30MIN`, `1H`, `H1`, `ABC12`, `12ABC`, and the primary itself are
not standalone integers. Volume Viewer detection is independent of numeric-token
selection: the number after `Viewer` is an ordinary token. It becomes the
sub-component when it is the first standalone integer, as in
`G10_1H_Volume_Viewer_2.tif`; it is ignored when an earlier integer exists, as in
`BlueE8_100_Volume_Viewer_1.tif`. If no standalone integer exists, the file is
listed as unparseable and skipped.

Colour recognition supports both colours touching a primary (`BlueE8_1.tif`) and
complete delimiter-separated colour tokens (`Sample_Blue_E8_1.tif`). It does not
search arbitrary substrings, so `SampleE8_1.tif` does not invent a colour.

## Pairing, ordering, and slides

Each logical column has this identity:

```text
(primary, sub-component, colour)
```

The non-Volume Viewer file occupies the top slot and the Volume Viewer file the
bottom slot. Missing members leave their slot blank. Multiple files occupying the
same logical slot are an error and generation remains disabled until the files are
resolved and scanned again.

Primaries use natural ordering (`A1`, `A2`, `A10`, `B1`). Within a primary,
columns are sorted by numeric sub-component and then colour; colourless items sort
before coloured items. Pagination occurs after sorting. A primary with 12 columns
and a maximum of 5 produces three slides titled `E9 - 1/3`, `E9 - 2/3`, and
`E9 - 3/3`. Different primaries are never mixed.

Slides use the standard widescreen 16:9 size (33.8667 × 19.05 cm). Five columns
at the default 5.5 cm image width and 0.3 cm gap fit within the configured margins.
Partial slides are centred. Top images share a top coordinate; the Volume Viewer
row begins after the tallest top image plus the vertical gap.

The width supplied in the GUI is never overridden. Every rendered height is
calculated from the decoded pixel dimensions. If a slide is too wide or its two
rows are too tall, generation stops with the relevant dimensions and a suggested
setting to reduce. Images are never cropped, stretched, squashed, or silently
shrunk.

## Run from source

Developer requirements:

- 64-bit Python 3.11–3.14; Python 3.12 is recommended for reproducible release builds
- A supported Windows, Linux, or macOS desktop environment

Create and activate a virtual environment, then install the project:

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m tiff_to_powerpoint
```

The installed `tiff-to-powerpoint` GUI command is equivalent.

## GUI workflow

1. Choose **Root image folder**.
2. Set **Filename delimiter** (default `_`).
3. Click **Scan Images**.
4. Review the table and status area. Unparseable files are skipped; duplicates block generation; unmatched pair members are warnings and retain blank slide slots.
5. Set **Image width (cm)**, **Image gap (cm)**, **Max columns per slide**, and **Show image labels**.
6. Choose an **Output PowerPoint** path with the Save As dialog.
7. Click **Generate PowerPoint**.

The image gap is used horizontally and vertically in version 1. Root folder,
delimiter, layout values, label choice, and output path are remembered between
launches through the platform's Qt settings store.

Developer logs rotate automatically and are stored at:

- Windows: `%LOCALAPPDATA%\TIFFToPowerPoint\logs\application.log`
- Linux: `$XDG_STATE_HOME/TIFFToPowerPoint/logs/application.log` or `~/.local/state/TIFFToPowerPoint/logs/application.log`
- macOS: `~/Library/Logs/TIFFToPowerPoint/logs/application.log`

## Tests

Install development dependencies, then run:

```bash
python -m pytest
```

The test suite covers the required filename examples, custom literal delimiters,
CSS colours, invalid and ambiguous names, natural ordering, numeric ordering,
colour-aware pairing, missing members, duplicates, pagination, slide centring,
aspect ratios, horizontal and vertical overflow, and recursive scanning.

The integration test creates 30 temporary TIFF files: 12 paired sub-components for
E9 and 3 for E8. It generates a presentation and verifies four slides, continuation
titles, and embedded picture aspect ratio.

## Build portable applications

The end user does **not** need Python, Pillow, Qt, package managers, TIFF codecs,
Microsoft Office, or internet access. Build dependencies are only required on the
developer machine.

PyInstaller builds for the operating system and CPU architecture on which it is
running; it is not a cross-compiler. Run the matching command on a native machine
or use the checked-in GitHub Actions workflow.

Linux x86_64 or ARM64:

```bash
build/build_linux.sh
```

macOS x86_64 or Apple Silicon ARM64:

```bash
build/build_macos.sh
```

Windows x86_64 or Windows on ARM64:

```bat
build\build.bat
```

Each local wrapper creates an isolated `.venv-build`, installs declared build
dependencies, then calls `build/build.py`. The common build driver detects the
native target, runs the tests, invokes PyInstaller, executes the packaged
`--self-test`, and creates a versioned archive plus SHA-256 checksum.

Example outputs:

```text
build-output/linux-x86_64/TIFFToPowerPoint/
releases/TIFFToPowerPoint-1.0.1-linux-x86_64.tar.gz
releases/TIFFToPowerPoint-1.0.1-linux-x86_64.tar.gz.sha256

build-output/windows-x86_64/TIFFToPowerPoint/
releases/TIFFToPowerPoint-1.0.1-windows-x86_64.zip

build-output/macos-arm64/TIFFToPowerPoint.app/
releases/TIFFToPowerPoint-1.0.1-macos-arm64.tar.gz
```

Extract the archive on a matching OS/architecture and launch the native executable
listed in the clean-machine checklist. One-folder packaging is intentional: it is
more reliable and starts faster than unpacking a large one-file executable on every
launch.

The PyInstaller specification explicitly collects Pillow image plugins (including
TIFF support) and python-pptx package data. Qt and compiled dependencies are handled
by PyInstaller's maintained hooks. No external `PATH`, ImageMagick, Ghostscript,
codec, Office, or runtime configuration is expected.

The workflow in `.github/workflows/build-portable.yml` builds six artifacts:

- Linux x86_64 and ARM64
- Windows x86_64 and ARM64
- macOS x86_64 and ARM64

The ARM GitHub runners and PySide6 Windows ARM64 support are currently preview
offerings, so review every job independently. Here, "x86" means modern 64-bit
x86_64/AMD64. 32-bit x86 is not supported by the current Python/Qt stack.

Use [build/clean-machine-checklist.md](build/clean-machine-checklist.md) for release
acceptance. Unsigned Windows/macOS builds work locally but should be code-signed
before broad distribution.

## Project structure

```text
src/tiff_to_powerpoint/
    models.py            Domain/configuration models
    colours.py           Bundled CSS named-colour data
    parser.py            Staged filename parser
    scanner.py           Recursive file discovery
    pairing.py           Duplicate detection, pairing, sorting, pagination
    analysis.py          Scan preview analysis and pair statuses
    layout.py            Pure coordinate calculation and overflow validation
    converter.py         Cached first-frame TIFF-to-PNG conversion
    generator.py         Direct PowerPoint generation
    configuration.py     GUI/config validation
    logging_config.py    Rotating developer log setup
    gui/                 PySide6 window and background worker adapter
tests/                   Unit and end-to-end integration tests
build/                   Cross-platform build driver, wrappers, spec, and checklist
.github/workflows/       Six-target native CI build matrix
```

Business logic has no dependency on the GUI. Parsing, pairing, pagination, and
layout calculation can be tested or reused independently.

## Assumptions and known limitations

- `.tif` is supported case-insensitively; `.tiff` is intentionally ignored because the source convention specifies `.tif`.
- A filename must contain exactly one primary match and, after marker removal, exactly one standalone integer token. Ambiguous files are skipped instead of guessed.
- A filename containing more than one distinct recognised colour is treated as ambiguous.
- Multi-page TIFFs use the first frame only. Source TIFFs are opened read-only and never modified.
- TIFF data is converted to PowerPoint-compatible 8-bit RGB/RGBA PNG. PNG is lossless, though higher-bit-depth scientific TIFF samples are mapped to the display-oriented colour depth PowerPoint expects.
- The generated file contains raster images and unobtrusive text labels; it does not preserve specialised TIFF metadata in the presentation.
- Each release must be built natively for its target OS/architecture and exercised on a matching clean machine. The automated packaged self-test is substantial but cannot substitute for visual acceptance testing.
