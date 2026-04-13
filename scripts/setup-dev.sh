#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python3}
PIP_TARGET_DIR=${PIP_TARGET_DIR:-.pydeps}
NPM_BIN=${NPM_BIN:-npm}

if "$PYTHON_BIN" -m venv --help >/dev/null 2>&1; then
  if "$PYTHON_BIN" -m venv .venv >/dev/null 2>&1; then
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e '.[dev,web]'
    echo "Backend ready in .venv"
  else
    echo "python3 -m venv is unavailable on this host, using local .pydeps fallback" >&2
    rm -rf .venv "$PIP_TARGET_DIR"
    "$PYTHON_BIN" -m pip install --target "$PIP_TARGET_DIR" '.[dev,web]'
    echo "Backend ready in $PIP_TARGET_DIR"
  fi
else
  rm -rf "$PIP_TARGET_DIR"
  "$PYTHON_BIN" -m pip install --target "$PIP_TARGET_DIR" '.[dev,web]'
  echo "Backend ready in $PIP_TARGET_DIR"
fi

"$NPM_BIN" --prefix web install

echo "Frontend ready in web/node_modules"
