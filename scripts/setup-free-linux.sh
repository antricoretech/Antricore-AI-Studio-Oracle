#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
.venv/bin/python -m studio.free_cli doctor
printf '%s\n' 'To add image inference: install compatible PyTorch, then pip install -r requirements-local-image.txt'
