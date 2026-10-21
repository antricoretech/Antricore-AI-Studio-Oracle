# Implementation Tracking — AI Influencer Studio

**Purpose:** Track every approved implementation activity, validation result, file change, status transition, blocker, and next action.

**Current status:** Phase 0 runtime hardening complete; Phase 2 Master Persona and ContentPack core completed on its dedicated branch after the final validation gate. Cross-cutting legacy-shell parity and model installation remain separately tracked.
**Tracking rule:** Update this file after every successfully verified activity. If an activity fails, record the failure and evidence before retrying. Do not mark an activity complete from intention or an unverified edit.

## Branch strategy

Implementation is organized as cumulative phase branches. `main` is the
verified integration branch; each phase branch contains the completed work of
the previous phases plus the active phase work. A phase is merged into `main`
only after its validation gate passes, then the next phase branch is created
from the updated `main`.

| Branch | Scope | Status |
|---|---|---|
| `phase/00-baseline` | Baseline and Phase 0 foundation checkpoint | CREATED |
| `phase/01-canonical-persona` | PersonaVersion, pack review/canonical selection, and unified media linkage | CHECKPOINTED |
| `phase/02-master-persona-content-packs` | Master Persona and ContentPack implementation | CHECKPOINTED |
| `phase/03-unified-media-assets` | Unified rendering and asset lifecycle | CHECKPOINTED |
| `phase/04-local-job-runner` | Persistent local job runner | ACTIVE |
| `phase/05-identity-conditioning` through `phase/09-analytics` | Subsequent roadmap phases | PLANNED |

Milestone tags use `phase-0-complete`, `phase-1-complete`, and the same
pattern for later phases. Model installation remains isolated to the final
installation gate and is not included in feature-phase branches.

## Status vocabulary

~~~text
PLANNED      Approved for future work but not started
IN_PROGRESS  Work is actively being performed
BLOCKED      Cannot proceed without a specific external decision/change
VERIFYING    Implementation exists and validation is running
COMPLETED    Implementation and required validation succeeded
REJECTED     Proposed approach was not accepted
DEFERRED     Intentionally postponed
~~~

## Activity record requirements

Every completed activity must record:

- Activity ID.
- Date and time.
- Phase.
- Objective.
- Files changed.
- Implementation summary.
- Validation commands/checks.
- Validation result.
- User approval reference.
- Risks or follow-up work.
- Next activity.

## Overall roadmap status

| Phase | Name | Status | Completion | Depends on | Notes |
|---|---|---|---:|---|---|
| 0 | Baseline and contracts | COMPLETED | 100% | User approval | Contracts, states, storage, API ownership, observability and runtime enforcement verified |
| 1 | Canonical PersonaVersion | IN_PROGRESS | 85% | Phase 0 | Core SQLite canonical source, v2 compatibility, pack review/canonical selection, unified asset linkage, archive reconciliation, and migration boundary are complete; CLI PersonaVersion alignment remains a compatibility carry-over |
| 2 | Master Persona and content packs | COMPLETED | 100% | Phase 1 | Formal Phase 2 exit gate passed: canonical Persona/PersonaVersion, ReferencePack, ContentPack, adult/glamour Identity Core anchoring, review/linkage/lineage controls, Production/Asset Review flow, frontend certification, and guarded legacy handoffs are complete; feature-equivalent legacy replacement remains a separate cross-cutting workstream |
| 3 | Unified rendering and assets | IN_PROGRESS | 65% | Phase 2 | Common media registration, direct Job/idempotency, legacy photoshoot diffusion, legacy Vault parent/pack registration, bounded cancellation/restart boundaries, and Vault cancellation/thread-resume guards completed; full persistent runner remains Phase 4 |
| 4 | Persistent local job runner | IN_PROGRESS | 90% | Phase 3 | Phase 4 branch active; durable dispatcher, execution leases/heartbeats, stale-job recovery, retry backoff, completed-prompt reconciliation, child-task progress, memory/disk preflight, restart-safe queue retention, shutdown reconciliation, standalone diffusion migration, and opt-in direct free-CLI registration completed; final model gate remains |
| 5 | Identity-conditioned rendering | PLANNED | 0% | Phases 2–4 | Benchmark before selection |
| 6 | Creator personality/content system | PLANNED | 0% | Phases 1–2 | Content pillars and creator behavior |
| 7 | Quality, review and export | PLANNED | 0% | Phases 3–5 | Human approval remains required |
| 8 | Publishing integration | PLANNED | 0% | Phase 7 | Account and policy gates |
| 9 | Analytics and optimization | PLANNED | 0% | Phase 8 | Feedback loop |

## Detailed activity log

