# AI Influencer Studio — project restore point

**Restore-point ID:** `2026-10-10-pre-phase-1-architecture`

**Created:** 10 October 2026 (Asia/Calcutta)

**Purpose:** This document freezes the agreed product direction, current implementation baseline, operating assumptions, model policy, safety boundaries, and next-step plan before the next architecture phase. Treat it as the decision and requirements restore point for this project.

> This is a documented restore point, not a binary source snapshot. The workspace currently has no Git repository, so exact code rollback requires keeping a copy of the complete project directory (including source, configuration, workflows and tests) or initializing Git and committing this baseline. Model weights, generated media, virtual environments and secrets are intentionally not part of the source restore point.

## 1. Product definition

AI Influencer Studio is a local/cloud-controlled production workspace for creating clearly disclosed media featuring original, fictional adult AI personas. The initial use case is fashion/lifestyle and glamour-oriented content that remains non-explicit and does not impersonate real people.

The application is designed around a no-paid-inference/API-credit workflow. The cloud provider still charges for GPU time, persistent storage, bandwidth and applicable taxes. Publicly downloadable model weights are not automatically obligation-free; every exact model revision and dependency must retain its license notices.

## 2. Canonical production flow

```text
Fictional adult persona
    → frozen identity capsule
    → rights-cleared master/reference image
    → image-to-video motion generation
    → optional local synthetic narration
    → FFmpeg assembly
    → manual media review
    → AI disclosure and export
    → series reuse
```

The persona and approved references are the source of truth. Each later asset must retain its parent persona/version, brief, model, seed and input lineage.

## 3. Current workflow status

### Already present in the project

- FastAPI + SQLite dashboard.
- Persona library and reference vault.
- Generation brief validation/import path.
- Connected pipeline navigation and grouped menu.
- Series planning and frozen persona concept.
- Media review/import path for files created by the direct CLI.
- Link tracking area.
- Workflow manager for verified ComfyUI API-format graphs.
- Monitoring tab and read-only `GET /api/monitor` checks.
- Direct local CLI pipeline in `studio/free_cli.py`.
- Optional ComfyUI API bridge.
- Default image and Wan2.2 API-format starter graphs in `workflows/`.
- Disclosure sidecar generation for direct pipeline exports.
- Unit/API tests and cloud smoke-test scripts.

### Current canonical menu

```text
Workspace
  Overview

Create
  Persona library
  New persona
  Reference vault
  Generation brief

Produce
  Image studio
  Video studio
  Voice & narration
  Series studio

Review & export
  Media review
  Approval queue
  Export packages
  Link tracking

Operations
  Workflow manager
  Monitoring
```

Groups collapse by default. The open state is remembered in the browser. The connected pipeline rail is:

```text
Persona → Brief → Master image → Motion video → Voice (optional) → Review & export → Series reuse
```

## 4. Current approved model set

The current allowlist is in `config/approved_models.json`.

| ID | Role | Current license label | Current status |
|---|---|---|---|
| `flux2-klein-4b` | Reference-conditioned master images | Apache-2.0 | Primary image model |
| `flux2-klein-base-4b` | Optional persona LoRA training base | Apache-2.0 | Training preparation only |
| `z-image-turbo` | Fast text-to-image alternative | Apache-2.0 | Optional draft model |
| `wan22-ti2v-5b` | Text/image-to-video | Apache-2.0 | Primary video model |
| `wan21-t2v-1.3b` | Lightweight 480p text-to-video fallback | Apache-2.0 | Fallback only; not identity I2V |
| `kokoro-82m` | Local narration | Apache-2.0 | Optional voice model |

The current direct CLI supports FLUX.2 Klein and Z-Image for images, Wan2.2 for video, Kokoro for voice and FFmpeg for assembly. Model selection is still partly hard-coded and is a major next-phase improvement.

## 5. Default workflow files

The project currently contains:

- `workflows/default_image_api.json` — generic ComfyUI API image graph using `{{CHECKPOINT}}` and prompt/seed/size placeholders.
- `workflows/wan22_ti2v_5b_default_api.json` — Wan2.2 TI2V 5B API graph using the official node pattern and placeholders such as `{{PROMPT}}`, `{{NEGATIVE_PROMPT}}`, `{{REFERENCE_IMAGE}}`, `{{SEED}}`, `{{WIDTH}}` and `{{HEIGHT}}`.

The application auto-detects these default graphs as available workflow entries. Model files, compatible ComfyUI nodes and exact runtime dependencies still need to exist on the render machine. Direct Python/CLI remains the primary no-credit path; ComfyUI is optional.

## 6. Persona and brief rules

### Persona identity capsule

Every persona should contain:

