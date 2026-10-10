#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the Studio control plane on a Linux GPU VM.
#
# This script deliberately does not install a CUDA/PyTorch wheel: the correct
# wheel depends on the provider's driver and CUDA runtime. Install that wheel
# first, then rerun with --image.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INSTALL_IMAGE=0
INSTALL_VOICE=0
INSTALL_DOWNLOAD=0

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap-cloud.sh [options]

Options:
  --image      Install Diffusers image dependencies (install PyTorch first)
  --voice      Install Kokoro voice dependencies
  --download   Install Hugging Face download dependencies
  --help       Show this help

The script creates .venv, installs the Studio control plane, creates .env if
needed, and runs the diagnostic command. Model weights are never downloaded
automatically.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image) INSTALL_IMAGE=1 ;;
    --voice) INSTALL_VOICE=1 ;;
    --download) INSTALL_DOWNLOAD=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This bootstrap script targets Linux cloud instances (use setup-free-windows.ps1 on Windows)." >&2
  exit 2
fi

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "Python 3.12 is required. Install it with the provider's OS package manager first." >&2
  exit 2
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Warning: ffmpeg is not installed; audio/video muxing will not work until it is added." >&2
fi

if [[ ! -d .venv ]]; then
  python3.12 -m venv .venv
fi

PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt

if [[ "$INSTALL_DOWNLOAD" -eq 1 ]]; then
  "$PYTHON" -m pip install -r requirements-download.txt
fi

if [[ "$INSTALL_IMAGE" -eq 1 ]]; then
  if ! "$PYTHON" -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    echo "A CUDA-enabled PyTorch installation is required before --image." >&2
    echo "Install the wheel matching the NVIDIA driver, then rerun this script with --image." >&2
    exit 2
  fi
  "$PYTHON" -m pip install -r requirements-local-image.txt
fi

if [[ "$INSTALL_VOICE" -eq 1 ]]; then
  "$PYTHON" -m pip install -r requirements-voice.txt
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

"$PYTHON" -m studio.free_cli doctor

cat <<'EOF'

Cloud bootstrap complete.
Next steps:
  1. Verify the GPU and CUDA status in the doctor output.
  2. Install the matching CUDA-enabled PyTorch wheel if it is missing.
  3. Install image/download dependencies with --image --download.
  4. Download only the approved models you need, explicitly with --yes.
  5. Start the dashboard through an SSH tunnel or an authenticated reverse proxy.
EOF