| Activity ID | Phase | Activity | Status | Verification | Date | Notes |
|---|---|---|---|---|---|---|
| DOC-001 | Planning | Consolidate current code, workflow and Master Persona analyses | COMPLETED | Existing analysis documents reviewed | 2026-10-21 | Basis for final roadmap |
| DOC-002 | Planning | Add adult/glamour content-pack requirements | COMPLETED | Architecture documentation updated | 2026-10-21 | Initial adult-pack track documented |
| DOC-003 | Planning | Update adult/glamour model so approved assets can become canonical anchors | COMPLETED | Final plan updated | 2026-10-21 | Requires explicit role, quality and review metadata |
| DOC-004 | Planning | Create implementation tracking structure | COMPLETED | This tracking file created | 2026-10-21 | Future implementation updates require evidence |
| DOC-005 | Planning | Organize active and archived documentation | COMPLETED | 19 Markdown files moved; two active files remain in docs root | 2026-10-21 | Archive path: docs/archieved doc/ |
| IMP-001 | Phase 0 | Define canonical domain contracts | COMPLETED | Final plan contract section reviewed | 2026-10-21 | Persona, PersonaVersion, ReferencePack, Asset, Job and ContentBrief boundaries |
| IMP-002 | Phase 0 | Define lifecycle state machines and ADRs | COMPLETED | Final plan state/ADR sections reviewed | 2026-10-21 | Persona, reference, brief and job states documented |
| BRANCH-001 | Planning | Create cumulative phase branch structure and Phase 1 checkpoint | COMPLETED | `git branch --list`; `git log --oneline --decorate`; local tags verified | 2026-10-21 | Created `phase/00-baseline`, committed Phase 1 as `9900255`, and created `phase-0-baseline` plus `phase-1-checkpoint-70`; no unrelated working-tree files were staged |
| IMP-013 | Phase 0 | Define storage, API ownership and observability contracts | COMPLETED | Final plan contract sections reviewed | 2026-10-21 | No runtime behavior changed |
| IMP-014 | Phase 0 | Add request/correlation ID middleware and structured trace logging | COMPLETED | `pytest -q tests/test_api.py tests/test_comfy.py` — 22 passed | 2026-10-21 02:11 +05:30 | Bounded incoming IDs are preserved; invalid/missing IDs are regenerated; response headers and request/job logs carry trace context |
| IMP-015 | Phase 0 | Enforce pending review for direct generated assets | COMPLETED | `pytest -q tests/test_api.py tests/test_comfy.py` — 22 passed; Photo Studio regression test passed | 2026-10-21 02:11 +05:30 | Photo Studio, Orchestrator, diffusion engine, and v2 fallback no longer auto-approve output; approval remains explicit |
| IMP-016 | Phase 1 | Record final-only model and heavyweight dependency installation register | COMPLETED | Final plan ADR-007 and this register reviewed | 2026-10-21 | No model, runtime, or heavyweight dependency installed |
| IMP-017 | Phase 1 | Add SQLite PersonaVersion foundation and lineage hooks | COMPLETED | `python -m compileall -q studio`; `pytest -q tests/test_api.py tests/test_comfy.py` — 23 passed; live DB schema version 5 verified | 2026-10-21 | Added schema migration/backfill, repository methods, freeze/version API, series binding, job lineage IDs, and regression coverage |
| IMP-018 | Phase 1 | Convert v2 JSON to canonical import/export compatibility and bind references to PersonaVersion | COMPLETED | `python -m compileall -q studio`; `pytest -q tests/test_api.py tests/test_comfy.py` — 24 passed; live DB schema version 6 verified | 2026-10-21 | v2 reads now resolve through SQLite; JSON remains backup/export; references carry version, role, class, review, rights, and metadata |
| IMP-019 | Phase 1 | Normalize v2 vault packs and reconcile archive/restore records | COMPLETED | `python -m compileall -q studio`; `pytest -q tests/test_api.py tests/test_comfy.py` — 24 passed; live DB schema version 7, 12 packs, 39 pack items verified | 2026-10-21 | Turnaround, detail, category, and adult/glamour packs are normalized; restore remaps packs to the restored PersonaVersion |
| IMP-020 | Phase 1 | Record new Master Persona migration boundary | COMPLETED | Final plan ADR-010 and this tracker updated; no runtime/data/model changes made | 2026-10-21 | New production personas use the new canonical structure and unique IDs; existing personas and packs remain preserved legacy/reference-only |
| IMP-021 | Phase 1 | Implement pack-level review, canonical selection, and unified media-asset linkage | COMPLETED | `python -m compileall -q studio`; `pytest -q tests/test_api.py tests/test_comfy.py` — 25 passed; live DB schema version 8, 12 packs, 39 pack items verified | 2026-10-21 | Pack/item review gates, asset links, PersonaVersion lineage, canonical selection, and rejection invalidation are active; model installation remains deferred |
| IMP-022 | Phase 2 | Add ContentPack persistence and canonical-anchor resolution | COMPLETED | `python -m compileall -q studio`; `pytest -q tests/test_api.py tests/test_comfy.py` — 26 passed; live DB schema version 9, 0 content packs, 0 content-pack items verified | 2026-10-21 | ContentPacks bind style directives and canonical ReferencePack anchors to one PersonaVersion; adult/glamour forces identity-core and identity-and-style authority; job/series resolution is active |
| IMP-023 | Phase 2 | Add Master Persona ContentPack authoring, review, and resolution workspace | COMPLETED | `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 27 passed; `node --check static/content_packs.js`; route/static smoke check returned 200 | 2026-10-21 | Added `/content-packs`, canonical-source eligibility display, style/metadata authoring, explicit review actions, anchor resolution, and adult/glamour-family client/server Identity Core enforcement; no model/dependency installation performed |
| UI-003 | Cross-cutting | Implement Master Persona creation and PersonaVersion lifecycle UI | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; Playwright Chromium smoke passed at desktop/mobile widths with no console errors | 2026-10-21 | `/workspace#personas` now creates new canonical Personas with structured characteristics and fictional-adult disclosure, loads immutable PersonaVersion lineage, preserves the newly created selection, and exposes guarded draft-to-frozen transition; no generation models installed |
| UI-004 | Cross-cutting | Implement ReferencePack review, asset linkage, and canonical-anchor selection UI | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; Playwright Chromium smoke passed at desktop/mobile widths with no console errors | 2026-10-21 | `/workspace#references` now reviews packs/items, confirms rights, links PersonaVersion-compatible image assets, selects/clears explicit canonical anchors, and explains eligibility gates; adult/glamour remains eligible for Identity Core anchoring; no generation models installed |
| UI-005 | Cross-cutting | Implement Asset Review and export-readiness UI | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; Playwright empty-state and populated/action smoke passed at desktop/mobile widths with no console errors | 2026-10-21 | `/workspace#assets` now exposes pending/approved/rejected review actions, quality/rights/disclosure/PersonaVersion indicators, media inspection, and approved-only package export; no generation models installed |
| UI-006 | Cross-cutting | Implement Production Queue and generation-readiness UI | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; Playwright empty/readiness and populated cancel/retry smoke passed at desktop/mobile widths with no console errors | 2026-10-21 | `/workspace#production` now shows Persona/PersonaVersion/rights/model-installation readiness gates, queue counts, job lineage/errors, and guarded cancel/retry actions; generation authoring and model installation remain deferred |
| UI-007 | Cross-cutting | Implement preflight-gated generation authoring UI | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; Playwright populated workflow/preflight smoke passed at desktop/mobile widths with no console errors | 2026-10-21 | `/workspace#production` now loads workflow catalog state, keeps uninstalled recipes disabled, authors prompt/canvas/ContentPack/rights requests, requires a passing `/api/preflight`, and queues only through the canonical job API; no generation job or model was installed/executed during validation |
| UI-008 | Cross-cutting | Add stale-asset and PersonaVersion-lineage visibility | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; fixture-driven Playwright smoke verified mismatch, stale-lineage, Reference linkage, and stale-anchor states with no page errors | 2026-10-21 | ReferencePack items now explain missing, rejected, pending, rights-blocked, ineligible, and PersonaVersion-mismatched states; Asset Review and ContentPacks surface stale reuse warnings; no model or generation job was installed/executed |
| UI-009 | Cross-cutting | Add canonical workspace accessibility and responsive smoke coverage | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m py_compile scripts/workspace-accessibility-smoke.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; fixture-driven `workspace-accessibility-smoke.py` passed at 320, 768, 1024, and 1440px with no page errors | 2026-10-21 | Added skip-link/main landmark semantics, `aria-busy` loading state, 320px toolbar overflow fix, named-control checks, and a repeatable non-destructive Playwright smoke; axe/screen-reader certification remains follow-up work |
| UI-010 | Cross-cutting | Add axe, accessibility-tree, and broader state certification | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile scripts/workspace-accessibility-smoke.py`; fixture-driven `workspace-accessibility-smoke.py` passed with pinned axe-core 4.10.2, Chrome accessibility-tree landmarks, loading, base API failure, view API failure, and empty-persona checks; canonical seven-view axe baseline returned zero WCAG 2A/2AA violations | 2026-10-21 | Corrected muted hint/placeholder contrast to the accessible `--muted` token; axe-core was loaded only by the audit runner and no application or model dependency was installed |
| UI-011 | Cross-cutting | Establish legacy-shell parity bridge and regression smoke | COMPLETED | `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py` — 1 passed; `node --check static/app.js`; `scripts/browser-smoke-test.py` passed with five legacy tabs, canonical workspace bridge, axe, accessibility-tree, and no page errors | 2026-10-21 | Root `/` remains preserved as the legacy V2 shell, now uses the module entrypoint and links to `/workspace`; full migration of legacy vault/orchestrator/story/gallery/system features remains planned and was not hidden behind this bridge |
| UI-012 | Cross-cutting | Add feature-by-feature legacy-to-canonical handoff map | COMPLETED | `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py`; `scripts/browser-smoke-test.py` passed with five canonical bridge targets, five legacy tabs, axe, accessibility-tree, and no page errors | 2026-10-21 | Legacy Vault, Generate, Story, Gallery, and System surfaces now expose explicit canonical destinations for Personas, Production, ContentPacks, Asset Review, and Overview; legacy behavior remains preserved while full replacement parity is still planned |
| UI-013 | Cross-cutting | Preserve active Persona identity across legacy-to-canonical handoffs | COMPLETED | `node --check static/app.js`; `.\\.venv\\Scripts\\python.exe -m py_compile scripts/browser-smoke-test.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py`; browser smoke verified every canonical bridge carries the selected `persona_id` | 2026-10-21 | Legacy handoff links now deep-link to `/workspace` with the selected canonical Persona ID; the canonical shell already resolves that query into the active PersonaVersion context; no duplicate identity store was introduced |
| UI-014 | Cross-cutting | Preserve active Persona on the global legacy workspace bridge | COMPLETED | `node --check static/app.js`; `.\\.venv\\Scripts\\python.exe -m py_compile scripts/browser-smoke-test.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py`; browser smoke verified the global workspace link carries the selected `persona_id` | 2026-10-21 | The root shell's direct canonical entry now uses the same Persona-preserving handoff contract as feature links; legacy behavior remains available and no second identity store was introduced |
| UI-015 | Production | Bind preflight approval to validated generation inputs | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 29 passed; browser smoke and canonical axe/accessibility/error-state smoke passed | 2026-10-21 | Workflow and dimensions are fingerprinted; changing them invalidates a previous preflight, and an in-flight response is discarded if its inputs are no longer current; no model or generation job was installed/executed |
| UI-016 | Cross-cutting | Add item-level legacy Gallery to canonical Asset Review handoff | COMPLETED | `node --check static/app.js`; `.\\.venv\\Scripts\\python.exe -m py_compile scripts/browser-smoke-test.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 29 passed; browser smoke verified the Gallery link uses the asset-owned Persona ID; canonical axe/accessibility/error-state smoke passed | 2026-10-21 | Each legacy Gallery card now offers canonical review for that asset's owning Persona; clicking the link no longer opens the legacy metadata modal; legacy Gallery remains available during parity migration |
| UI-017 | Cross-cutting | Route legacy Master Vault persona creation through canonical draft handoff | COMPLETED | `node --check static/app.js`; `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` â€” 29 passed; `scripts/browser-smoke-test.py` passed; `scripts/workspace-accessibility-smoke.py` passed; Playwright runtime draft-prefill test passed; `.\\.venv\\Scripts\\python.exe -m pip check` passed | 2026-10-21 | Legacy Vault synthesis now stores an editable local draft and opens `/workspace#personas`; canonical creation is the only new-persona write path, while legacy Vault generation remains available only as synthesis/reference compatibility |
| UI-018 | Production | Route legacy Orchestrator generation through canonical Production draft handoff | COMPLETED | `node --check static/app.js`; `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` â€” 29 passed; browser smoke and canonical accessibility/error-state smoke passed; Playwright runtime handoff test passed; `.\\.venv\\Scripts\\python.exe -m pip check` passed | 2026-10-21 | Legacy Orchestrator Generate now stores a session-scoped draft and opens `/workspace#production` with Persona context; canonical rights, ContentPack, preflight, and job API gates remain authoritative; no generation model or job was installed/executed |
| PLAN-001 | Cross-cutting | Record frontend migration and dependency-installation boundary | COMPLETED | Final plan ADR-013, frontend migration workstream, and installation policy updated | 2026-10-21 | Current frontend is recorded as a legacy shell; canonical UI replacement is required across the implementation; application dependencies/tooling may be installed or updated, while generation models remain final-gate-only |
| UI-001 | Cross-cutting | Strengthen shared frontend API client and adopt it in ContentPack workspace | COMPLETED | `node --check static/modules/api.js`; `node --check static/content_packs.js`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 27 passed; Playwright Chromium smoke passed; `.\\.venv\\Scripts\\python.exe -m pip check` passed | 2026-10-21 | Added normalized `ApiError`, JSON parsing, 401 handling, AbortController propagation, bounded GET retries, and shared GET/POST/PATCH helpers; ContentPack UI no longer owns a duplicate fetch adapter. `tests/test_frontend.py` still has the known legacy-shell failure because `/` loads `static/app.js` without `type="module"`; main-shell migration remains planned. |
| UI-002 | Cross-cutting | Build first canonical frontend shell and navigation | COMPLETED | `node --check static/workspace.js`; `python -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` — 28 passed; Playwright Chromium smoke passed at desktop/mobile widths with seven navigation destinations and no console errors | 2026-10-21 | Added `/workspace` with API-backed Overview, Master Personas, ReferencePacks, ContentPacks, Production Queue, Asset Review, and Publishing Readiness views; `/` remains a preserved legacy route until parity is verified |
| IMP-003 | Phase 1 | Introduce canonical PersonaVersion persistence | COMPLETED | Superseded by IMP-017; schema/version tests passed | 2026-10-21 | Original backlog row retained for traceability; canonical implementation is complete |
| IMP-004 | Phase 1 | Convert v2 JSON persona data to import/export | COMPLETED | Superseded by IMP-018; v2 compatibility tests passed | 2026-10-21 | Original backlog row retained for traceability; JSON remains explicit backup/export compatibility |
| IMP-005 | Phase 2 | Reclassify and review Master Persona packs | COMPLETED | Superseded by IMP-021, IMP-022, and IMP-023 | 2026-10-21 | Adult/glamour packs retain Identity Core plus style authority |
| IMP-006 | Phase 3 | Unify render, asset and storage contracts | IN_PROGRESS | MEDIA-001, JOB-002, MEDIA-002, MEDIA-003, RUNNER-001, and MEDIA-004 verified | 2026-10-21 | Canonical app routes are migrated; standalone CLI/diffusion compatibility paths remain bounded carry-over work |
| IMP-007 | Phase 4 | Add persistent local job execution | IN_PROGRESS | JOB-004 through JOB-010 and MEDIA-005 through MEDIA-007 verified | 2026-10-21 | One heavy job remains the default for the 16 GB Mac; standalone diffusion and opt-in direct free-CLI generation now use the canonical asset boundary; only the final model/readiness gate remains for this runner track |
| IMP-008 | Phase 5 | Benchmark identity-conditioning methods | PLANNED | Not started | — | IP-Adapter FaceID, InstantID, PuLID, LoRA option |
| IMP-009 | Phase 6 | Add creator personality and content planning | PLANNED | Not started | — | Include adult/glamour content pillars |
| IMP-010 | Phase 7 | Add quality and review gates | PLANNED | Not started | — | Identity, anatomy, disclosure and policy checks |
| IMP-011 | Phase 8 | Add account-aware publishing workflow | PLANNED | Not started | — | Only approved assets |
| IMP-012 | Phase 9 | Add analytics and optimization loop | PLANNED | Not started | — | After publishing stability |