- Original fictional name.
- Adult age of 18 or older.
- Face geometry, skin tone, eyes, hair and fictional distinguishing feature.
- Physique, posture and movement cues.
- Wardrobe, fabrics, palette, accessories and grooming.
- Personality, interests, values, speech style and mannerisms.
- Cultural/world context, home base and recurring locations.
- Camera language, framing, lens/depth, lighting and colour grade.
- Fixed traits that must not drift.
- Approved synthetic or rights-cleared reference images.
- Disclosure language and content boundaries.

Frozen personas are versioned conceptually through an `identity_version`. Editing a frozen identity should create a new version rather than silently changing an existing series.

### Generation brief

The brief should contain:

- `schema_version` and title.
- Persona and identity anchor.
- Image prompt and negative prompt.
- Video/motion prompt and negative prompt.
- Canvas, aspect ratio, width, height, FPS and duration.
- Seed and quality profile.
- Selected image/video/voice workflow.
- Optional narration text and voice preset.
- Series and episode information.
- Review, rights and disclosure fields.

The JSON handoff is intended to be generated in ChatGPT, saved locally, validated, and then uploaded to the dashboard. Import must stage the values; it must never start a render automatically.

## 7. Safety, rights and publishing boundaries

The project supports fictional adult fashion/lifestyle and glamour direction. It must not be used for:

- Minors or youthful-looking characters.
- Explicit sexual acts.
- Non-consensual sexualized content.
- Real-person, celebrity or private-person impersonation.
- Face/voice likeness use without documented permission.
- Deceptive endorsements or fabricated real-world experiences.
- Circumventing platform policies or moderation.

Every final export requires manual review and a clear AI/synthetic disclosure. Keep model notices, source permissions, prompt metadata and disclosure records with the exported asset.

## 8. Hardware and deployment baseline

### Local Windows workstation

Known local configuration:

- AMD Athlon Silver 3050U.
- 20 GB RAM.
- Integrated AMD Radeon graphics with approximately 2 GB shared graphics memory.
- Approximately 1 TB total storage, mostly used.

Use this machine for VS Code, the dashboard, prompt/persona authoring, monitoring, database work, testing, review and lightweight CPU narration. It is not a practical target for Wan2.2 or large FLUX/Qwen/Mochi inference.

### Cloud render target

The selected cloud profile is approximately:

- RTX 6000 Pro-class GPU with 96 GB VRAM.
- 64 vCPU.
- 192 GB RAM.
- 300 GB persistent storage.

Use the cloud as the render worker. Keep the dashboard/control plane private and connect through SSH tunnelling or another authenticated private channel. Do not expose the unauthenticated local development dashboard publicly.

### Storage policy

Do not install every model at once. The recommended active profile is FLUX.2 Klein, Z-Image Turbo, Wan2.2 TI2V 5B, Wan2.1 T2V 1.3B, Kokoro and FFmpeg. Keep at least 20% disk free. Qwen, Mochi, LTX and other large experimental checkpoints should be optional and removable.

## 9. Deep-research model policy

### Recommended production tier

- FLUX.2 Klein 4B — master/reference image.
- Z-Image Turbo — fast image drafts.
- Wan2.2 TI2V 5B — identity-aware image-to-video.
- Wan2.1 T2V 1.3B — low-resource text-to-video fallback.
- Kokoro-82M — local narration.

### Candidate expansion tier

- Qwen Image and Qwen Image Edit — strong Apache-2.0 image/edit candidates, but large.
- Lumina-Image-2.0 — Apache-2.0 alternative image model.
- FLUX.2 Klein FP8 — lower-memory image distribution where quality is acceptable.

### Legal/compatibility review tier

- LTX-Video and LTX-2.
- HunyuanVideo-I2V.
- CogVideoX.
- Mochi 1.
- Stable Diffusion 3.5.
- OpenVoice, F5-TTS and CosyVoice.
- InstantID, PuLID and IP-Adapter.
- ControlNet/OpenPose/DWPose and other control checkpoints.

Do not describe the review-tier models as unrestricted open source. Code, weights, voice packs, detectors and custom nodes can have different licenses. Store the exact revision, license URL and dependency notices before enabling commercial output.

## 10. Required next architecture improvements

### P0 — before adding many new models

