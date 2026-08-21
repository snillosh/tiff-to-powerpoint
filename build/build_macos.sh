#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "ERROR: build_macos.sh must run on macOS." >&2
    exit 1
fi
exec "$(dirname "$0")/build_unix.sh" "$@"

