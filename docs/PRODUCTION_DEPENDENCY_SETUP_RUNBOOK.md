# Production Dependency Setup Runbook

This runbook records the dependency and runtime sequence for installing and validating AI Influencer Studio on the declared production target:

- Apple MacBook with M5 processor
- 16 GB unified memory
- 512 GB storage
- Local canonical and legacy applications kept as separate runtimes

This is a preparation document. It does not authorize installation by itself.
Generation models, model weights, identity adapters, and model repositories remain
deferred until the final model-installation gate is explicitly approved.

## Current baseline

The current development environment already has the application and test tooling
required for non-model work:

- FastAPI, Uvicorn, HTTPX, Pillow, Pydantic, multipart handling, and dotenv support
- Pytest and pytest-asyncio
- Playwright package and browser validation previously completed
- Python keyring for the publishing secret-storage boundary
- Node.js/npm for frontend tooling
- FFmpeg is available on the current Windows development host, but must be
  independently validated on the production Mac
- `pip check` currently passes

The following model-generation packages are intentionally absent from the current
environment:

- PyTorch
- Diffusers
- Transformers
- Accelerate
- Safetensors
- Hugging Face Hub client
- NumPy
- SoundFile
- Kokoro
- OpenCV
- InsightFace and its ONNX runtime support
- IP-Adapter source/package
- ComfyUI and any custom nodes

No model weights or model repositories are installed.

## Installation sequence

Perform the following stages in order on the production Mac. Stop at a failed
validation gate; do not continue to model installation until the application and
runtime gates pass.

### Stage 0 — Preserve and inspect the baseline

1. Clone or update the repository from the approved `main` branch.
2. Confirm the working tree is clean.
3. Confirm the Python version selected for the project.
4. Create a project-local virtual environment.
5. Record macOS version, M5 model, unified-memory size, free disk space, Python
   version, and Git commit in the production setup record.
6. Do not place model files inside Git-tracked directories unless the project
   storage policy explicitly permits it.

Validation gate:

```text
git status --short --branch
python --version
python -m pip --version
df -h
```

Expected result: clean repository, supported Python runtime, and enough free space
for the selected model set plus temporary caches and generated media.

### Stage 1 — Install application and development dependencies

