#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
PORT="${PORT:-8124}"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Studio virtual environment not found: ${PYTHON}" >&2
  exit 1
fi

export STUDIO_APP_SURFACE="legacy"
export DATA_DIR="${PROJECT_ROOT}/data"
export STUDIO_GENERATED_DIR="${PROJECT_ROOT}/generated"
exec "${PYTHON}" -m uvicorn studio.legacy_app:app --host 127.0.0.1 --port "${PORT}" "$@"
