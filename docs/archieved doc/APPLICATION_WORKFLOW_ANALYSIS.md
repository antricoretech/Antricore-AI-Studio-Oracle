# AI Influencer Studio — Application Workflow Analysis

**Purpose:** Future reference for understanding the current application workflow, execution paths, architectural strengths, risks, and improvement priorities.

**Analysis scope:** Read-only inspection of the current repository. No code, configuration, dependency, installation, database, or generated-media changes were made as part of this analysis.

**Primary evidence inspected:** `README.md`, `docs/WORKFLOW_GUIDE.md`, `docs/NAVIGATION.md`, `docs/SERIES_GUIDE.md`, `docs/MONITORING.md`, `studio/app.py`, `studio/api_v2.py`, `studio/orchestrator.py`, `studio/database.py`, `studio/repositories.py`, `studio/diffusion_engine.py`, `static/app.js`, `static/modules/*.js`, `config/workflow_catalog.json`, and the API/frontend/ComfyUI tests.

## Executive view

The application is designed as a local-first creative production control plane for fictional synthetic-media personas. Its intended lifecycle is:

```text
Start local app
  → inspect readiness and available engines/workflows
  → create or import a persona
  → synthesize persona DNA and establish identity anchors
  → generate/freeze a reference vault
  → write a photo/video/narration brief
  → compile prompts and choose an engine/workflow
  → run generation asynchronously
  → store outputs with lineage, disclosure and quality metadata
  → manually review and approve
  → export/package or use the approved output in a series
```

This is a sensible production workflow. The strongest concept is the separation between identity setup, creative direction, generation, and review. The main weakness is that the implementation currently has multiple overlapping versions of those stages:

1. **Core control-plane workflow:** FastAPI + SQLite under `/api/...`.
2. **V2 Master Vault workflow:** JSON persona library + background 13-pack generation under `/api/v2/...`.
3. **Orchestrator/photoshoot workflow:** prompt synthesis and direct diffusion rendering, also exposed partly through `/api/v2/orchestrator/...` and partly through SQLite-backed routes.

The product therefore feels like a capable studio assembled in phases, rather than one fully unified pipeline. This is not inherently bad, but the boundaries need to become explicit before adding more automation such as social publishing, scheduled posting, or multiple persona accounts.

## End-to-end workflow map

### 1. Startup and local readiness

The FastAPI application starts through `studio.app:app`. Its lifespan initializes SQLite storage, creates the data directories, tracks active async jobs, and cancels unfinished in-process tasks during shutdown. Static files are served from `static/`; generated media is served from `generated/`.

The monitoring path checks:

- API availability.
- Optional bearer-token security configuration.
- SQLite availability and free storage.
- Optional ComfyUI connection and checkpoint visibility.
- Installed versus catalog-only workflows.
- FFmpeg, Kokoro, Wan2.2 runtime, Python, and CUDA checks.
- Active, failed, cancelled, and retried job counts.

**View:** This is a good operational entry point. The distinction between “catalog recipe” and “installed/verified graph” is particularly valuable because it prevents a catalog entry from being mistaken for a runnable generation backend. The current readiness signal is still a diagnostic snapshot, not a hard execution gate; some warnings can remain while users continue into generation.

### 2. Persona creation and identity setup

The UI’s primary persona workflow begins with a narrative. The narrative is sent to `/api/v2/personas/synthesize`, which produces structured persona DNA: name, age, origin, biometrics, master prompt, negative constraints, and diversity ringfences.

When the user selects “Generate & Freeze 13-Image Master Vault,” the frontend re-synthesizes the current narrative, then sends the result to `/api/v2/personas/create`. That route:

1. Derives a persona ID from the name.
2. Builds a `PersonaSpecification`.
3. Uses `MasterPersonaPromptBuilder` to create 13 reference-pack specifications.
4. Stores the persona and pack metadata in `data/personas_v2.json`.
5. Creates a `generated/master_persona_<persona_id>` directory.
6. Starts a daemon background thread for sequential pack generation.
7. Returns a job ID immediately.

