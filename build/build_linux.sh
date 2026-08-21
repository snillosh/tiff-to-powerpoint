#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "ERROR: build_linux.sh must run on Linux." >&2
    exit 1
fi
exec "$(dirname "$0")/build_unix.sh" "$@"