| CLOSE-002 | Phase 2 | Run Phase 2 formal exit gate and close the Master Persona/ContentPack core | COMPLETED | `node --check static/workspace.js`; `node --check static/modules/api.js`; `node --check static/content_packs.js`; `.\\.venv\\Scripts\\python.exe -m compileall -q studio`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 29 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/browser-smoke-test.py --url http://127.0.0.1:8123`; `scripts/workspace-accessibility-smoke.py --url http://127.0.0.1:8123` | 2026-10-21 | Phase 2 formal exit criteria passed. Adult/glamour remains Identity Core plus style authority, canonical selection is explicitly reviewed and lineage-safe, and no image/audio/video model or generation job was installed or executed. Legacy feature-equivalent replacement remains separately tracked. Next: create the Phase 3 branch only after Phase 2 integration approval. |
| BRANCH-003 | Planning / Phase 3 | Create and activate the Phase 3 unified media/assets branch | COMPLETED | `git switch -c phase/03-unified-media-assets`; branch and Phase 2 tag verified; unrelated working-tree changes preserved | 2026-10-21 | Phase 3 is isolated from the Phase 2 checkpoint. Next: implement and verify the common media registration/storage boundary before migrating direct rendering routes. |
| BRANCH-004 | Planning / Phase 4 | Create and activate the Phase 4 local job runner branch | COMPLETED | `git switch -c phase/04-local-job-runner`; branch and Phase 3 checkpoint verified; unrelated working-tree changes preserved | 2026-10-21 | Phase 4 starts from the verified Phase 3 head and carries the approved CLI/diffusion compatibility work as explicit follow-up. |
| MEDIA-001 | Phase 3 | Implement the common media registration and canonical asset storage boundary | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/assets.py studio/app.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 29 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/browser-smoke-test.py --url http://127.0.0.1:8123`; `scripts/workspace-accessibility-smoke.py --url http://127.0.0.1:8123` | 2026-10-21 | Added `studio/assets.py`; centralized output filenames, safe path resolution, media registration, hashes, metadata, quality, PersonaVersion/job lineage, and pending review. Migrated imports, canonical job outputs, Photo Studio, voice, Orchestrator anchor/batch, reference serving, package export, and missing-file handling. No generation model was installed or executed. Next: route direct generation through the persistent Job contract and add idempotency. |
| JOB-002 | Phase 3 | Route direct generation through the common Job contract and add idempotency | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/app.py studio/assets.py studio/database.py studio/repositories.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 29 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/browser-smoke-test.py --url http://127.0.0.1:8123`; `scripts/workspace-accessibility-smoke.py --url http://127.0.0.1:8123` | 2026-10-21 | Added jobs schema version 10 with idempotency and result metadata. Photo Studio, voice, Orchestrator anchor, Orchestrator batch, and canonical job requests now persist Job lineage and reuse completed idempotent results. Concurrent key collisions are resolved from the unique database index. Model installation and execution were not performed. Next: migrate the standalone diffusion path and add persistent worker boundaries. |
| MEDIA-002 | Phase 3 | Migrate legacy photoshoot diffusion through the canonical Job and media boundaries | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/api_v2.py studio/diffusion_engine.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 30 passed; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/browser-smoke-test.py --url http://127.0.0.1:8123`; `scripts/workspace-accessibility-smoke.py --url http://127.0.0.1:8123` | 2026-10-21 | `/api/v2/orchestrator/generate` now records Job lineage, accepts idempotency, uses canonical `register_media_asset`, and returns canonical asset-file URLs while preserving legacy response compatibility. Fallback media also remains pending review and lineage-safe. Model installation and execution were not performed. Next: migrate the legacy Master Vault background generator and introduce persistent worker/retry/recovery boundaries. |
| MEDIA-003 | Phase 3 | Migrate the legacy 13-pack Master Vault worker to canonical parent Job and pack asset registration | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/api_v2.py studio/assets.py studio/diffusion_engine.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 31 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` — 38 passed, 1 pre-existing failure in `test_registry_only_freely_available_models` because `flux1-dev-gguf` has `FLUX.1-dev Non-Commercial License`; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/browser-smoke-test.py --url http://127.0.0.1:8123`; `scripts/workspace-accessibility-smoke.py --url http://127.0.0.1:8123` | 2026-10-21 | Vault generation now creates/resumes a canonical parent Job, registers each pack once with PersonaVersion/job/pack-index lineage, persists partial results, and preserves legacy preview copies for shell compatibility. No model was installed or executed. The unrelated model-license test failure was not changed. Next: introduce persistent worker/retry/recovery boundaries and migrate remaining legacy execution semantics. |
| RUNNER-001 | Phase 3 | Add bounded local execution, cooperative cancellation, ComfyUI interruption, and restart recovery observability | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/app.py studio/comfy.py studio/settings.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 32 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` — 39 passed, 1 pre-existing failure in `test_registry_only_freely_available_models` because `flux1-dev-gguf` has `FLUX.1-dev Non-Commercial License`; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/browser-smoke-test.py --url http://127.0.0.1:8123`; `scripts/workspace-accessibility-smoke.py --url http://127.0.0.1:8123` | 2026-10-21 | Added `STUDIO_JOB_CONCURRENCY` with a safe default of 1, durable cancellation checks, best-effort ComfyUI `/interrupt`, explicit interrupted-state logging, and cooperative task cleanup. Restarted active jobs remain interrupted and require explicit retry to prevent duplicate remote execution. No model was installed or executed; unrelated frontend/generated working-tree changes were preserved. Next: complete Phase 3 migration of remaining legacy execution paths, then implement the full Phase 4 persistent worker/retry/backoff/restart reconciliation service. |
| MEDIA-004 | Phase 3 | Harden legacy Vault cancellation, persisted pack recovery metadata, and thread-resume deduplication | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/api_v2.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 33 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` — 40 passed, 1 pre-existing model-license failure; `.\\.venv\\Scripts\\python.exe -m pip check`; browser and workspace accessibility smoke passed | 2026-10-21 | Vault parent Jobs now persist pack specs, launched threads are tracked and cleaned up, cancellation is checked before each pack and before canonical registration/completion, and a cancelled parent cannot be overwritten as completed. No model was installed or executed. Remaining standalone CLI/diffusion behavior is explicitly carried into Phase 4. |
| AUDIT-004 | Phase 0–3 gate | Audit Phase 0–3 readiness before Phase 4 | COMPLETED | `compileall -q studio`; `pip check`; `deployment-readiness.py` returned warning only for unavailable PyTorch; full suite 40 passed with 1 pre-existing model-license failure; prior browser/accessibility smoke passed; branch/status audit completed | 2026-10-21 | Phase 0 and Phase 2 are complete; Phase 1 core is complete but CLI PersonaVersion alignment remains; Phase 3 app routes are complete but standalone CLI/diffusion compatibility paths remain. User approved carrying those items into Phase 4. No model was installed or executed. |
| JOB-004 | Phase 4 | Replace request-created generation tasks with a durable queued-row dispatcher | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/app.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_frontend.py tests/test_api.py tests/test_comfy.py` — 34 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` — 41 passed, 1 pre-existing model-license failure; `.\\.venv\\Scripts\\python.exe -m pip check`; browser and workspace accessibility smoke passed; no model-backed job executed | 2026-10-21 | Created `phase/04-local-job-runner`; the supervisor claims persisted `queued` rows, applies configured bounded concurrency, wakes on enqueue/retry/completion, rejects unrecoverable queue metadata, and retains explicit interrupted-job recovery. Next: add leases/heartbeats, retry backoff, and prompt reconciliation. |

| JOB-005 | Phase 4 | Add execution leases, heartbeats, stale-job recovery, and retry backoff | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/app.py studio/comfy.py studio/settings.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` â€” 34 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` â€” 42 passed, 1 pre-existing model-license failure; default pytest collection also reports optional `torch`/`cv2` script imports because model dependencies remain deferred; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/deployment-readiness.py` warning only for unavailable PyTorch; no model-backed job executed | 2026-10-21 | Jobs now persist worker, start, heartbeat, lease-expiry, and next-retry metadata; active ComfyUI polling refreshes leases; expired running/submitted rows become interrupted; cancellation/completion/failure clear leases; retry uses capped exponential delay with `STUDIO_JOB_RETRY_BACKOFF_SECONDS` and `STUDIO_JOB_MAX_ATTEMPTS`. Next: prompt reconciliation, child-task progress, and memory/disk preflight. |

