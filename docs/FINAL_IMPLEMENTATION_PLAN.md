# Final Implementation Plan — AI Influencer Studio

**Status:** Phase 0 runtime hardening completed; Phase 2 Master Persona and ContentPack core completed on its dedicated branch; Phase 1 reconciliation and cross-cutting legacy parity remain tracked  
**Target:** Local-first modular monolith on a 16 GB unified-memory Mac  
**Goal:** Build a reliable AI influencer persona and content-creator studio from persona design through reviewed, export-ready, and optionally publishable content.

## Implementation boundary

This document remains the implementation roadmap and decision record. Runtime implementation is now authorized; each completed activity must be verified and recorded in `docs/IMPLEMENTATION_TRACKING.md` before the next activity is marked complete.

## Final architecture recommendation

Keep the application as a modular monolith:

~~~text
FastAPI API
  + SQLite system of record
  + canonical local asset storage
  + persistent local job runner
  + image/video/audio adapters
  + review and provenance services
  + optional platform publishing service
~~~

Do not introduce microservices, Kubernetes, distributed queues, or a vector database yet. Consolidate identity, jobs, assets, review, and provenance first.

The key decision is:

> SQLite becomes the canonical system of record. JSON becomes import/export, backup, and interchange format rather than a second live persona database.

## Complete product journey

~~~text
Workspace startup
  → readiness checks
  → persona draft
  → persona synthesis
  → Identity Core generation
  → identity/reference review
  → PersonaVersion freeze
  → creator personality setup
  → lifestyle/world setup
  → content-pillar setup
  → content brief
  → render preflight
  → persistent render job
  → identity/content quality checks
  → manual review
  → export package
  → optional platform publishing
  → analytics feedback
~~~

## Current code-to-target mapping

