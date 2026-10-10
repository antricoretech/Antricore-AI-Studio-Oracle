# Cloud deployment runbook

This document deploys the AI Influencer Studio to a Linux GPU VM and runs the
local-only fictional-adult fashion/lifestyle pipeline:

```text
fictional persona -> FLUX master image -> Wan2.2 image-to-video
-> optional Kokoro narration -> FFmpeg mux -> manual review + disclosure
```

The cloud VM performs inference locally. The pipeline does not call a hosted
image/video API and does not consume generation credits. The GPU provider still
charges for VM runtime, persistent storage, bandwidth and any applicable tax.

## 1. Target cloud configuration

The documented target is the selected `gpu.rtx6000pro.96g` instance:

- 96 GB advertised GPU memory (verify with `nvidia-smi`)
- 64 vCPU
- 192 GB system RAM
- 300 GB persistent SSD
- Linux image with SSH access

The runbook also works on another NVIDIA Linux VM if it has enough VRAM. The
core Wan2.2 TI2V-5B path should be treated as a 24 GB minimum workload; lower
memory machines require different optimization and are not this deployment
target.

## 2. What is deployed where

### Local Windows workstation

- Source editing in VS Code
- API/UI development
- Unit and integration tests
- Prompt and persona review
- Git/source synchronization

Do not copy the local `.venv`, model weights or generated media unless they are
needed for a specific backup. The local integrated Radeon GPU is not the
inference target.

### Cloud GPU VM

- CUDA-enabled PyTorch
- FLUX image environment
- Separate Wan2.2 environment
- Kokoro voice dependencies when narration is enabled
- FFmpeg
- Approved model weights
- `generated/` outputs and dashboard `data/`

## 3. Persistent storage and directory layout

Place the project on the provider's persistent SSD volume. Do not keep model
weights on an ephemeral boot disk. A suitable layout is:

```text
/mnt/ai-influencer-studio/       persistent project volume
  .env                            local server configuration (never commit)
  .venv/                          Studio control-plane environment
  models/                         approved Hugging Face weights
  external/Wan22/                 official Wan source + separate venv
  generated/                      master images, videos and audio
  data/                           SQLite database, references and workflows
```

The application uses `DATA_DIR` for dashboard data. If the project is mounted
at `/mnt/ai-influencer-studio`, set:

```bash
export DATA_DIR=/mnt/ai-influencer-studio/data
```

Keep at least 20% of the 300 GB volume free. Start with FLUX Klein 4B and Wan2.2
TI2V-5B; add optional checkpoints only after measuring remaining space.

## 4. Provider and network preparation

Before connecting, confirm with the provider:

1. `nvidia-smi` exposes the advertised GPU and memory.
2. CUDA drivers are installed and compatible with the available PyTorch wheel.
3. The 300 GB disk is persistent across stop/start operations.
4. SSH key authentication is enabled.
5. Port 22 can be restricted to your own IP address.
6. The instance is not preemptible unless its storage and restart behavior are
   understood.
7. Download bandwidth and egress charges are acceptable.

Do not expose the Studio port publicly. The dashboard is intentionally a local
development control panel without authentication. Use an SSH tunnel instead.

## 5. First SSH connection

From Windows PowerShell, replace the placeholders with the provider values:

```powershell
ssh -i $env:USERPROFILE\.ssh\ai-studio-cloud.pem ubuntu@SERVER_IP
```

On the VM, identify the persistent volume and mount it according to the
provider's instructions. Do not format a disk containing existing data. Then:

```bash
df -h
mkdir -p /mnt/ai-influencer-studio
cd /mnt/ai-influencer-studio
```

The exact mount command varies by provider; verify the mount with `df -h` before
downloading model weights.

## 6. Install operating-system packages

Use the provider's current Ubuntu image. The commands below install only basic
build/runtime tools; do not replace the provider's NVIDIA driver blindly.

```bash
sudo apt-get update
sudo apt-get install -y git ffmpeg build-essential curl ca-certificates
python3.12 --version
ffmpeg -version | head -n 1
nvidia-smi
```