| JOB-006 | Phase 4 | Reconcile completed ComfyUI prompts after restart and deduplicate recovered assets | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/app.py studio/comfy.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` â€” 35 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` â€” 43 passed, 1 pre-existing model-license failure; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/deployment-readiness.py` warning only for unavailable PyTorch; no model-backed job executed | 2026-10-21 | Added ComfyUI history lookup, startup reconciliation for interrupted jobs with persisted prompt IDs, terminal failure handling for remote errors, shared canonical output finalization, and SHA-256 deduplication so repeated recovery cannot create duplicate assets. Pending prompts remain interrupted for explicit operator retry. Next: child-task progress and memory/disk preflight. |

| JOB-007 | Phase 4 | Persist and display stage and child-task progress | COMPLETED | `node --check static/workspace.js`; `.\\.venv\\Scripts\\python.exe -m py_compile studio/app.py studio/database.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` â€” 35 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` â€” 43 passed, 1 pre-existing model-license failure; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/browser-smoke-test.py --url http://127.0.0.1:8123`; `scripts/workspace-accessibility-smoke.py --url http://127.0.0.1:8123`; `scripts/deployment-readiness.py` warning only for unavailable PyTorch; no model-backed job executed | 2026-10-21 | Added schema version 12 progress fields, durable stages/percent/detail/child output state, shared updates across normal execution and prompt reconciliation, retry/cancel/terminal state reporting, `/api/jobs` progress parsing, and canonical Production Queue progress UI. No generation model was installed or executed. Next: memory/disk preflight. |

