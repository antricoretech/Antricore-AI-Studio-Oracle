# Step-by-step VS Code local setup (no paid API / no credit usage)

## 0. Hardware decision

| Local GPU situation | Start with | Video recommendation |
|---|---|---|
| No NVIDIA GPU | dashboard + CPU Kokoro, evaluate model options | don't expect practical large video generation locally |
| 6–8GB VRAM | experiment with quantized ComfyUI models / offload (NOT tested in this package) | Wan2.1 T2V-1.3B on 480p with offload (text-video, not persona-conditioned) |
| 12GB VRAM | FLUX.2 Klein with CPU offloading may be possible, not guaranteed | Wan2.2 TI2V 5B official reference setup unlikely at 720p |
| 16GB VRAM | FLUX.2 Klein 4B and optional Z-Image Turbo | video still benefits from quantization or increased VRAM |
| 24GB+ VRAM | recommended for photo + video stack | Wan2.2 TI2V-5B 720p official CLI with offload |

Before spending bandwidth, run `python -m studio.free_cli doctor` and examine your GPU name and VRAM. CPU-only and Intel/AMD/Apple hardware require different model-specific configurations not provided as a turnkey profile here.

## 1. Windows install

Install Git, VS Code, Python 3.12, NVIDIA driver and FFmpeg. Open the extracted project in VS Code. In PowerShell:

```powershell
.\scripts\setup-free-windows.ps1 -DownloadTools
.\.venv\Scripts\python.exe -m studio.free_cli doctor
```

Install a compatible PyTorch release for your GPU from https://pytorch.org/get-started/locally/ . **Verify torch.cuda.is_available() == True** before inference:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.__version__)"
.\.venv\Scripts\python.exe -m pip install -r requirements-local-image.txt
```

Clone only official repositories you need (does not install models):

```powershell
.\scripts\clone-github-repos.ps1 -Names ComfyUI,Flux2,AIToolkit,Wan22,Kokoro
```

### Cloud Linux deployment

The recommended RTX6000 Pro cloud instance is a deployment target, not a
replacement for local source development. Upload or clone the repository on a
Linux GPU VM, then run:

```bash
bash scripts/bootstrap-cloud.sh
```

Install the provider-compatible CUDA PyTorch wheel first, then install the
optional image and download dependencies:

```bash
bash scripts/bootstrap-cloud.sh --image --download
```

Add `--voice` if Kokoro narration is needed. The script never downloads model
weights automatically. Keep `models/`, `generated/` and `data/` on persistent
storage, and keep the dashboard bound to `127.0.0.1` when accessing it through
an SSH tunnel. Do not commit `.env`, model weights or generated media.

## 2. Download a licensed model once

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli download --model flux2-klein-4b --yes
```

Downloads public Hugging Face **files** to `models/flux2-klein-4b/`; this is not a pay-per-generation API. To train LoRA, download a separate Base checkpoint:

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli download --model flux2-klein-base-4b --yes
```

Do not download every model unless your GPU and disk capacity justify it. Run `doctor` again to see which model directories are present.

## 3. Generate master portrait

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli image --offline --cpu-offload --prompt "Photorealistic head-and-shoulders editorial photograph of an original fictional adult woman in her late 20s, dark wavy hair, brown eyes, subtle freckles, natural studio daylight, neutral background, realistic skin texture, fully clothed, no brands, professional photographic composition" --width 768 --height 1152 --steps 4 --seed 44 --output generated\master.png
```

On an appropriately large GPU, `--cpu-offload` can be omitted for better speed. If the pipeline runs out of memory, reduce resolution; note larger DRAM and offloading are not guaranteed to solve every issue.

## 4. Generate new scenes using the same reference

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli image --offline --cpu-offload --reference generated\master.png --prompt "Make a different photographic scene featuring EXACTLY the same fictional adult woman shown in the reference: outdoors at an early-morning coffee shop, soft natural sunlight, new casual jacket, candid smile, realistic human face, no face-swap artifacts" --width 768 --height 1152 --seed 45 --output generated\scene_01.png
```

To use more than one reference, repeat `--reference path/to/file.png`. The model is not a mathematically perfect identity lock; evaluate facial stability and curate a high-quality multi-angle identity library before LoRA training.

## 5. Local text-to-speech

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
.\.venv\Scripts\python.exe -m studio.free_cli voice --voice af_heart --text "Hi, welcome to my studio. This is an AI-generated character." --output generated\narration.wav
```

On some systems, `espeak-ng` is required for language phonemes. This generates synthetic narration; do not clone real individuals without their consent.

## 6. Local image-to-video with Wan2.2

**Prefer WSL2 Ubuntu / Linux for Wan2.2's demanding video dependencies.** In PowerShell, clone the source and download public weights:

