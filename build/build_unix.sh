#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_command="${PYTHON:-python3}"
if [[ ! -x ".venv-build/bin/python" ]]; then
    "$python_command" -m venv .venv-build
fi

.venv-build/bin/python -m pip install --upgrade pip
.venv-build/bin/python -m pip install --upgrade -e '.[dev,build]'
.venv-build/bin/python build/build.py "$@"