| JOB-008 | Phase 4 | Add memory and disk preflight resource gates | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/app.py studio/preflight.py studio/settings.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` â€” 36 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` â€” 44 passed, 1 pre-existing model-license failure; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/deployment-readiness.py` warning only for unavailable PyTorch; `node --check static/workspace.js`; no model-backed job executed | 2026-10-21 | Added dependency-free total/available memory probing with optional already-installed psutil support, conservative image/video/audio working-set estimates, configurable free-disk/memory/safety thresholds, read-only resource checks in `/api/preflight`, and a canonical `/api/jobs` queue gate that rejects unsafe resource conditions before persistence. No model or generation dependency was installed. Next: final runner hardening and broader operational validation. |

| JOB-009 | Phase 4 | Harden restart recovery to retain queued work safely | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/database.py studio/app.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` â€” 37 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` â€” 45 passed, 1 pre-existing model-license failure; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/deployment-readiness.py` warning only for unavailable PyTorch; no model-backed job executed | 2026-10-21 | Restart migration now leaves durable `queued` rows eligible for automatic dispatcher pickup while converting only `running`, `submitted`, and `cancelling` work to `interrupted`; retry schedules and ownership metadata are preserved safely. Next: final operational failure-injection and shutdown validation. |

| JOB-010 | Phase 4 | Reconcile managed jobs during graceful shutdown and failure injection | COMPLETED | `.\\.venv\\Scripts\\python.exe -m compileall -q studio tests`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` â€” 38 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` â€” 46 passed, 1 pre-existing failure in `test_registry_only_freely_available_models` because `flux1-dev-gguf` has `FLUX.1-dev Non-Commercial License`; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/deployment-readiness.py` warning only for unavailable PyTorch; no model-backed job executed | 2026-10-21 | Shutdown now snapshots managed Job IDs, cancels runner tasks, and reconciles only `running`, `submitted`, and `cancelling` rows as interrupted; durable `queued` rows remain eligible for a later dispatcher. The existing unrelated license assertion and deferred PyTorch warning remain unchanged. Next: broader CLI/diffusion compatibility cleanup and final model-installation gate. |

| MEDIA-005 | Phase 4 | Route standalone diffusion registration through the canonical asset boundary | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/diffusion_engine.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py` â€” 39 passed; `.\\.venv\\Scripts\\python.exe -m pytest -q tests` â€” 47 passed, 1 pre-existing failure in `test_registry_only_freely_available_models`; `.\\.venv\\Scripts\\python.exe -m pip check`; `scripts/deployment-readiness.py` warning only for unavailable PyTorch; no model-backed job executed | 2026-10-21 | The optional standalone diffusion registration mode now requires a canonical Persona, binds the latest PersonaVersion, stores bytes in the canonical output store, records hash/quality/lineage metadata, and leaves review pending with rights unconfirmed. The legacy render URL remains in the response for compatibility. The free CLI still writes caller-selected files and remains the next convergence item. |

| MEDIA-006 | Phase 4 | Add explicit free-CLI output registration into the canonical Asset store | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/free_cli.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_free_cli.py tests/test_api.py tests/test_comfy.py` â€” 47 passed, 1 pre-existing failure in `test_registry_only_freely_available_models`; `.\\.venv\\Scripts\\python.exe -m pip check`; no model-backed job executed | 2026-10-21 | Added `python -m studio.free_cli register`, which validates an existing image/video/audio file, requires a canonical Persona, binds its latest PersonaVersion, stores through `register_media_asset`, and keeps review pending unless the operator explicitly confirms rights. Direct generation commands remain compatibility paths and do not auto-register or auto-approve outputs. |

| MEDIA-007 | Phase 4 | Add opt-in canonical registration to direct free-CLI generation commands | COMPLETED | `.\\.venv\\Scripts\\python.exe -m py_compile studio/free_cli.py`; `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_free_cli.py tests/test_api.py tests/test_comfy.py` â€” 47 passed, 1 pre-existing failure in `test_registry_only_freely_available_models`; `.\\.venv\\Scripts\\python.exe -m studio.free_cli image --help`; `.\\.venv\\Scripts\\python.exe -m pip check`; no model-backed job executed | 2026-10-21 | Direct image, video, voice, mux, and pipeline commands accept an optional canonical `--persona-id`; when supplied after successful local generation, outputs are registered through the same Asset boundary. Without the flag, existing caller-selected file behavior is preserved. No command auto-confirms rights or review. |

| GATE-001 | Final gate | Audit target hardware, model register, and installation boundary | COMPLETED | PowerShell host audit: Windows 10 / HP 245 G7 / ~19.2 GB RAM; `.\\.venv\\Scripts\\python.exe scripts/deployment-readiness.py` returned warning only for unavailable PyTorch; official MPS/model source review completed; no model or Mac-specific runtime installed | 2026-10-21 | Current host is not the declared Apple M5 target, so MPS and unified-memory fit cannot be validated here. Recommended next gate: target-Mac installation of one image model, one short-video model, Kokoro, and required runtime packages one at a time with pinned revisions/checksums and measured memory/disk evidence. Wan2.2 5B remains excluded from the first 16 GB benchmark. |

## Frontend migration workstream

The existing `static/index.html`, `static/app.js`, and `static/styles.css`
surface is a legacy shell. It remains preserved while canonical replacements are
implemented and verified; it is not the production source of truth for the new
PersonaVersion/ReferencePack/ContentPack journey.

| Work item | Status | Required outcome |
|---|---|---|
| Canonical API client and normalized error handling | COMPLETED | `static/modules/api.js` now centralizes normalized errors, cancellation, bounded GET retries, and JSON helpers; adopted by canonical shell and ContentPack UI |
| Canonical frontend shell and navigation | COMPLETED | `/workspace` provides seven API-backed navigation destinations; legacy `/` remains during parity migration |
| Persona and PersonaVersion screens | COMPLETED | `/workspace#personas` creates new Master Personas, shows draft/frozen PersonaVersion lineage, and calls canonical create/version/freeze APIs; unique IDs remain server-owned |
| ReferencePack review and canonical selection screens | COMPLETED | `/workspace#references` exposes pack/item review, rights confirmation, image-asset linkage, eligibility diagnostics, and explicit canonical selection/clearing through canonical APIs |
| ContentPack author/review/resolve screen | COMPLETED | `/content-packs` is available on the Phase 2 branch |
| Generation and asset-review screens | COMPLETED | Asset Review, Production Queue, preflight-gated generation authoring, stale-preflight protection, and stale-asset/lineage visualization are complete for the Phase 2 gate; full model-backed execution remains deferred to later runtime phases |
| Export and Instagram publishing-readiness screens | PLANNED | Only approved, disclosed, policy-checked assets can advance |
| Accessibility/responsive/regression coverage | COMPLETED | Automated skip-link, landmark, named-control, loading/error/empty, no-overflow, 320/768/1024/1440px, axe WCAG 2A/2AA, and Chrome accessibility-tree coverage is available; manual assistive-technology certification remains operational follow-up |
| Legacy-shell parity bridge | COMPLETED | Root legacy shell is module-loaded, preserves Persona context on global, feature-level, and Gallery item-level canonical links, has a real-tab/axe/accessibility-tree smoke gate, and maps each legacy surface to a canonical destination; feature-by-feature replacement remains planned |
| Legacy-shell retirement | PLANNED | Remove only after canonical replacement parity and regression evidence |

