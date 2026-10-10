# Detailed model and repository audit — 9 October 2026

## Audit criteria

1. **No paid inference API or credit meter:** after local download the model can run without sending images or prompts to a paid service.
2. **Commercially viable permission for the exact pretrained weights:** prefer Apache-2.0; don't assume GitHub source license covers weights.
3. **Public code on GitHub and free public checkpoints:** public checkpoints are typically hosted on Hugging Face or ModelScope because weights are too large for ordinary Git repositories.
4. **Usable locally:** inference must fit a machine's GPU/CPU/RAM/disk, perhaps with quantization/offloading (these are not free hardware upgrades).
5. **No identity deception:** content depicts original, synthetic adults and is labeled appropriately.

### Approvals: base model weights

| Function | GitHub code | Public weights | Code / weights summary | Local feasibility | Status |
|---|---|---|---|---|---|
| Image generation + identity reference editing | https://github.com/black-forest-labs/flux2 | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | Apache-2.0 code / **4B** Apache-2.0 weights | ~13 GB VRAM documented; offload possible with time/RAM cost | DEFAULT |
| Persona LoRA training base | https://github.com/black-forest-labs/flux2 | https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B | **4B Base** Apache-2.0 weights | training needs substantial VRAM and more complex setup | APPROVED, manual integration |
| Fast photorealistic images | https://github.com/Tongyi-MAI/Z-Image | https://huggingface.co/Tongyi-MAI/Z-Image-Turbo | Apache-2.0 code / Apache-2.0 weights | model maintainers target ~16GB VRAM | OPTIONAL |
| Image-to-video / text-to-video | https://github.com/Wan-Video/Wan2.2 | https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B | Apache-2.0 code / Apache-2.0 weights | official 720p CLI guidance ~24 GB VRAM | APPROVED, separate env |
| Lower-spec TEXT-to-video | https://github.com/Wan-Video/Wan2.1 | https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B | Apache-2.0 code / Apache-2.0 weights | lighter 480p text-video, but not reference I2V | OPTIONAL, not CLI-integrated |
| Offline TTS / synthetic voice | https://github.com/hexgrad/kokoro | https://huggingface.co/hexgrad/Kokoro-82M | Apache-2.0 library + Apache-2.0 weights | suitable for CPU | APPROVED |
| LoRA training SOFTWARE | https://github.com/ostris/ai-toolkit | Uses chosen base model (above) | MIT training toolkit; the model being trained has its own license | substantial training compute; base model supported | APPROVED, clone/configure |
| Generation backend | https://github.com/comfy-org/ComfyUI | none: separately load approved models | GPL-3.0 code; model weights separately licensed | GPU depends on graph | APPROVED, optional |
| Local clip encode / mux | https://github.com/FFmpeg/FFmpeg | none | FFmpeg built under configurable license, commonly LGPL/GPL by build | CPU; no inference credits | APPROVED, respect binary license |

### Investigate individually, not in the default commercial dependency set

- **MuseTalk** https://github.com/TMElyralab/MuseTalk — MIT code and project states its own trained models may be used commercially. **However**, the authors explicitly require compliance with separate dependencies (Whisper, ft-mse-vae, dwpose, S3FD, etc.) and exclude non-commercial test footage from commercial use. Not included in the zero-ambiguity default; optional later after a complete dependency/model chain audit. A separate Python environment is needed.
- **LatentSync** https://github.com/bytedance/LatentSync — Apache-2.0 code but **LatentSync-1.5 weights are labeled `openrail++`**, and data preprocessing uses InsightFace. Not on the Apache-only pretrained allowlist.
- **LivePortrait** https://github.com/KlingAIResearch/LivePortrait — MIT code but default pipelines include pretrained InsightFace detection components with noncommercial terms. A verified replacement detection stack would be needed.
- **ReActor / Roop / FaceFusion** — do **not** bundle `inswapper_128.onnx`, pretrained InsightFace/ArcFace models or assumed-commercial face-swapping models without separate proof of rights. Training your own fictional persona and using reference-conditioned generation avoids relying on this dependency.
- **FLUX.2 Klein 9B and FLUX.2 dev** — their **weight** licenses are non-commercial; the Apache-2.0 source repo doesn't make the weights commercial.
- **FLUX.1 dev** — not part of the approved weights list; do not replace the 4B recommendation with it.
- **SDXL base / derived checkpoints** — commercially usable in various circumstances but licenses are not the requested simple permissive Apache-2.0 baseline; prior SDXL presets were removed from the distributed runtime workflows.
- **Cloud-based APIs, Runway, Kling hosted, Midjourney, paid voice platforms and cloud GPU rentals** — not part of local zero-credit execution.

### What Apache-2.0 means here

It permits commercial use with no licensing fee or per-output credit charge. It still requires preserving the license and relevant copyright/NOTICE terms in redistributed copies and observing trademark/patent/disclaimer rules. **It does not mean “no license” or guarantee that input/outputs cannot infringe third-party rights.** MIT, GPL and FFmpeg licenses also apply to their respective programs.

### Operational considerations

- **Weights are not stored in GitHub source checkouts.** Use this project's `download` CLI to fetch the exact public Hugging Face model repositories into `models/` once; model repos can be >20 GB. `Wan2.2-TI2V-5B` HF tree is ~34 GB.
- Hugging Face login typically isn't needed for public ungated model repositories; bandwidth, abuse limits or hosting policy may still affect downloads. `huggingface_hub` is a free download library, not a paid inference provider.
- **Offload does not guarantee a model fits every GPU.** Large system RAM, fast SSD and patience may be required.
- Local model execution is unmetered per generation but requires owned/accessible compatible hardware and electricity. GPU VRAM and runtime depend on resolution, graph, precision, quantization, and installed versions.
- Default FLUX.2 Klein 4B is an **inference model** (fast distilled); its **Base 4B** sibling is recommended for fine-tuning. LoRA adapters must match model architecture.
- Video generation can still show identity drift, flicker and anatomy artifacts. Audio muxing does NOT align lips with audio. Lip-sync must be added as a separate model after license verification.
- Corporate/business usage should record code and weights' license versions and retain third-party notices in distributed software artifacts.

### Primary sources to recheck before deployment

- FLUX.2 official license table: https://github.com/black-forest-labs/flux2#model-overview
- FLUX.2 Klein 4B model card: https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- FLUX.2 Klein Base 4B model card: https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B
- Wan2.2 README and 24GB requirement: https://github.com/Wan-Video/Wan2.2#run-wan22
- Wan2.2 TI2V model card: https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B
- Z-Image model card: https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- Kokoro model card: https://huggingface.co/hexgrad/Kokoro-82M
- Ostris AI Toolkit readme: https://github.com/ostris/ai-toolkit
- MuseTalk project disclaimer: https://github.com/TMElyralab/MuseTalk#disclaimerlicense
- LatentSync model terms: https://huggingface.co/ByteDance/LatentSync-1.5
- ComfyUI software license: https://github.com/comfy-org/ComfyUI/blob/master/LICENSE