Install the project’s ordinary application dependencies first:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-browser.txt
python -m pip install -r requirements-publishing.txt
```

Install the Playwright browser only if the production validation plan requires
browser smoke testing:

```text
python -m playwright install chromium
```

Validation gate:

```text
python -m pip check
python -m pytest -q tests
python -m compileall -q studio tests
```

Expected result: application tests pass without importing or executing generation
models. Existing non-blocking deprecation warnings must be recorded rather than
silently ignored.

### Stage 2 — Validate media tooling

Confirm that the Mac has a native FFmpeg executable and that it can read and write
the media formats required by the application.

Validation gate:

```text
ffmpeg -version
ffprobe -version
```

Then run the project’s media-container and export tests. If FFmpeg is absent or
uses an incompatible architecture, stop and resolve it before video/audio work.

### Stage 3 — Install the Apple Silicon image runtime

Install the PyTorch build recommended for the target Apple Silicon/macOS/Python
combination. Do not copy a CUDA or Windows wheel to the Mac. Record the exact
package versions and source URL after installation.

Then install the image pipeline dependencies from the project manifest:

```text
python -m pip install -r requirements-local-image.txt
```

This stage covers:

- PyTorch and MPS execution
- Diffusers pipeline loading
- Transformers text encoders
- Accelerate device/offload helpers
- Safetensors checkpoint loading
- Hugging Face Hub access for the later approved download step

Validation gate before any model download:

```text
python -c "import torch; print(torch.__version__); print(torch.backends.mps.is_available())"
python -c "import diffusers, transformers, accelerate, safetensors, huggingface_hub; print('image runtime imports passed')"
python -m pip check
```

Expected result: imports succeed, MPS availability is reported accurately, and no
CUDA-specific path is selected.

### Stage 4 — Install identity and visual-quality dependencies

Identity consistency is a separate dependency layer from the base image model.
The repository’s identity-conditioning scripts currently reference:

- OpenCV
- InsightFace
- An ONNX runtime compatible with Apple Silicon
- IP-Adapter FaceID source/package
- NumPy

Before installing, pin versions that are compatible with the selected Python and
MPS runtime. The current project manifests do not yet fully enumerate this layer;
the install record must capture the exact packages, repositories, revisions, and
licenses used.

Validation gate:

```text
python -c "import cv2, numpy, insightface; print('vision runtime imports passed')"
```

Do not download identity adapter checkpoints at this stage unless the final model
gate has been approved. Code packages and model weights must be recorded
separately.

### Stage 5 — Install optional voice dependencies

Only install this stage if narration or voice generation is included in the
production scope:

```text
python -m pip install -r requirements-voice.txt
```

This provides the Kokoro runtime, SoundFile, and NumPy. The Kokoro model files and
voice assets remain subject to the final model gate.

Validation gate:

```text
python -c "import kokoro, soundfile, numpy; print('voice runtime imports passed')"
python -m pip check
```

### Stage 6 — Install optional ComfyUI runtime

ComfyUI is an optional local backend for graph-based image, video, and audio
workflows. It is not required for the direct legacy SDXL renderer or for ordinary
canonical application development.

If selected for production:

1. Install ComfyUI in a separately managed local runtime directory.
2. Install only approved custom nodes required by the selected workflows.
3. Record each node repository, commit, license, and compatibility result.
4. Configure `COMFYUI_URL` to a local address only.
5. Validate the health and workflow API without submitting a model job.

Validation gate:

```text
GET http://127.0.0.1:8188/system_stats
GET http://127.0.0.1:8188/object_info
```

The application must continue to start when ComfyUI is offline if ComfyUI is not
part of the selected production profile.

### Stage 7 — Final model and asset installation gate

This stage requires explicit approval after all earlier stages pass.

Do not install every model in the registry. Select one primary image model after
the target-Mac benchmark and keep only the compatibility or fallback models that
are justified by the production workflow.

### Image-model selection matrix

| Model ID | Intended role | Production recommendation | License / decision note | Runtime note |
|---|---|---|---|---|
| `flux2-klein-4b` | Canonical primary image generation and reference-image editing | **Primary benchmark candidate** for the M5/16 GB Mac | Apache-2.0; verify the exact model-card terms and current release before installation | Requires measured MPS memory, speed, identity consistency, and adult/glamour prompt-quality testing |
| `juggernaut-xl-v10` | Legacy SDXL photoshoot and existing legacy content compatibility | **Legacy compatibility model** | CreativeML OpenRAIL++-M; verify commercial-use terms for the selected checkpoint | Explicitly supported by `studio/diffusion_engine.py`; checkpoint filename/path is fixed and must not be substituted |
| `cyberrealistic-xl` | Alternative legacy SDXL photorealism baseline | **Optional legacy fallback** | CreativeML OpenRAIL++-M; verify commercial-use terms for the selected checkpoint | Explicitly supported by `studio/diffusion_engine.py`; benchmark against Juggernaut before retaining both |
| `z-image-turbo` | Fast image-generation benchmark and possible lightweight alternative | Optional | Apache-2.0; verify model-card terms and output quality | Benchmark latency, MPS memory, hands/face quality, and identity stability before production use |
| `flux2-klein-base-4b` | Training/reference and identity-conditioning experimentation | Not required for first production setup | Apache-2.0; use only if the training/reference workflow is approved | Do not install merely because it is in the registry; it is not the first-line generation model |
| `pony-diffusion-v6-xl` | Specialized SDXL style/content experimentation | **Do not install by default** | Fair AI Public License 1.0-SD; monetized inference and commercial-use restrictions require explicit legal review | Style bias and license constraints make it unsuitable as the default commercial influencer model |
| `flux1-dev-gguf` | Legacy FLUX experiment | **Exclude from commercial production** | FLUX.1-dev Non-Commercial License | Keep out of the commercial production install unless the use case and license are explicitly approved |

The recommended first production benchmark set is:

1. `flux2-klein-4b` as the canonical primary candidate.
2. `juggernaut-xl-v10` for legacy SDXL compatibility.
3. `cyberrealistic-xl` only if it wins a measured legacy-quality comparison.
4. `z-image-turbo` only if its speed and quality justify a separate runtime path.

The benchmark must use the new Master Persona structure and include front,
three-quarter, profile, full-body, lifestyle, adult/glamour, and product-content
scenarios. Adult/glamour packs remain part of the Identity Core and must be
evaluated for identity consistency, body/wardrobe continuity, disclosure, review,
and canonical-anchor lineage—not treated as an unrelated model test.

The image model is only one part of the production stack. Install the selected,
license-verified assets together with the explicitly approved supporting assets:

- Base image model
- Identity-conditioning adapter and face encoder
- Video model, if video is enabled
- Voice model, if narration is enabled
- Required VAE, text encoder, tokenizer, and auxiliary files
- Approved ComfyUI checkpoints or custom-node assets

For every asset record:

- Model or asset ID
- Upstream URL and exact revision
- License and commercial-use interpretation
- File checksum
- Download date and installer identity
- Disk usage
- Expected and measured peak unified-memory usage
- Supported resolution and workflow
- Removal/rollback procedure

Do not mix checkpoints between model IDs. The legacy SDXL runtime uses explicit
checkpoint mappings and must fail if its declared file is missing; it must never
select an unrelated file from the models directory.

## Production validation sequence after installation

Run these in order:

1. `pip check`
2. Application unit and API tests
3. Canonical application startup and readiness check
4. Legacy application startup and route-boundary check
5. FFmpeg/media-container validation
6. Image runtime import and MPS capability check
7. Model registry and checkpoint-path preflight
8. One controlled identity benchmark case
9. One controlled content-pack case, including adult/glamour Identity Core
   authority and review state
10. Video/audio smoke tests only if those runtimes and models were approved
11. Publishing remains disabled until Instagram staging credentials, account
    allowlist, public-media configuration, and explicit operator approval are
    complete

No production account should receive generated or published content until the
asset review, rights, disclosure, identity-lineage, and destination-policy gates
pass.

## Rollback and recovery

- Keep the pre-install Git commit recorded.
- Use a separate virtual environment or an environment lock/export for each
  production attempt.
- Remove or disable only the failed dependency layer; do not delete generated
  assets or the canonical database as part of dependency rollback.
- Keep model caches outside the source tree so dependency rollback cannot remove
  application code.
- If MPS memory pressure occurs, stop generation, preserve the failure evidence,
  and reduce resolution/concurrency only through an approved configuration change.
- Never resolve a missing checkpoint by renaming or substituting another model.

## Final installation record template

Complete this for every installation activity:

```text
Date/time:
Operator:
Mac model / macOS:
Git commit:
Python version:
Virtual-environment path:
Component/register ID:
Package or repository:
Exact version/revision:
Source URL:
License:
Command used:
Validation command:
Validation result:
Disk usage:
Peak unified-memory usage:
Rollback/removal command:
Notes / known warnings:
```

## Current pending register

| Register ID | Component | Current status | Gate |
|---|---|---|---|
| RUNTIME-001 | PyTorch Apple Silicon/MPS build | Not installed | Feature/final |
| RUNTIME-002 | Diffusers, Transformers, Accelerate, Safetensors, Hugging Face Hub | Not installed | Feature/final |
| RUNTIME-003 | ComfyUI and approved custom nodes | Not installed | Optional feature/final |
| RUNTIME-004 | FFmpeg | Present on Windows host; Mac validation pending | Feature |
| RUNTIME-005 | OpenCV and auxiliary vision/identity packages | Not installed; manifest expansion required | Feature/final |
| Voice runtime | Kokoro, SoundFile, NumPy | Not installed | Optional feature |
| RUNTIME-006 | Playwright and Chromium | Installed | Feature |
| RUNTIME-007 | Python keyring and OS backend | Installed; Mac Keychain validation pending | Feature |

Models and model weights remain tracked separately as `MODEL-001` through
`MODEL-004` and must remain `NOT INSTALLED` until the final approval gate.