## Dependency installation boundary

Application dependencies and development/frontend tooling may be installed or
updated when required for implementation, testing, or runtime integration. The
following remain prohibited until the final model-installation gate:

- image generation models or weights;
- audio/voice generation models or weights;
- video generation models or weights; and
- model repositories or downloads whose purpose is generation inference.

Any allowed dependency change must be added to the register with the package,
version, reason, source, command, validation, and rollback/removal notes.

## Adult/glamour implementation checklist

| Requirement | Status | Evidence/notes |
|---|---|---|
| Adult/glamour is a first-class content class | COMPLETED | Adult/glamour family is normalized as `adult_glamour`, `lingerie`, `boudoir`, or `nude_editorial` with identity-and-style authority |
| Adult/glamour guides content style | COMPLETED | Pack authority and content class are retained through review and selection |
| Approved adult/glamour assets can become canonical anchors | COMPLETED | Backend selection and `/content-packs` UI require an approved eligible pack/item, linked approved image asset, rights, and matching PersonaVersion |
| Adult/glamour assets are not auto-approved | COMPLETED | Direct generation paths now begin `pending`; explicit review remains required |
| Fictional adult status is explicit | COMPLETED | Persona and asset disclosure contracts remain required for generation/import |
| Rights and consent metadata is captured | COMPLETED | Reference-pack items and Assets carry rights confirmation gates |
| Disclosure is attached to export | PLANNED | Review/export phase |
| Platform policy is checked separately | PLANNED | Publishing phase |
| Restricted visibility/export controls exist | PLANNED | Review and publishing UI phase |
| Identity quality is evaluated on adult anchors | PLANNED | AI evaluation phase |

## Phase 2 ContentPack controls

| Requirement | Status | Evidence/notes |
|---|---|---|
| ContentPack is bound to one PersonaVersion | COMPLETED | Schema version 9 and create/resolver APIs enforce source-version matching |
| ContentPack reuses canonical assets by linkage, not duplication | COMPLETED | ContentPackItem stores ReferencePackItem and Asset IDs |
| ContentPack style directives are persisted and resolved | COMPLETED | `style_json` is returned by the approved resolver and appended to queued job prompts when requested |
| Adult/glamour ContentPack is part of Identity Core | COMPLETED | Adult/glamour creation forces `identity_core=true` and `identity_authority=identity_and_style` |
| Unapproved/stale anchors cannot resolve | COMPLETED | Resolver revalidates source pack, selected items, asset review, rights, version, and file presence |
| Master Persona UI authors/reviews ContentPacks | COMPLETED | `/content-packs` supports source selection, style/metadata authoring, pending review, approval/rejection, and canonical resolution |

## Legacy persona disposition

The user confirmed that new Master Personas will be generated with the new
structure and existing personas will not be used after the implementation.
This is a migration boundary, not a deletion request.

| Control | Required disposition | Status |
|---|---|---|
| Existing persona records | Preserve unchanged for reference, audit, and export | RECORDED |
| Existing generated/reference packs | Preserve as legacy/reference-only; do not use as new production source | RECORDED |
| New production Master Personas | Create through Persona + PersonaVersion + ReferencePack + ContentPack + review/lineage flow | RECORDED |
| Persona identifiers | Issue new unique IDs; do not reuse legacy IDs | RECORDED |
| Legacy asset promotion | Never automatic; require explicit import, provenance, rights/consent, review, and canonical selection | RECORDED |
| v2 compatibility | Retain for inspection/export/explicit import only; new creation targets canonical APIs | RECORDED |

No legacy persona or pack was deleted, rewritten, or promoted by this decision.

## Validation ledger

Phase 0 documentation and runtime enforcement are complete. The following
activities were verified:

~~~text
Activity: IMP-014
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - Request-ID response-header regression test
  - Correlation-ID response-header regression test
Result: PASS — 22 passed
Evidence: Compile succeeded; missing IDs are generated; safe supplied IDs are preserved; invalid IDs are replaced.

Activity: IMP-015
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - Photo Studio generation regression test with mocked local image backend
  - Source audit of Photo Studio, Orchestrator, diffusion-engine, and v2 fallback inserts
Result: PASS — compile succeeded; 22 passed
Evidence: Generated assets are inserted with review=pending and require explicit review before export/use.
~~~

The broader targeted command also included `tests/test_frontend.py` and reported one
unrelated existing failure: that test expects `type="module"` while the current
`static/index.html` uses a classic script tag. The existing frontend changes were
preserved and this issue is deferred to the frontend implementation phase. The
maintained `tests/` suite reported two unrelated existing failures: the model
license-registry assertion and the same frontend module-script assertion. The
backend Phase 0 gate remains green with 22 passed tests.

The repository-wide command also attempted to collect experimental scripts under
`scripts/` and stopped because optional `cv2` and `torch` packages are absent.
Those heavyweight model dependencies are not required for Phase 0 runtime
hardening and were intentionally not installed.

Future entries must include the exact validation command or inspection evidence:

~~~text
Activity: IMP-006
Validation:
  - pytest -q relevant test modules
  - storage resolver integration test
  - asset manifest file existence check
Result: PASS or FAIL
Evidence: summary and relevant output
~~~

### Phase 1 foundation validation

~~~text
Activity: IMP-017
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - Persona creation creates a draft PersonaVersion snapshot
  - Freeze transitions the version to frozen and returns the frozen version
  - Series rows store persona_version_id
  - Job lineage records persona_version and persona_version_id
  - Read-only live database check confirms schema version 5 and persona_versions table
Result: PASS — compile succeeded; 23 passed
Evidence: Phase 1 PersonaVersion foundation is active without installing models or heavyweight runtimes.
~~~