The frontend polls `/api/v2/personas/vault-status/{job_id}` and updates the pack progress UI. The worker reuses an existing non-trivial file when present, otherwise calls the diffusion engine, copies the render into the persona folder, records completion in an in-memory/cache-backed job tracker, and marks the vault complete after all 13 packs are processed.

**View:** The user experience is clear: describe → inspect synthesized DNA → generate vault → monitor progress → use the persona. The freeze concept is also useful because repeatable series should not silently change identity.

**Important qualification:** The current “freeze” is primarily a workflow/state convention and file-generation milestone. It is not yet a rigorous, immutable persona version with cryptographic references to every pack, model, prompt, seed, and review decision. The v2 JSON record can be changed by the application, and the background job status is only partially durable.

### 3. Persona selection and active context

The frontend maintains an active persona selection and uses it across the dashboard, orchestrator, photo studio, gallery, and series views. On refresh, persona state is loaded and the active persona is reselected.

There are multiple sources for persona context:

- `data/personas_v2.json` for the v2 persona library and 13-pack URLs.
- SQLite `personas` for the core API, jobs, assets, references, series, and lineage.
- Hardcoded/default persona records and generated asset catalogs in v2 code.
- Frontend assumptions such as fallback avatars and a preference for a named persona in Photo Studio.

**View:** The active-persona UX is appropriate for a multi-persona studio. However, the application does not yet have a single canonical persona repository. A user can create a persona through one path and then encounter incomplete or different representations in another path. This is the most important workflow-level issue.

### 4. Prompt and creative brief preparation

The app supports several prompt-entry patterns:

- Freeform persona narrative synthesis.
- Generation brief JSON validation through `/api/briefs/validate`.
- DNA-driven prompt compilation through `/api/v2/orchestrator/compile-dna-prompt`.
- Scene suggestions through `/api/v2/orchestrator/suggest-scenes`.
- Photo Studio preset compilation through `/api/photo-studio/compile-prompt`.
- Manual image/video job submission through the legacy job form.

The DNA compiler combines persona biometrics, narrative, framing, lens, lighting, and one of four stylistic variations. Photo Studio combines persona appearance with selected location, costume, expression, and angle presets, then presents a prompt for user approval.

**View:** Prompt compilation is one of the strongest product ideas in the repository. It gives users structured creative controls while preserving a stable identity suffix. The danger is duplication: several prompt builders independently encode identity, negative prompts, aspect ratios, and defaults. Over time, two screens can produce materially different prompts for the same persona and scene.

### 5. Generation engine selection

The system supports two broad execution routes:

#### A. Direct/local engine paths

The free CLI and diffusion engine are intended for local model execution, including image generation and some local video/narration orchestration. This is the more direct route for Apple Silicon or other local environments, subject to model and memory limits.

#### B. ComfyUI control-plane path

The dashboard discovers installed API-format workflows, imports verified JSON graphs, substitutes placeholders such as `{{PROMPT}}`, `{{NEGATIVE_PROMPT}}`, `{{CHECKPOINT}}`, `{{WIDTH}}`, `{{HEIGHT}}`, `{{SEED}}`, `{{REFERENCE_IMAGE}}`, and `{{AUDIO_FILENAME}}`, then submits the graph to a separately running ComfyUI instance.

**View:** The adapter model is a good design choice. It allows the app to remain a control plane rather than embedding every model runtime. The workflow catalog/readiness distinction reduces operator confusion.

The limitation is that “workflow available,” “model installed,” “backend reachable,” and “hardware capable” are separate conditions. The current preflight and monitor endpoints report them, but the product workflow would benefit from making them visibly sequential: a user should know exactly which condition blocked a render before queueing it.

### 6. Job queue and asynchronous execution

For the core route, `/api/jobs` validates:

- Persona existence.
- Rights confirmation.
- Workflow existence and API-format validity.
- Required checkpoint, reference image, and audio inputs.
- Canvas dimensions.
- Persona ownership of selected assets/references.
- Approval and rights status for source and audio assets.

