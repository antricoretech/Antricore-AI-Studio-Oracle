#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p external
if [ "$#" -eq 0 ]; then set -- ComfyUI Flux2 AIToolkit Wan22 Kokoro; fi
for name in "$@"; do
  case "$name" in
    ComfyUI) url='https://github.com/comfy-org/ComfyUI.git';;
    AIToolkit) url='https://github.com/ostris/ai-toolkit.git';;
    Flux2) url='https://github.com/black-forest-labs/flux2.git';;
    ZImage) url='https://github.com/Tongyi-MAI/Z-Image.git';;
    Wan22) url='https://github.com/Wan-Video/Wan2.2.git';;
    Wan21) url='https://github.com/Wan-Video/Wan2.1.git';;
    Kokoro) url='https://github.com/hexgrad/kokoro.git';;
    MuseTalk) url='https://github.com/TMElyralab/MuseTalk.git';;
    VHS) url='https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git';;
    *) echo "Unapproved repository $name" >&2; exit 2;;
  esac
  if [ -d "external/$name" ]; then echo "Skipping $name"; else git clone --depth 1 "$url" "external/$name"; fi
done
printf '%s\n' 'Source cloned. Model weights are downloaded separately.'