~~~text
Activity: IMP-018
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - First v2 access imports legacy JSON into canonical SQLite
  - v2 export returns schema_version persona-v2-export-1
  - Explicit v2 import merges new personas into canonical SQLite
  - Reference rows bind persona_version_id and expose role/content_class/review/rights metadata
  - Read-only live database check confirms schema version 6 and reference metadata columns
Result: PASS — compile succeeded; 24 passed
Evidence: data/personas_v2.json remains a three-persona compatibility backup; no models or heavyweight runtimes installed.
~~~

~~~text
Activity: IMP-019
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - v2 access creates turnaround, micro-detail, category-baseline, and adult/glamour packs
  - adult/glamour pack retains identity_and_style authority and pending review
  - archive stores reference packs and restore remaps them to the restored PersonaVersion
  - read-only live database check confirms schema version 7, 12 packs, and 39 pack items
Result: PASS — compile succeeded; 24 passed
Evidence: Adult/glamour remains part of the identity authority model without automatic approval; no models or heavyweight runtimes installed.
~~~

~~~text
Activity: IMP-021
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - Pack and item review endpoints reject unsafe approval transitions
  - Linked pack items expose asset_id, asset kind/review, and Asset PersonaVersion lineage
  - Canonical selection rejects missing/unapproved/mismatched assets
  - Asset rejection clears linked item and pack canonical selections
  - Read-only live database check confirms schema version 8, 12 packs, and 39 pack items
Result: PASS — compile succeeded; 25 passed; live schema migration verified
Evidence: Pack-level review/canonical selection and unified media-asset linkage are active without installing models or heavyweight runtimes.
~~~

The broader maintained `tests` command completed with 32 passed and two
unrelated pre-existing failures: the free-model license registry assertion and
the frontend module-script assertion. No Phase 1 pack/linkage regression was
reported by that run.

~~~text
Activity: IMP-022
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - ContentPack and ContentPackItem records bind to one PersonaVersion and canonical ReferencePack
  - Adult/glamour ContentPacks force identity_core and identity_and_style authority
  - Resolver returns persisted style directives and canonical Asset anchors
  - Rejected canonical assets invalidate ContentPack resolution
  - Job and series queue paths resolve approved ContentPack/canonical anchors when no explicit source is supplied
  - Read-only live database check confirms schema version 9 and empty new ContentPack tables
Result: PASS — compile succeeded; 26 passed; live schema migration verified
Evidence: Phase 2 ContentPack persistence and canonical-anchor resolution are active without installing models or heavyweight runtimes.
~~~

~~~text
Activity: IMP-023
Validation:
  - .\\.venv\\Scripts\\python.exe -m compileall -q studio
  - .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py tests/test_comfy.py
  - node --check static/content_packs.js
  - Route/static smoke check: GET /content-packs, /static/content_packs.js, and /static/content_packs.css returned 200
  - Workspace exposes only approved canonical ReferencePacks as selectable ContentPack sources
  - Authoring persists style and metadata; review remains explicit; resolve displays canonical anchors
  - Adult/glamour-family classes force Identity Core and identity_and_style authority in both UI and repository logic
Result: PASS — compile succeeded; 27 passed; JavaScript syntax and route/static checks passed
Evidence: Master Persona ContentPack authoring/review/resolution is available on the Phase 2 branch without installing models or heavyweight runtimes.
~~~

## Blockers and decisions

| ID | Blocker/decision | Status | Owner/action |
|---|---|---|---|
| DEC-001 | Approve Phase 0 implementation scope | CLOSED | User approved with “Start Phase 0” |
| DEC-002 | Select canonical identity-conditioning benchmark set | OPEN | After Phase 0/2 foundation |
| DEC-003 | Confirm publishing platforms and account model | OPEN | Before Phase 8 |
| DEC-004 | Install all image/audio/video generation models and model assets only at final installation gate | CLOSED | User clarification recorded; ordinary application/runtime dependencies may be installed or updated when required |
| DEC-005 | Create new Master Personas with the new structure; existing personas are legacy/reference-only after implementation | CLOSED | User clarification recorded; preserve old data, use new unique IDs, and require explicit reviewed import for any legacy reuse |
| DEC-006 | Migrate the current frontend to the new canonical implementation; permit non-model dependency/tooling updates while keeping generation models final-gate-only | CLOSED | User clarification recorded; frontend migration workstream and ADR-013 added |
| DEC-007 | Run final model/runtime installation on the declared Apple M5 target rather than the current Windows host | OPEN | User/action: open the repository in the target Mac environment before installing MPS/runtime/model artifacts |

## Final model and dependency installation register

**Global policy:** Generation models, model weights, and model repositories are
`NOT INSTALLED — FINAL GATE ONLY`. Application dependencies and development
tooling may be installed or updated during Phases 1–9 when required, but every
change must be recorded with version, reason, source, command, validation, and
rollback notes.

| Register ID | Component | Purpose | Source / license to verify | M5/16 GB fit to validate | Expected footprint | Install gate | Status |
|---|---|---|---|---|---:|---|---|
| MODEL-001 | Local image model selected from approved registry | Base image generation | Pinned upstream repository and license record | MPS memory, resolution, quantization benchmark | TBD | Final | NOT INSTALLED |
| MODEL-002 | Identity-conditioning adapter candidate | Face and identity consistency | Pinned upstream repository and model license | MPS support and peak unified memory | TBD | Final | NOT INSTALLED |
| MODEL-003 | Wan2.2 or approved local video model | Image-to-video and reels | Pinned upstream repository and license record | Sequential generation and disk/cache benchmark | TBD | Final | NOT INSTALLED |
| MODEL-004 | Kokoro or approved local narration model | Voice generation | Pinned upstream repository and license record | CPU/MPS latency and voice asset size | TBD | Final | NOT INSTALLED |
| RUNTIME-001 | PyTorch + Apple Silicon/MPS build | Local ML execution | Official package source and version pin | MPS compatibility and memory behavior | TBD | Feature/Final | NOT INSTALLED |
| RUNTIME-002 | Diffusers / Transformers / safetensors | Image pipeline runtime | Official package sources and version pins | Python 3.12 and MPS compatibility | TBD | Feature/Final | NOT INSTALLED |
| RUNTIME-003 | ComfyUI and approved custom nodes | Optional graph execution | Official repository and node licenses | Local service stability and disk use | TBD | Feature/Final | NOT INSTALLED |
| RUNTIME-004 | FFmpeg | Media assembly and validation | Official distribution/license record | Apple Silicon executable and codec coverage | TBD | Feature/Final | NOT INSTALLED |
| RUNTIME-005 | OpenCV and auxiliary vision packages | Face/quality evaluation | Official package sources and licenses | Install size and MPS/CPU behavior | TBD | Feature/Final | NOT INSTALLED |
| RUNTIME-006 | Playwright 1.64.0 + Chromium test browser 156.0.8078.4 | Frontend smoke and responsive UI validation | PyPI Playwright package and official Playwright browser distribution | Windows development validation; not a generation runtime | ~39 MB package plus browser cache | Feature | INSTALLED |

Each row must later gain: pinned version/revision, checksum, download URL,
installation date, installer identity, validation command, measured peak memory,
disk usage, and rollback/removal instructions.

## Change log