If `python3.12` is unavailable, install it using the OS/provider-supported
method first. Do not use an unrelated Python version for the Wan environment.

## 7. Transfer or clone the source

### Preferred: private Git repository

Create a private repository containing source code only, then clone it onto the
persistent volume:

```bash
cd /mnt/ai-influencer-studio
git clone YOUR_PRIVATE_REPOSITORY_URL app
cd app
```

The repository must not contain `.env`, `.venv`, `models/`, `generated/`,
`data/`, or `external/` artifacts. The included `.gitignore` excludes those
paths.

### Alternative: VS Code Remote-SSH or file upload

If the project has no Git remote, upload the source through VS Code Remote-SSH,
WinSCP or another authenticated file-transfer tool. Exclude these directories
from the upload:

```text
.venv/  models/  generated/  data/  external/  .pytest_cache/
```

After transfer, verify that `README.md`, `studio/`, `scripts/`, `config/` and
`tests/` are present.

## 8. Bootstrap the Studio environment

From the project root on the VM:

```bash
cd /mnt/ai-influencer-studio/app
export DATA_DIR=/mnt/ai-influencer-studio/data
bash scripts/bootstrap-cloud.sh
```

This creates `.venv`, installs the control-plane dependencies, creates `.env`
when absent, and runs the diagnostic command. It does not download model
weights and does not install CUDA/PyTorch automatically.

## 9. Install CUDA-enabled PyTorch

Use the official PyTorch selector for the exact provider driver/runtime:

<https://pytorch.org/get-started/locally/>

Install the selected command inside the Studio environment, then verify the
GPU before installing Diffusers:

```bash
.venv/bin/python -c "import torch; print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"
.venv/bin/python -c "import torch; print(round(torch.cuda.get_device_properties(0).total_memory/1024**3, 1), 'GiB')" 
```

The first command must print `cuda True`. If it does not, stop and correct the
driver/PyTorch installation before downloading large weights.

Install the optional Studio dependencies:

```bash
bash scripts/bootstrap-cloud.sh --image --download --voice
```

Use `--voice` only if narration is needed. Kokoro may download its public voice
data the first time it is used.

## 10. Clone the official Wan2.2 source

The video backend uses a separate Python environment to isolate Wan's rapidly
changing dependencies:

```bash
bash scripts/clone-github-repos.sh Wan22
cd external/Wan22
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
```

Install the CUDA-compatible PyTorch wheel in this environment as well, then
follow the official Wan2.2 installation instructions:

<https://github.com/Wan-Video/Wan2.2>

```bash
.venv/bin/python -m pip install -r requirements.txt
cd ../..
```

The Studio's `.venv` and `external/Wan22/.venv` are intentionally separate.

## 11. Download only the approved core models

Run these commands from the Studio root:

```bash
.venv/bin/python -m studio.free_cli download --model flux2-klein-4b --yes
.venv/bin/python -m studio.free_cli download --model wan22-ti2v-5b --yes
```

Optional models should be added one at a time after checking disk space:

```bash
.venv/bin/python -m studio.free_cli download --model flux2-klein-base-4b --yes
.venv/bin/python -m studio.free_cli download --model z-image-turbo --yes
```

Do not download every available checkpoint by default. Model files are large,
and model licenses apply to the exact revision downloaded. Retain the model
card URL and revision in your deployment notes.

Confirm the installation:

```bash
.venv/bin/python -m studio.free_cli doctor
```

The doctor output must show CUDA available and the expected model directories.

## 12. Run the non-destructive cloud smoke test

```bash
bash scripts/cloud-smoke-test.sh
```

This checks GPU visibility, FFmpeg, Python dependencies, the test suite and the
pipeline dry-run. It does not generate media or download additional weights.

Expected result: CUDA is available, tests pass, and the dry-run reports
`"inference": "local-only"`.

## 13. Test the Wan command before rendering

Generate and inspect the exact command without running video inference:

```bash
.venv/bin/python -m studio.free_cli video \
  --reference generated/master.png \
  --prompt "The same fictional adult character smiles and walks naturally toward the camera; stable face, gentle motion" \
  --python external/Wan22/.venv/bin/python \
  --output generated/reel.mp4 \
  --dry-run
```

The reference image must exist. Create it with the image command or use the
pipeline dry-run first.

## 14. Run the complete local-only pipeline

First inspect the plan:

```bash
.venv/bin/python -m studio.free_cli pipeline --dry-run \
  --offline --cpu-offload \
  --prompt "Photorealistic editorial portrait of an original fictional adult woman in her late 20s, fully clothed, natural daylight" \
  --video-prompt "The same fictional adult character smiles, walks slowly toward the camera and turns naturally; stable face and body, no text" \
  --narration "Welcome to my fictional AI studio." \
  --python external/Wan22/.venv/bin/python
```

After confirming the paths, remove `--dry-run`:

```bash
.venv/bin/python -m studio.free_cli pipeline \
  --offline --cpu-offload \
  --prompt "Photorealistic editorial portrait of an original fictional adult woman in her late 20s, fully clothed, natural daylight" \
  --video-prompt "The same fictional adult character smiles, walks slowly toward the camera and turns naturally; stable face and body, no text" \
  --narration "Welcome to my fictional AI studio." \
  --python external/Wan22/.venv/bin/python \
  --output generated/reel_with_voice.mp4
```

If narration is not required, omit `--narration`; the pipeline then produces a
video without Kokoro or FFmpeg muxing. Each stage writes an intermediate file
for manual review. The final command writes a disclosure sidecar beside the
video. A sidecar is a review aid, not a substitute for the platform's own AI
label or disclosure controls.

## 15. Optional dashboard access through an SSH tunnel

Start the dashboard on the VM, bound only to loopback:

```bash
cd /mnt/ai-influencer-studio/app
export DATA_DIR=/mnt/ai-influencer-studio/data
.venv/bin/python -m uvicorn studio.app:app --host 127.0.0.1 --port 8000
```

From the local Windows workstation, create the tunnel:

```powershell
ssh -i $env:USERPROFILE\.ssh\ai-studio-cloud.pem -N -L 8000:127.0.0.1:8000 ubuntu@SERVER_IP
```

Open `http://127.0.0.1:8000` locally. Do not change the server bind address to
`0.0.0.0` unless authentication and a hardened reverse proxy are implemented.

The dashboard's ComfyUI queue is optional. It is not required for the direct
FLUX -> Wan2.2 -> Kokoro -> FFmpeg pipeline documented here.

After every cloud start or restart, open the dashboard's **Monitoring** tab
below Link tracking and click **Run checks**. Confirm the API/database, GPU
runtime, Wan2.2 environment, FFmpeg/Kokoro dependencies, model directories,
workflow inventory, queue and persistent storage before starting a render.
The check is read-only and does not download weights or invoke inference.

## 16. Review and publication checklist

Before saving or publishing an output:

- Confirm the character is fictional and adult.
- Confirm all reference images, driving videos and voices are owned or used
  with permission.
- Check face identity, hands, anatomy, temporal flicker and unwanted text.
- Check the narration and audio/video alignment.
- Confirm the output does not imply a real person's endorsement or identity.
- Preserve model/software license notices in any distributed application.
- Add a clear AI-generated/synthetic-media disclosure where required.
- Keep rejected outputs out of public folders and remove them when no longer
  needed.

Audio muxing is not lip-sync. If a future lip-sync or character-animation
backend is added, it must be reviewed separately for model, dependency and
input-media licensing before use.

## 17. Updates and backups

Update source code without deleting the persistent model directory:

```bash
cd /mnt/ai-influencer-studio/app
git pull --ff-only
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

Back up at least:

- `.env` (securely, not in Git)
- `data/studio.db`
- `data/references/`
- approved generated outputs
- model manifest/revision notes

Model weights can usually be re-downloaded; generated media and persona
references may not be recoverable. Use the provider's volume snapshots when
available.

## 18. Stop the server and control cost

When not generating media:

1. Stop the Uvicorn process.
2. Stop or suspend the GPU instance through the provider dashboard.
3. Keep the persistent storage volume if it contains models/data.
4. Confirm the billing state and disk snapshot status.

At the quoted ₹101.87/hour, leaving the GPU running continuously is
approximately ₹74,365 per 730-hour month, before storage, bandwidth and tax.

## 19. Troubleshooting

### `CUDA: unavailable`

Run `nvidia-smi`, verify the NVIDIA driver, and reinstall the PyTorch wheel
selected for that driver. Do not proceed to model downloads until CUDA is true.

### `Weights absent` or `Clone Wan22 first`

Run the model download command and clone the official Wan repository. Ensure
commands are run from the Studio root and paths are correct.

### Out-of-memory during image generation

Keep `--cpu-offload`, reduce width/height, close other GPU processes and run
only one generation at a time.

### Out-of-memory during Wan generation

Use the official offload flags through the current wrapper, reduce the video
area or length, and confirm no other model is occupying the GPU. Do not assume
multiple GPUs combine VRAM for this single-process path.

### `ffmpeg` not found

Install it with the OS package manager and rerun the doctor command.

### Dashboard data disappeared after restart

The project or `DATA_DIR` is on ephemeral storage. Move it to the persistent
volume and verify with `df -h` before creating new personas.

### Model download fills the disk

Stop the download, remove only the incomplete/unneeded model directory, clear
unused Hugging Face caches, and keep the core FLUX + Wan2.2 set. Do not delete
the persistent volume or project root recursively.

## 19A. Phase 7 deployment readiness and browser smoke checks

After starting Uvicorn through the private SSH tunnel, run the explicit
readiness gate:

```bash
export STUDIO_URL=http://127.0.0.1:8000
.venv/bin/python scripts/deployment-readiness.py --url "$STUDIO_URL"
```

The cloud profile blocks when authentication, CUDA, FFmpeg, required model
weights, model revisions or core storage checks are not ready. Set
`STUDIO_REQUIRED_MODELS` on the server to override the default
`flux2-klein-4b,wan22-ti2v-5b` selection. A model with an unpinned revision is
deliberately not production-ready; record the exact Hugging Face commit/tag in
`config/approved_models.json` after verifying the model card.

The check is read-only. It does not queue work, download weights or call a
hosted inference API. For a local source-only sanity check, omit `--url`.

For browser-level verification, install the optional dependency and run the
dashboard smoke test while the server is available through the same tunnel:

```bash
.venv/bin/pip install -r requirements-browser.txt
.venv/bin/playwright install chromium
.venv/bin/python scripts/browser-smoke-test.py --url "$STUDIO_URL"
```

The browser test checks the dashboard shell, grouped navigation, generation,
workflow and monitoring panels. It does not create a persona, upload media or
queue a render.

The existing smoke script remains non-destructive by default. To intentionally
run one GPU render using an already validated local brief, opt in explicitly:

```bash
RUN_RENDER_SMOKE=1 \
STUDIO_RENDER_BRIEF=/mnt/ai-influencer-studio/app/config/generation_brief.example.json \
STUDIO_RENDER_OFFLINE=1 \
bash scripts/cloud-smoke-test.sh
```

This writes media and consumes GPU time; review and remove the generated test
outputs after validation. Never enable it from an unattended startup hook.

## 20. Deployment completion criteria

Deployment is complete only when all of the following are true:

- `nvidia-smi` shows the expected GPU.
- `torch.cuda.is_available()` is `True` in the Studio and Wan environments.
- `cloud-smoke-test.sh` passes.
- FLUX master image generation succeeds.
- Wan2.2 dry-run and real image-to-video generation succeed.
- Optional Kokoro audio generation and FFmpeg mux succeed, if enabled.
- The disclosure sidecar is produced.
- Outputs and dashboard data survive a stop/start test.
- The dashboard is reachable only through the SSH tunnel.
- Model and software license records are stored with the deployment notes.