The job is persisted in SQLite with request JSON and lineage JSON, then scheduled as an asyncio task. Execution moves through queued → running → submitted → completed or failed. On success, ComfyUI outputs are downloaded into `data/outputs`, hashed, measured, quality-checked, and inserted into the assets table. Series episodes are updated through the job relationship.

**View:** This is the most mature workflow in the codebase. It has meaningful validation, lineage, output normalization, review state, retry/cancel support, and test coverage. The explicit approval requirement before animating a source asset is a good safety and quality boundary.

**Operational risk:** The queue is process-local. SQLite records the job, but the actual task lives in the current server process. Restart recovery marks active jobs as interrupted, but it does not reconstruct and resume the actual work automatically. This is acceptable for a local single-user studio, but it will matter for long video renders or unattended publishing.

### 7. Photo Studio direct-generation route

Photo Studio compiles a prompt and calls `/api/photo-studio/generate`. This route invokes an engine directly and stores the resulting image as an asset. The frontend displays a progress sequence, then refreshes the media-review state.

This route is intentionally more immediate than the ComfyUI job queue. It is convenient for interactive image exploration.

**View:** Photo Studio is a good exploratory UX, but it is not fully aligned with the core job lifecycle. It can become a parallel rendering system with different metadata, defaults, review behavior, and storage semantics. For a production workflow, interactive renders should still emit the same canonical job/asset/lineage records as queued renders.

### 8. Review, approval, disclosure, and export

Generated/imported assets are represented in SQLite with:

- Persona and optional job association.
- File kind and filename.
- Prompt.
- Review state (`pending`, `approved`, etc.).
- Rights confirmation.
- Disclosure text.
- SHA-256 hash.
- Media metadata.
- Quality report.

The review route allows the operator to approve or reject media. Approved assets can be packaged with a manifest and `AI-DISCLOSURE.txt`. The application therefore treats generation and publication-readiness as separate stages.

**View:** This separation is exactly right for the intended product. It should remain a hard boundary even if future Instagram automation is added. “Generated” must never automatically mean “publishable.”

The main weakness is inconsistency across render paths. The core ComfyUI path creates pending assets with rich provenance. Some v2/direct/fallback paths use their own files, in-memory records, or simplified asset inserts. That can make the gallery show something that is visually available but not equally auditable.

### 9. Series workflow

Series creation requires a frozen persona. The series stores a shared prompt and individual episodes, each with an image prompt and a video-motion prompt. Queueing an episode selects the latest available reference or approved image, builds a core job, and links the episode to that job.

**View:** This is a strong bridge from one-off creation to repeatable content production. The requirement to freeze identity before creating a series is correct. The selection rule “latest reference or latest approved image” is convenient but potentially risky: “latest” is not always “canonical.” A later approved image may be a scene variation rather than an identity anchor.

### 10. Social publishing boundary

The current repository contains research and documentation for Instagram integration, but the inspected implementation does not yet provide a production Instagram publishing workflow. The current application stops at generation, review, packaging, and link tracking.

That boundary is healthy. Future publishing should consume only approved, disclosure-ready assets and should reference a specific persona/account mapping, content decision, approval event, and publish attempt. It should not be connected directly to raw generation output.

## Architecture and state-flow assessment

### What is working well

1. **The stages are conceptually separated.** Identity, prompt construction, rendering, review, and export are understandable as separate responsibilities.
2. **The core job route has useful controls.** Rights checks, reference ownership, approval gating, lineage, retries, cancellation, and output hashing are meaningful production features.
3. **The app is local-first.** The operator can inspect readiness, run SQLite locally, use local files, and connect to optional engines.
4. **The workflow catalog is operationally explicit.** Catalog recipes are not falsely advertised as installed graphs.
5. **The series model is directionally correct.** A frozen persona is a prerequisite for repeatability.
6. **Disclosure and packaging are built into the asset model.** This is a strong foundation for responsible publishing automation.

### Main workflow risks

#### 1. Multiple persona stores

The v2 JSON persona store and SQLite persona store are not the same record. The v2 Master Vault creates a persona in JSON, while core routes create personas in SQLite. Orchestrator routes primarily query SQLite. This can produce a persona that appears in one part of the UI but lacks the references, assets, identity capsule, or frozen state expected by another part.

