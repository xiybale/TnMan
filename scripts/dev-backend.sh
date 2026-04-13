#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}
RELOAD=${RELOAD:-0}

CMD=(python3 scripts/python_with_local_deps.py -m tennis_pro_manager serve-api --host "$HOST" --port "$PORT")
if [[ "$RELOAD" == "1" ]]; then
  CMD+=(--reload)
fi
CMD+=("$@")

exec "${CMD[@]}"
