#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to run the frontend dev server. Install Node/npm first." >&2
  exit 127
fi

exec npm --prefix web run dev -- --host 127.0.0.1 --port 5173 "$@"
