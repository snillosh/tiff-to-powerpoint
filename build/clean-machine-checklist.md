# Clean-machine acceptance checklist

Test every release on a clean machine or VM matching its operating system and
CPU architecture. Python, Microsoft Office, and developer tools should not be
installed.

- Confirm the archive name matches the target (`linux`, `windows`, or `macos`; `x86_64` or `arm64`).
- Verify the adjacent SHA-256 checksum before extracting.
- Launch the application and confirm the main window opens without a missing library/module error.
- Use the folder picker and scan nested `.tif` and `.TIF` files.
- Confirm valid, invalid, unmatched, and duplicate filenames are reported accurately.
- Generate a presentation containing ordinary and multi-page TIFFs.
- Confirm the first TIFF frame is used and source TIFF files are unchanged.
- Open the result in PowerPoint or LibreOffice Impress and inspect titles, labels, pagination, and aspect ratios.
- Confirm deliberately too-wide and too-tall layouts produce useful errors rather than distorted images.
- Confirm the platform log is created.
- Disconnect networking and repeat scan and generation to confirm normal use is fully offline.

Platform launch points:

- Linux: `TIFFToPowerPoint/TIFFToPowerPoint`
- Windows: `TIFFToPowerPoint\TIFFToPowerPoint.exe`
- macOS: `TIFFToPowerPoint.app` (unsigned local builds may require right-clicking and choosing **Open**)

The build process automatically runs `--self-test` against the packaged executable.
That verifies Qt imports, TIFF decoding, parsing/pairing, PNG conversion, direct
PowerPoint creation, and reopening the `.pptx`, but it does not replace a visual
clean-machine acceptance test.

Windows and macOS releases should be code-signed before broad public distribution
to avoid SmartScreen or Gatekeeper warnings.