| Date | Change | Result |
|---|---|---|
| 2026-10-21 | Created final implementation roadmap | Adult/glamour assets may become approved canonical identity anchors |
| 2026-10-21 | Created implementation tracking file | Future successful activities require evidence-based updates |
| 2026-10-21 | Organized documentation | Kept final plan and tracking file active; moved 19 other Markdown files to docs/archieved doc/ |
| 2026-10-21 | Completed Phase 0 contracts baseline | Domain ownership, lifecycle states, storage, API ownership, observability and ADRs documented; no runtime code changed |
| 2026-10-21 02:11 +05:30 | Completed Phase 0 runtime hardening | Added bounded request/correlation traceability and removed direct-generation auto-approval; backend regression suite passed |
| 2026-10-21 02:12 +05:30 | Recorded validation boundaries | Maintained suite has two unrelated pre-existing failures; repository-wide collection also requires optional model packages; no Phase 0 regression detected |
| 2026-10-21 | Recorded final-only model installation policy | Added ADR-007, register, install gate, and decision DEC-004; model artifacts remain final-gate-only while ordinary dependencies may be added when needed |
| 2026-10-21 | Completed Phase 1 PersonaVersion foundation | Added SQLite version table/backfill, draft/frozen lifecycle, version APIs, series binding, and job lineage; compile and 23-test backend gate passed |
| 2026-10-21 | Completed Phase 1 v2 compatibility/reference binding | Added canonical v2 import/export facade, schema version 6 reference metadata, PersonaVersion binding, and 24-test backend gate; model installation remains deferred |
| 2026-10-21 | Completed Phase 1 ReferencePack normalization | Added schema version 7 pack/item tables, adult/glamour identity authority metadata, and archive/restore PersonaVersion remapping; 24-test backend gate passed |
| 2026-10-21 | Recorded new Master Persona migration boundary | Added ADR-010 and legacy persona disposition controls; existing personas/packs remain untouched and new production creation will use the new canonical structure |
| 2026-10-21 | Completed Phase 1 pack review and unified media linkage | Added schema version 8 asset/pack linkage, PersonaVersion-bound assets, review/canonical APIs, rejection invalidation, v2 routes, and regression coverage; 25-test backend gate passed |
| 2026-10-21 | Created phase branch structure and Phase 1 checkpoint | Added `phase/00-baseline` and `phase/01-canonical-persona`; committed Phase 1 as `9900255`; added `phase-0-baseline` and `phase-1-checkpoint-70` tags |
| 2026-10-21 | Started Phase 2 ContentPack implementation | Created `phase/02-master-persona-content-packs`; added schema version 9 ContentPack persistence, resolver APIs, canonical job/series fallback, adult/glamour identity-core enforcement, and 26-test backend gate |
| 2026-10-21 | Completed Phase 2 ContentPack workspace slice | Added `/content-packs` author/review/resolve UI, expanded adult/glamour-family Identity Core enforcement, added route/UI regression coverage, and passed 27-test backend gate; model installation remains deferred |
| 2026-10-21 | Recorded frontend migration and dependency boundary | Current frontend is designated a legacy shell requiring canonical replacement; application/tooling dependencies may be installed or updated, while image/audio/video generation models remain final-gate-only |
| 2026-10-21 | Completed shared frontend API-client foundation | Installed Playwright 1.64.0 and Chromium test browser; centralized API errors/cancellation/retries/helpers; ContentPack browser smoke and 27-test backend gate passed; no generation models installed |
| 2026-10-21 | Completed canonical frontend shell slice | Added `/workspace` and responsive API-backed navigation for identity, reference, ContentPack, production, asset-review, and publishing-readiness workflows; 28-test backend gate and Chromium desktop/mobile smoke passed |
| 2026-10-21 | Completed stale-asset and lineage visibility slice | Added ReferencePack lineage diagnostics, pack summaries, active-persona asset linkage, stale ContentPack/Asset Review warnings, and fixture-driven Chromium smoke; 28-test backend gate passed; model installation remains deferred |
| 2026-10-21 | Completed canonical workspace accessibility/responsive slice | Added skip-link and landmark semantics, `aria-busy` loading state, mobile toolbar constraint, and repeatable Playwright coverage at 320/768/1024/1440px; no models or generation jobs were installed/executed |
| 2026-10-21 | Completed axe/error-state certification and legacy parity bridge | Pinned axe-core 4.10.2 audit runner returned zero canonical and legacy WCAG 2A/2AA violations; Chrome accessibility-tree and loading/error/empty checks passed; root legacy shell gained module entrypoint and canonical-workspace bridge; feature retirement remains deferred |
| 2026-10-21 | Completed legacy-to-canonical handoff map | Added explicit links from Vault, Generate, Story, Gallery, and System legacy surfaces to the canonical Personas, Production, ContentPacks, Asset Review, and Overview views; browser smoke verifies all five targets |
| 2026-10-21 | Completed Persona-preserving legacy handoff | Legacy canonical links now carry the active `persona_id`; browser regression verifies target mapping and selected Persona propagation without changing the legacy data store |
| 2026-10-21 | Completed global Persona-preserving workspace bridge | Root shell's direct canonical workspace link now carries the active `persona_id`; frontend and browser regression gates passed without changing legacy behavior |
| 2026-10-21 | Completed stale-preflight protection | Canonical Production now rejects stale or superseded preflight results before queueing; frontend, API, browser, and accessibility regression gates passed |
| 2026-10-21 | Completed Gallery-to-Asset-Review handoff | Legacy Gallery cards now link to canonical Asset Review using the asset-owned Persona ID; browser and accessibility regression gates passed |
| 2026-10-21 | Completed legacy Master Vault canonical creation handoff | Vault synthesis now creates an editable session-scoped canonical draft instead of writing through the legacy v2 creation endpoint; canonical form prefill, 29-test suite, browser smoke, accessibility smoke, runtime handoff test, and `pip check` passed; no generation model or media job was installed/executed |
| 2026-10-21 | Completed legacy Orchestrator canonical Production handoff | Orchestrator Generate now creates a reviewable session-scoped Production draft instead of calling the legacy generation endpoint; canonical preflight/rights/job gates remain required; runtime handoff and regression validation passed without model installation or job execution |
| 2026-10-21 | Completed Phase 4 shutdown reconciliation hardening | Managed runner tasks are reconciled on graceful shutdown; active execution rows become interrupted while durable queued rows remain queued; focused suite passed 38 tests, full suite passed 46 with the known model-license assertion, and no models were installed or executed |
| 2026-10-21 | Completed Phase 4 standalone diffusion asset-boundary migration | Optional diffusion registration now uses canonical PersonaVersion-aware media storage with pending review, unconfirmed rights, hashes, quality, and lineage metadata; focused suite passed 39 tests, full suite passed 47 with the known model-license assertion, and no models were installed or executed |
| 2026-10-21 | Completed Phase 4 explicit free-CLI registration bridge | Added canonical registration for existing CLI image/video/audio outputs with PersonaVersion binding, media validation, pending review, and explicit rights confirmation; targeted suite passed 47 tests with the known model-license assertion, and no models were installed or executed |
| 2026-10-21 | Completed Phase 4 opt-in direct free-CLI registration | Image, video, voice, mux, and pipeline commands can now register successful outputs when given a canonical `--persona-id`; targeted suite passed 47 tests with the known model-license assertion, help validation passed, and no models were installed or executed |
| 2026-10-21 | Audited final model/runtime installation gate | Confirmed the current host is Windows HP 245 G7 rather than the declared Apple M5 target; recorded target-Mac requirement, minimal install sequence, source/license verification, and no-install decision |

