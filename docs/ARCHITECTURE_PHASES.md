# Phase 1 and Phase 2 implementation notes

This document is the restore-point description for the first hardening and
structure pass. The application remains a modular monolith: the dashboard,
SQLite control plane and local render workers stay in one repository, while
the boundaries are explicit enough to extract a worker later.

## Phase 1 — runtime safety and observability

- **Optional bearer authentication:** set `STUDIO_AUTH_TOKEN` before exposing
  the service through a cloud tunnel. Requests to `/api/*` and `/go/*` then
  require `Authorization: Bearer <token>` (or `X-Studio-Token`). With no token,
  the existing loopback-only workflow remains compatible.
- **Bounded uploads:** briefs, persona JSON, workflows, references and imported
  assets are read in chunks with configurable limits. Images are decoded and
  signature-checked rather than trusted from a filename. Set
  `STUDIO_STRICT_MEDIA=1` on a production worker to require basic video/audio
  container signatures as well.
- **Durable job request metadata:** each job stores the validated request JSON,
  timestamps and state transitions. A restart marks in-flight work as
  `interrupted` so it is visible and can be retried instead of disappearing.
- **Lifecycle-aware workers:** background tasks are tracked on FastAPI startup
  and cancelled cleanly during shutdown. The current worker is still
  in-process; a durable external queue is intentionally a later phase.
- **Structured events:** job start, queue, completion and failure events are
  logged with job/persona/workflow identifiers.

## Phase 2 — modular monolith boundaries

- `studio/settings.py` owns environment-backed limits and authentication.
- `studio/policies.py` owns shared disclosure and negative-prompt defaults.
- `studio/schemas.py` owns HTTP request models while `studio/brief.py` remains
  the ChatGPT JSON contract.
- `studio/media.py` owns bounded reads, image decoding and media signatures.
- `studio/repositories.py` owns the first persistence operations and exposes a
  transaction-backed series create path.
- `studio/database.py` now records schema version `4`, adds useful indexes and
  exposes `write_many()` for atomic multi-row writes.

The route module is intentionally not split into microservices yet. The next
safe extraction is a job service/worker process once the cloud deployment
needs retries across multiple machines.

## Recommended cloud environment

```text
STUDIO_AUTH_TOKEN=<long random secret>
STUDIO_STRICT_MEDIA=1
STUDIO_MAX_ASSET_BYTES=524288000
STUDIO_JOB_TIMEOUT_SECONDS=3600
```

Keep the dashboard bound to `127.0.0.1` and use an authenticated SSH tunnel or
private network. Do not publish the unauthenticated mode to the internet.

## Phase 3 — execution reliability

- `GET /api/preflight?workflow_id=<id>` runs read-only storage, workflow and
  FFmpeg checks before a render is queued.
- Jobs persist `lineage_json`, `attempt` and cancellation state. The lineage
  captures persona version, workflow/checkpoint, references, seed and canvas.
- `POST /api/jobs/{id}/cancel` stops an active local task and records the
  operator action. `POST /api/jobs/{id}/retry` reuses validated request
  metadata for failed, interrupted or cancelled work.
- Monitoring now exposes active, failed, cancelled and retried queue counts.

The queue is still a single-process worker by design. A cross-machine durable
queue and GPU lease are the next scale step, not an implicit dependency of the
local workflow.

## Phase 4 — frontend cleanup

- The dashboard now runs as an ES module entrypoint instead of a legacy global
  script. Shared DOM/state helpers live in `static/modules/core.js`.
- HTTP parsing, authentication errors and JSON POST handling live in
  `static/modules/api.js`.
- Collapsible navigation and its persisted open state live in
  `static/modules/navigation.js`.
- Generation now exposes the Phase 3 preflight check before queueing, while
  job cards expose cancel/retry actions and monitoring shows access security.
- Static module delivery is covered by a frontend smoke test; the Python API
  contract remains unchanged.

No bundler or npm toolchain is required yet. This keeps the dashboard usable
on the same lightweight local/cloud Python deployment; a later UI phase can
add type checking and browser end-to-end tests when Node tooling is available.

## Phase 5 — quality and export provenance

- Assets store a SHA-256 hash, basic media metadata and the latest quality
  report. Image files are decoded during the check; disclosure and lineage are
  surfaced as explicit review signals.
- Approved assets expose a manifest endpoint and a ZIP export containing the
  media file, `manifest.json` and `AI-DISCLOSURE.txt`.
- Approval blocks integrity errors but still requires human review; warnings
  such as missing lineage do not silently publish anything.
- The gallery shows the quality status and offers the export package only after
  approval.