1. **Model registry:** ID, task, repository, exact revision, hashes, file manifest, license/SPDX label, model size, VRAM minimum/recommended, backend, capabilities, status and safety tier.
2. **Engine adapters:** common image/video/audio interfaces instead of model-specific `if` branches in `free_cli.py`.
3. **Capability matching:** show only models compatible with the requested task, reference inputs, resolution, backend and available VRAM.
4. **Render preflight:** GPU/driver/PyTorch, free VRAM, disk space, FFmpeg, Kokoro, Wan environment, model files, hashes, workflow placeholders and ComfyUI node compatibility.
5. **Model installer:** resumable downloads, explicit confirmation, disk estimator, checksum validation, license acceptance and cleanup.
6. **Cloud/local profiles:** separate control-plane and render-worker configuration with an active model cache profile.
7. **Lineage metadata:** persona version, input references, model revision, workflow, seed, prompts, parameters, hardware profile, hashes and disclosure.
8. **Queue reliability:** retry, cancel, resume after restart, GPU locking, idempotency, OOM fallback, progress and failure diagnostics.

### P1 — quality and consistency

1. Identity similarity and face-landmark checks against the frozen master.
2. Frame sampling and contact sheets for every video.
3. Blur, flicker, frame-corruption, anatomy and sudden-identity-change warnings.
4. Model-specific prompt compilation from one canonical creative brief.
5. Fixed benchmark persona/scenes for latency, peak VRAM, quality, identity score and flicker.
6. Persona snapshots and immutable series continuity bibles.
7. Voice presets, loudness normalization, silence trimming and optional subtitles.
8. Human approval remains mandatory; automated checks only flag risk.

### P2 — scale and operations

1. Optional LoRA/adapter training per persona after quality testing.
2. Quantization, offload, tiling and multi-GPU profiles.
3. Structured logs, metrics, alerts and failure taxonomy.
4. Dependency lockfiles, SBOM and license reports.
5. Experimental model catalog behind explicit legal/quality gates.

## 11. Monitoring tab target

The Monitoring tab should be divided into:

- API and database.
- GPU, CUDA/ROCm and driver.
- CPU/RAM/disk.
- ComfyUI connection and node inventory.
- Wan2.2 environment.
- FFmpeg and Kokoro runtime.
- Installed model files and hashes.
- Workflow validity and dependency compatibility.
- Queue state, retry counts and throughput.
- Last successful/failed render.
- Quality warnings and review backlog.

`READY`, `CHECK` and `ERROR` should remain the visible statuses, with actionable diagnostics and a timestamp. Monitoring must remain read-only and must not download models or start inference.

## 12. Recommended user experience

The dashboard should guide one user action at a time:

1. Create or import a persona.
2. Add a reference and freeze identity.
3. Load a generation brief.
4. Choose an image profile/model.
5. Generate and approve a master image.
6. Choose a video profile/model and motion brief.
7. Add optional narration.
8. Queue, monitor and inspect output.
9. Approve/reject with disclosure.
10. Reuse the frozen persona for the next episode.

The Overview screen should show recent generated images/videos, active jobs, frozen personas, next action and system status without unnecessary scrolling. Creative production remains separate from the advanced Workflow Manager and Monitoring operations areas.

## 13. Restore and rollback instructions

If future work diverges from this direction:

1. Stop implementation and read this file first.
2. Preserve the current `data/`, `generated/` and `.env` files separately.
3. Restore source files from the project backup that corresponds to this restore-point ID.
4. Reinstall only the approved active model profile.
5. Run the test suite and cloud smoke test.
6. Run Monitoring and resolve `ERROR` states before rendering.
7. Reconfirm persona, rights, disclosure and model licenses.

Because the workspace is not currently a Git repository, the recommended immediate operational safeguard is to make a timestamped copy of the project directory excluding caches, virtual environments, model weights and generated media. A later implementation phase should initialize Git and tag the resulting commit as `restore-2026-10-10-pre-phase-1`.

## 14. Canonical project references

- `README.md` — project overview and local/cloud usage.
- `docs/CLOUD_DEPLOYMENT.md` — cloud VM runbook.
- `docs/LOCAL_FREE_SETUP.md` — local free setup.
- `docs/FREE_MODEL_RESEARCH.md` — current model/license research snapshot.
- `docs/GENERATION_BRIEF.md` — ChatGPT brief and persona handoff rules.
- `docs/SERIES_GUIDE.md` — frozen persona and series workflow.
- `docs/NAVIGATION.md` — menu and connected pipeline.
- `docs/MONITORING.md` — monitoring behavior.
- `docs/WORKFLOW_GUIDE.md` — ComfyUI/API workflow guidance.
- `config/approved_models.json` — current model allowlist.
- `config/workflow_catalog.json` — workflow catalog.
- `workflows/default_image_api.json` — default image API graph.
- `workflows/wan22_ti2v_5b_default_api.json` — default Wan2.2 API graph.

## 15. Confirmation gate

This restore point freezes the state before implementing the model-registry, adapter, preflight, quality-gate and reliability phases. No new model or architecture change should be implemented against this baseline without explicitly updating this file or creating a new numbered restore point.