**Impact:** Cross-screen persona inconsistency, wrong anchor selection, duplicated personas, and future account-assignment errors.

#### 2. Multiple render paths

The ComfyUI job pipeline, v2 direct orchestration, Photo Studio generation, and fallback display paths do not share exactly the same execution and provenance contract.

**Impact:** Inconsistent review state, metadata quality, storage location, retry behavior, and auditability.

#### 3. “Freeze” is not a true version boundary

The database has `identity_locked` and `identity_version`, while the v2 JSON record has generated pack metadata and vault status. These are useful flags, but there is no single immutable version object that binds the persona definition to exact reference files and generation settings.

**Impact:** A future edit, replacement reference, or regenerated pack may look like the same persona even when the visual identity has changed.

#### 4. Reference selection can be semantically wrong

Series queueing and some UI flows choose the latest reference or latest approved image. That is a chronological rule, not an identity-quality rule.

**Impact:** A scene render, casual image, or alternate angle could become the anchor for future episodes.

#### 5. Background vault generation is only partially durable

The vault generation tracker uses process memory plus a JSON cache and a daemon thread. It can detect some incomplete files after restart, but the generation transaction is not represented as a normal persistent job with per-pack records and strong idempotency.

**Impact:** Duplicate work, ambiguous partial completion, and unclear recovery after interruption.

#### 6. Frontend workflow logic is still partly duplicated

The frontend has modular files, but the main `static/app.js` still contains substantial orchestration, persona, vault, prompt, and generation logic. This increases the chance that one view’s state or endpoint assumptions drift from another’s.

**Impact:** UI behavior can be correct in one route while stale or inconsistent in another.

#### 7. Defaults are not always neutral

Some UI and orchestration paths include named-persona preferences, fallback image URLs, hardcoded biometric descriptions, or default model choices. Those are useful demo defaults, but they can leak into a multi-persona production workflow if a selection is missing.

**Impact:** Content can be generated for the wrong persona or with a demo identity fallback.

## Recommended target workflow

The current workflow should converge toward this explicit state machine:

```text
PersonaDraft
  → PersonaSynthesized
  → PersonaVersionReview
  → PersonaVersionFrozen
  → ReferencePackGeneration
  → ReferencePackReview
  → PersonaVersionReady
  → BriefDraft
  → BriefApproved
  → RenderQueued
  → Rendered
  → AssetReview
  → AssetApproved
  → ExportReady
  → OptionalPublishQueued
  → Published / Failed / Retriable
```

The important design point is that each downstream stage should receive an explicit immutable identifier rather than infer context from “latest,” “active,” a filename, or a fallback persona.

## Prioritized improvement suggestions

### Priority 1 — Establish one canonical persona aggregate

Create a documented canonical persona record that owns:

- Stable persona ID.
- Version ID.
- Narrative and structured DNA.
- Freeze status.
- Canonical front anchor.
- Approved reference-pack members.
- Model/checkpoint/prompt/seed provenance.
- Rights and disclosure status.
- Optional publishing-account bindings.

The JSON v2 representation and SQLite operational records can remain as implementation details, but every route should resolve through the same canonical identity contract.

**Expected benefit:** Prevents cross-workflow persona drift and gives future social automation a reliable identity/account owner.

### Priority 2 — Make reference roles explicit

Distinguish `canonical_identity_anchor`, `vault_reference`, `scene_source`, `approved_thumbnail`, and `derived_asset`. Do not choose anchors by recency alone.

**Expected benefit:** Safer series continuity and fewer accidental identity changes.

### Priority 3 — Unify all generation paths behind one render contract

Interactive Photo Studio, orchestrator renders, CLI imports, and ComfyUI jobs should all produce the same conceptual records: request, execution, output asset, lineage, quality result, and review state.

**Expected benefit:** Consistent media review, retry, export, and future publication behavior.

### Priority 4 — Turn vault generation into a persistent workflow

Represent the vault as a parent job with 13 child pack tasks. Persist each pack’s state, prompt, seed, model, source, output hash, and review state.

