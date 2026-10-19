# AI Influencer Studio — Free / Local / Open-Source-First Edition

**Research update: 9 October 2026.** A VS Code project for producing clearly disclosed, fully fictional adult synthetic influencer media using self-hosted, publicly downloadable models. **No paid inference API, subscription, credits, API keys, or commercial-model license purchase is required for the recommended base workflow.**

> IMPORTANT — “Free” never means “no license.” Apache-2.0, MIT and GPL-3.0 all have legally binding terms. You must respect required notices and third-party dependencies. You pay for your hardware, electricity, disk capacity and internet bandwidth if applicable. GitHub generally hosts **code**, while large **model weights** are distributed free from public Hugging Face repositories. This project does not bundle model weights.

---

## 🧠 Neural Models & Persona Generation Architecture

> **Git-Ignore Notice**: Large model weights (`.safetensors`, `.bin`, `.gguf`, `.onnx`, `models/`) are strictly excluded from git tracking via [.gitignore](file:///.gitignore) to keep the repository lightweight. Model weights are stored locally in the `models/` directory according to the specifications below.

AI Influencer Studio utilizes a multi-model neural pipeline tailored for ultra-consistent, photorealistic virtual influencer synthesis, multi-angle biometric identity freezing, and video animation.

### 1. Primary Persona Synthesis Checkpoint: Juggernaut XL v10 (RunDiffusion NSFW Edition)
* **Local Checkpoint Path**: `models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors`
* **Base Architecture**: Stable Diffusion XL (SDXL) Base 1.0 (Dual CLIP text encoders: OpenCLIP ViT-bigG/14 + OpenAI ViT-L/14, 77-token budgeting)
* **Inference Precision**: `fp16` on Apple Silicon Metal Performance Shaders (MPS) or NVIDIA CUDA
* **Scheduler**: `DPMSolverMultistepScheduler` (Karras sigmas), 20–30 inference steps, Guidance Scale (CFG): 5.0–7.0
* **Target Resolutions**: 768×1152 (2:3 portrait standard), 832×1216 (9:16 vertical story), 1024×1024 (1:1 square)
* **Why this model**: Juggernaut XL v10 by RunDiffusion is specifically trained for hyper-realistic human skin micro-pores, natural catchlights, fine facial bone structures, and anatomically precise body proportions (e.g. 36-24-30 standard, athletic hourglass curves).
* **Role in Master Persona Vault**: Generates all **13 Frozen Vault Reference Packs**:
  1. `01 Front (0° Turnaround)` — Direct eye-level canonical portrait
  2. `02 Left (-90° Turnaround)` — Left side profile anchor
  3. `03 Right (+90° Turnaround)` — Right side profile anchor
  4. `04 Back (180° Turnaround)` — Rear silhouette, neck & cascading hair anchor
  5. `05 Macro Eyes & Lips` — Extreme close-up epidermal texture & iris striations
  6. `06 High Fashion` — Editorial tailored styling
  7. `07 Athleisure` — Sculpted fitness & dynamic gym posture
  8. `08 Casual Street` — Metropolitan candid lifestyle
  9. `09 Resortwear` — Golden hour poolside promenade
  10. `10 Boudoir Half (18+)` — Intimate satin baseline
  11. `11 Boudoir Full (18+)` — Artistic full silhouette
  12. `12 Lingerie Half (18+)` — Sheer lace intimate baseline
  13. `13 Lingerie & Stockings (18+)` — Full stockings & corset baseline

---

### 2. Facial Identity Anchor: IP-Adapter FaceID PlusV2 SDXL
* **Local Weights Path**:
  * `models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl.bin`
  * `models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl_lora.safetensors`
* **Identity Extractor**: InsightFace `buffalo_l` (512-dimensional normalized facial embedding vector)
* **Role**: Ingests the 0° canonical front portrait and projects face-id vectors into the cross-attention layers of the SDXL UNet. This mathematically forces identical bone structure, eye shape, nose bridge, and lip curves across all subsequent photoshoot generations and diverse camera angles.

---

### 3. Alternative Checkpoints & Benchmark Engines
* **CyberRealistic XL Play v10.0 FP16** (`models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors`): Specialized for softer daylight illumination and European/Mediterranean facial features.
* **Pony Diffusion V6 XL** (`models/pony-diffusion-v6-xl/ponyDiffusionV6XL_v6StartWithThisOne.safetensors`): High-aesthetic artistic baseline testing.
* **FLUX.1-dev Q4_K_S GGUF** (`models/flux-1-dev-gguf/flux1-dev-Q4_K_S.gguf`) with `scg-anatomy-female-v2` LoRA (`models/flux-lora/`): 12B flow-matching transformer for next-generation biometric benchmark rendering.

---

### 4. Motion, Story & Video Engines
* **Stable Video Diffusion XT (SVD-XT 1.1)** (`models/svd-xt/`): Converts frozen 13-pack master persona keyframes into cinematic 25-frame vertical reel clips without face distortion.
* **LivePortrait Engine** (`LivePortrait/`): Landmark-guided neural facial animation for Story Studio talking head videos and dynamic speech synchronization.

---

### 5. Local Models Directory Layout

Place downloaded weights in the following structure:

```
models/
├── juggernaut-xl-v10/
│   └── Juggernaut-X-RunDiffusion-NSFW.safetensors   # (Primary Master Persona Checkpoint ~6.6 GB)
├── ip-adapter-faceid/
│   ├── ip-adapter-faceid-plusv2_sdxl.bin           # (FaceID adapter weights)
│   └── ip-adapter-faceid-plusv2_sdxl_lora.safetensors # (FaceID LoRA weights)
├── cyberrealistic-xl/
│   └── CyberRealisticXLPlay_V10.0_FP16.safetensors  # (Alternative photorealism)
├── pony-diffusion-v6-xl/
│   ├── ponyDiffusionV6XL_v6StartWithThisOne.safetensors
│   └── sdxl_vae.safetensors
├── flux-1-dev-gguf/
│   └── flux1-dev-Q4_K_S.gguf
├── flux-lora/
│   └── scg-anatomy-female-v2.safetensors
└── svd-xt/
    ├── unet/diffusion_pytorch_model.fp16.safetensors
    ├── image_encoder/model.fp16.safetensors
    └── vae/diffusion_pytorch_model.fp16.safetensors
```

### 6. Hardware Acceleration
* **Apple Silicon (M1/M2/M3/M4 Max/Ultra)**: Accelerated via PyTorch Metal Performance Shaders (`torch.backends.mps`) with FP16 zero-copy unified memory. Recommended: 24 GB+ unified memory.
* **NVIDIA RTX GPUs**: Accelerated via PyTorch CUDA with FP16 or BF16. Recommended: 16 GB–24 GB VRAM (RTX 3090, 4080, 4090, or A100/H100).

---

## What is actually runnable?

- ✅ Existing **FastAPI + SQLite dashboard**, persona reference library, manual review and ComfyUI API bridge.
- ✅ Standalone **`studio.free_cli doctor`** (no GPU or downloads required).
- ✅ Allowlisted **public model downloader** (requires internet, local disk, explicit `--yes`; no paid credits).
- ✅ Local **FLUX.2 Klein 4B** text-to-image and 1+ reference-image editing through Diffusers (requires enough GPU/RAM + installed weights).
- ✅ Local **Z-Image Turbo** optional text-to-image pipeline (hardware dependent).
- ✅ Official **Wan2.2 TI2V-5B** image-to-video/text-to-video CLI wrapper after you clone, install and download the official model (reference CLI says ~24 GB VRAM for 720p with offload).
- ✅ **Kokoro** local speech synthesis when optional dependencies are installed; **FFmpeg** local audio muxing.
- ⚠️ **Persona LoRA training** uses an *external separately installed* Ostris AI Toolkit against FLUX.2 Klein 4B Base. The library is researched but there is **no turnkey LoRA trainer or trained persona included**.
- ⚠️ **Talking-head lip sync** is *not integrated by default*. MuseTalk is a possible research option, but its complete pretrained third-party dependency license chain must be checked before commercial use.
- ⚠️ **ComfyUI** is optional for the standalone local CLI but needed for the original dashboard's ComfyUI generation queue. The project does **not** ship ready-to-run model-specific ComfyUI JSON graphs; export a verified local workflow before using this route.
- ❌ No online social publishing, social account access, cloud infrastructure, auto-LoRA identity scoring, fully automated face swaps, payment collection or GPU-tested end-to-end video rendering.

## Get started: Windows 11 + NVIDIA GPU + VS Code

1. Install [Python 3.12](https://www.python.org/downloads/), [Git](https://git-scm.com/), VS Code with Python extension, and latest NVIDIA drivers. Install [FFmpeg](https://ffmpeg.org/) if combining video/audio.
2. Extract the ZIP; in VS Code **File → Open Folder**, select this project and **Terminal → New Terminal**.
3. In PowerShell:

```powershell
.\scripts\setup-free-windows.ps1 -DownloadTools
.\.venv\Scripts\python.exe -m studio.free_cli doctor
```

4. Install a GPU-compatible PyTorch wheel following **https://pytorch.org/get-started/locally/**. Do not blindly install a CUDA version that does not match your driver. Then:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-local-image.txt
.\.venv\Scripts\python.exe -m studio.free_cli download --model flux2-klein-4b --yes
```

5. Generate a fictional character portrait:

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli image --offline --prompt "Photorealistic editorial portrait of a fictional 27-year-old adult woman, dark brown wavy hair, warm natural daylight, candid photography, fully clothed" --output generated\master.png --cpu-offload
```

6. After approving your master image, generate the **same fictional character with a different scene** using reference conditioning:

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli image --offline --reference generated\master.png --prompt "Use the person in the reference image as the same fictional adult character; documentary street photograph at a café, natural smile, different outfit, realistic lighting" --output generated\cafe.png --cpu-offload
```

**Identity preservation is probabilistic**, not guaranteed; approve outputs manually. The reference-image workflow is the no-training starting path.

## Local narration

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
.\.venv\Scripts\python.exe -m studio.free_cli voice --text "Hello from my new creative studio" --voice af_heart --output generated\voice.wav
```

Kokoro may require eSpeak NG and will fetch its publicly available model/voice data the first time; it is CPU-capable.

## One-command local pipeline

After the image and Wan2.2 environments are installed and the required weights
are downloaded on the GPU server, run the complete local-only flow:

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli pipeline --offline --cpu-offload `
  --prompt "Photorealistic editorial portrait of an original fictional adult woman in her late 20s, fully clothed, natural daylight" `
  --video-prompt "The same fictional adult character smiles, walks slowly toward the camera and turns naturally; stable face and body, no text" `
  --narration "Welcome to my fictional AI studio." `
  --python "C:\path\to\wan-python.exe" `
  --output generated\reel_with_voice.mp4
```

Use `--dry-run` first to inspect the stages. Omit `--narration` to produce a
video without Kokoro or FFmpeg. The command uses local model weights only; it
does not call an inference API or consume generation credits. A disclosure
sidecar is written beside the final output for manual publication review.

## Video (high-VRAM machines; WSL2/Linux recommended)

Install Wan2.2 in a separate virtual environment from the Studio. Detailed steps: **docs/LOCAL_FREE_SETUP.md**.

```powershell
.\scripts\clone-github-repos.ps1 -Names Wan22
.\.venv\Scripts\python.exe -m studio.free_cli download --model wan22-ti2v-5b --yes
.\.venv\Scripts\python.exe -m studio.free_cli video --reference generated\master.png --prompt "The same fictional adult character smiles, turns slightly toward the camera; gentle natural movement, stable face" --python "C:\path\to\wan-python.exe" --output generated\reel.mp4 --dry-run
```

Remove `--dry-run` to run it only after installing the Wan2.2 requirements into the separate Python environment. **Do not turn on Dashscope API prompt extension**; its optional cloud API is unnecessary for local inference. See GitHub docs for Wan2.2 ~24 GB VRAM 720p reference configuration.

For lower-capacity GPUs, Wan2.1 T2V-1.3B (Apache-2.0) is a **480p text-to-video-only fallback**, not a substitute for identity-preserving image-to-video.

## Dashboard (optional)

The Production Studio workflow selector includes default recipes for FLUX.2, Z-Image, Wan2.2, Wan2.1, Kokoro, FFmpeg and imported ComfyUI graphs. Recipes are visible immediately, but a dashboard queue job requires a separately running ComfyUI and a verified API-format graph; catalog-only entries are marked setup-required until installed. See `config/workflow_catalog.json`.

```powershell
.\.venv\Scripts\python.exe -m uvicorn studio.app:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Persona/reference storage works immediately. Generation jobs in the dashboard require **a separately running ComfyUI and an imported compatible API-format workflow**; model weights and workflows are **not** included. The direct CLI path can be brought back into **Review & export → Media review → Import a completed pipeline output**, where the file remains pending until manual approval and disclosure confirmation. This mode is meant for testing custom graphs, not automatic model licensing guarantees. Standalone free CLI is the easiest base path.

For a cloud worker or any non-loopback tunnel, configure an access token and
strict media checks before starting Uvicorn:

```powershell
$env:STUDIO_AUTH_TOKEN = "use-a-long-random-secret"
$env:STUDIO_STRICT_MEDIA = "1"
.\.venv\Scripts\python.exe -m uvicorn studio.app:app --host 127.0.0.1 --port 8000
```

The dashboard's Operations → Monitoring panel reports whether authentication
is configured. See `docs/ARCHITECTURE_PHASES.md` for Phase 1/2 hardening and
module boundaries.

## Documentation

- `docs/LOCAL_FREE_SETUP.md` — hardware, installations, model downloads and exact commands
- `scripts/bootstrap-cloud.sh` — repeatable Linux GPU VM bootstrap for the cloud deployment target
- `docs/CLOUD_DEPLOYMENT.md` — complete cloud provisioning, model setup, pipeline, security and operations runbook
- `scripts/cloud-smoke-test.sh` — non-destructive cloud GPU/dependency/test validation
- `docs/FREE_MODEL_RESEARCH.md` — license decision matrix, GitHub links, exclusion list and key caveats
- `config/approved_models.json` — allowlisted Apache-2.0 **model weights** (not a dependency audit)
- `GET /api/models` and Operations → Monitoring — capability-aware model inventory with local installation, VRAM and revision-pin status
- `studio/free_cli.py` — runnable offline/local commands
- `scripts/clone-github-repos.ps1` / `.sh` — allowlisted source repository checkouts
- `docs/WORKFLOW_GUIDE.md` — ComfyUI adapters, revised guidance
- `docs/SERIES_GUIDE.md` — freeze personas, plan repeatable episodes and preserve continuity
- `docs/NAVIGATION.md` — grouped menu, connected pipeline rail and stage hand-offs
- `docs/MONITORING.md` — startup checks for API, GPU, models, runtimes, workflows and storage
- `scripts/deployment-readiness.py` — read-only cloud/source deployment gate
- `scripts/browser-smoke-test.py` + `requirements-browser.txt` — optional Playwright dashboard smoke test

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tests check API behavior, mocked ComfyUI execution, model allowlist and CLI validation. **They do not test CUDA inference, Hugging Face downloads, Wan model loading, GPU RAM behavior, LoRA training, or lip-sync quality**. Do not treat passing tests as a performance benchmark.

## Usage boundaries

Create fictional adult identities with the desired fashion or glamour direction, obtain permissions for any real likeness/footage/voice, use rights-cleared source media, disclose realistic synthetic media where relevant, preserve required OSS notices, and review every third-party model plus dependency license before commercial distribution. Bold adult glamour is supported; do not generate minors, explicit sexual acts, non-consensual content, real-person impersonation or deceptive endorsements, experiences or interactions that never happened.