```powershell
.\scripts\clone-github-repos.ps1 -Names Wan22
.\.venv\Scripts\python.exe -m studio.free_cli download --model wan22-ti2v-5b --yes
```

Create a **separate** Python environment inside `external/Wan22` (on Linux/WSL2 is recommended):

```bash
cd external/Wan22
python3.12 -m venv .venv
source .venv/bin/activate
# Install matching NVIDIA/CUDA PyTorch per official upstream instructions.
pip install -r requirements.txt
```

From the **Studio root**, use the Studio's Python or call the separate Wan Python explicitly. First generate a dry-run command:

```bash
python -m studio.free_cli video --reference generated/master.png --prompt "The exact same fictional adult woman as the reference smiles and turns toward the lens; smooth gentle motion, stable face" --python external/Wan22/.venv/bin/python --output generated/reel.mp4 --dry-run
```

After dependencies are confirmed, remove `--dry-run`. For Windows, pass an absolute path to the Wan environment's `python.exe`. The Studio automatically selects **Wan2.2 TI2V-5B**, **`704*1280`** portrait video area, and local prompt processing, with **no Dashscope/cloud API**. Official Wan guidance lists **at least 24GB GPU VRAM for 720p** with offloading.

If you lack a 24GB GPU, consider optimized ComfyUI quantized workflows but those require their own installation/compatibility tests. The 1.3B Wan2.1 fallback is **text-to-video**, not the same image-to-video identity control.

## 7. Assemble audio and video locally

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli mux --video generated\reel.mp4 --audio generated\narration.wav --output generated\reel_with_voice.mp4
```

**Mux != lip-sync.** The narration plays with video; facial movement is not automatically synchronized to speech. For lip-sync experimentation, MuseTalk is optional; verify the licenses of every included detector/weight and avoid rights-uncleared pretrained dependencies for a commercial pipeline.

### Complete local-only pipeline

Once the separate Wan2.2 environment is ready, the image, video, optional
narration and mux stages can be run together:

```bash
python -m studio.free_cli pipeline --dry-run \
  --prompt "Photorealistic editorial portrait of an original fictional adult woman, fully clothed, natural daylight" \
  --video-prompt "The same fictional adult character smiles and walks naturally toward the camera; stable face, gentle motion" \
  --narration "Welcome to my fictional AI studio." \
  --python external/Wan22/.venv/bin/python
```

Remove `--dry-run` after verifying the model directories and environments. The
pipeline runs entirely on local/cloud-hosted weights, writes each intermediate
artifact for review, and creates a disclosure sidecar next to the final video.

## 8. LoRA training (identity refinement)

The MIT-licensed Ostris AI Toolkit supports `black-forest-labs/FLUX.2-klein-base-4B`. Clone it, install its documented environment and use its GUI/CLI to set: base model `FLUX.2-klein-base-4B`, your curated photos, a unique fiction-only identity token, and a dedicated output folder. Its rapidly changing training UI/config means no untested turnkey training config is shipped. **A trained LoRA and automated adapter injection into this CLI are not yet included.** Don't select the Klein 9B or FLUX.2 dev checkpoint, whose weights are non-commercial.

## 9. Original dashboard / ComfyUI (optional)

Run `python -m uvicorn studio.app:app --host 127.0.0.1 --port 8000`. It gives persona catalog, reference uploads, result review and job tracking. To render from dashboard, first manually install ComfyUI, import a graph tested with approved Apache-weight checkpoints, and export the ComfyUI **API JSON** into Studio Workflows. For the direct CLI path, use Media Review's **Import a completed pipeline output** form after the local pipeline finishes; imported files remain pending until manual review and disclosure confirmation. No default SDXL jobs are preloaded in this edition because SDXL presets have been removed.

## 10. Cost, licensing, completeness checklist

- [ ] Model weight license verified for **exact** model ID and version (not simply Github source)
- [ ] Appropriate VRAM/system RAM/disk space available
- [ ] GitHub code cloned separately from publicly hosted free weights
- [ ] GPU-specific PyTorch installed; dependencies isolated
- [ ] Synthetic persona and original/consented footage only
- [ ] Narration original and audience AI disclosure appropriate
- [ ] Required Apache/MIT/GPL attribution and NOTICE files preserved where applicable
- [ ] Model outputs visually approved before commercial posting
- [ ] No cloud API keys, paid inference endpoints or restricted weights added through custom ComfyUI nodes

**Guarantee boundary:** This package's tests validate Python commands and APIs using mocks, not GPU feasibility, photorealistic quality, model download success, dependency resolution on every Windows driver, or production scalability. Full automated character LoRA training and synchronized mouth animation remain integration work.
