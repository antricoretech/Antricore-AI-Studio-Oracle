#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
PORT="${PORT:-8123}"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Studio virtual environment not found: ${PYTHON}" >&2
  exit 1
fi

export STUDIO_APP_SURFACE="canonical"
export DATA_DIR="${PROJECT_ROOT}/data/canonical"
export STUDIO_GENERATED_DIR="${PROJECT_ROOT}/data/canonical/generated"
exec "${PYTHON}" -m uvicorn studio.canonical_app:app --host 127.0.0.1 --port "${PORT}" "$@"