| Current area | Current role | Target role |
|---|---|---|
| studio/app.py | Main FastAPI routes | Thin API/controller layer |
| studio/api_v2.py | JSON personas and Vault jobs | Persona/version service using canonical persistence |
| studio/orchestrator.py | Prompt compilation and direct rendering | Prompt service plus common render-job submission |
| studio/diffusion_engine.py | Direct SDXL rendering | Model adapter with reference conditioning and job contract |
| studio/database.py | SQLite schema and transactions | Canonical persistence and migrations |
| studio/repositories.py | Partial persistence boundary | Persona, version, pack, job, asset, review and publishing repositories |
| studio/schemas.py | HTTP request schemas | Versioned API/domain contracts |
| studio/brief.py | JSON brief contract | ContentBrief import/export contract |
| static/app.js | Large workflow controller | Gradually decomposed feature modules |
| static/modules/*.js | Modular frontend features | Standard frontend implementation pattern |
| generated/ and data/outputs/ | Multiple media locations | One canonical storage resolver |
| tests/ | Core API/mock coverage | Domain, integration, E2E and AI-evaluation coverage |

## Canonical domain model

### Persona

Stable creator identity: id, display name, fictional-adult status, disclosure, and creation time.

### PersonaVersion

Immutable snapshot containing identity capsule, creator profile, lifestyle world, audience profile, content strategy, status, and frozen time.

### ReferencePack

Reference groups with explicit roles:

~~~text
identity_core
creator_style
lifestyle
adult_glamour
commercial_brand
~~~

### ReferenceAsset

Every reference records role, file, prompt, model, workflow, seed, hash, review status, quality status, and canonical eligibility.

### ContentBrief

Every brief records PersonaVersion, content pillar, format, narrative, visual direction, emotional goal, platform, disclosure, and approval status.

### Job and Asset

All rendering paths use the same lifecycle:

~~~text
Brief → RenderRequest → Job → Execution → Asset → QualityResult
      → ReviewDecision → Export or Publish
~~~

## Master Persona design

The Master Persona must become a Creator Identity System rather than only a 13-image visual vault.

### Identity Core

Recommended calibration set:

- Neutral front.
- Left and right 3/4 views.
- True left and right profiles.
- Neutral back.
- Neutral full body.
- Smile, serious, closed-eye, and speaking expressions.
- Eye and mouth macro.
- Hands and distinctive-feature macro.

### Creator Style Pack

Fashion, fitness, casual, resort, selfie, and UGC visual style references.

### Lifestyle Pack

Home, café, city, workspace, travel, fitness, fashion, vacation, bedroom, and hotel environments.

### Adult/Glamour Pack

Adult/glamour packs must not be isolated from the Identity Core. They must:

1. Guide adult/glamour content style.
2. Provide eligible canonical identity anchors when explicitly reviewed and approved.

Planned categories include boudoir, lingerie, stockings/corsetry, nude artistic/editorial glamour, sensual portrait campaigns, intimate lifestyle scenes, adult beauty/product campaigns, and restricted commercial glamour.

The correct model is one unified reference authority system:

~~~text
ReferenceAsset
  ├── identity_authority: canonical | supporting | style_only
  ├── content_class: general | adult_glamour | lingerie | nude_editorial
  ├── canonical_flag: true | false
  ├── review_status: pending | approved | rejected
  └── destination_policy: local_only | review_required | eligible
~~~

An adult/glamour image may become a canonical identity anchor when it passes identity, quality, age, rights, consent, disclosure, and review checks. Adult images must not automatically become canonical merely because generation succeeded.

Required boundaries remain:

- Explicitly fictional adult persona.
- Clear adult presentation.
- Rights and consent confirmation.
- No minors or age-ambiguous personas.
- No real-person sexual impersonation.
- No non-consensual or exploitative content.
- Manual review before approval.
- Platform-policy review before publishing.

## Implementation phases

### Phase 0 — Baseline and contracts

Define domain objects, lifecycle states, API contracts, storage conventions, logging, correlation IDs, and architecture decision records.

Exit: every route has a domain owner and every generated file maps to a documented asset contract.

### Phase 1 — Canonical Persona and PersonaVersion

- Make SQLite canonical.
- Convert the v2 JSON persona data to import/export.
- Add immutable PersonaVersion records.
- Add explicit canonical reference selection.
- Add reference roles and pack-level review.
- Make series and jobs reference PersonaVersion.

Current foundation slice completed: SQLite now persists a PersonaVersion snapshot
for each persona, freeze returns the frozen version, series stores the bound
version ID, and queued-job lineage records the version number and ID. v2 JSON
compatibility import/export is now active, and uploaded references carry their
bound PersonaVersion, role, content class, review, and rights metadata. Full
archive lifecycle reconciliation, pack-level review, and downstream version
enforcement remain the next Phase 1 activities.

The rich v2 vault is now normalized into ReferencePack and ReferencePackItem
records. Adult/glamour packs retain `identity_authority=identity_and_style`,
remain review-pending, and are canonical-eligible only after explicit review.
Archive and restore preserve pack metadata while remapping records to the
restored PersonaVersion.

Phase 1 review/linkage slice completed: reference-pack and item review APIs
now require rights confirmation before approval; pack review is invalidated by
unsafe item changes; canonical selection requires an approved eligible pack,
approved item(s), approved rights-confirmed image assets, matching
PersonaVersion lineage, and an existing media file. Pack items now link to the
unified assets table, generated/imported media carries PersonaVersion lineage,
and rejecting a linked asset automatically clears its canonical selection.

Migration boundary: existing personas and their existing generated/reference
packs are legacy/reference-only after the new implementation is released.
They must not be used as the production source for newly created Master
Personas. New production personas receive new unique IDs and are created
through the canonical Persona, immutable PersonaVersion, ReferencePack,
ReferencePackItem/Asset, ContentPack, review, and lineage flow. Existing
records remain preserved for inspection, export, audit, or explicit import;
they are not deleted, silently converted, or automatically promoted into
canonical identity anchors.

Exit: Vault, Orchestrator, Photo Studio, CLI, and series workflows resolve the same persona/version.

### Phase 2 — Unified Master Persona and content packs

- Reclassify the current 13-pack into explicit reference roles.
- Add 3/4 views, expression references, neutral full body, hands, and details.
- Add creator-style, lifestyle, commercial, and adult/glamour packs.
- Permit reviewed adult/glamour assets to become canonical anchors.
- Record authority, content class, review, consent, rights, and policy metadata.

Phase 2 first slice completed: ContentPack and ContentPackItem persistence now
binds every production content pack to one PersonaVersion and one reviewed,
canonical ReferencePack. The resolver returns style directives together with
approved identity anchors. Adult/glamour ContentPacks force
`identity_core=true` and `identity_authority=identity_and_style`, so they guide
content style while remaining part of the canonical identity system. Jobs and
series queueing can resolve an approved ContentPack or fall back to the
approved canonical asset for the active PersonaVersion.

Phase 2 UI slice completed: the focused `/content-packs` workspace lets an
operator select a Master Persona, inspect eligible canonical ReferencePacks,
author style directives and metadata, create a pending ContentPack, explicitly
approve/reject it, and resolve its final canonical anchors. The adult/glamour
family (`adult_glamour`, `lingerie`, `boudoir`, and `nude_editorial`) is forced
through the same Identity Core plus style authority rule at the backend boundary
so UI choices cannot downgrade these packs into style-only presets.

The frontend API-client foundation is also complete: the shared module now
normalizes API errors, propagates request cancellation, retries only safe GET
requests on transient failures, and provides JSON GET/POST/PATCH helpers. The
ContentPack workspace consumes this adapter; remaining legacy screens still
require migration before the frontend workstream exits.

The first canonical shell slice is available at `/workspace`. It provides
API-backed navigation for Overview, Master Personas, ReferencePacks,
ContentPacks, Production Queue, Asset Review, and Publishing Readiness. The
legacy `/` route remains available during migration and will not be replaced
until the canonical screens reach parity and pass regression coverage.

The next frontend slice is also complete: `/workspace#personas` now creates a
new Master Persona through the canonical API with structured identity
characteristics and an explicit fictional-adult disclosure, preserves the new
persona as the active selection, displays its immutable PersonaVersion lineage,
and exposes the guarded draft-to-frozen transition. This keeps identity
creation aligned with the new Persona/PersonaVersion boundary; existing legacy
personas remain preserved and are not reused. Model installation remains a
final-gate activity.

ReferencePack review is now available at `/workspace#references`. Operators
can review packs and items, confirm rights, link PersonaVersion-compatible
image assets, inspect canonical eligibility diagnostics, and explicitly select
or clear canonical anchors. The same gates apply to adult/glamour packs, which
remain eligible to serve as Identity Core anchors when approved; the UI cannot
downgrade that authority to style-only.

Asset Review is now available at `/workspace#assets`. It keeps generated and
imported media pending until an explicit decision, shows quality, rights,
disclosure, and PersonaVersion lineage, supports approve/reject/pending
transitions through the canonical API, and exposes package export only for
approved assets. It now also loads active-persona ReferencePack linkage so
stale and mismatched canonical relationships are visible before reuse.

Production Queue is now available at `/workspace#production`. It exposes the
Persona/PersonaVersion, rights/disclosure, and final model-installation gates,
shows active/completed/failed counts, preserves job and ContentPack lineage,
surfaces errors, and provides guarded cancel/retry actions through the existing
job API. Generation authoring remains gated by workflow readiness, read-only
preflight, explicit rights confirmation, and the final model-installation
boundary.

The generation-authoring flow is now integrated into the same Production view.
It loads workflow readiness, keeps catalog recipes disabled until their local
verified graph is available, captures prompt/canvas/ContentPack/rights inputs,
calls the read-only `/api/preflight` contract, and enables queue submission
only after a passing result. This validates the application flow without
installing or executing any image, audio, or video generation model.

The canonical shell now also makes stale lineage explicit. ReferencePack
items explain missing assets, rejected or pending review, rights blocks,
eligibility failures, and PersonaVersion mismatches; pack summaries count
stale canonical candidates and identify invalidated selections. Asset Review
loads the active persona's ReferencePack links and exposes a dedicated
Reference linkage panel, while ContentPacks show a stale-anchor warning when
their approved anchors no longer match the bound PersonaVersion. This keeps
adult/glamour packs inside the same Identity Core lineage and prevents a
stored-but-invalid media link from being mistaken for a reusable canonical
anchor.

Responsive and keyboard smoke coverage is now part of the canonical workspace
gate. The page provides a skip link, labelled main landmark, explicit loading
busy state, and a 320px toolbar constraint; fixture-driven Chromium validation
covers 320, 768, 1024, and 1440px layouts, named interactive controls, no
horizontal overflow, and page-error detection.

The certification gate is now automated for the canonical workspace: pinned
axe-core 4.10.2 reports zero WCAG 2A/2AA violations across the seven views,
Chrome's accessibility tree exposes the main/navigation/heading landmarks,
and fixture scenarios cover loading, base API failure, view API failure, and
empty-persona recovery. Error announcements use `role="alert"`, while normal
status updates remain polite. Manual VoiceOver/Narrator verification is still
an operational follow-up rather than a claim of complete assistive-technology
certification.

Legacy-shell parity has started with a bounded bridge. The root `/` V2 shell is
still preserved, now loads its app entrypoint as a module, exposes a direct
`/workspace` link, and has a real-tab smoke gate with axe and accessibility-tree
checks. It has not been retired because its vault, orchestrator, story studio,
gallery, and system/telemetry feature surfaces are not yet feature-equivalent
to the canonical journey. The next migration work should move those remaining
capabilities behind canonical contracts one surface at a time, preserving `/`
until replacement parity and regression evidence are complete.

The migration bridge now includes explicit legacy-to-canonical handoffs: Master
Vault opens Master Personas, Generate opens Production, Story opens ContentPacks,
Gallery opens Asset Review, and System opens Overview. These links make the
canonical journey reachable from every preserved legacy surface without
silently changing the legacy behavior. Full feature-equivalent replacement and
legacy retirement still require surface-by-surface migration and regression
evidence.

Legacy handoffs also preserve the active identity. The legacy persona selector
now updates each canonical destination with `persona_id`, and `/workspace`
resolves that query against the canonical Persona registry before loading the
requested view. This keeps PersonaVersion context aligned across the bridge
without creating a second client-side identity store.

The root shell's direct “Open Canonical Workspace” entry follows the same
rule, so users cannot lose the selected Persona simply by leaving a legacy tab
through the global bridge.

Canonical Production also binds a successful preflight to the exact workflow
and dimensions it validated. If those inputs change, the preflight is cleared;
an in-flight response whose inputs are no longer current is discarded and the
user must validate again before queueing.

The preserved legacy Gallery now exposes an item-level handoff to canonical
Asset Review. The handoff uses the asset's owning Persona ID rather than the
currently selected global Persona, preventing cross-persona review mistakes.

The legacy Master Vault's freeze action now follows the new-persona boundary as
well. It synthesizes the narrative locally, stores an editable draft in
browser session storage, and opens canonical `/workspace#personas`; the user
must review and submit the draft through `POST /api/personas`. The old
`/api/v2/personas/create` path is no longer the production creation path, so a
new Master Persona cannot accidentally bypass PersonaVersion lineage. The
handoff preserves biometrics, master/negative identity prompts, wardrobe and
world ringfences, and structured style/identity characteristics without
creating a record or starting a media job before review.

The legacy Orchestrator Generate action follows the same boundary. It now
stores a session-scoped generation draft with the selected scene, dimensions,
aspect ratio, and requested legacy model, then opens canonical
`/workspace#production` with the active Persona ID. Canonical Production owns
rights confirmation, approved ContentPack selection, preflight, and the final
`POST /api/jobs`; the legacy generate endpoint is not used to bypass those
gates.

### Phase 2 closeout — validated

The formal Phase 2 exit gate is complete on
`phase/02-master-persona-content-packs`. The canonical journey distinguishes
identity references from style/content references, binds them to a
PersonaVersion, and permits approved adult/glamour references to participate in
Identity Core canonical anchoring. Adult/glamour, lingerie, boudoir, and
nude-editorial ContentPacks retain both style authority and Identity Core
authority; they cannot be downgraded to style-only presets by the UI or API.

The completion gate covered Persona and PersonaVersion creation, ReferencePack
review and canonical selection, rights and media linkage, ContentPack authoring
and resolution, stale-lineage protection, Production preflight and queue
lineage, Asset Review, guarded legacy handoffs, and frontend/API/browser/axe/
accessibility-tree/error-state validation.

Legacy feature-equivalent replacement and retirement of the preserved `/` shell
remain a cross-cutting frontend workstream. Deeper Story Studio, Gallery,
Vault-inspector, and System/Telemetry replacement is not silently claimed as
complete by this Phase 2 domain closeout. Generation-model installation and
model-backed execution also remain deferred to their planned final gates.

### Phase 3 starting audit — unified media and asset lifecycle

Phase 3 begins on `phase/03-unified-media-assets`. The current runtime has
several direct rendering paths: canonical `/api/jobs`, Photo Studio generation,
Orchestrator anchor/batch generation, and the standalone diffusion engine. They
do not yet share one asset-registration and storage contract. The main risks are
duplicate media copies in `data/outputs`, `data/references`, and `generated`,
direct generation routes that do not create a Job lineage record, missing
idempotency keys, and file-serving paths that do not consistently verify the
recorded media file.

The first Phase 3 implementation slice is therefore the common media
registration/storage boundary. It must preserve pending review, PersonaVersion
lineage, disclosure, rights, hash, metadata, and quality results for every
image, video, and audio output before the direct rendering routes are migrated
to the shared job contract. Model installation remains deferred.

Phase 3 slice 1 is complete: operator imports, canonical job outputs, Photo
Studio images, voice outputs, and Orchestrator anchor/batch outputs now use the
same registration boundary and canonical output resolver. Reference records
reuse the linked asset file instead of creating a second media copy. Missing
asset files fail closed through the API, while every newly registered output
starts in pending review. Direct generation still runs outside the persistent
Job service in some routes; that migration is the next Phase 3 slice.

Phase 3 slice 2 is complete: direct Photo Studio, voice, Orchestrator anchor,
and Orchestrator batch requests now create a Job record, attach the Job ID to
registered outputs, persist the final result summary, and accept a bounded
`Idempotency-Key`. Repeated requests with the same key reuse the completed
result instead of creating duplicate media. Canonical `/api/jobs` requests
also persist idempotency and result metadata. The local execution remains
request-bound until persistent worker, retry, cancellation, and restart
recovery work in Phase 4; the unique database index also closes concurrent
idempotency races.

Phase 3 slice 3 is complete: the legacy `/api/v2/orchestrator/generate`
photoshoot route now creates a canonical Job, supports bounded idempotency,
registers successful diffusion output through the shared asset boundary, and
stores compatibility fallback media through the same pending-review path.
Its legacy response shape remains available, but the returned media URL now
resolves through `/api/assets/{asset_id}/file` and carries Job/asset lineage.
The diffusion engine can skip its legacy SQLite write when called by this
route; the older Master Vault background generator remains a separate legacy
workflow for a later migration.

Phase 3 slice 4 is complete: the legacy 13-pack Master Vault background
generator now creates or resumes a canonical parent Job, registers each pack
once with PersonaVersion and pack-index lineage, persists partial progress and
asset IDs in `jobs.result_json`, and marks the parent Job completed or failed.
The legacy `generated/master_persona_*` copies remain as compatibility previews
for the preserved shell, while canonical `data/outputs` media is now the
reviewable source of truth. Resumed packs reuse an existing canonical asset or
register an existing preview without invoking the renderer again.

Phase 3 slice 5 is complete: the local execution boundary now uses a bounded
asyncio semaphore with `STUDIO_JOB_CONCURRENCY=1` by default, checks durable
cancel state before expensive work and during ComfyUI polling, attempts the
local ComfyUI `/interrupt` endpoint when an active task is cancelled, and
records interrupted execution without overwriting an operator-cancelled job.
Startup logs expose the interrupted-job count and the explicit retry policy.
This is a safe bridge toward Phase 4: active jobs are never silently replayed
after restart, and the persisted retry endpoint remains the operator-controlled
recovery path until prompt reconciliation and backoff are implemented.

### Cross-cutting frontend migration workstream

The current static frontend is a legacy shell and is not considered aligned
with the new implementation. It must be migrated alongside the domain phases,
not treated as a final cosmetic pass. The new frontend will use the canonical
Persona, PersonaVersion, ReferencePack, Asset, ContentPack, Job, review, and
publishing contracts as its source of truth.

The migration sequence is:

- establish one API client with normalized errors, request cancellation, and
  stale-response protection;
- replace legacy/v2 fixture-driven persona and vault screens with canonical
  PersonaVersion-aware screens; the legacy Vault freeze action must remain a
  draft handoff only until the Vault surface itself reaches full parity;
- add the complete Master Persona journey: creation, version state, reference
  review, canonical selection, ContentPack authoring, identity/style review,
  generation, asset approval, export, and publishing readiness;
- make adult/glamour controls explicit in the UI, including Identity Core
  authority, fictional-adult disclosure, rights confirmation, visibility, and
  review state;
- provide consistent loading, empty, error, pending, approved, rejected, and
  stale-lineage states across every screen;
- verify responsive behavior and keyboard/screen-reader access at the major
  desktop and MacBook viewport sizes; and
- retire legacy screens only after their canonical replacements have equivalent
  API, review, lineage, and regression coverage.

Dependencies may be installed or updated when required for application
development, testing, frontend tooling, or runtime integration. Image, audio,
and video generation models, model weights, and model repositories remain
deferred to the final model-installation gate.

Exit: identity and style references are distinguishable, while approved adult/glamour references can participate in canonical identity anchoring.

### Phase 3 — Unified rendering and asset lifecycle

- Route Photo Studio and Orchestrator rendering through the common job service.
- Normalize CLI imports.
- Remove automatic approval.
- Centralize file resolution.
- Add idempotency and complete lineage.
- Ensure every output begins as pending.

Exit: Generated, Approved, and Publishable are separate states for every content class.

### Phase 4 — Persistent local job runner

- Persist progress and child tasks.
- Add retry, backoff, cancellation, and restart recovery.
- Add bounded concurrency.
- Add model unload and memory cleanup.
- Add disk and memory preflight.

For the 16 GB Mac, default to one heavy generation task and sequential Vault/content-pack generation.

Phase 3 already establishes the first bounded-runner boundary and explicit
interrupted status. Phase 4 must still replace request-created tasks with a
durable dispatcher, add retry/backoff policy and ComfyUI prompt reconciliation,
persist child-task progress, and add memory/disk preflight before increasing
concurrency.

Exit: interrupted jobs are resumable or clearly interrupted, and the UI never reports completion before output validation succeeds.

### Phase 5 — Identity-conditioned rendering

Benchmark text-only generation against IP-Adapter FaceID, InstantID, PuLID, and, if necessary, a controlled LoRA/DreamBooth adapter.

Measure face similarity, body consistency, prompt adherence, pose diversity, adult/glamour identity consistency, video drift, latency, memory use, and human approval rate.

Exit: one production identity method is selected from measured results on project personas and target hardware.

### Phase 6 — Creator personality and content system

Add personality, values, interests, humor, voice, mannerisms, audience, content pillars, emotional objectives, brand positioning, captions, and scripts.

Use this brief formula:

~~~text
Identity + Story + Visual + Emotion + Format + Audience Goal + Disclosure
~~~

Exit: a brief can be created without manually repeating persona behavior, visual identity, or disclosure instructions.

### Phase 7 — Quality, review, and export

Add checks for file integrity, identity similarity, anatomy, hands, video flicker, facial drift, audio timing, disclosure, rights, content class, and destination policy.

Exit: every review decision records status, reason, reviewer, and timestamp; approved assets export with manifest and disclosure sidecar.

### Phase 8 — Publishing integration

Add platform accounts, Persona-to-account binding, content calendar, captions, publish attempts, retries, audit logs, and platform responses.

Publishing requires:

~~~text
Approved asset
+ approved caption
+ disclosure
+ frozen PersonaVersion
+ assigned account
+ platform-policy check
~~~

Exit: the publishing layer cannot consume raw or unreviewed output.

### Phase 9 — Analytics and optimization

Track pillar performance, format performance, audience response, campaign results, rejection reasons, model/version attribution, and identity failures.

Optimize content strategy before changing persona identity.

## Performance plan for the target Mac

- One heavy model at a time.
- Sequential Vault and content-pack generation.
- Bounded local queue.
- Preview resolution before final resolution.
- Explicit model unload.
- Thumbnail/original separation.
- Disk and memory estimates before generation.
- Image jobs prioritized over video jobs.
- No silent concurrent model loading.

## Testing plan

### Unit tests

Cover PersonaVersion rules, pack roles, adult metadata, prompt compilation, job transitions, asset approval, path resolution, and idempotency.

### Integration tests

Cover persona creation, identity freeze, Vault generation, adult-pack review, brief-to-job, job-to-asset, export, series continuity, retry, and restart.

### End-to-end tests

~~~text
Create persona → freeze identity → generate content → review → approve → export
~~~

Also test:

~~~text
Adult/glamour asset → anchor eligibility review → content review
  → disclosure/rights review → approve or reject → export/publishing decision
~~~

## Priority order

~~~text
P0  Canonical PersonaVersion
P0  Unified asset and storage contract
P0  Remove automatic approval
P0  Adult/glamour metadata and review gates
P1  Persistent local job runner
P1  Unified Master Persona packs
P1  Identity-conditioned rendering
P1  Creator personality and content planner
P2  Publishing integration
P2  Analytics and optimization
P3  Distributed infrastructure
~~~

## Final implementation decision

The next implementation milestone is the Canonical Persona, PersonaVersion, ReferencePack, Asset, and Job foundation.

Adult/glamour content is a first-class capability and can contribute canonical identity anchors. The implementation must use explicit role, quality, age, rights, consent, disclosure, and review metadata rather than automatic approval.


## Phase 0 completed baseline

Phase 0 is documented and verified as a design/contracts milestone, with its two low-risk runtime enforcement items now completed: request/correlation traceability and pending-review defaults for direct generated assets. The larger PersonaVersion, storage-resolver, and unified-rendering migrations remain intentionally deferred to their planned phases.

### Canonical ownership map

| Domain | Canonical owner after Phase 1 | Current implementation risk |
|---|---|---|
| Persona identity | SQLite Persona and PersonaVersion | v2 JSON and SQLite are currently separate |
| Identity references | ReferencePack and ReferenceAsset | reference_images and assets overlap |
| Content direction | ContentBrief | prompts are built in several modules |
| Render execution | Job and JobAttempt | async tasks and daemon threads are partly process-local |
| Media files | AssetStorage resolver | generated/renders and data/outputs both exist |
| Review | ReviewDecision | direct generation paths now begin pending; common review service remains a Phase 3/7 consolidation |
| Publishing | PublishPlan and PublishAttempt | not implemented yet |
| Analytics | ContentPerformance | not implemented yet |

### Contract rules

1. Every downstream operation must reference a PersonaVersion.
2. A PersonaVersion is immutable after freeze.
3. A canonical identity anchor is explicit; recency is not sufficient.
4. Any ReferenceAsset, including adult/glamour content, can be canonical only after explicit eligibility and review.
5. Generated, pending, approved, exportable, and publishable are different states.
6. Every Asset must resolve to one canonical file path and one database record.
7. JSON is an import/export format, not a second live source of truth.
8. Every Job records input PersonaVersion, brief, workflow, model, seed, and output lineage.
9. Publishing can consume only approved, disclosure-ready assets.
10. Adult/glamour classification does not bypass age, rights, consent, quality, disclosure, review, or destination-policy checks.

### Lifecycle state machines

#### PersonaVersion

~~~text
draft
  → synthesized
  → identity_review
  → frozen
  → superseded
  → archived
~~~

Only a frozen PersonaVersion can be used to create repeatable series or production content.

#### ReferenceAsset

~~~text
generated
  → pending_review
  → approved
  → canonical_eligible
  → canonical
~~~

Alternative rejection path:

~~~text
generated → pending_review → rejected
~~~

Canonical eligibility does not automatically mean canonical. The operator must explicitly select the canonical anchor or anchor set.

#### ContentBrief

~~~text
draft
  → compiled
  → approved
  → queued
  → rendered
  → review
  → approved
  → exportable
  → publishable
~~~

#### Job

~~~text
queued
  → running
  → submitted
  → completed
  → failed
  → retryable
  → cancelled
  → interrupted
~~~

A job is not complete until output files exist, pass integrity checks, and are recorded as Assets.

### Storage contract

The future canonical layout is:

~~~text
data/
├── studio.db
├── assets/
│   ├── originals/
│   ├── derivatives/
│   ├── thumbnails/
│   └── manifests/
├── references/
├── workspaces/
├── workflows/
└── job-artifacts/
~~~

The application must use a storage resolver rather than constructing media paths inside route handlers. Existing generated files require an explicit migration decision during Phase 1 or Phase 3; no files are moved automatically by Phase 0. The current Phase 0 hardening deliberately leaves the existing `generated/renders` and `data/outputs` split unchanged until that migration is designed and tested.

### API ownership contract

| API group | Domain owner | Allowed responsibility |
|---|---|---|
| /api/personas | Persona service | Create/read/freeze/version personas |
| /api/personas/{id}/references | Reference service | Upload and review references |
| /api/v2/personas/* | Compatibility facade | Resolve through canonical PersonaVersion |
| /api/jobs/* | Job service | Queue, monitor, retry, cancel jobs |
| /api/assets/* | Asset/review service | File access, manifests, review, export |
| /api/series/* | Content planning service | Series and episode planning |
| /api/photo-studio/* | Content/render facade | Compile briefs and submit common jobs |
| /api/orchestrator/* | Prompt/render facade | Compile prompts and submit common jobs |
| /api/monitor, /api/readiness | Operations service | Non-mutating health and readiness |
| Future /api/publishing/* | Publishing service | Account binding and approved publishing only |

Routes should not directly create duplicate persona or asset representations outside their owning service.

### Observability contract

Every future request and job should carry:

~~~text
request_id
correlation_id
persona_id
persona_version_id
brief_id
job_id
asset_id
workflow_id
model_id
attempt
~~~

Required events:

~~~text
request_received
persona_created
persona_version_frozen
reference_generated
reference_reviewed
job_queued
job_started
job_progressed
job_completed
job_failed
asset_created
asset_reviewed
asset_exported
publish_requested
publish_completed
publish_failed
~~~

Logs must not contain secrets, access tokens, or unnecessary sensitive content. Long-running jobs must expose structured progress and failure categories. The current runtime now emits bounded request/correlation IDs on every HTTP response and in structured request/job log payloads; PersonaVersion, brief, asset, and attempt propagation will be completed with the corresponding domain migrations.

### Architecture decisions recorded in Phase 0

#### ADR-001 — Modular monolith first

Decision: Keep FastAPI, SQLite, local storage, and adapters in one repository with explicit module boundaries.

Reason: The current product is local-first and single-operator. Independent scaling and team size do not yet justify microservices.

Revisit when: Multiple workers, multiple operators, or independent service scaling becomes a real requirement.

#### ADR-002 — SQLite as canonical local system of record

Decision: SQLite owns live Persona, PersonaVersion, ReferenceAsset, Job, Asset, ReviewDecision, and future publishing records.

Reason: It already owns the strongest lineage, review, and job data.

Trade-off: JSON Vault compatibility requires an import/export migration.

#### ADR-003 — PersonaVersion is the identity boundary

Decision: Production generation and series jobs reference immutable PersonaVersion records.

Reason: A lock flag alone does not preserve the exact identity snapshot used by downstream content.

Trade-off: Editing identity requires a new version and explicit migration.

#### ADR-004 — One asset contract and storage resolver

Decision: All generation, import, Photo Studio, Orchestrator, and CLI paths must produce the same Asset contract and use one resolver.

Reason: The current generated/renders and data/outputs split creates broken lineage and export risk.

Trade-off: Existing direct paths must be adapted to the common service.

#### ADR-005 — Review is separate from generation

Decision: All outputs begin as pending; approval is an explicit action.

Reason: Generated content, including adult/glamour content, is not automatically suitable for export or publication.

Trade-off: The operator has an additional review step, but gains quality, rights, disclosure, and policy control.

#### ADR-006 — Adult/glamour references share identity authority

Decision: Adult/glamour assets are first-class ReferenceAssets and may become canonical identity anchors after explicit review.

Reason: The visual identity must remain consistent across the persona's actual content range, including adult/glamour content.

Trade-off: Adult assets require stronger visibility, rights, consent, disclosure, age, and destination-policy metadata.

#### ADR-007 — Install generation models last; allow required runtime dependencies

Decision: Keep image, audio, and video generation model downloads, model
weights, model repositories, and generated model assets out of the development
loop until the final installation and hardware-validation phase. Application
dependencies, frontend tooling, test packages, media utilities, and runtime
libraries may be installed or updated during feature work when required.

Reason: Model artifacts consume substantial disk, memory, and setup time on the
16 GB Mac, while ordinary dependencies may be necessary to implement and
validate the application contracts, persistence, review gates, and lineage.

Trade-off: Model-backed integration tests remain mocked or contract-level until
the final model gate; dependency changes must be versioned and validated so
development environments remain reproducible.

Revisit when: The Phase 7/8 release candidate is ready and the model register has approved source, license, checksum, storage, and hardware-fit entries.

#### ADR-008 — v2 JSON is a compatibility facade, not a live store

Decision: Import legacy v2 persona JSON into SQLite Persona and PersonaVersion records on first v2 access. Keep JSON as an explicit backup/export format and expose version-aware compatibility responses from the v2 router.

Reason: Existing v2 UI and vault data must remain usable while eliminating two competing live persona sources of truth.

Trade-off: Rich v2 fields are preserved inside the PersonaVersion snapshot until they are normalized into dedicated reference-pack and content-pack tables.

Revisit when: ReferencePack and ContentPack persistence is complete and the v2 compatibility facade can be reduced to import/export only.

#### ADR-009 — Normalize legacy vault packs without auto-approving them

Decision: Convert turnaround, micro-detail, category-baseline, and adult/glamour vault groups into ReferencePack records with explicit identity authority, content class, review, and canonical eligibility metadata.

Reason: The v2 JSON shape contains meaningful identity and style structure that must remain available to the creator workflow, while generated/reference media must not bypass review.

Trade-off: Legacy pack files are represented by source URLs and metadata until the asset-storage resolver and pack media ingestion are completed.

Revisit when: ReferencePack media is migrated into the unified Asset contract and pack-level review UI is implemented.

#### ADR-010 - Create new Master Personas; do not reuse legacy personas after migration

Decision: The post-implementation production workflow creates Master Personas
using the new canonical structure. Existing personas, generated outputs, and
reference packs remain unchanged legacy/reference data and are not selected as
the source for new production personas. New persona IDs must not reuse legacy
IDs.

Reason: The new structure establishes stronger identity/version boundaries,
pack authority, adult/glamour identity-and-style anchors, review gates, and
job/content lineage. Treating old records as active production inputs would
reintroduce ambiguous ownership and make migration behavior implicit.

Migration rule: No legacy asset becomes a canonical anchor automatically. If
a future workflow needs to reuse one, it must pass an explicit import path
with provenance, rights/consent metadata, review, identity-quality checks,
and canonical selection. The v2 compatibility facade may remain available for
inspection and export, but new creation targets the canonical flow.

Trade-off: Existing personas do not receive automatic upgrades or continued
production compatibility. This avoids destructive conversion and keeps the
new identity system deterministic, at the cost of requiring intentional
recreation or explicit, reviewed import when old material is valuable.

Revisit when: A separately approved legacy-import/migration workflow has
provenance, review, rollback, and regression coverage.

#### ADR-011 - Canonical anchors require reviewed, version-matched media assets

Decision: A ReferencePack may become canonical only through an explicit review
and selection workflow. Every selected item must be approved, rights-confirmed,
eligible, linked to an approved image Asset, and bound to the same
PersonaVersion as the pack. Rejection of a linked Asset clears the canonical
selection.

Reason: Pack metadata alone is not sufficient identity evidence. The media
asset must be traceable to the PersonaVersion that owns the pack so downstream
rendering cannot silently mix identity generations or use unreviewed output.

Trade-off: Legacy pack items with URLs but no unified Asset link remain
inspectable and reviewable, but cannot be promoted to canonical anchors until
they pass an explicit, versioned media import/link step.

Revisit when: ContentPack persistence and downstream render resolution consume
the canonical selection directly and provide end-to-end lineage assertions.

#### ADR-012 - ContentPacks resolve reviewed canonical anchors instead of copying media

Decision: A production ContentPack stores style/content directives and links
to selected ReferencePack items and their unified Assets. It does not copy or
re-author identity media. Resolution is allowed only while the ContentPack,
source ReferencePack, selected items, and linked assets remain approved and
PersonaVersion-compatible.

Adult/glamour rule: Adult/glamour ContentPacks are identity-core packs with
`identity_and_style` authority. They are not isolated style presets and cannot
be created from an unreviewed or non-canonical source pack.

Trade-off: ContentPack creation is intentionally explicit and requires a
reviewed canonical source. This prevents legacy or stale media from becoming
active identity input, but requires the creator to complete the reference
review workflow first.

Revisit when: The full Master Persona UI can author and review ContentPack
items directly while preserving the same resolver contract.

#### ADR-013 - Migrate the frontend to canonical contracts as a cross-cutting workstream

Decision: The existing static frontend remains a compatibility shell while
screens are replaced incrementally with PersonaVersion-aware workflows. New
production UI features must consume the canonical APIs and review/lineage
contracts; legacy v2 fixtures and presentation-only state cannot be a source of
production truth.

Reason: The domain model is changing across persona creation, reference packs,
ContentPacks, assets, jobs, and publishing. Keeping the old frontend intact
would make the application appear functional while bypassing review, identity
authority, and lineage rules.

Trade-off: The application may temporarily expose the legacy shell and new
workflow screens at the same time. This costs migration effort, but permits
incremental verification and avoids a high-risk frontend rewrite without
backend contract coverage.

Dependency rule: Application dependencies and development tooling may be
installed or updated when needed and must be recorded with version and
validation evidence. Generation models, model weights, and model repositories
remain final-gate-only.

### Phase 0 exit criteria

- Canonical domain ownership is documented.
- PersonaVersion is defined as the identity boundary.
- Reference authority rules are documented.
- Adult/glamour canonical-anchor behavior is documented.
- Job, asset, review, export, and publishing states are documented.
- Storage and lineage rules are documented.
- API responsibilities are documented.
- Observability fields and events are documented.
- Architectural trade-offs and revisit triggers are documented.
- Phase 1 implementation dependencies are identified.

### Phase 0 runtime enforcement completed

- Request and correlation IDs are generated or safely propagated for every HTTP request.
- IDs are returned as `X-Request-ID` and `X-Correlation-ID` response headers.
- Structured request completion logs and core job lifecycle logs include the trace IDs.
- Direct Photo Studio, Orchestrator, diffusion-engine, and v2 fallback asset records begin with `review='pending'`.
- A regression test verifies generated Photo Studio output cannot bypass review.
- Storage unification, canonical PersonaVersion persistence, identity conditioning, and full render-job convergence remain deferred to Phases 1–5.

### Model and dependency installation policy

The project will maintain a controlled register of every model, runtime, and
heavyweight dependency. Application dependencies and development tooling may be
installed or updated during feature work when required; each change must record
purpose, version, source, install command, validation result, and rollback
notes. Image, audio, and video generation models, model weights, and model
repositories are excluded from that permission and remain final-gate-only after
the application contracts and review workflow are stable.


