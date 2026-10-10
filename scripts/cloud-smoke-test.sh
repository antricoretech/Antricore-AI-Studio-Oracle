#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing $PYTHON. Run bash scripts/bootstrap-cloud.sh first." >&2
  exit 2
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi is not available; this is not a ready NVIDIA cloud VM." >&2
  exit 2
fi

echo '=== GPU ==='
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

echo '=== Runtime dependencies ==='
command -v ffmpeg >/dev/null 2>&1 || { echo 'FFmpeg is missing.' >&2; exit 2; }
"$PYTHON" -c 'import torch; assert torch.cuda.is_available(), "CUDA unavailable"; print(torch.__version__, torch.cuda.get_device_name(0))'

echo '=== Application tests ==='
"$PYTHON" -m pytest -q

echo '=== Local pipeline dry-run ==='
"$PYTHON" -m studio.free_cli pipeline --dry-run \
  --prompt 'Original fictional adult fashion portrait' \
  --video-prompt 'Gentle natural movement, stable face, no text'

echo 'Cloud smoke test passed. No model inference or large download was started.'