**Expected benefit:** Reliable restart/retry behavior and auditable identity creation.

### Priority 5 — Replace implicit fallback behavior with visible blocking states

If no persona, anchor, model, or compatible workflow is selected, the UI should block and explain the missing requirement. Demo fallback images should be clearly marked as previews and never silently enter a production asset path.

**Expected benefit:** Fewer wrong-persona renders and easier diagnosis.

### Priority 6 — Keep generation and publication strictly separate

Future Instagram integration should accept only assets that are approved, rights-confirmed, disclosure-ready, and associated with a frozen persona version. The publishing layer should never call a raw diffusion endpoint as part of posting.

**Expected benefit:** Stronger compliance, reproducibility, and operator control.

### Priority 7 — Make readiness a workflow gate

Expose a single preflight result for each render request that clearly answers:

- Is the persona version ready?
- Is the selected anchor approved?
- Is the workflow installed and valid?
- Is the model present and compatible?
- Is the engine reachable?
- Is the canvas supported?
- Is storage sufficient?
- Are rights and disclosure inputs complete?

**Expected benefit:** Less trial-and-error and fewer jobs that fail after queueing.

## Suggested operating procedure for the current codebase

Until the architecture is consolidated, the safest current operator workflow is:

1. Start the app on loopback.
2. Check Operations → Monitoring and resolve critical warnings.
3. Use one persona creation path consistently for a given persona; do not recreate the same persona through both v2 JSON and SQLite routes.
4. Complete the Master Vault generation and manually inspect the front, profiles, macro, and baseline packs.
5. Treat the front anchor as the canonical identity source; do not rely on the latest generated image.
6. Use prompt compilation to create a brief, then review the resulting prompt before rendering.
7. Prefer the core job route for auditable production renders; use Photo Studio for exploration only until its metadata path is unified.
8. Review and approve every output before using it as a source or series asset.
9. Export the approved package and disclosure sidecar for downstream use.
10. Keep future publishing as a separate, approval-gated stage.

## Non-obvious findings

### Finding 1 — The project’s largest risk is state divergence, not model integration

The code already has several model/engine adapters and substantial validation. The harder problem is that identity and asset state can be represented differently depending on which UI route created them.

**Confidence:** High; directly supported by the separate JSON and SQLite paths.

### Finding 2 — The core queue is more production-ready than the newer visual workflows

The SQLite job path has stronger validation, lineage, review, retry, cancellation, and test coverage than the direct orchestrator/v2 paths. The newest-looking UI is not necessarily the most durable execution path.

**Confidence:** Medium-high; supported by route behavior and tests.

### Finding 3 — The “latest approved image” rule is a hidden identity risk

Approval status proves that an image passed review; it does not prove that it is the correct identity anchor. A scene image can be approved and still be a poor reference for future identity preservation.

**Confidence:** High; supported by series queue selection logic.

### Finding 4 — The application is ready for a publishing layer only after asset provenance is normalized

The existing disclosure, rights, review, hash, manifest, and lineage fields are a good foundation. However, the multiple generation paths mean that not every visible result is equally complete as a publishable asset.

**Confidence:** Medium-high.

### Finding 5 — The local-first design is appropriate for the current product stage

SQLite, local files, optional ComfyUI, and read-only readiness checks are a reasonable fit for a single-operator studio. Distributed queues and cloud control would add complexity before the identity/state model is unified.

**Confidence:** Medium; this is an architectural judgment based on the current scope and deployment documentation.

## Final assessment

The application has a promising production workflow and a strong conceptual foundation: create a fictional persona, freeze identity references, produce repeatable media, review it, and export it with disclosure and provenance. The core workflow is coherent enough for local single-user experimentation and controlled image/video production.

The next architectural milestone should not be another generation feature. It should be workflow consolidation: one canonical persona/version model, one reference-role system, one render/asset contract, and one explicit approval boundary before publishing. Once those are in place, Instagram account assignment and multi-persona automation can be added without making the publishing layer responsible for resolving ambiguous identity or asset state.

