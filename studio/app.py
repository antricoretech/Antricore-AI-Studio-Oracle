"""VS Code runnable control panel for ComfyUI-based fictional influencer creation.

Local-first by default. Configure ``STUDIO_AUTH_TOKEN`` before binding outside
loopback or using a shared cloud worker.
"""
from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
import importlib.util
import json
import os
import re
import secrets
import sqlite3
import shutil
import sys
import tempfile
import time
import uuid
import logging
import zipfile
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_CATALOG = ROOT / "config" / "workflow_catalog.json"
DEFAULT_WORKFLOW_LABELS = {
    "default_image_api": ("Default image API · checkpoint", "Built-in ComfyUI API starter graph; choose an installed checkpoint before queueing."),
    "wan22_ti2v_5b_default_api": ("Wan2.2 TI2V 5B · default image-to-video API", "Built-in official-style Wan2.2 TI2V graph; requires the matching diffusion model, text encoder and VAE."),
}
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from . import database as db
from .assets import asset_file as resolve_asset_file, reference_path, register_media_asset, validate_import_suffix
from .brief import PersonaBrief, PersonaCharacteristics, brief_dict, parse_brief_bytes, parse_persona_bytes
from .comfy import ComfyClient, output_files, render_graph, validate_graph
from .engines import get as get_engine, rows as engine_rows
from .media import read_limited, validate_image_bytes, validate_media_signature
from .model_registry import get as get_model, rows as model_rows, workflow_model
from .policies import AI_DISCLOSURE, normalize_content_class, normalize_destination_policy
from .publishing_policies import catalog as publishing_policy_catalog, evaluate as evaluate_publishing_policy, infer_format
from .publishing_providers import PublishError, ProviderDisabled, catalog as publishing_provider_catalog, get as get_publishing_provider
from .secrets import SecretStoreUnavailable, catalog as secret_storage_catalog, get_store
from .preflight import resource_preflight, workflow_preflight
from .provenance import manifest, media_metadata, quality_report, sha256_bytes
from .identity_conditioning import method_catalog, scenario_catalog
from .repositories import ContentArtifactRepository, ContentBriefRepository, ContentPackRepository, CreatorProfileRepository, IdentityBenchmarkRepository, JobRepository, PersonaRepository, PublishingRepository, ReferencePackRepository, SeriesRepository
from .readiness import evaluate as evaluate_readiness
from .schemas import (
    AssetAssessmentIn, ContentArtifactIn, ContentArtifactReviewIn, ContentBriefIn, ContentPackIn, ContentPackReviewIn, CreatorProfileIn, IdentityBenchmarkIn, IdentityBenchmarkResultIn, JobIn, LinkIn, PersonaIn, ReviewIn, ReferencePackReviewIn, ReferencePackCanonicalIn, ReferencePackAssetLinkIn,
    SeriesEpisodeIn, SeriesIn, SeriesQueueIn, VoiceIn, PhotoStudioPromptIn, PhotoStudioGenerateIn,
    OrchestratorCompilePersonaIn, OrchestratorCreatePersonaIn, OrchestratorRenderAnchorIn, OrchestratorLockAnchorIn, PublishingAccountIn, PublishDryRunIn, PublishingAuthorizationPlanIn,
    OrchestratorSynthesizeScenesIn, OrchestratorBatchGenerateIn
)
from . import orchestrator
from .settings import get_settings

logger = logging.getLogger("studio")
_request_id_context: ContextVar[str] = ContextVar("studio_request_id", default="")
_correlation_id_context: ContextVar[str] = ContextVar("studio_correlation_id", default="")
_TRACE_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uid():
    return uuid.uuid4().hex


def _trace_id(value: str | None) -> str:
    """Accept bounded operator-supplied trace IDs, otherwise generate one."""

    value = (value or "").strip()
    return value if _TRACE_ID_PATTERN.fullmatch(value) else uid()


def _log_data(data: dict | None = None) -> dict:
    """Merge request trace context into structured log payloads."""

    payload = {
        "request_id": _request_id_context.get(),
        "correlation_id": _correlation_id_context.get(),
    }
    if data:
        payload.update(data)
    return {"data": payload}


def _job_cancel_requested(job_id: str) -> bool:
    row = db.row("SELECT status, cancel_requested FROM jobs WHERE id=?", (job_id,))
    return bool(row and (row.get("cancel_requested") or row.get("status") == "cancelled"))


def _worker_id() -> str:
    return getattr(app.state, "worker_id", "studio-local")


def _lease_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=get_settings().job_lease_seconds)).isoformat(timespec="seconds")


def _claim_job(job_id: str):
    timestamp = now()
    db.write(
        "UPDATE jobs SET status='running', worker_id=?, started_at=COALESCE(started_at,?), "
        "heartbeat_at=?, lease_expires_at=?, updated_at=?, progress_stage='starting', "
        "progress_percent=0, progress_detail='Worker claimed job' "
        "WHERE id=? AND status NOT IN ('completed','failed','cancelled')",
        (_worker_id(), timestamp, timestamp, _lease_expiry(), timestamp, job_id),
    )


def _heartbeat_job(job_id: str, status: str | None = None):
    timestamp = now()
    assignments = ["heartbeat_at=?", "lease_expires_at=?", "updated_at=?"]
    values = [timestamp, _lease_expiry(), timestamp]
    if status:
        assignments.append("status=?")
        values.append(status)
    values.append(job_id)
    db.write(
        f"UPDATE jobs SET {', '.join(assignments)} WHERE id=? AND status IN ('running','submitted')",
        tuple(values),
    )


def _update_job_progress(job_id: str, stage: str, percent: int, detail: str = "", children: list[dict] | None = None):
    """Persist bounded stage and child-task progress alongside the lease."""

    timestamp = now()
    bounded_percent = max(0, min(100, int(percent)))
    progress = {"children": children or []}
    db.write(
        "UPDATE jobs SET progress_stage=?, progress_percent=?, progress_detail=?, progress_json=?, "
        "heartbeat_at=?, lease_expires_at=?, updated_at=? WHERE id=? AND status IN ('running','submitted')",
        (stage[:80], bounded_percent, detail[:500], json.dumps(progress, ensure_ascii=False), timestamp, _lease_expiry(), timestamp, job_id),
    )


def _retry_delay(attempt: int) -> int:
    settings = get_settings()
    exponent = max(0, int(attempt) - 2)
    return min(settings.job_retry_backoff_seconds * (2 ** exponent), 300)


def _recover_expired_jobs():
    """Mark jobs whose local execution lease expired as interrupted."""

    expired = db.all_rows(
        "SELECT id, worker_id, lease_expires_at FROM jobs "
        "WHERE status IN ('running','submitted') AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?",
        (now(),),
    )
    for row in expired:
        job_id = row["id"]
        updated = now()
        db.write(
            "UPDATE jobs SET status='interrupted', error=?, finished_at=?, updated_at=?, "
            "worker_id=NULL, heartbeat_at=NULL, lease_expires_at=NULL, progress_stage='interrupted', "
            "progress_detail='Execution lease expired; retry from Studio' "
            "WHERE id=? AND status IN ('running','submitted')",
            ("Execution lease expired; retry from Studio", updated, updated, job_id),
        )
        task = getattr(app.state, "job_task_map", {}).get(job_id)
        if task and not task.done():
            task.cancel()
        logger.warning("job_lease_expired", extra=_log_data({"job_id": job_id, "worker_id": row.get("worker_id")}))


def _mark_job_interrupted(job_id: str, reason: str = "Job execution was interrupted; retry from Studio"):
    timestamp = now()
    db.write(
        "UPDATE jobs SET status='interrupted', error=?, finished_at=?, updated_at=?, "
        "worker_id=NULL, heartbeat_at=NULL, lease_expires_at=NULL, progress_stage='interrupted', "
        "progress_detail=? "
        "WHERE id=? AND status NOT IN ('completed','failed','cancelled')",
        (reason[:1500], timestamp, timestamp, reason[:500], job_id),
    )


def _mark_shutdown_jobs_interrupted(job_ids: list[str]) -> int:
    """Reconcile managed jobs after task cancellation during application stop.

    A task can be cancelled while waiting for the semaphore, before
    ``execute_job`` claims it and records the normal interruption transition.
    Only rows that represent active execution are changed here. Durable
    ``queued`` rows remain queued so a later process can dispatch them.
    """

    interrupted = 0
    for job_id in job_ids:
        row = db.row("SELECT status FROM jobs WHERE id=?", (job_id,))
        if row and row["status"] in {"running", "submitted", "cancelling"}:
            _mark_job_interrupted(job_id, "Studio stopped while job was executing; retry from Studio")
            interrupted += 1
    return interrupted


def _normalized_idempotency_key(value: str | None) -> str | None:
    key = (value or "").strip()
    if not key:
        return None
    if not _IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
        raise HTTPException(400, "Idempotency-Key must contain only letters, numbers, '.', '_', ':', or '-'")
    return key


def _payload_json(payload) -> str:
    try:
        return payload.model_dump_json()
    except AttributeError:
        return payload.json()


def _reusable_idempotent_result(existing: dict) -> dict:
    try:
        return json.loads(existing.get("result_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        raise HTTPException(409, "Completed idempotent job has no reusable result") from None


def _raise_idempotency_conflict(existing: dict):
    if existing["status"] == "completed":
        return _reusable_idempotent_result(existing)
    raise HTTPException(409, f"Idempotency key is already associated with job {existing['id']} ({existing['status']})")


def _start_direct_job(*, person: dict, workflow_id: str, kind: str, prompt: str, payload, lineage: dict, idempotency_key: str | None):
    key = _normalized_idempotency_key(idempotency_key)
    if key:
        existing = JobRepository.by_idempotency_key(key)
        if existing:
            return None, _raise_idempotency_conflict(existing)

    job_id = uid()
    created = now()
    try:
        JobRepository.create(
            job_id=job_id,
            persona_id=person["id"],
            workflow_id=workflow_id,
            kind=kind,
            prompt=prompt,
            request_json=_payload_json(payload),
            lineage_json=json.dumps(lineage, separators=(",", ":")),
            created_at=created,
            idempotency_key=key,
        )
    except sqlite3.IntegrityError:
        # The lookup above is only an optimization; the unique partial index is
        # the authority when two requests arrive at the same time.
        if not key:
            raise
        existing = JobRepository.by_idempotency_key(key)
        if not existing:
            raise
        return None, _raise_idempotency_conflict(existing)
    return job_id, None


async def _finish_direct_job(job_id: str, handler):
    db.write("UPDATE jobs SET status='running', updated_at=? WHERE id=?", (now(), job_id))
    _update_job_progress(job_id, "running", 5, "Direct job is executing")
    try:
        result = await handler()
        _mark_job_completed(job_id, result)
        return result
    except HTTPException as exc:
        _mark_job_failed(job_id, str(exc.detail))
        raise
    except Exception as exc:
        _mark_job_failed(job_id, str(exc))
        raise HTTPException(500, str(exc)[:300]) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    app.state.worker_id = f"studio-{uuid.uuid4().hex[:12]}"
    app.state.job_tasks = set()
    app.state.job_task_map = {}
    app.state.job_semaphore = asyncio.Semaphore(get_settings().job_concurrency)
    app.state.job_dispatch_event = asyncio.Event()
    interrupted = db.row("SELECT COUNT(*) AS count FROM jobs WHERE status='interrupted'")
    app.state.job_reconciler = asyncio.create_task(_reconcile_interrupted_prompts(), name="studio-job-reconciler")
    app.state.job_dispatcher = asyncio.create_task(_job_dispatch_loop(), name="studio-job-dispatcher")
    logger.info("studio_started", extra={"data_dir": str(db.DATA)})
    logger.info("job_recovery_state", extra=_log_data({
        "interrupted_jobs": int((interrupted or {}).get("count") or 0),
        "concurrency": get_settings().job_concurrency,
        "worker_id": app.state.worker_id,
        "lease_seconds": get_settings().job_lease_seconds,
        "max_attempts": get_settings().job_max_attempts,
        "retry_policy": "explicit_operator_retry",
    }))
    try:
        yield
    finally:
        reconciler = getattr(app.state, "job_reconciler", None)
        if reconciler and not reconciler.done():
            reconciler.cancel()
        dispatcher = getattr(app.state, "job_dispatcher", None)
        if dispatcher and not dispatcher.done():
            dispatcher.cancel()
        if reconciler:
            await asyncio.gather(reconciler, return_exceptions=True)
        if dispatcher:
            await asyncio.gather(dispatcher, return_exceptions=True)
        tasks = list(getattr(app.state, "job_tasks", set()))
        managed_job_ids = list(getattr(app.state, "job_task_map", {}).keys())
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        interrupted = _mark_shutdown_jobs_interrupted(managed_job_ids)
        logger.info("studio_stopped", extra={"cancelled_tasks": len(tasks), "interrupted_jobs": interrupted})

app = FastAPI(title="AI Influencer Studio", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/generated", StaticFiles(directory=ROOT / "generated"), name="generated")

from .api_v2 import router as v2_router
app.include_router(v2_router, prefix="/api/v2")


@app.middleware("http")
async def optional_token_auth(request: Request, call_next):
    """Require a bearer token only when the operator explicitly configures one."""

    settings = get_settings()
    if settings.auth_token and (request.url.path.startswith("/api/") or request.url.path.startswith("/go/")):
        supplied = request.headers.get("authorization", "")
        token = supplied[7:].strip() if supplied.lower().startswith("bearer ") else request.headers.get("x-studio-token", "")
        if token != settings.auth_token:
            return JSONResponse({"detail": "Studio authentication required"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
    return await call_next(request)


@app.middleware("http")
async def request_trace_context(request: Request, call_next):
    """Attach bounded request/correlation IDs to every response and log event."""

    supplied_request_id = request.headers.get("x-request-id")
    supplied_correlation_id = request.headers.get("x-correlation-id")
    request_id = _trace_id(supplied_request_id or supplied_correlation_id)
    correlation_id = _trace_id(supplied_correlation_id or supplied_request_id)
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    request_token = _request_id_context.set(request_id)
    correlation_token = _correlation_id_context.set(correlation_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "request_completed",
            extra=_log_data({
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }),
        )
        return response
    finally:
        _request_id_context.reset(request_token)
        _correlation_id_context.reset(correlation_token)


def workflow_path(wid):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{3,100}", wid):
        raise HTTPException(400, "Invalid workflow id")
    for root in [db.WORKFLOWS, ROOT / "workflows"]:
        path = root / f"{wid}.json"
        if path.is_file():
            return path
    if any(item.get("id") == wid for item in workflow_catalog()):
        raise HTTPException(409, "This workflow is a catalog recipe, not an installed ComfyUI graph. Use the direct CLI path or import a verified API-format graph first.")
    raise HTTPException(404, "Workflow not found")


def workflow_catalog():
    try:
        payload = json.loads(WORKFLOW_CATALOG.read_text(encoding="utf8"))
        return payload if isinstance(payload, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def workflow_list():
    entries = []
    installed = set()
    for location in [ROOT / "workflows", db.WORKFLOWS]:
        for path in sorted(location.glob("*.json")):
            try:
                graph = json.loads(path.read_text(encoding="utf8"))
                validate_graph(graph)
                text = path.read_text(encoding="utf8")
                installed.add(path.stem)
                default_label, default_description = DEFAULT_WORKFLOW_LABELS.get(path.stem, (path.stem, "Verified API-format graph installed locally."))
                entries.append({"id": path.stem, "label": default_label, "nodes": len(graph), "ready": True, "backend": "comfyui", "model": "custom", "task": "video.image_to_video" if any(x in path.stem.lower() for x in ("video", "wan", "ltx", "talk", "lip")) else "image.text_to_image", "description": default_description, "requires_reference": "{{REFERENCE_IMAGE}}" in text, "requires_audio": "{{AUDIO_FILENAME}}" in text,
                                "requires_checkpoint": "{{CHECKPOINT}}" in text,
                                "supports_prompt": "{{PROMPT}}" in text, "category": "video" if any(x in path.stem.lower() for x in ("video", "wan", "ltx", "talk", "lip")) else "image"})
            except Exception:
                continue
    entries.extend(item for item in workflow_catalog() if item.get("id") not in installed)
    for item in entries:
        model = get_model(item.get("model"))
        if model:
            item.setdefault("capabilities", model.get("capabilities", []))
            item.setdefault("license", model.get("license"))
            item.setdefault("min_vram_gb", model.get("min_vram_gb"))
            item.setdefault("recommended_vram_gb", model.get("recommended_vram_gb"))
            item.setdefault("revision", model.get("revision"))
        engine = get_engine(item.get("backend"))
        if engine:
            item.setdefault("engine_label", engine.label)
            item.setdefault("engine_description", engine.description)
        item.setdefault("task", workflow_model(item)[2])
    return entries


def _monitor_status(ok: bool, detail: str, **extra):
    return {"status": "ready" if ok else "warning", "detail": detail, **extra}


def _model_monitor_rows():
    return model_rows()


def _runtime_monitor_rows():
    rows = []
    ffmpeg = shutil.which("ffmpeg")
    rows.append({"id": "ffmpeg", "label": "FFmpeg", "status": "ready" if ffmpeg else "warning", "detail": ffmpeg or "Not found on PATH"})
    modules = {name: importlib.util.find_spec(name) is not None for name in ("kokoro", "soundfile", "numpy")}
    missing = [name for name, present in modules.items() if not present]
    rows.append({"id": "kokoro", "label": "Kokoro narration", "status": "ready" if not missing else "warning", "detail": "Kokoro and audio dependencies available" if not missing else "Missing: " + ", ".join(missing)})
    wan_root = ROOT / "external" / "Wan22"
    wan_python = os.getenv("WAN_PYTHON", "")
    candidates = [Path(wan_python)] if wan_python else []
    candidates.extend([wan_root / ".venv" / "Scripts" / "python.exe", wan_root / ".venv" / "bin" / "python"])
    executable = next((path for path in candidates if path and path.is_file()), None)
    wan_ready = (wan_root / "generate.py").is_file() and executable is not None
    rows.append({"id": "wan22", "label": "Wan2.2 runtime", "status": "ready" if wan_ready else "warning", "detail": "Official checkout and separate Python runtime ready" if wan_ready else "Need external/Wan22/generate.py and a Wan Python environment", "python": str(executable) if executable else ""})
    try:
        import torch
        cuda = bool(torch.cuda.is_available())
        if cuda:
            device = torch.cuda.get_device_properties(0)
            rows.append({"id": "gpu", "label": "CUDA GPU", "status": "ready", "detail": f"{device.name} · {device.total_memory / (1024 ** 3):.1f} GiB VRAM", "cuda": True})
        else:
            rows.append({"id": "gpu", "label": "CUDA GPU", "status": "warning", "detail": "CUDA is unavailable in this Python runtime", "cuda": False})
    except Exception as exc:
        rows.append({"id": "gpu", "label": "CUDA GPU", "status": "warning", "detail": "PyTorch unavailable: " + str(exc)[:160], "cuda": False})
    rows.append({"id": "python", "label": "Studio Python", "status": "ready", "detail": sys.version.split()[0] + " · " + sys.executable})
    return rows


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/content-packs", response_class=HTMLResponse)
def content_packs_page():
    """Serve the focused Master Persona ContentPack authoring workspace."""
    return FileResponse(ROOT / "static" / "content_packs.html")


@app.get("/workspace", response_class=HTMLResponse)
def canonical_workspace_page():
    """Serve the canonical API-backed frontend shell during legacy UI migration."""
    return FileResponse(ROOT / "static" / "workspace.html")


@app.post("/api/briefs/validate")
async def validate_brief(file: UploadFile = File(...)):
    """Validate a ChatGPT-authored generation brief without queuing work."""
    try:
        raw = await read_limited(file, get_settings().brief_max_bytes)
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    try:
        brief = parse_brief_bytes(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return brief_dict(brief)


def persona_response(person):
    """Expose stored persona characteristics as JSON, not a raw DB string."""
    if not person:
        return person
    result = dict(person)
    raw = result.pop("characteristics_json", "{}")
    try:
        result["characteristics"] = json.loads(raw or "{}")
    except json.JSONDecodeError:
        result["characteristics"] = {}
    version = PersonaRepository.current_version(result.get("id")) if result.get("id") else None
    if version:
        result["current_version"] = persona_version_response(version)
    return result


def persona_version_response(version):
    if not version:
        return None
    result = dict(version)
    raw_snapshot = result.pop("snapshot_json", "{}")
    try:
        result["snapshot"] = json.loads(raw_snapshot or "{}")
    except json.JSONDecodeError:
        result["snapshot"] = {}
    return result


def store_persona(payload: PersonaIn):
    pid = uid()
    return persona_response(PersonaRepository.create(
        persona_id=pid,
        name=payload.name.strip(),
        age=payload.age,
        description=payload.description.strip(),
        appearance=payload.appearance.strip(),
        disclosure=payload.disclosure.strip(),
        created_at=now(),
        characteristics=brief_dict(payload.characteristics),
    ))


def persona_input_from_brief(brief: PersonaBrief):
    characteristics = brief_dict(brief.characteristics)
    characteristics["consistency_anchor"] = brief.consistency_anchor
    return PersonaIn(name=brief.name, age=brief.age, appearance=brief.appearance,
                     description=brief.description, disclosure=brief_disclosure(brief.disclosure),
                     characteristics=PersonaCharacteristics(**characteristics))


def brief_disclosure(value):
    if isinstance(value, str):
        return value[:250]
    if isinstance(value, dict):
        for key in ("public_disclosure", "short_disclosure", "on_screen_disclosure"):
            if isinstance(value.get(key), str) and value[key].strip():
                return value[key].strip()[:250]
    return "Fictional AI-generated adult persona"


@app.post("/api/personas/import", status_code=201)
async def import_persona(file: UploadFile = File(...)):
    """Validate and create one persona from a ChatGPT-authored JSON file."""
    try:
        raw = await read_limited(file, get_settings().brief_max_bytes)
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    try:
        brief = parse_persona_bytes(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return store_persona(persona_input_from_brief(brief.persona))


@app.get("/api/health")
async def health():
    try:
        async with ComfyClient() as client:
            stats = await client.health()
        return {"app": "ready", "comfyui": "connected", "comfy_devices": stats.get("devices", [])}
    except Exception as e:
        return {"app": "ready", "comfyui": "offline", "detail": str(e)[:200]}


@app.get("/api/checkpoints")
async def checkpoints():
    try:
        async with ComfyClient() as client:
            result = await client.checkpoints()
        return {"checkpoints": result}
    except Exception as e:
        return {"checkpoints": [], "error": str(e)[:200]}


@app.get("/api/models")
def models():
    """Return approved models, capabilities and local installation status."""
    return model_rows()


@app.get("/api/engines")
def engines():
    """Return the render adapters understood by this control plane."""
    return engine_rows()


@app.get("/api/readiness")
async def readiness(profile: str = "local"):
    """Return explicit local/cloud deployment blockers without starting work."""
    snapshot = await monitor()
    return evaluate_readiness(snapshot, profile=profile)


@app.get("/api/monitor")
async def monitor():
    """Return a read-only startup/readiness snapshot for the local/cloud worker."""
    checks = {"api": _monitor_status(True, "FastAPI control plane is responding", version=app.version)}
    settings = get_settings()
    checks["security"] = _monitor_status(
        bool(settings.auth_token),
        "Bearer token configured" if settings.auth_token else "Authentication disabled; keep the server on loopback or use an SSH tunnel",
        auth_configured=bool(settings.auth_token),
        strict_media_validation=settings.strict_media_validation,
    )
    try:
        db.row("SELECT 1 AS ok")
        usage = shutil.disk_usage(db.DATA)
        used_pct = round((usage.used / usage.total) * 100, 1) if usage.total else 0
        checks["database"] = _monitor_status(True, "SQLite is responding", path=str(db.DB), size_mb=round(db.DB.stat().st_size / (1024 * 1024), 2) if db.DB.exists() else 0)
        checks["storage"] = _monitor_status(usage.free > 10 * 1024 ** 3, f"{usage.free / (1024 ** 3):.1f} GiB free", free_gb=round(usage.free / (1024 ** 3), 2), total_gb=round(usage.total / (1024 ** 3), 2), used_pct=used_pct)
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)[:240]}
        checks["storage"] = {"status": "error", "detail": "Storage check failed"}

    comfy = {"status": "warning", "detail": "Optional ComfyUI bridge is offline", "url": os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")}
    try:
        async with ComfyClient() as client:
            stats = await asyncio.wait_for(client.health(), timeout=6)
            checkpoint_data = await asyncio.wait_for(client.checkpoints(), timeout=6)
        devices = stats.get("devices", []) if isinstance(stats, dict) else []
        checkpoint_count = len(checkpoint_data) if isinstance(checkpoint_data, list) else 0
        comfy = {"status": "ready", "detail": "ComfyUI bridge responding", "url": os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"), "devices": devices, "checkpoint_count": checkpoint_count}
    except Exception as exc:
        comfy["detail"] = str(exc)[:240]
    checks["connections"] = [{"id": "comfyui", "label": "ComfyUI API", **comfy}]

    workflows = workflow_list()
    ready_workflows = [item for item in workflows if item.get("ready")]
    catalog_workflows = [item for item in workflows if not item.get("ready")]
    checks["workflows"] = {"status": "ready" if ready_workflows else "warning", "detail": f"{len(ready_workflows)} verified graph(s), {len(catalog_workflows)} catalog recipe(s)", "ready_count": len(ready_workflows), "catalog_count": len(catalog_workflows), "items": workflows}
    checks["runtime"] = _runtime_monitor_rows()
    checks["models"] = _model_monitor_rows()
    active_jobs = db.row("SELECT COUNT(*) AS n FROM jobs WHERE status IN ('queued','running','submitted','cancelling')")
    failed_jobs = db.row("SELECT COUNT(*) AS n FROM jobs WHERE status='failed'")
    cancelled_jobs = db.row("SELECT COUNT(*) AS n FROM jobs WHERE status='cancelled'")
    retry_jobs = db.row("SELECT COUNT(*) AS n FROM jobs WHERE attempt > 1")
    checks["queue"] = {"status": "warning" if failed_jobs["n"] else "ready", "detail": f"{active_jobs['n']} active job(s), {failed_jobs['n']} failed job(s)", "active": active_jobs["n"], "failed": failed_jobs["n"], "cancelled": cancelled_jobs["n"], "retried": retry_jobs["n"]}
    all_statuses = [checks["api"]["status"], checks["database"]["status"], checks["storage"]["status"], checks["security"]["status"], comfy["status"], checks["workflows"]["status"], checks["queue"]["status"]] + [item["status"] for item in checks["runtime"]] + [item["status"] for item in checks["models"]]
    overall = "error" if "error" in all_statuses else "degraded" if "warning" in all_statuses else "ready"
    return {"checked_at": now(), "overall": {"status": overall, "detail": "Core app is healthy; review warnings before a GPU render" if overall == "degraded" else "All checked integrations are ready" if overall == "ready" else "A core monitoring check failed"}, **checks}


@app.post("/api/personas", status_code=201)
def create_persona(payload: PersonaIn):
    return store_persona(payload)


@app.get("/api/personas")
def list_personas():
    return [persona_response(row) for row in db.all_rows("SELECT * FROM personas ORDER BY created_at DESC")]


@app.post("/api/personas/{pid}/freeze")
def freeze_persona(pid: str):
    person = db.row("SELECT * FROM personas WHERE id=?", (pid,))
    if not person:
        raise HTTPException(404, "Persona not found")
    frozen_version = PersonaRepository.freeze(pid, now())
    if not frozen_version:
        raise HTTPException(409, "Persona has no persisted identity version")
    result = persona_response(db.row("SELECT * FROM personas WHERE id=?", (pid,)))
    result["frozen_version"] = persona_version_response(frozen_version)
    return result


@app.get("/api/personas/{pid}/versions")
def list_persona_versions(pid: str):
    must_persona(pid)
    return [persona_version_response(version) for version in PersonaRepository.versions(pid)]


@app.get("/api/personas/{pid}/versions/{version_id}")
def get_persona_version(pid: str, version_id: str):
    must_persona(pid)
    version = PersonaRepository.version(pid, version_id)
    if not version:
        raise HTTPException(404, "Persona version not found")
    return persona_version_response(version)


@app.get("/api/personas/{pid}/references")
def list_references(pid: str):
    must_persona(pid)
    return db.all_rows(
        "SELECT id, persona_id, asset_id, filename, label, created_at, persona_version_id, role, content_class, review, rights_confirmed, metadata_json FROM reference_images WHERE persona_id=? ORDER BY created_at DESC",
        (pid,),
    )


@app.get("/api/personas/{pid}/reference-packs")
def list_reference_packs(pid: str):
    must_persona(pid)
    return ReferencePackRepository.list(pid)


@app.get("/api/personas/{pid}/reference-packs/{pack_id}")
def get_reference_pack(pid: str, pack_id: str):
    must_persona(pid)
    pack = ReferencePackRepository.get(pid, pack_id)
    if not pack:
        raise HTTPException(404, "Reference pack not found")
    return pack


@app.patch("/api/personas/{pid}/reference-packs/{pack_id}/review")
def review_reference_pack(pid: str, pack_id: str, payload: ReferencePackReviewIn):
    must_persona(pid)
    try:
        return ReferencePackRepository.review_pack(
            persona_id=pid, pack_id=pack_id, review=payload.review,
            rights_confirmed=payload.rights_confirmed, reviewed_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.patch("/api/personas/{pid}/reference-packs/{pack_id}/canonical")
def select_reference_pack_canonical(pid: str, pack_id: str, payload: ReferencePackCanonicalIn):
    must_persona(pid)
    try:
        return ReferencePackRepository.select_canonical(
            persona_id=pid, pack_id=pack_id, selected=payload.selected, item_ids=payload.item_ids,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.patch("/api/personas/{pid}/reference-packs/{pack_id}/items/{item_id}/review")
def review_reference_pack_item(pid: str, pack_id: str, item_id: str, payload: ReferencePackReviewIn):
    must_persona(pid)
    try:
        return ReferencePackRepository.review_item(
            persona_id=pid, pack_id=pack_id, item_id=item_id, review=payload.review,
            rights_confirmed=payload.rights_confirmed, reviewed_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/personas/{pid}/reference-packs/{pack_id}/items/{item_id}/asset")
def link_reference_pack_asset(pid: str, pack_id: str, item_id: str, payload: ReferencePackAssetLinkIn):
    must_persona(pid)
    try:
        return ReferencePackRepository.link_asset(
            persona_id=pid, pack_id=pack_id, item_id=item_id, asset_id=payload.asset_id,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/creator-profile")
def get_creator_profile(pid: str, persona_version_id: str | None = None):
    must_persona(pid)
    version = PersonaRepository.version(pid, persona_version_id) if persona_version_id else PersonaRepository.current_version(pid)
    if not version:
        raise HTTPException(409, "Persona has no persisted identity version")
    return {
        "persona_id": pid,
        "persona_version_id": version["id"],
        "version_state": version["state"],
        "profile": CreatorProfileRepository.get(pid, version["id"]),
    }


@app.put("/api/personas/{pid}/creator-profile")
def upsert_creator_profile(pid: str, payload: CreatorProfileIn):
    must_persona(pid)
    try:
        profile = CreatorProfileRepository.upsert(
            persona_id=pid,
            persona_version_id=payload.persona_version_id,
            personality=payload.personality,
            audience=payload.audience,
            content_pillars=[pillar.model_dump() if hasattr(pillar, "model_dump") else pillar.dict() for pillar in payload.content_pillars],
            brand=payload.brand,
            voice=payload.voice,
            disclosure=payload.disclosure,
            metadata=payload.metadata,
            updated_at=now(),
        )
        version = PersonaRepository.version(pid, profile["persona_version_id"])
        return {
            "persona_id": pid,
            "persona_version_id": profile["persona_version_id"],
            "version_state": version["state"] if version else "draft",
            "profile": profile,
        }
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-packs")
def list_content_packs(pid: str):
    must_persona(pid)
    return ContentPackRepository.list(pid)


@app.post("/api/personas/{pid}/content-packs", status_code=201)
def create_content_pack(pid: str, payload: ContentPackIn):
    must_persona(pid)
    version = PersonaRepository.version(pid, payload.persona_version_id) if payload.persona_version_id else PersonaRepository.current_version(pid)
    if not version:
        raise HTTPException(409, "Persona has no persisted identity version")
    try:
        return ContentPackRepository.create(
            persona_id=pid,
            persona_version_id=version["id"],
            reference_pack_id=payload.reference_pack_id,
            pack_type=payload.pack_type.strip(),
            name=payload.name.strip(),
            content_class=payload.content_class.strip(),
            identity_authority=payload.identity_authority.strip(),
            identity_core=payload.identity_core,
            style=payload.style,
            metadata=payload.metadata,
            item_ids=payload.reference_item_ids,
            created_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-packs/{pack_id}")
def get_content_pack(pid: str, pack_id: str):
    must_persona(pid)
    pack = ContentPackRepository.get(pid, pack_id)
    if not pack:
        raise HTTPException(404, "ContentPack not found")
    return pack


@app.patch("/api/personas/{pid}/content-packs/{pack_id}/review")
def review_content_pack(pid: str, pack_id: str, payload: ContentPackReviewIn):
    must_persona(pid)
    try:
        return ContentPackRepository.review(persona_id=pid, pack_id=pack_id, review=payload.review, reviewed_at=now())
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-packs/{pack_id}/resolve")
def resolve_content_pack(pid: str, pack_id: str):
    must_persona(pid)
    try:
        return ContentPackRepository.resolve(pid, pack_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-briefs")
def list_content_briefs(pid: str):
    must_persona(pid)
    return ContentBriefRepository.list(pid)


@app.post("/api/personas/{pid}/content-briefs", status_code=201)
def create_content_brief(pid: str, payload: ContentBriefIn):
    must_persona(pid)
    version = PersonaRepository.version(pid, payload.persona_version_id) if payload.persona_version_id else PersonaRepository.current_version(pid)
    if not version:
        raise HTTPException(409, "Persona has no persisted identity version")
    try:
        return ContentBriefRepository.create(
            persona_id=pid,
            persona_version_id=version["id"],
            creator_profile_id=payload.creator_profile_id,
            content_pack_id=payload.content_pack_id,
            title=payload.title,
            format=payload.format,
            content_class=payload.content_class,
            pillar_key=payload.pillar_key,
            audience_goal=payload.audience_goal,
            emotional_objective=payload.emotional_objective,
            story_direction=payload.story_direction,
            visual_direction=payload.visual_direction,
            motion_direction=payload.motion_direction,
            caption_direction=payload.caption_direction,
            script_direction=payload.script_direction,
            disclosure=payload.disclosure,
            metadata=payload.metadata,
            created_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-briefs/{brief_id}")
def get_content_brief(pid: str, brief_id: str):
    must_persona(pid)
    brief = ContentBriefRepository.get(pid, brief_id)
    if not brief:
        raise HTTPException(404, "ContentBrief not found")
    return brief


@app.put("/api/personas/{pid}/content-briefs/{brief_id}")
def update_content_brief(pid: str, brief_id: str, payload: ContentBriefIn):
    must_persona(pid)
    existing = ContentBriefRepository.get(pid, brief_id)
    if not existing:
        raise HTTPException(404, "ContentBrief not found")
    if payload.persona_version_id and payload.persona_version_id != existing["persona_version_id"]:
        raise HTTPException(409, "ContentBrief PersonaVersion cannot be changed")
    try:
        return ContentBriefRepository.update(
            persona_id=pid,
            brief_id=brief_id,
            creator_profile_id=payload.creator_profile_id,
            content_pack_id=payload.content_pack_id,
            title=payload.title,
            format=payload.format,
            content_class=payload.content_class,
            pillar_key=payload.pillar_key,
            audience_goal=payload.audience_goal,
            emotional_objective=payload.emotional_objective,
            story_direction=payload.story_direction,
            visual_direction=payload.visual_direction,
            motion_direction=payload.motion_direction,
            caption_direction=payload.caption_direction,
            script_direction=payload.script_direction,
            disclosure=payload.disclosure,
            metadata=payload.metadata,
            updated_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.patch("/api/personas/{pid}/content-briefs/{brief_id}/approve")
def approve_content_brief(pid: str, brief_id: str):
    must_persona(pid)
    try:
        return ContentBriefRepository.approve(persona_id=pid, brief_id=brief_id, reviewed_at=now())
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-briefs/{brief_id}/resolve")
def resolve_content_brief(pid: str, brief_id: str):
    must_persona(pid)
    try:
        return ContentBriefRepository.resolve(pid, brief_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-artifacts")
def list_content_artifacts(pid: str):
    must_persona(pid)
    return ContentArtifactRepository.list(pid)


@app.get("/api/personas/{pid}/content-briefs/{brief_id}/artifacts")
def list_brief_artifacts(pid: str, brief_id: str):
    must_persona(pid)
    if not ContentBriefRepository.get(pid, brief_id):
        raise HTTPException(404, "ContentBrief not found")
    return ContentArtifactRepository.list_for_brief(pid, brief_id)


@app.post("/api/personas/{pid}/content-briefs/{brief_id}/artifacts", status_code=201)
def create_content_artifact(pid: str, brief_id: str, payload: ContentArtifactIn):
    must_persona(pid)
    try:
        return ContentArtifactRepository.create(
            persona_id=pid,
            brief_id=brief_id,
            artifact_type=payload.artifact_type,
            content=payload.content,
            metadata=payload.metadata,
            created_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-artifacts/{artifact_id}")
def get_content_artifact(pid: str, artifact_id: str):
    must_persona(pid)
    artifact = ContentArtifactRepository.get(pid, artifact_id)
    if not artifact:
        raise HTTPException(404, "Content artifact not found")
    return artifact


@app.post("/api/personas/{pid}/content-artifacts/{artifact_id}/quality")
def assess_content_artifact(pid: str, artifact_id: str):
    must_persona(pid)
    try:
        return ContentArtifactRepository.assess(persona_id=pid, artifact_id=artifact_id, evaluated_at=now())
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.put("/api/personas/{pid}/content-artifacts/{artifact_id}")
def update_content_artifact(pid: str, artifact_id: str, payload: ContentArtifactIn):
    must_persona(pid)
    existing = ContentArtifactRepository.get(pid, artifact_id)
    if not existing:
        raise HTTPException(404, "Content artifact not found")
    try:
        if payload.artifact_type.strip().lower() != existing["artifact_type"]:
            raise ValueError("Content artifact type cannot be changed")
        return ContentArtifactRepository.update(
            persona_id=pid,
            artifact_id=artifact_id,
            content=payload.content,
            metadata=payload.metadata,
            updated_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.patch("/api/personas/{pid}/content-artifacts/{artifact_id}/review")
def review_content_artifact(pid: str, artifact_id: str, payload: ContentArtifactReviewIn):
    must_persona(pid)
    try:
        return ContentArtifactRepository.review(
            persona_id=pid, artifact_id=artifact_id, review=payload.review, reviewed_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/content-artifacts/{artifact_id}/resolve")
def resolve_content_artifact(pid: str, artifact_id: str):
    must_persona(pid)
    try:
        return ContentArtifactRepository.resolve(pid, artifact_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/identity-conditioning/catalog")
def identity_conditioning_catalog():
    return {
        "execution_status": "deferred_final_gate",
        "methods": method_catalog(),
        "scenarios": scenario_catalog(),
    }


@app.get("/api/personas/{pid}/identity-benchmarks")
def list_identity_benchmarks(pid: str):
    must_persona(pid)
    return IdentityBenchmarkRepository.list(pid)


@app.post("/api/personas/{pid}/identity-benchmarks", status_code=201)
def create_identity_benchmark(pid: str, payload: IdentityBenchmarkIn):
    must_persona(pid)
    version = PersonaRepository.version(pid, payload.persona_version_id) if payload.persona_version_id else PersonaRepository.current_version(pid)
    if not version:
        raise HTTPException(409, "Persona has no persisted identity version")
    if version["state"] != "frozen":
        raise HTTPException(409, "Freeze the PersonaVersion before creating an identity benchmark")
    anchor = ReferencePackRepository.resolve_canonical_asset(pid, version["id"])
    if not anchor:
        raise HTTPException(409, "Identity benchmark requires an approved canonical anchor for the selected PersonaVersion")
    try:
        return IdentityBenchmarkRepository.create(
            persona_id=pid,
            persona_version_id=version["id"],
            anchor=anchor,
            base_model_id=payload.base_model_id,
            methods=payload.methods,
            scenario_ids=payload.scenario_ids,
            metadata=payload.metadata,
            created_at=now(),
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/personas/{pid}/identity-benchmarks/{benchmark_id}")
def get_identity_benchmark(pid: str, benchmark_id: str):
    must_persona(pid)
    benchmark = IdentityBenchmarkRepository.get(pid, benchmark_id)
    if not benchmark:
        raise HTTPException(404, "Identity benchmark not found")
    return benchmark


@app.post("/api/personas/{pid}/identity-benchmarks/{benchmark_id}/cases/{case_id}/result")
def record_identity_benchmark_result(pid: str, benchmark_id: str, case_id: str, payload: IdentityBenchmarkResultIn):
    must_persona(pid)
    try:
        return IdentityBenchmarkRepository.record_case_result(
            persona_id=pid,
            benchmark_id=benchmark_id,
            case_id=case_id,
            status=payload.status,
            metrics=payload.metrics,
            notes=payload.notes,
            error=payload.error,
            output_asset_id=payload.output_asset_id,
            updated_at=now(),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


def series_response(row):
    result = dict(row)
    result["episodes"] = db.all_rows("SELECT * FROM series_episodes WHERE series_id=? ORDER BY episode_no", (result["id"],))
    return result


@app.get("/api/series")
def list_series():
    return [series_response(row) for row in db.all_rows("SELECT series.*, personas.name AS persona_name, personas.identity_locked, personas.identity_version FROM series JOIN personas ON personas.id=series.persona_id ORDER BY series.created_at DESC")]


@app.post("/api/series", status_code=201)
def create_series(payload: SeriesIn):
    person = must_persona(payload.persona_id)
    if not person.get("identity_locked"):
        raise HTTPException(409, "Freeze the persona identity before creating a repeatable series")
    persona_version = PersonaRepository.current_version(person["id"])
    if not persona_version or persona_version.get("state") != "frozen":
        raise HTTPException(409, "A frozen PersonaVersion is required before creating a repeatable series")
    sid = uid()
    episodes = []
    for index, episode in enumerate(payload.episodes, start=1):
        prompt = f"{payload.shared_prompt.strip()}\nEpisode direction: {episode.prompt.strip()}"
        video_prompt = f"{payload.shared_prompt.strip()}\nEpisode motion: {episode.video_prompt.strip()}"
        episodes.append((uid(), index, episode.title.strip(), prompt, video_prompt, now()))
    SeriesRepository.create(series_id=sid, persona_id=person["id"], persona_version_id=persona_version["id"], title=payload.title.strip(),
                            description=payload.description.strip(), shared_prompt=payload.shared_prompt.strip(),
                            created_at=now(), episodes=episodes)
    return series_response(db.row("SELECT series.*, personas.name AS persona_name, personas.identity_locked, personas.identity_version FROM series JOIN personas ON personas.id=series.persona_id WHERE series.id=?", (sid,)))


@app.post("/api/series/{sid}/episodes/{eid}/queue", status_code=202)
async def queue_series_episode(sid: str, eid: str, payload: SeriesQueueIn):
    row = db.row("SELECT series.*, series_episodes.title AS episode_title, series_episodes.prompt, series_episodes.video_prompt, personas.identity_locked FROM series JOIN series_episodes ON series_episodes.series_id=series.id JOIN personas ON personas.id=series.persona_id WHERE series.id=? AND series_episodes.id=?", (sid, eid))
    if not row:
        raise HTTPException(404, "Series episode not found")
    if not row["identity_locked"]:
        raise HTTPException(409, "Freeze the persona identity before queueing a series episode")
    if not payload.reference_id and not payload.source_asset_id:
        canonical = ReferencePackRepository.resolve_canonical_asset(row["persona_id"], row.get("persona_version_id"))
        if canonical:
            payload.source_asset_id = canonical["id"]
    if not payload.reference_id and not payload.source_asset_id:
        latest = db.row("SELECT id, 'reference' AS source, created_at FROM reference_images WHERE persona_id=? UNION ALL SELECT id, 'asset' AS source, created_at FROM assets WHERE persona_id=? AND kind='image' AND review='approved' ORDER BY created_at DESC LIMIT 1", (row["persona_id"], row["persona_id"]))
        if latest:
            if latest["source"] == "reference":
                payload.reference_id = latest["id"]
            else:
                payload.source_asset_id = latest["id"]
    job = JobIn(persona_id=row["persona_id"], workflow_id=payload.workflow_id, checkpoint=payload.checkpoint,
                reference_id=payload.reference_id, source_asset_id=payload.source_asset_id, audio_asset_id=payload.audio_asset_id,
                content_pack_id=payload.content_pack_id,
                prompt=row["prompt"], video_prompt=row["video_prompt"], width=payload.width,
                height=payload.height, seed=payload.seed if payload.seed is not None else secrets.randbelow(2147483647),
                rights_confirmed=payload.rights_confirmed)
    result = await create_job(job)
    db.write("UPDATE series_episodes SET job_id=?, status='queued' WHERE id=? AND series_id=?", (result["id"], eid, sid))
    db.write("UPDATE series SET status='active' WHERE id=?", (sid,))
    return {"series_id": sid, "episode_id": eid, "job_id": result["id"], "status": "queued"}


@app.post("/api/personas/{pid}/references", status_code=201)
async def add_reference(pid: str, file: UploadFile = File(...), label: str = Form("Master reference"), rights_confirmed: bool = Form(False)):
    person = db.row("SELECT id, identity_locked FROM personas WHERE id=?", (pid,))
    if not person:
        raise HTTPException(404, "Persona not found")
    if person["identity_locked"]:
        raise HTTPException(409, "Persona identity is frozen; create a new persona/version before changing its reference vault")
    if not rights_confirmed:
        raise HTTPException(400, "Confirm you have rights to this image and likeness")
    try:
        raw = await read_limited(file, get_settings().reference_max_bytes)
        extension = validate_image_bytes(raw)
    except Exception as e:
        raise HTTPException(400, f"Invalid PNG, JPEG, or WEBP image: {e}") from e
    version = PersonaRepository.current_version(pid)
    normalized_label = label.strip()[:100]
    label_lower = normalized_label.lower()
    role = "identity_anchor" if any(term in label_lower for term in ("master", "anchor", "identity")) else "supporting"
    content_class = "adult_glamour" if any(term in label_lower for term in ("adult", "boudoir", "lingerie", "glamour", "intimate")) else "identity"
    asset = register_media_asset(
        persona_id=pid,
        persona_version_id=version["id"] if version else None,
        job_id=None,
        kind="image",
        prompt=normalized_label,
        raw=raw,
        disclosure=AI_DISCLOSURE,
        rights_confirmed=True,
        original_filename=file.filename,
        lineage={"source": "operator_upload"},
        content_class=content_class,
        destination_policy="review_required",
    )
    aid = asset["id"]
    filename = asset["filename"]
    rid = uid()
    created = now()
    db.write(
        "INSERT INTO reference_images (id, persona_id, filename, label, created_at, asset_id, persona_version_id, role, content_class, review, rights_confirmed, metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, pid, filename, normalized_label, created, aid, version["id"] if version else None, role, content_class, "pending", 1, json.dumps({"source": "operator_upload"})),
    )
    return {"id": rid, "asset_id": aid, "label": normalized_label, "role": role, "content_class": content_class, "review": "pending", "persona_version_id": version["id"] if version else None, "url": f"/api/references/{rid}/file", "asset_url": f"/api/assets/{aid}/file"}


@app.get("/api/references/{rid}/file")
def reference_file(rid: str):
    row = db.row("SELECT filename, asset_id FROM reference_images WHERE id=?", (rid,))
    if not row:
        raise HTTPException(404)
    if row.get("asset_id"):
        asset = db.row("SELECT * FROM assets WHERE id=?", (row["asset_id"],))
        if asset:
            try:
                return FileResponse(resolve_asset_file(asset))
            except FileNotFoundError:
                raise HTTPException(404, "Reference media file is missing") from None
    path = reference_path(row["filename"])
    if not path.is_file():
        raise HTTPException(404, "Reference media file is missing")
    return FileResponse(path)


@app.get("/api/workflows")
def get_workflows():
    return workflow_list()


@app.post("/api/workflows", status_code=201)
async def import_workflow(file: UploadFile = File(...), label: str = Form("Custom")):
    try:
        raw = await read_limited(file, get_settings().workflow_max_bytes)
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    try:
        graph = json.loads(raw)
        validate_graph(graph)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(400, str(e)) from e
    slug = re.sub(r"[^a-z0-9_-]", "_", label.lower().strip())[:32].strip("_") or "workflow"
    wid = f"{slug}_{uid()[:8]}"
    (db.WORKFLOWS / f"{wid}.json").write_text(json.dumps(graph, indent=2), encoding="utf8")
    return {"id": wid, "nodes": len(graph)}


def must_persona(pid):
    person = db.row("SELECT * FROM personas WHERE id=?", (pid,))
    if not person:
        raise HTTPException(404, "Persona not found")
    return person


def persona_characteristics_text(person):
    """Flatten the structured identity capsule into a stable prompt suffix."""
    raw = person.get("characteristics_json", "{}")
    try:
        profile = json.loads(raw or "{}")
    except json.JSONDecodeError:
        profile = {}
    def flatten(value, limit=1200):
        if isinstance(value, dict):
            text = "; ".join(f"{key.replace('_', ' ')}: {flatten(item, 300)}" for key, item in value.items() if item not in (None, "", [], {}))
        elif isinstance(value, list):
            text = ", ".join(flatten(item, 180) for item in value if item not in (None, "", [], {}))
        else:
            text = str(value)
        return text[:limit]

    parts = [section.replace('_', ' ').title() + " — " + flatten(values) for section, values in profile.items() if values not in (None, "", [], {})]
    text = "Structured identity capsule: " + " | ".join(parts) if parts else ""
    return text[:6000]


async def _finalize_comfy_outputs(job_id: str, payload: JobIn, person: dict, persona_version: dict | None, outputs: dict, client: ComfyClient):
    """Download and register ComfyUI outputs exactly once for a canonical Job."""

    files = output_files(outputs)
    if not files:
        raise RuntimeError("Workflow completed but no SaveImage / SaveVideo or compatible output was detected")
    asset_ids = []
    children = [
        {"id": f"output-{index + 1}", "label": item.get("filename", f"output-{index + 1}"), "state": "queued", "percent": 0}
        for index, item in enumerate(files[:20])
    ]
    _update_job_progress(job_id, "downloading_outputs", 45, f"Preparing {len(children)} output(s)", children)
    for index, item in enumerate(files[:20]):
        children[index]["state"] = "running"
        _update_job_progress(job_id, "downloading_outputs", 45 + int((index / max(1, len(children))) * 30), f"Downloading output {index + 1} of {len(children)}", children)
        content = await client.download(item)
        children[index]["percent"] = 70
        if len(content) > get_settings().output_max_bytes:
            raise ValueError("Generated output exceeds 200MB safety limit")
        ext = Path(item["filename"]).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".gif", ".wav", ".mp3", ".flac"}:
            children[index]["state"] = "skipped"
            children[index]["percent"] = 100
            continue
        kind = "video" if ext in {".mp4", ".webm", ".gif"} else "audio" if ext in {".wav", ".mp3", ".flac"} else "image"
        digest = sha256_bytes(content)
        existing = db.row("SELECT id FROM assets WHERE job_id=? AND sha256=? ORDER BY created_at LIMIT 1", (job_id, digest))
        if existing:
            asset_ids.append(existing["id"])
            children[index]["state"] = "completed"
            children[index]["percent"] = 100
            continue
        _update_job_progress(job_id, "registering_assets", 80 + int((index / max(1, len(children))) * 15), f"Registering output {index + 1} of {len(children)}", children)
        disclosure = person.get("disclosure") or AI_DISCLOSURE
        content_pack = db.row(
            "SELECT content_class FROM content_packs WHERE id=? AND persona_id=?",
            (payload.content_pack_id, person["id"]),
        ) if payload.content_pack_id else None
        asset = register_media_asset(
            persona_id=person["id"],
            persona_version_id=persona_version["id"] if persona_version else None,
            job_id=job_id,
            kind=kind,
            prompt=payload.prompt,
            raw=content,
            disclosure=disclosure,
            rights_confirmed=payload.rights_confirmed,
            original_filename=item["filename"],
            lineage={"job_id": job_id, "workflow_id": payload.workflow_id, "comfy_prompt_id": db.row("SELECT comfy_prompt_id FROM jobs WHERE id=?", (job_id,)).get("comfy_prompt_id")},
            content_class=(content_pack or {}).get("content_class") or "identity",
            destination_policy="review_required",
        )
        asset_ids.append(asset["id"])
        children[index]["state"] = "completed"
        children[index]["percent"] = 100
    if not asset_ids:
        raise RuntimeError("Workflow completed but no supported media outputs were available")
    _update_job_progress(job_id, "finalizing", 95, f"Finalizing {len(asset_ids)} asset(s)", children)
    return {"job_id": job_id, "asset_ids": asset_ids, "output_count": len(asset_ids), "reconciled": False, "children": children}


def _mark_job_completed(job_id: str, result: dict):
    timestamp = now()
    db.write(
        "UPDATE jobs SET status='completed', result_json=?, finished_at=?, updated_at=?, "
        "worker_id=NULL, heartbeat_at=NULL, lease_expires_at=NULL, next_retry_at=NULL, "
        "progress_stage='completed', progress_percent=100, progress_detail='Completed successfully', progress_json=? WHERE id=?",
        (json.dumps(result, ensure_ascii=False), timestamp, timestamp, json.dumps({"children": result.get("children", [])}, ensure_ascii=False), job_id),
    )
    db.write("UPDATE series_episodes SET status='completed' WHERE job_id=?", (job_id,))


def _mark_job_failed(job_id: str, error: str):
    timestamp = now()
    db.write(
        "UPDATE jobs SET status='failed', error=?, finished_at=?, updated_at=?, "
        "worker_id=NULL, heartbeat_at=NULL, lease_expires_at=NULL, next_retry_at=NULL, "
        "progress_stage='failed', progress_percent=100, progress_detail=? WHERE id=?",
        (error[:1500], timestamp, timestamp, error[:500], job_id),
    )
    db.write("UPDATE series_episodes SET status='failed' WHERE job_id=?", (job_id,))


async def _reconcile_interrupted_prompts():
    """Attach completed ComfyUI history to interrupted canonical Jobs once."""

    rows = db.all_rows(
        "SELECT * FROM jobs WHERE status='interrupted' AND cancel_requested=0 "
        "AND comfy_prompt_id IS NOT NULL ORDER BY updated_at, created_at"
    )
    if not rows:
        return
    try:
        async with ComfyClient() as client:
            for row in rows:
                job_id = row["id"]
                try:
                    entry = await client.history(row["comfy_prompt_id"])
                    if not entry:
                        continue
                    status = entry.get("status", {}) if isinstance(entry, dict) else {}
                    if status.get("status_str") == "error":
                        _mark_job_failed(job_id, f"ComfyUI execution failed during recovery: {str(status.get('messages', []))[-1000:]}")
                        continue
                    if not (status.get("completed") is True or entry.get("outputs")):
                        continue
                    raw = json.loads(row.get("request_json") or "{}")
                    payload = JobIn(**raw)
                    person = db.row("SELECT * FROM personas WHERE id=?", (payload.persona_id,))
                    if not person:
                        raise ValueError("Persona for recovered job is no longer available")
                    persona_version = PersonaRepository.current_version(person["id"])
                    _claim_job(job_id)
                    _update_job_progress(job_id, "reconciling_prompt", 30, "Recovered completed ComfyUI prompt")
                    result = await _finalize_comfy_outputs(job_id, payload, person, persona_version, entry.get("outputs", {}), client)
                    result["reconciled"] = True
                    _mark_job_completed(job_id, result)
                    logger.info("job_reconciled", extra=_log_data({"job_id": job_id, "prompt_id": row["comfy_prompt_id"], "outputs": result["output_count"]}))
                except (json.JSONDecodeError, TypeError, ValueError, RuntimeError, OSError) as exc:
                    _mark_job_failed(job_id, f"Prompt reconciliation failed: {str(exc)[:1400]}")
                    logger.exception("job_reconciliation_failed", extra=_log_data({"job_id": job_id}))
    except Exception as exc:
        # ComfyUI may not be running while the Studio starts. Leave rows
        # interrupted so the operator can retry after the local backend is up.
        logger.warning("job_reconciliation_unavailable", extra=_log_data({"error": str(exc)[:300]}), exc_info=True)


async def execute_job(job_id, payload: JobIn, person: dict):
    try:
        if _job_cancel_requested(job_id):
            return
        persona_version = PersonaRepository.current_version(person["id"])
        _claim_job(job_id)
        claimed = db.row("SELECT status FROM jobs WHERE id=?", (job_id,))
        if not claimed or claimed["status"] == "cancelled":
            return
        logger.info("job_started", extra=_log_data({"job_id": job_id, "persona_id": person.get("id"), "workflow_id": payload.workflow_id}))
        _update_job_progress(job_id, "preparing_inputs", 10, "Loading workflow and identity inputs")
        graph = json.loads(workflow_path(payload.workflow_id).read_text(encoding="utf8"))
        creative_prompt = payload.video_prompt if (payload.video_prompt and ("video" in payload.workflow_id.lower() or "wan" in payload.workflow_id.lower())) else payload.prompt
        profile_text = persona_characteristics_text(person)
        values = {"PROMPT": f"Fictional adult character {person['name']} ({person['age']} years old), {person['appearance']}. {person['description']}. {profile_text} {creative_prompt}",
                  "NEGATIVE_PROMPT": payload.negative_prompt, "CHECKPOINT": payload.checkpoint,
                  "WIDTH": payload.width, "HEIGHT": payload.height, "SEED": payload.seed,
                  "REFERENCE_IMAGE": "", "AUDIO_FILENAME": ""}
        async with ComfyClient() as client:
            prompt_id = None
            if payload.reference_id or payload.source_asset_id:
                if payload.reference_id:
                    ref = db.row("SELECT * FROM reference_images WHERE id=? AND persona_id=?", (payload.reference_id, payload.persona_id))
                    if not ref:
                        raise ValueError("Reference does not belong to this persona")
                    if ref.get("asset_id"):
                        ref_asset = db.row("SELECT * FROM assets WHERE id=?", (ref["asset_id"],))
                        if not ref_asset:
                            raise ValueError("Reference asset is missing")
                        content = resolve_asset_file(ref_asset).read_bytes()
                    else:
                        content = reference_path(ref["filename"]).read_bytes()
                    filename = ref["filename"]
                else:
                    source = db.row("SELECT * FROM assets WHERE id=? AND persona_id=?", (payload.source_asset_id, payload.persona_id))
                    if not source or source["kind"] != "image":
                        raise ValueError("Source asset not found or is not an image")
                    content = resolve_asset_file(source).read_bytes()
                    filename = source["filename"]
                values["REFERENCE_IMAGE"] = await client.upload_reference(content, filename)
            if payload.audio_asset_id:
                audio = db.row("SELECT * FROM assets WHERE id=? AND persona_id=? AND kind='audio'", (payload.audio_asset_id, payload.persona_id))
                if not audio:
                    raise ValueError("Selected audio asset does not belong to this persona")
                values["AUDIO_FILENAME"] = await client.upload_audio(resolve_asset_file(audio).read_bytes(), audio["filename"])
            graph = render_graph(graph, values)
            _update_job_progress(job_id, "submitting_prompt", 25, "Submitting validated workflow to ComfyUI")
            if _job_cancel_requested(job_id):
                return
            prompt_id = await client.submit(graph)
            db.write("UPDATE jobs SET status='submitted', comfy_prompt_id=?, updated_at=? WHERE id=?", (prompt_id, now(), job_id))
            _heartbeat_job(job_id, status="submitted")
            _update_job_progress(job_id, "waiting_for_comfy", 35, f"Waiting for ComfyUI prompt {prompt_id}")
            try:
                outputs = await asyncio.wait_for(
                    client.wait(
                        prompt_id,
                        cancel_check=lambda: _job_cancel_requested(job_id),
                        heartbeat=lambda: _heartbeat_job(job_id),
                    ),
                    timeout=get_settings().job_timeout_seconds,
                )
            except asyncio.CancelledError:
                try:
                    await client.interrupt()
                except Exception:
                    logger.warning("comfy_interrupt_failed", extra=_log_data({"job_id": job_id, "prompt_id": prompt_id}), exc_info=True)
                raise
            if _job_cancel_requested(job_id):
                return
            _update_job_progress(job_id, "processing_outputs", 42, "ComfyUI completed; validating outputs")
            result = await _finalize_comfy_outputs(job_id, payload, person, persona_version, outputs, client)
            if _job_cancel_requested(job_id):
                return
            _mark_job_completed(job_id, result)
            logger.info("job_completed", extra=_log_data({"job_id": job_id, "outputs": result["output_count"]}))
    except asyncio.CancelledError:
        if not _job_cancel_requested(job_id):
            _mark_job_interrupted(job_id)
        logger.info("job_interrupted", extra=_log_data({"job_id": job_id}))
        return
    except Exception as e:
        logger.exception("job_failed", extra=_log_data({"job_id": job_id}))
        _mark_job_failed(job_id, str(e))


@app.post("/api/jobs", status_code=202)
async def create_job(payload: JobIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    person = must_persona(payload.persona_id)
    if not payload.rights_confirmed:
        raise HTTPException(400, "Confirm all inputs and likeness rights before starting generation")
    persona_version = PersonaRepository.current_version(person["id"])
    if not persona_version:
        raise HTTPException(409, "Persona has no persisted identity version")
    if payload.content_pack_id:
        try:
            resolved_pack = ContentPackRepository.resolve(person["id"], payload.content_pack_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        style_text = json.dumps(resolved_pack["style"], ensure_ascii=False, sort_keys=True)
        payload.prompt = f"{payload.prompt}\nContentPack style directives: {style_text}"[:3000]
        if not payload.reference_id and not payload.source_asset_id:
            payload.source_asset_id = resolved_pack["anchors"][0]["asset_id"]
    if not payload.reference_id and not payload.source_asset_id:
        canonical = ReferencePackRepository.resolve_canonical_asset(person["id"], persona_version["id"])
        if canonical:
            payload.source_asset_id = canonical["id"]
    path = workflow_path(payload.workflow_id)
    text = path.read_text(encoding="utf8")
    if "{{CHECKPOINT}}" in text and not payload.checkpoint:
        raise HTTPException(400, "Select a checkpoint for this workflow")
    if "{{REFERENCE_IMAGE}}" in text and not (payload.reference_id or payload.source_asset_id):
        raise HTTPException(400, "Workflow requires a reference image")
    if "{{AUDIO_FILENAME}}" in text and not payload.audio_asset_id:
        raise HTTPException(400, "Workflow requires a generated audio asset")
    if payload.width % 8 or payload.height % 8:
        raise HTTPException(400, "Width and height must be multiples of 8")
    resource_checks = resource_preflight(workflow_id=payload.workflow_id, width=payload.width, height=payload.height)
    resource_errors = [item["detail"] for item in resource_checks if item.get("status") == "error"]
    if resource_errors:
        raise HTTPException(409, "Resource preflight failed: " + "; ".join(resource_errors)[:1200])
    if payload.reference_id and not db.row("SELECT id FROM reference_images WHERE id=? AND persona_id=?", (payload.reference_id, payload.persona_id)):
        raise HTTPException(400, "Invalid reference for selected persona")
    if payload.source_asset_id:
        source = db.row("SELECT id, kind, review, rights_confirmed FROM assets WHERE id=? AND persona_id=?", (payload.source_asset_id, payload.persona_id))
        if not source or source["kind"] != "image":
            raise HTTPException(400, "Source asset not found or is not an image")
        if source["review"] != "approved":
            raise HTTPException(400, "Approve the source master image in Media Review before animating it")
        if not source["rights_confirmed"]:
            raise HTTPException(400, "Source master image is missing rights confirmation")
    if payload.audio_asset_id:
        audio = db.row("SELECT id, kind, review, rights_confirmed FROM assets WHERE id=? AND persona_id=?", (payload.audio_asset_id, payload.persona_id))
        if not audio or audio["kind"] != "audio":
            raise HTTPException(400, "Audio asset not found for this persona")
        if audio["review"] != "approved":
            raise HTTPException(400, "Approve the narration in Media Review before attaching it")
        if not audio["rights_confirmed"]:
            raise HTTPException(400, "Narration asset is missing rights confirmation")
    normalized_key = _normalized_idempotency_key(idempotency_key)
    if normalized_key:
        existing = JobRepository.by_idempotency_key(normalized_key)
        if existing:
            result = _raise_idempotency_conflict(existing)
            return {"id": existing["id"], "status": existing["status"], "result": result}

    jid = uid()
    category = "video" if "video" in payload.workflow_id.lower() or "wan" in payload.workflow_id.lower() else "image"
    try:
        request_json = payload.model_dump_json()
    except AttributeError:  # Pydantic v1 compatibility for older local installs.
        request_json = payload.json()
    created = now()
    lineage = {
        "persona_id": person["id"],
        "persona_version": persona_version["version_no"],
        "persona_version_id": persona_version["id"],
        "persona_version_state": persona_version["state"],
        "workflow_id": payload.workflow_id,
        "checkpoint": payload.checkpoint,
        "reference_id": payload.reference_id,
        "source_asset_id": payload.source_asset_id,
        "audio_asset_id": payload.audio_asset_id,
        "content_pack_id": payload.content_pack_id,
        "seed": payload.seed,
        "width": payload.width,
        "height": payload.height,
    }
    try:
        JobRepository.create(job_id=jid, persona_id=person["id"], workflow_id=payload.workflow_id,
                             kind=category, prompt=payload.prompt, request_json=request_json,
                             lineage_json=json.dumps(lineage, separators=(",", ":")), created_at=created,
                             idempotency_key=normalized_key)
    except sqlite3.IntegrityError:
        if not normalized_key:
            raise
        existing = JobRepository.by_idempotency_key(normalized_key)
        if not existing:
            raise
        result = _raise_idempotency_conflict(existing)
        return {"id": existing["id"], "status": existing["status"], "result": result}
    _job_task(jid, payload, person)
    logger.info("job_queued", extra=_log_data({"job_id": jid, "persona_id": person["id"], "workflow_id": payload.workflow_id}))
    return {"id": jid, "status": "queued"}


@app.get("/api/preflight")
def preflight(workflow_id: str | None = None, model_id: str | None = None,
              task: str | None = None, width: int | None = None,
              height: int | None = None):
    """Run non-mutating checks before a render is queued."""

    checks = workflow_preflight(workflow_id, model_id=model_id, task=task, width=width, height=height)
    statuses = [item["status"] for item in checks]
    overall = "error" if "error" in statuses else "degraded" if "warning" in statuses else "ready"
    return {"checked_at": now(), "overall": overall, "checks": checks}


def _start_managed_job(job_id: str, payload: JobIn, person: dict):
    async def run():
        semaphore = getattr(app.state, "job_semaphore", None)
        if semaphore is None:
            await execute_job(job_id, payload, person)
            return
        async with semaphore:
            await execute_job(job_id, payload, person)

    task = asyncio.create_task(run(), name=f"studio-job-{job_id}")
    task_map = getattr(app.state, "job_task_map", None)
    tasks = getattr(app.state, "job_tasks", None)
    if tasks is not None:
        tasks.add(task)
    if task_map is not None:
        task_map[job_id] = task
    def finished(done):
        if tasks is not None:
            tasks.discard(done)
        if task_map is not None:
            task_map.pop(job_id, None)
        event = getattr(app.state, "job_dispatch_event", None)
        if event is not None:
            event.set()
    task.add_done_callback(finished)
    return task


async def _dispatch_queued_jobs():
    """Claim durable queued jobs and hand them to bounded in-process tasks."""

    task_map = getattr(app.state, "job_task_map", {})
    capacity = max(0, get_settings().job_concurrency - len(task_map))
    if capacity <= 0:
        return
    rows = db.all_rows(
        "SELECT * FROM jobs WHERE status='queued' AND "
        "(next_retry_at IS NULL OR next_retry_at <= ?) ORDER BY created_at ASC LIMIT ?",
        (now(), capacity),
    )
    for row in rows:
        job_id = row["id"]
        if job_id in task_map:
            continue
        try:
            raw = json.loads(row.get("request_json") or "{}")
            payload = JobIn(**raw)
            person = db.row("SELECT * FROM personas WHERE id=?", (payload.persona_id,))
            if not person:
                raise ValueError("Persona for queued job is no longer available")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            _mark_job_failed(job_id, f"Queued job request is not recoverable: {str(exc)[:1400]}")
            logger.error("job_dispatch_rejected", extra=_log_data({"job_id": job_id, "error": str(exc)[:300]}))
            continue
        _start_managed_job(job_id, payload, person)


async def _job_dispatch_loop():
    """Durable queue supervisor for local generation jobs."""

    while True:
        _recover_expired_jobs()
        await _dispatch_queued_jobs()
        event = getattr(app.state, "job_dispatch_event", None)
        if event is None:
            await asyncio.sleep(0.25)
            continue
        event.clear()
        try:
            await asyncio.wait_for(event.wait(), timeout=0.25)
        except asyncio.TimeoutError:
            pass


def _job_task(job_id: str, payload: JobIn, person: dict):
    """Wake the durable dispatcher after a Job row is committed."""

    event = getattr(app.state, "job_dispatch_event", None)
    if event is not None:
        event.set()
    return None


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = db.row("SELECT id,status FROM jobs WHERE id=?", (job_id,))
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] in {"completed", "failed", "cancelled"}:
        raise HTTPException(409, f"Job is already {job['status']}")
    timestamp = now()
    db.write(
        "UPDATE jobs SET status='cancelled', cancel_requested=1, finished_at=?, updated_at=?, error=?, "
        "worker_id=NULL, heartbeat_at=NULL, lease_expires_at=NULL, progress_stage='cancelled', "
        "progress_percent=100, progress_detail='Cancelled by operator' WHERE id=?",
        (timestamp, timestamp, "Cancelled by operator", job_id),
    )
    task = getattr(app.state, "job_task_map", {}).get(job_id)
    if task and not task.done():
        task.cancel()
    logger.info("job_cancelled", extra=_log_data({"job_id": job_id}))
    return {"id": job_id, "status": "cancelled"}


@app.post("/api/jobs/{job_id}/retry", status_code=202)
async def retry_job(job_id: str):
    job = db.row("SELECT * FROM jobs WHERE id=?", (job_id,))
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] not in {"failed", "interrupted", "cancelled"}:
        raise HTTPException(409, "Only failed, interrupted, or cancelled jobs can be retried")
    try:
        raw = json.loads(job.get("request_json") or "{}")
        payload = JobIn(**raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(409, "This legacy job has no retryable request metadata") from exc
    person = must_persona(payload.persona_id)
    attempt = int(job.get("attempt") or 1) + 1
    settings = get_settings()
    if attempt > settings.job_max_attempts:
        raise HTTPException(409, f"Maximum retry attempts reached ({settings.job_max_attempts})")
    delay = _retry_delay(attempt)
    next_retry_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(timespec="seconds")
    timestamp = now()
    db.write(
        "UPDATE jobs SET status='queued', attempt=?, cancel_requested=0, error=NULL, finished_at=NULL, "
        "updated_at=?, next_retry_at=?, worker_id=NULL, heartbeat_at=NULL, lease_expires_at=NULL, "
        "progress_stage='queued', progress_percent=0, progress_detail=?, progress_json='{}' WHERE id=?",
        (attempt, timestamp, next_retry_at, f"Retry scheduled in {delay} second(s)", job_id),
    )
    _job_task(job_id, payload, person)
    logger.info("job_retried", extra=_log_data({"job_id": job_id, "attempt": attempt, "retry_after_seconds": delay}))
    return {"id": job_id, "status": "queued", "attempt": attempt, "next_retry_at": next_retry_at, "retry_after_seconds": delay}


@app.get("/api/jobs")
def get_jobs():
    rows = db.all_rows("SELECT jobs.*,personas.name AS persona_name FROM jobs JOIN personas ON personas.id=jobs.persona_id ORDER BY jobs.created_at DESC LIMIT 100")
    for item in rows:
        try:
            item["lineage"] = json.loads(item.pop("lineage_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            item["lineage"] = {}
        try:
            item["result"] = json.loads(item.pop("result_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            item["result"] = {}
        try:
            item["progress"] = json.loads(item.pop("progress_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            item["progress"] = {}
    return rows


@app.get("/api/assets")
def get_assets():
    rows = db.all_rows("SELECT assets.*,personas.name AS persona_name FROM assets JOIN personas ON personas.id=assets.persona_id ORDER BY assets.created_at DESC LIMIT 150")
    for item in rows:
        for key in ("metadata_json", "quality_json"):
            try:
                item[key.removesuffix("_json")] = json.loads(item[key] or "{}")
            except (TypeError, json.JSONDecodeError):
                item[key.removesuffix("_json")] = {}
    return rows


@app.post("/api/assets/import", status_code=201)
async def import_asset(
    persona_id: str = Form(...),
    file: UploadFile = File(...),
    kind: str = Form("video"),
    prompt: str = Form("Imported local pipeline output"),
    disclosure: str = Form(AI_DISCLOSURE),
    rights_confirmed: bool = Form(False),
    content_class: str = Form("identity"),
    destination_policy: str = Form("review_required"),
):
    person = must_persona(persona_id)
    if not rights_confirmed:
        raise HTTPException(400, "Confirm this output and its source inputs are rights-cleared")
    if kind not in {"image", "video", "audio"}:
        raise HTTPException(400, "Asset kind must be image, video, or audio")
    if len(prompt.strip()) < 5:
        raise HTTPException(400, "Describe the imported scene or pipeline output")
    if len(disclosure.strip()) < 20:
        raise HTTPException(400, "Include a clear AI-generated disclosure")
    normalized_content_class = normalize_content_class(content_class)
    try:
        normalized_destination_policy = normalize_destination_policy(destination_policy)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        raw = await read_limited(file, get_settings().asset_max_bytes)
        validate_import_suffix(kind, file.filename or "")
        if kind == "image":
            # Images are always decoded so a renamed executable cannot enter the media vault.
            suffix = validate_image_bytes(raw)
        else:
            validate_media_signature(raw, kind, strict=get_settings().strict_media_validation)
    except ValueError as exc:
        raise HTTPException(413 if "exceeds" in str(exc) else 400, str(exc)) from exc
    disclosure = disclosure.strip()[:300]
    persona_version = PersonaRepository.current_version(person["id"])
    asset = register_media_asset(
        persona_id=person["id"],
        persona_version_id=persona_version["id"] if persona_version else None,
        job_id=None,
        kind=kind,
        prompt=prompt.strip()[:3000],
        raw=raw,
        disclosure=disclosure,
        rights_confirmed=True,
        original_filename=file.filename,
        lineage={"source": "local_import"},
        content_class=normalized_content_class,
        destination_policy=normalized_destination_policy,
    )
    return {"id": asset["id"], "kind": kind, "review": asset["review"], "url": f"/api/assets/{asset['id']}/file"}


@app.get("/api/assets/{aid}/file")
def asset_file(aid: str):
    asset = db.row("SELECT * FROM assets WHERE id=?", (aid,))
    if not asset:
        raise HTTPException(404, "Asset not found")
    try:
        return FileResponse(resolve_asset_file(asset))
    except FileNotFoundError:
        raise HTTPException(404, "Asset media file is missing") from None


_ASSET_ASSESSMENT_METRICS = {
    "identity_score": ("identity_similarity", "Identity similarity"),
    "anatomy_score": ("anatomy", "Anatomy integrity"),
    "hands_score": ("hands", "Hands integrity"),
    "facial_drift_score": ("facial_drift", "Facial drift"),
    "temporal_stability_score": ("temporal_stability", "Temporal stability"),
    "audio_timing_score": ("audio_timing", "Audio timing"),
}


def _apply_asset_assessment(asset: dict, quality: dict, assessment: dict | None = None):
    stored = assessment
    if stored is None:
        try:
            persisted = json.loads(asset.get("quality_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            persisted = {}
        stored = persisted.get("assessment") if isinstance(persisted, dict) else None
    check_ids = {item[0] for item in _ASSET_ASSESSMENT_METRICS.values()} | {"human_quality_assessment"}
    quality["checks"] = [item for item in quality.get("checks", []) if item.get("id") not in check_ids]
    if not isinstance(stored, dict):
        quality["checks"].append({
            "id": "human_quality_assessment",
            "status": "warning",
            "detail": "No operator or model quality assessment has been recorded",
        })
        quality.pop("assessment", None)
        return quality
    scores = stored.get("scores") if isinstance(stored.get("scores"), dict) else {}
    quality["assessment"] = stored
    relevant = ["identity_score", "anatomy_score", "hands_score", "facial_drift_score"]
    if asset.get("kind") == "video":
        relevant.extend(("temporal_stability_score", "audio_timing_score"))
    elif asset.get("kind") == "audio":
        relevant.append("audio_timing_score")
    for field in relevant:
        check_id, label = _ASSET_ASSESSMENT_METRICS[field]
        score = scores.get(field)
        if score is None:
            quality["checks"].append({"id": check_id, "status": "warning", "detail": f"{label} assessment is not recorded"})
        elif score < 0.70:
            quality["checks"].append({"id": check_id, "status": "error", "detail": f"{label} score {score:.2f} is below the 0.70 approval threshold"})
        else:
            quality["checks"].append({"id": check_id, "status": "ready", "detail": f"{label} score {score:.2f}"})
    return quality


def _apply_asset_identity_lineage(asset: dict, job: dict | None, quality: dict):
    version_id = asset.get("persona_version_id")
    version = db.row(
        "SELECT id, persona_id, state, version_no FROM persona_versions WHERE id=? AND persona_id=?",
        (version_id, asset.get("persona_id")),
    ) if version_id else None
    if not version:
        quality["checks"].append({
            "id": "identity_version",
            "status": "warning",
            "detail": "Asset is not bound to a verified PersonaVersion",
        })
    else:
        quality["checks"].append({
            "id": "identity_version",
            "status": "ready",
            "detail": f"Asset is bound to PersonaVersion {version['id']}",
        })
        quality["checks"].append({
            "id": "identity_state",
            "status": "ready" if version["state"] == "frozen" else "warning",
            "detail": "PersonaVersion is frozen" if version["state"] == "frozen" else "PersonaVersion remains draft",
        })
    if job:
        try:
            request = json.loads(job.get("request_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            request = {}
        try:
            lineage = json.loads(job.get("lineage_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            lineage = {}
        content_pack_id = lineage.get("content_pack_id") or request.get("content_pack_id")
        if content_pack_id:
            pack = db.row(
                "SELECT id, persona_version_id, review, content_class FROM content_packs WHERE id=? AND persona_id=?",
                (content_pack_id, asset.get("persona_id")),
            )
            pack_ready = bool(pack and pack["review"] == "approved" and pack["persona_version_id"] == version_id)
            quality["checks"].append({
                "id": "content_pack_lineage",
                "status": "ready" if pack_ready else "error",
                "detail": "Approved ContentPack and Asset PersonaVersion match" if pack_ready else "ContentPack lineage is missing approval or PersonaVersion alignment",
            })


def _asset_bundle(aid: str):
    asset = db.row("SELECT * FROM assets WHERE id=?", (aid,))
    if not asset:
        raise HTTPException(404, "Asset not found")
    job = db.row("SELECT * FROM jobs WHERE id=?", (asset.get("job_id"),)) if asset.get("job_id") else None
    person = db.row("SELECT * FROM personas WHERE id=?", (asset["persona_id"],))
    try:
        path = resolve_asset_file(asset)
    except FileNotFoundError:
        raise HTTPException(404, "Asset media file is missing") from None
    try:
        metadata = json.loads(asset.get("metadata_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        metadata = {}
    quality = quality_report(path, asset["kind"], asset.get("disclosure") or AI_DISCLOSURE,
                             lineage={"job_id": asset.get("job_id")} if asset.get("job_id") else metadata.get("lineage"),
                             expected_sha256=asset.get("sha256"),
                             strict_media=get_settings().strict_media_validation)
    content_class = normalize_content_class(asset.get("content_class"))
    quality["checks"].append({
        "id": "content_class",
        "status": "ready" if content_class else "warning",
        "detail": f"Content class recorded: {content_class}" if content_class else "Record a content class before destination review",
    })
    try:
        destination_policy = normalize_destination_policy(asset.get("destination_policy"))
    except ValueError:
        destination_policy = "review_required"
        quality["checks"].append({
            "id": "destination_policy",
            "status": "error",
            "detail": "Asset has an unsupported destination policy",
        })
    else:
        policy_status = "ready" if destination_policy in {"local_only", "eligible"} else "warning"
        policy_detail = {
            "local_only": "Asset is restricted to local export until a destination is explicitly selected",
            "review_required": "Destination policy review is required before publishing",
            "eligible": "Destination policy eligibility has been recorded",
        }[destination_policy]
        quality["checks"].append({"id": "destination_policy", "status": policy_status, "detail": policy_detail})
    rights_ok = bool(asset.get("rights_confirmed"))
    quality["checks"].append({
        "id": "rights",
        "status": "ready" if rights_ok else "warning",
        "detail": "Rights confirmation recorded" if rights_ok else "Rights confirmation is required before approval or export",
    })
    _apply_asset_identity_lineage(asset, job, quality)
    _apply_asset_assessment(asset, quality)
    statuses = [item["status"] for item in quality.get("checks", [])]
    quality["status"] = "error" if "error" in statuses else "warning" if "warning" in statuses else "ready"
    return asset, job, person, quality


@app.get("/api/assets/{aid}/manifest")
def asset_manifest(aid: str):
    asset, job, person, quality = _asset_bundle(aid)
    return manifest(asset, job=job, persona=person, quality=quality)


@app.get("/api/assets/{aid}/quality")
def asset_quality(aid: str):
    _asset, _job, _person, quality = _asset_bundle(aid)
    return quality


@app.post("/api/assets/{aid}/quality")
def refresh_asset_quality(aid: str):
    _asset, _job, _person, quality = _asset_bundle(aid)
    db.write("UPDATE assets SET quality_json=? WHERE id=?", (json.dumps(quality, ensure_ascii=False), aid))
    return {"id": aid, "quality": quality}


@app.get("/api/assets/{aid}/publishing-readiness")
def asset_publishing_readiness(aid: str):
    asset, _job, _person, quality = _asset_bundle(aid)
    quality_checks = {item.get("id"): item for item in quality.get("checks", [])}
    checks = [
        {
            "id": "review",
            "status": "ready" if asset.get("review") == "approved" and asset.get("reviewed_at") else "error",
            "detail": "Asset has an approved, timestamped review decision" if asset.get("review") == "approved" and asset.get("reviewed_at") else "Asset must be approved with review evidence",
        },
        quality_checks.get("rights", {"id": "rights", "status": "error", "detail": "Rights check is missing"}),
        quality_checks.get("disclosure", {"id": "disclosure", "status": "error", "detail": "Disclosure check is missing"}),
        quality_checks.get("identity_version", {"id": "identity_version", "status": "error", "detail": "PersonaVersion check is missing"}),
        quality_checks.get("identity_state", {"id": "identity_state", "status": "error", "detail": "PersonaVersion state check is missing"}),
        quality_checks.get("content_class", {"id": "content_class", "status": "error", "detail": "Content class check is missing"}),
        {
            "id": "destination_policy",
            "status": "ready" if asset.get("destination_policy") == "eligible" else "error",
            "detail": "Destination policy is eligible for external publishing" if asset.get("destination_policy") == "eligible" else "Destination policy must be eligible for external publishing",
        },
        {
            "id": "quality",
            "status": "ready" if quality.get("status") == "ready" else "error",
            "detail": "All recorded quality checks passed" if quality.get("status") == "ready" else "Resolve quality warnings or errors before publishing",
        },
    ]
    ready = all(item.get("status") == "ready" for item in checks)
    return {
        "id": aid,
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "content_class": asset.get("content_class") or "identity",
        "destination_policy": asset.get("destination_policy") or "review_required",
        "checks": checks,
    }


@app.get("/api/publishing/policies")
def publishing_policies():
    return {
        "execution_status": "catalog_only",
        "external_calls": False,
        "policies": publishing_policy_catalog(),
        "providers": publishing_provider_catalog(),
    }


@app.get("/api/publishing/providers")
def publishing_providers():
    return {"external_calls": False, "secret_storage": secret_storage_catalog(), "providers": publishing_provider_catalog()}


@app.get("/api/publishing/security")
def publishing_security():
    return {
        "external_calls": False,
        "secret_storage": secret_storage_catalog(),
        "database_secret_values": False,
        "token_reference_policy": "opaque_reference_only",
    }


def _publishing_account_response(account: dict | None):
    return account or {}


def _oauth_verifier_ref(session_id: str) -> str:
    return f"publishing/oauth/{session_id}/pkce-verifier"


def _account_token_ref(account_id: str) -> str:
    return f"publishing/account/{account_id}/tokens"


def _delete_secret(reference: str):
    try:
        get_store().delete(reference)
    except (SecretStoreUnavailable, ValueError):
        pass


@app.get("/api/personas/{pid}/publishing-accounts")
def list_publishing_accounts(pid: str):
    if not db.row("SELECT id FROM personas WHERE id=?", (pid,)):
        raise HTTPException(404, "Persona not found")
    return PublishingRepository.accounts(pid)


@app.post("/api/personas/{pid}/publishing-accounts", status_code=201)
def create_publishing_account(pid: str, payload: PublishingAccountIn):
    if not db.row("SELECT id FROM personas WHERE id=?", (pid,)):
        raise HTTPException(404, "Persona not found")
    platform = payload.platform.strip().lower()
    account_type = payload.account_type.strip().lower()
    if platform not in publishing_policy_catalog():
        raise HTTPException(400, "Unsupported publishing platform")
    if platform == "instagram" and account_type not in {"professional", "business", "creator"}:
        raise HTTPException(400, "Instagram account must be professional, business, or creator")
    try:
        return _publishing_account_response(PublishingRepository.create_account(
            account_id=uid(), persona_id=pid, platform=platform,
            account_label=payload.account_label.strip(), account_type=account_type,
            handle=(payload.handle or "").strip() or None,
            external_account_id=(payload.external_account_id or "").strip() or None,
            metadata=dict(payload.metadata or {}), created_at=now(),
        ))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with this label is already bound to this persona") from None


@app.get("/api/publishing-accounts/{account_id}/authorization-sessions")
def list_authorization_sessions(account_id: str):
    account = PublishingRepository.account(account_id)
    if not account:
        raise HTTPException(404, "Publishing account not found")
    return PublishingRepository.auth_sessions(account_id)


@app.get("/oauth/callback")
@app.get("/api/publishing/oauth/callback")
def publishing_oauth_callback(provider: str | None = None, state: str | None = None,
                              code: str | None = None, error: str | None = None,
                              error_description: str | None = None):
    """Validate and consume a provider callback, with explicitly gated exchange.

    The raw OAuth state and authorization code are request-only values. The
    session stores only a state hash and is atomically consumed once. Token
    exchange is disabled unless the provider and runtime feature gate are
    explicitly enabled.
    """
    state = (state or "").strip()
    if not state or len(state) > 512:
        raise HTTPException(400, "OAuth callback state is missing or invalid")
    session = PublishingRepository.auth_session_by_state_hash(
        hashlib.sha256(state.encode("utf-8")).hexdigest()
    )
    if not session:
        raise HTTPException(400, "OAuth callback state is invalid")
    provider_name = (provider or "").strip().lower()
    if provider_name and provider_name != session["provider"]:
        raise HTTPException(400, "OAuth callback provider does not match the authorization session")
    try:
        provider_impl = get_publishing_provider(session["provider"])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    exchange_enabled = bool(getattr(provider_impl, "token_exchange_enabled", lambda: False)())
    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        expires_at = datetime.min.replace(tzinfo=timezone.utc)
    callback_at = datetime.now(timezone.utc)
    if expires_at <= callback_at:
        PublishingRepository.consume_auth_session(
            session_id=session["id"], status="expired", consumed_at=callback_at.isoformat(timespec="seconds"),
            error="OAuth authorization session expired",
        )
        _delete_secret(_oauth_verifier_ref(session["id"]))
        raise HTTPException(400, "OAuth authorization session expired")
    if session.get("status") != "planned" or session.get("consumed_at"):
        raise HTTPException(409, "OAuth authorization session has already been consumed")
    if error:
        # Persist only a bounded provider error code. Never retain the
        # provider's free-form description, which may contain sensitive data.
        safe_error = re.sub(r"[^A-Za-z0-9._:-]+", "_", error.strip().lower())[:80] or "provider_denied"
        consumed = PublishingRepository.consume_auth_session(
            session_id=session["id"], status="denied", consumed_at=callback_at.isoformat(timespec="seconds"),
            error=safe_error,
        )
        if not consumed:
            raise HTTPException(409, "OAuth authorization session has already been consumed")
        _delete_secret(_oauth_verifier_ref(session["id"]))
        return {
            "status": "denied",
            "session": consumed,
            "provider": session["provider"],
            "external_calls": False,
            "token_exchange": "not_run",
        }
    if not code or len(code) > 4096:
        raise HTTPException(400, "OAuth callback authorization code is missing or invalid")
    if exchange_enabled:
        claimed = PublishingRepository.claim_auth_session(session["id"])
        if not claimed:
            raise HTTPException(409, "OAuth authorization session has already been consumed")
        verifier_ref = _oauth_verifier_ref(session["id"])
        try:
            verifier = get_store().get(verifier_ref)
            if not verifier:
                raise ProviderDisabled("PKCE verifier is not available in the OS keychain")
            token_payload = provider_impl.exchange_code(
                auth_mode=session["auth_mode"], redirect_uri=session["redirect_uri"],
                code=code, code_verifier=verifier,
            )
            token_ref = _account_token_ref(session["account_id"])
            token_bundle = dict(token_payload)
            token_bundle.update({
                "provider": session["provider"],
                "auth_mode": session["auth_mode"],
                "stored_at": callback_at.isoformat(timespec="seconds"),
            })
            get_store().put(token_ref, json.dumps(token_bundle, ensure_ascii=False))
            account = PublishingRepository.account(session["account_id"])
            metadata = dict(account.get("metadata") or {}) if account else {}
            metadata.update({
                "provider": session["provider"],
                "auth_mode": session["auth_mode"],
                "authorized_at": callback_at.isoformat(timespec="seconds"),
                "token_storage": "os_keyring",
                "token_type": token_payload.get("token_type"),
                "scope": token_payload.get("scope"),
                "expires_in": token_payload.get("expires_in"),
            })
            authorized_account = PublishingRepository.authorize_account(
                account_id=session["account_id"], token_ref=token_ref,
                metadata=metadata, updated_at=callback_at.isoformat(timespec="seconds"),
            )
            finalized = PublishingRepository.finalize_auth_session(
                session_id=session["id"], status="authorized",
                consumed_at=callback_at.isoformat(timespec="seconds"),
            )
            if not finalized:
                raise RuntimeError("OAuth authorization session could not be finalized")
            _delete_secret(verifier_ref)
            return {
                "status": "authorized",
                "session": finalized,
                "account": authorized_account,
                "provider": session["provider"],
                "external_calls": True,
                "token_exchange": "completed",
                "token_stored": True,
            }
        except (ProviderDisabled, SecretStoreUnavailable, ValueError, RuntimeError) as exc:
            PublishingRepository.finalize_auth_session(
                session_id=session["id"], status="exchange_failed",
                consumed_at=callback_at.isoformat(timespec="seconds"), error="token_exchange_failed",
            )
            _delete_secret(verifier_ref)
            raise HTTPException(502, "Meta token exchange failed") from exc
    consumed = PublishingRepository.consume_auth_session(
        session_id=session["id"], status="callback_received", consumed_at=callback_at.isoformat(timespec="seconds"),
    )
    if not consumed:
        raise HTTPException(409, "OAuth authorization session has already been consumed")
    return {
        "status": "callback_received",
        "session": consumed,
        "provider": session["provider"],
        "external_calls": False,
        "token_exchange": "disabled",
        "authorization_code_stored": False,
    }


@app.post("/api/publishing-accounts/{account_id}/token-refresh")
def refresh_publishing_account_token(account_id: str):
    account = PublishingRepository.account(account_id)
    if not account:
        raise HTTPException(404, "Publishing account not found")
    provider_name = (account.get("metadata") or {}).get("provider", "meta_instagram")
    try:
        provider_impl = get_publishing_provider(provider_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not bool(getattr(provider_impl, "token_exchange_enabled", lambda: False)()):
        raise HTTPException(409, "Token refresh is disabled by provider configuration")
    token_ref = PublishingRepository.account_token_ref(account_id)
    if not token_ref:
        raise HTTPException(409, "Publishing account has no keychain token bundle")
    try:
        raw_bundle = get_store().get(token_ref)
        bundle = json.loads(raw_bundle or "")
        refresh_token = bundle.get("refresh_token")
        if not refresh_token:
            raise ValueError("Token bundle has no refresh token")
        refreshed = provider_impl.refresh_token(
            auth_mode=(account.get("metadata") or {}).get("auth_mode", "instagram_login"),
            refresh_token=refresh_token,
        )
        updated_bundle = dict(bundle)
        updated_bundle.update({
            key: value for key, value in refreshed.items()
            if not (key == "refresh_token" and not value)
        })
        updated_bundle.update({"provider": provider_name, "stored_at": now()})
        get_store().put(token_ref, json.dumps(updated_bundle, ensure_ascii=False))
    except (SecretStoreUnavailable, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "Meta token refresh failed") from exc
    metadata = dict(account.get("metadata") or {})
    metadata.update({
        "refreshed_at": now(),
        "token_storage": "os_keyring",
        "token_type": refreshed.get("token_type"),
        "scope": refreshed.get("scope"),
        "expires_in": refreshed.get("expires_in"),
    })
    updated_account = PublishingRepository.authorize_account(
        account_id=account_id, token_ref=token_ref, metadata=metadata, updated_at=now(),
    )
    return {
        "status": "authorized",
        "account": updated_account,
        "provider": provider_name,
        "external_calls": True,
        "token_refresh": "completed",
        "token_stored": True,
    }


@app.post("/api/publishing-accounts/{account_id}/verify")
def verify_publishing_account(account_id: str):
    account = PublishingRepository.account(account_id)
    if not account:
        raise HTTPException(404, "Publishing account not found")
    if account.get("platform") != "instagram":
        raise HTTPException(400, "Only Instagram account verification is supported")
    if account.get("status") not in {"authorized", "verified"}:
        raise HTTPException(409, "Authorize the publishing account before verification")
    metadata = account.get("metadata") or {}
    provider_name = metadata.get("provider", "meta_instagram")
    try:
        provider_impl = get_publishing_provider(provider_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not bool(getattr(provider_impl, "account_verification_enabled", lambda: False)()):
        raise HTTPException(409, "Meta account verification is disabled by provider configuration")
    token_ref = PublishingRepository.account_token_ref(account_id)
    if not token_ref:
        raise HTTPException(409, "Publishing account has no keychain token bundle")
    try:
        bundle = json.loads(get_store().get(token_ref) or "")
        if not isinstance(bundle, dict) or not bundle.get("access_token"):
            raise ValueError("Token bundle has no access token")
        verification = provider_impl.verify_account(
            auth_mode=metadata.get("auth_mode", "instagram_login"),
            access_token=bundle["access_token"],
        )
    except (SecretStoreUnavailable, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "Meta account verification failed") from exc
    account_type = verification.get("account_type")
    if account_type not in {"professional", "business", "creator"}:
        raise HTTPException(409, "Verified Instagram account is not a professional, business, or creator account")
    metadata.update({
        "verified_at": now(),
        "verified_by_provider": provider_name,
        "verified_external_account_id": verification["external_account_id"],
        "verified_handle": verification.get("handle"),
    })
    verified_account = PublishingRepository.verify_account(
        account_id=account_id, external_account_id=verification["external_account_id"],
        handle=verification.get("handle"), account_type=account_type,
        metadata=metadata, updated_at=now(),
    )
    return {
        "status": "verified",
        "account": verified_account,
        "provider": provider_name,
        "external_calls": True,
        "account_verified": True,
    }


def _asset_public_media(asset: dict) -> dict:
    try:
        metadata = json.loads(asset.get("metadata_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        metadata = {}
    value = metadata.get("publishing_media")
    return value if isinstance(value, dict) else {}


@app.post("/api/assets/{aid}/public-media")
def prepare_public_media(aid: str):
    asset, _job, _person, _quality = _asset_bundle(aid)
    base = asset_publishing_readiness(aid)
    if not base["ready"]:
        raise HTTPException(409, "Asset must pass publishing readiness before public media delivery is prepared")
    enabled = os.getenv("STUDIO_ENABLE_PUBLIC_MEDIA_DELIVERY", "0").lower() in {"1", "true", "yes"}
    base_url = os.getenv("STUDIO_PUBLIC_MEDIA_BASE_URL", "").strip().rstrip("/")
    parsed = urlparse(base_url)
    allow_insecure = os.getenv("STUDIO_ALLOW_INSECURE_PUBLIC_MEDIA", "0").lower() in {"1", "true", "yes"}
    if not enabled or not parsed.netloc or parsed.scheme not in ({"http", "https"} if allow_insecure else {"https"}):
        raise HTTPException(409, "Public media delivery is not explicitly configured with an HTTPS base URL")
    try:
        metadata = json.loads(asset.get("metadata_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        metadata = {}
    public_url = f"{base_url}/api/assets/{quote(aid, safe='')}/file"
    media = {
        "status": "ready",
        "url": public_url,
        "provider": "configured_public_base_url",
        "prepared_at": now(),
        "network_verified": False,
    }
    metadata["publishing_media"] = media
    db.write("UPDATE assets SET metadata_json=? WHERE id=?", (json.dumps(metadata, ensure_ascii=False), aid))
    return {"id": aid, "status": "ready", "media": media, "external_calls": False}


@app.post("/api/publishing-accounts/{account_id}/authorization-plan")
def create_authorization_plan(account_id: str, payload: PublishingAuthorizationPlanIn):
    account = PublishingRepository.account(account_id)
    if not account:
        raise HTTPException(404, "Publishing account not found")
    try:
        provider = get_publishing_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    provider_name = payload.provider.strip().lower()
    if provider_name == "meta_instagram" and account.get("platform") != "instagram":
        raise HTTPException(400, "Meta Instagram provider requires an Instagram account binding")
    redirect = urlparse(payload.redirect_uri.strip())
    if redirect.scheme not in {"http", "https"} or not redirect.netloc:
        raise HTTPException(400, "redirect_uri must be an absolute HTTP(S) URL")
    scopes = list(dict.fromkeys(scope.strip()[:160] for scope in payload.scopes if scope.strip()))[:20]
    created_at = now()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(timespec="seconds")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    capability = provider.catalog()
    status = "blocked"
    error = "Selected provider does not support OAuth; no authorization URL was created"
    authorization = {}
    try:
        authorization = provider.authorization_plan(
            auth_mode=payload.auth_mode.strip().lower(), redirect_uri=payload.redirect_uri.strip(),
            state=state, code_verifier=verifier, requested_scopes=scopes,
        )
        status = "planned"
        error = None
    except AttributeError:
        pass
    except ProviderDisabled as exc:
        error = str(exc)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    session_scopes = authorization.get("scopes", scopes)
    auth_mode = authorization.get("auth_mode", payload.auth_mode.strip().lower())
    session_id = uid()
    verifier_storage = "hashes_only"
    if authorization.get("token_exchange_enabled"):
        try:
            get_store().put(_oauth_verifier_ref(session_id), verifier)
        except (SecretStoreUnavailable, ValueError) as exc:
            raise HTTPException(503, "OS keychain could not retain the PKCE verifier") from exc
        verifier_storage = "os_keyring_verifier"
    session = PublishingRepository.create_auth_session(
        session_id=session_id, account_id=account_id, provider=provider_name,
        auth_mode=auth_mode,
        state_hash=hashlib.sha256(state.encode("utf-8")).hexdigest(),
        verifier_hash=hashlib.sha256(verifier.encode("utf-8")).hexdigest(),
        redirect_uri=payload.redirect_uri.strip(), scopes=session_scopes, status=status,
        expires_at=expires_at, error=error, created_at=created_at,
    )
    return {
        "session": session,
        "provider": capability,
        "authorization_url": authorization.get("authorization_url"),
        "state_issued": bool(authorization),
        "state": state if authorization else None,
        "code_verifier": authorization.get("code_verifier") if verifier_storage == "hashes_only" else None,
        "scopes": session_scopes,
        "secret_storage": verifier_storage,
        "external_calls": False,
        "status": status,
        "error": error,
    }


@app.get("/api/assets/{aid}/platform-readiness")
def asset_platform_readiness(aid: str, platform: str = "instagram", format: str | None = None, account_id: str | None = None):
    asset, _job, _person, quality = _asset_bundle(aid)
    base = asset_publishing_readiness(aid)
    format_name = format or infer_format(platform, asset.get("kind") or "")
    if not format_name:
        raise HTTPException(400, "A supported publishing format is required for this asset kind")
    try:
        account = PublishingRepository.account(account_id, asset.get("persona_id")) if account_id else None
        account_metadata = account.get("metadata") or {} if account else {}
        public_media = _asset_public_media(asset)
        report = evaluate_publishing_policy(
            platform,
            format_name,
            asset_kind=asset.get("kind") or "",
            base_ready=base["ready"],
            destination_policy=asset.get("destination_policy") or "review_required",
            public_media_url=bool(public_media.get("status") == "ready" and public_media.get("url")),
            account_bound=bool(account and account.get("status") == "verified"),
            permissions_configured=bool(account and account.get("status") == "verified" and account_metadata.get("scope")),
            professional_account=bool(account and account.get("account_type") in {"professional", "business", "creator"} and account.get("status") == "verified"),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "id": aid,
        "content_class": asset.get("content_class") or "identity",
        "destination_policy": asset.get("destination_policy") or "review_required",
        "base_readiness": base,
        "platform_readiness": report,
        "quality_status": quality.get("status"),
        "account": account,
        "public_media": public_media,
    }


@app.post("/api/assets/{aid}/publish-dry-run")
def publish_dry_run(aid: str, payload: PublishDryRunIn):
    asset, _job, _person, quality = _asset_bundle(aid)
    account = PublishingRepository.account(payload.account_id, asset.get("persona_id"))
    if not account:
        raise HTTPException(404, "Publishing account is not bound to this persona")
    format_name = payload.format or infer_format(account["platform"], asset.get("kind") or "")
    if not format_name:
        raise HTTPException(400, "A supported publishing format is required for this asset kind")
    base = asset_publishing_readiness(aid)
    try:
        account_metadata = account.get("metadata") or {}
        public_media = _asset_public_media(asset)
        policy = evaluate_publishing_policy(
            account["platform"], format_name, asset_kind=asset.get("kind") or "",
            base_ready=base["ready"], destination_policy=asset.get("destination_policy") or "review_required",
            public_media_url=bool(public_media.get("status") == "ready" and public_media.get("url")),
            account_bound=account.get("status") == "verified",
            permissions_configured=account.get("status") == "verified" and bool(account_metadata.get("scope")),
            professional_account=account.get("status") == "verified" and account.get("account_type") in {"professional", "business", "creator"},
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    caption_check = {"id": "approved_caption", "status": "blocked", "detail": "An approved caption ContentArtifact is required before publishing"}
    artifact = None
    if payload.content_artifact_id:
        artifact = db.row("SELECT id, persona_id, artifact_type, status, quality_status FROM content_artifacts WHERE id=?", (payload.content_artifact_id,))
        if artifact and artifact["persona_id"] == asset.get("persona_id") and artifact["artifact_type"] == "caption" and artifact["status"] == "approved" and artifact["quality_status"] == "passed":
            caption_check = {"id": "approved_caption", "status": "ready", "detail": "Approved caption ContentArtifact is bound to the same persona"}
        else:
            caption_check["detail"] = "Caption artifact must belong to the persona, be a caption, and be approved with passed quality"
    checks = list(policy["checks"]) + [caption_check]
    try:
        provider = get_publishing_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    response = provider.dry_run(platform=account["platform"], format_name=format_name, checks=checks, account_id=account["id"])
    existing = PublishingRepository.attempt_by_key(payload.idempotency_key)
    if existing:
        return {"replayed": True, "attempt": existing}
    attempt = PublishingRepository.create_attempt(
        attempt_id=uid(), persona_id=asset["persona_id"], persona_version_id=asset.get("persona_version_id"),
        asset_id=aid, content_artifact_id=payload.content_artifact_id, account_id=account["id"],
        platform=account["platform"], format_name=format_name, idempotency_key=payload.idempotency_key,
        status=response["status"], request={"asset_id": aid, "account_id": account["id"], "format": format_name, "content_artifact_id": payload.content_artifact_id},
        response=response, error=None if response["ready"] else "Dry run is blocked by one or more publishing checks", created_at=now(),
    )
    return {"replayed": False, "attempt": attempt, "quality_status": quality.get("status")}


@app.post("/api/assets/{aid}/publish")
def publish_asset(aid: str, payload: PublishDryRunIn):
    asset, _job, _person, quality = _asset_bundle(aid)
    account = PublishingRepository.account(payload.account_id, asset.get("persona_id"))
    if not account:
        raise HTTPException(404, "Publishing account is not bound to this persona")
    existing = PublishingRepository.attempt_by_key(payload.idempotency_key)
    if existing:
        return {"replayed": True, "attempt": existing}
    if account.get("platform") != "instagram" or account.get("status") != "verified":
        raise HTTPException(409, "A verified Instagram account is required before publishing")
    format_name = payload.format or infer_format(account["platform"], asset.get("kind") or "")
    if not format_name:
        raise HTTPException(400, "A supported publishing format is required for this asset kind")
    base = asset_publishing_readiness(aid)
    account_metadata = account.get("metadata") or {}
    public_media = _asset_public_media(asset)
    try:
        policy = evaluate_publishing_policy(
            account["platform"], format_name, asset_kind=asset.get("kind") or "",
            base_ready=base["ready"], destination_policy=asset.get("destination_policy") or "review_required",
            public_media_url=bool(public_media.get("status") == "ready" and public_media.get("url")),
            account_bound=True,
            permissions_configured=bool(account_metadata.get("scope")),
            professional_account=account.get("account_type") in {"professional", "business", "creator"},
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    caption_check = {"id": "approved_caption", "status": "blocked", "detail": "An approved caption ContentArtifact is required before publishing"}
    caption = ""
    if payload.content_artifact_id:
        artifact = db.row("SELECT id, persona_id, artifact_type, status, quality_status, content FROM content_artifacts WHERE id=?", (payload.content_artifact_id,))
        if artifact and artifact["persona_id"] == asset.get("persona_id") and artifact["artifact_type"] == "caption" and artifact["status"] == "approved" and artifact["quality_status"] == "passed":
            caption = artifact.get("content") or ""
            caption_check = {"id": "approved_caption", "status": "ready", "detail": "Approved caption ContentArtifact is bound to the same persona"}
    checks = list(policy["checks"]) + [caption_check]
    if any(check.get("status") != "ready" for check in checks):
        raise HTTPException(409, {"message": "Publishing readiness is blocked", "checks": checks})
    try:
        provider = get_publishing_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not bool(getattr(provider, "publish_enabled", lambda: False)()):
        raise HTTPException(409, "Instagram publishing is disabled by provider configuration")
    if not bool(getattr(provider, "publish_account_allowed", lambda _external_account_id: False)(account.get("external_account_id") or "")):
        raise HTTPException(409, "The Instagram account is not allowlisted for the configured publishing environment")
    token_ref = PublishingRepository.account_token_ref(account["id"])
    if not token_ref:
        raise HTTPException(409, "Publishing account has no keychain token bundle")
    try:
        bundle = json.loads(get_store().get(token_ref) or "")
        if not isinstance(bundle, dict) or not bundle.get("access_token"):
            raise ValueError("Token bundle has no access token")
        published = provider.publish(
            auth_mode=account_metadata.get("auth_mode", "instagram_login"),
            external_account_id=account.get("external_account_id") or "",
            access_token=bundle["access_token"], media_url=public_media["url"],
            format_name=format_name, caption=caption,
        )
        response = {
            "provider": payload.provider.strip().lower(), "execution_status": "published",
            "external_calls": True, "status": "published", "ready": True, "media": published,
        }
        attempt = PublishingRepository.create_attempt(
            attempt_id=uid(), persona_id=asset["persona_id"], persona_version_id=asset.get("persona_version_id"),
            asset_id=aid, content_artifact_id=payload.content_artifact_id, account_id=account["id"],
            platform=account["platform"], format_name=format_name, idempotency_key=payload.idempotency_key,
            status="published", request={"asset_id": aid, "account_id": account["id"], "format": format_name, "content_artifact_id": payload.content_artifact_id},
            response=response, error=None, created_at=now(), dry_run=False,
        )
        return {"replayed": False, "attempt": attempt, "quality_status": quality.get("status")}
    except (SecretStoreUnavailable, ValueError, RuntimeError, json.JSONDecodeError, PublishError) as exc:
        retryable = bool(getattr(exc, "retryable", False))
        response = {
            "provider": payload.provider.strip().lower(), "execution_status": "failed",
            "external_calls": True, "status": "failed", "ready": False, "retryable": retryable,
        }
        PublishingRepository.create_attempt(
            attempt_id=uid(), persona_id=asset["persona_id"], persona_version_id=asset.get("persona_version_id"),
            asset_id=aid, content_artifact_id=payload.content_artifact_id, account_id=account["id"],
            platform=account["platform"], format_name=format_name, idempotency_key=payload.idempotency_key,
            status="failed", request={"asset_id": aid, "account_id": account["id"], "format": format_name, "content_artifact_id": payload.content_artifact_id},
            response=response, error="publish_failed", created_at=now(), dry_run=False,
        )
        raise HTTPException(502, "Instagram publishing failed") from exc


@app.post("/api/assets/{aid}/assessment")
def assess_asset(aid: str, payload: AssetAssessmentIn):
    asset, _job, _person, quality = _asset_bundle(aid)
    values = payload.model_dump()
    scores = {key: value for key, value in values.items() if key.endswith("_score") and value is not None}
    if not scores:
        raise HTTPException(400, "Record at least one quality score")
    evaluator = (payload.evaluator or "local_operator").strip()[:120] or "local_operator"
    assessment = {
        "source": "operator",
        "evaluator": evaluator,
        "assessed_at": now(),
        "scores": scores,
        "notes": (payload.notes or "").strip()[:2000],
    }
    _apply_asset_assessment(asset, quality, assessment)
    statuses = [item["status"] for item in quality.get("checks", [])]
    quality["status"] = "error" if "error" in statuses else "warning" if "warning" in statuses else "ready"
    review_reset = asset.get("review") == "approved"
    db.write(
        "UPDATE assets SET quality_json=?, review=CASE WHEN review='approved' THEN 'pending' ELSE review END WHERE id=?",
        (json.dumps(quality, ensure_ascii=False), aid),
    )
    if review_reset:
        ReferencePackRepository.invalidate_canonical_for_asset(aid)
    return {"id": aid, "review": "pending" if review_reset else asset.get("review"), "quality": quality, "assessment": assessment}


@app.get("/api/assets/{aid}/package")
def asset_package(aid: str):
    asset, job, person, quality = _asset_bundle(aid)
    if asset["review"] != "approved":
        raise HTTPException(409, "Approve the asset before exporting a package")
    if not asset.get("rights_confirmed"):
        raise HTTPException(409, "Confirm rights before exporting a package")
    if len((asset.get("disclosure") or "").strip()) < 20:
        raise HTTPException(409, "Add a clear AI-generated disclosure before exporting a package")
    if quality["status"] == "error":
        raise HTTPException(409, "Quality checks found an integrity error; resolve it before export")
    payload = manifest(asset, job=job, persona=person, quality=quality)
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(asset["filename"], resolve_asset_file(asset).read_bytes())
        bundle.writestr("manifest.json", json.dumps(payload, indent=2, ensure_ascii=False))
        bundle.writestr("AI-DISCLOSURE.txt", asset.get("disclosure") or AI_DISCLOSURE)
    archive.seek(0)
    return StreamingResponse(iter([archive.getvalue()]), media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="asset_{aid}.zip"'})


@app.patch("/api/assets/{aid}/review")
def set_review(aid: str, payload: ReviewIn):
    if payload.review not in {"approved", "rejected", "pending"}:
        raise HTTPException(400, "Review must be approved, rejected, or pending")
    if not db.row("SELECT id FROM assets WHERE id=?", (aid,)):
        raise HTTPException(404)
    reviewer = (payload.reviewer or "local_operator").strip()[:120] or "local_operator"
    reason = (payload.reason or "").strip()[:1000] or f"Operator marked asset {payload.review}"
    reviewed_at = now()
    if payload.review == "approved":
        asset, job, _person, quality = _asset_bundle(aid)
        if not asset.get("rights_confirmed"):
            raise HTTPException(409, "Confirm rights before approving the asset")
        if len((asset.get("disclosure") or "").strip()) < 20:
            raise HTTPException(409, "Add a clear AI-generated disclosure before approving the asset")
        if quality["status"] == "error":
            raise HTTPException(409, "Quality checks found an integrity error; inspect the asset before approving")
        db.write(
            "UPDATE assets SET review=?, quality_json=?, reviewed_at=?, reviewer=?, review_reason=? WHERE id=?",
            (payload.review, json.dumps(quality, ensure_ascii=False), reviewed_at, reviewer, reason, aid),
        )
        return {"id": aid, "review": payload.review, "quality": quality, "reviewed_at": reviewed_at, "reviewer": reviewer, "review_reason": reason}
    db.write(
        "UPDATE assets SET review=?, reviewed_at=?, reviewer=?, review_reason=? WHERE id=?",
        (payload.review, reviewed_at, reviewer, reason, aid),
    )
    ReferencePackRepository.invalidate_canonical_for_asset(aid)
    return {"id": aid, "review": payload.review, "reviewed_at": reviewed_at, "reviewer": reviewer, "review_reason": reason}


@app.post("/api/voice", status_code=202)
async def create_voice(payload: VoiceIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    person = must_persona(payload.persona_id)
    persona_version = PersonaRepository.current_version(person["id"])
    job_id, reused = _start_direct_job(
        person=person,
        workflow_id="voice_generation",
        kind="audio",
        prompt=payload.text,
        payload=payload,
        lineage={"execution_mode": "voice", "persona_version_id": persona_version["id"] if persona_version else None, "voice": payload.voice},
        idempotency_key=idempotency_key,
    )
    if reused is not None:
        return reused

    async def run_voice():
        from .voice import synthesize
        temp_path = Path(tempfile.gettempdir()) / f"studio_voice_{job_id}.wav"
        try:
            await asyncio.to_thread(synthesize, payload.text, payload.voice, temp_path)
            raw = temp_path.read_bytes()
        except Exception as exc:
            raise HTTPException(503, f"Voice generation unavailable: {str(exc)[:250]}") from exc
        finally:
            temp_path.unlink(missing_ok=True)
        disclosure = person.get("disclosure") or AI_DISCLOSURE
        asset = register_media_asset(
            persona_id=person["id"],
            persona_version_id=persona_version["id"] if persona_version else None,
            job_id=job_id,
            kind="audio",
            prompt=payload.text,
            raw=raw,
            disclosure=disclosure,
            rights_confirmed=True,
            original_filename="voice.wav",
            lineage={"job_id": job_id, "execution_mode": "voice"},
        )
        return {"id": asset["id"], "job_id": job_id, "url": f"/api/assets/{asset['id']}/file"}

    return await _finish_direct_job(job_id, run_voice)


@app.post("/api/links", status_code=201)
def create_link(payload: LinkIn):
    p = urlparse(payload.destination)
    if p.scheme != "https" or not p.netloc or p.username or p.password:
        raise HTTPException(400, "Destination must be a normal HTTPS URL")
    code = secrets.token_urlsafe(5)
    db.write("INSERT INTO links VALUES (?,?,?,?,?)", (code, payload.label, payload.destination, 0, now()))
    return {"code": code, "path": f"/go/{code}"}


@app.get("/api/links")
def list_links():
    return db.all_rows("SELECT * FROM links ORDER BY created_at DESC")


@app.get("/go/{code}")
def visit_link(code: str):
    link = db.row("SELECT destination FROM links WHERE code=?", (code,))
    if not link:
        raise HTTPException(404)
    db.write("UPDATE links SET clicks=clicks+1 WHERE code=?", (code,))
    return RedirectResponse(link["destination"], status_code=302)


@app.get("/api/summary")
def summary():
    def count(table, where=""):
        return db.row(f"SELECT COUNT(*) AS n FROM {table} {where}")["n"]
    return {"personas": count("personas"), "jobs": count("jobs"), "assets": count("assets"),
            "approved": count("assets", "WHERE review='approved'"),
            "clicks": db.row("SELECT COALESCE(SUM(clicks),0) AS n FROM links")["n"]}


PHOTO_STUDIO_PRESETS = {
    "locations": [
        {"id": "med_beach", "label": "🏖️ Mediterranean Beach", "prompt": "sunlit Mediterranean beach in Amalfi, azure sea waves, warm golden sunlight, soft white sand, coastal cliffs backdrop"},
        {"id": "luxury_loft", "label": "🏢 Minimalist Modern Loft", "prompt": "modern minimalist architectural loft, floor-to-ceiling glass windows, soft afternoon diffused natural light, concrete and warm oak interior"},
        {"id": "paris_cafe", "label": "☕ Parisian Café Terrace", "prompt": "quaint Parisian sidewalk café terrace, cobblestones, warm ambient bistro glow, blurred street bokeh, elegant outdoor table"},
        {"id": "penthouse_balcony", "label": "🌆 Penthouse Balcony Twilight", "prompt": "luxury high-rise penthouse glass balcony, dramatic city skyline at twilight, architectural glass railing, sophisticated ambient mood lighting"},
        {"id": "tropical_resort", "label": "🌿 Tropical Private Villa", "prompt": "private tropical infinity pool villa, lush palm fronds, turquoise water reflections, bright sun-drenched resort atmosphere"},
        {"id": "art_studio", "label": "🏛️ High-End Art Gallery", "prompt": "contemporary minimalist art gallery, polished concrete floors, dramatic museum spotlighting, clean architectural lines"},
    ],
    "costumes": [
        {"id": "black_bikini", "label": "👙 Designer String Bikini", "prompt": "minimalist designer black string bikini, sheer unbuttoned white linen oversized shirt draped over shoulders, delicate gold body chain"},
        {"id": "emerald_slip", "label": "👗 Emerald Silk Slip Dress", "prompt": "emerald green backless silk slip dress, thin delicate straps, fluid luxurious fabric, floor-length minimalist silhouette"},
        {"id": "oversized_blazer", "label": "🧥 Tailored Oversized Blazer", "prompt": "chic oversized charcoal wool blazer, minimalist black silk bralette underneath, high-waisted tailored trousers"},
        {"id": "ribbed_swimsuit", "label": "🏊 White Ribbed Swimsuit", "prompt": "sporty white ribbed one-piece swimsuit, high-cut leg, scoop back, clean athletic elegance"},
        {"id": "cashmere_denim", "label": "👚 Off-Shoulder Cashmere", "prompt": "relaxed off-shoulder ivory cashmere knit sweater, vintage high-waist denim, effortless Parisian casual chic"},
        {"id": "crochet_resort", "label": "✨ Terracotta Crochet Set", "prompt": "terracotta crochet bikini set with matching sheer macramé resort cover-up skirt, golden summer resort fashion"},
    ],
    "expressions": [
        {"id": "confident_gaze", "label": "✨ Confident Editorial Gaze", "prompt": "confident poised editorial gaze directly into lens, subtle parted lips, composed magnetic expression"},
        {"id": "candid_smile", "label": "😊 Warm Candid Smile", "prompt": "spontaneous radiant candid smile, crinkled hazel-green eyes with warmth, joyful relaxed natural expression"},
        {"id": "seductive_moody", "label": "🌙 Seductive & Mysterious", "prompt": "seductive intense gaze over shoulder, moody alluring expression, dramatic captivating eyes"},
        {"id": "thoughtful_calm", "label": "💭 Thoughtful & Observant", "prompt": "thoughtful serene gaze looking slightly away from camera, soft contemplative resting expression"},
    ],
    "angles": [
        {"id": "full_body", "label": "📸 Full Body Editorial", "prompt": "full body fashion editorial shot, head to toe framing, standing poised, natural posture, clean perspective"},
        {"id": "medium_shot", "label": "👤 Medium Shot (Waist-Up)", "prompt": "medium shot waist-up portrait, balanced framing capturing wardrobe styling and facial expressions"},
        {"id": "close_up", "label": "🔍 Intimate Close-Up Portrait", "prompt": "intimate close-up portrait, focusing on sharp hazel-green eyes with amber flecks, natural skin pores, crescent freckle, subtle parted lips"},
        {"id": "candid_35mm", "label": "📐 35mm Candid Dynamic", "prompt": "candid 35mm street photography framing, slightly low angle dynamic composition, cinematic depth of field"},
    ],
    "aspect_ratios": [
        {"id": "portrait_2_3", "label": "Portrait (2:3 · 768×1152)", "width": 768, "height": 1152},
        {"id": "vertical_9_16", "label": "Story / Vertical (9:16 · 704×1280)", "width": 704, "height": 1280},
        {"id": "standard_3_4", "label": "Standard (3:4 · 832×1104)", "width": 832, "height": 1104},
        {"id": "square_1_1", "label": "Square (1:1 · 1024×1024)", "width": 1024, "height": 1024},
    ],
}


def build_photo_studio_prompt(person: dict, payload: PhotoStudioPromptIn) -> tuple[str, str]:
    name = person.get("name", "Adult model")
    age = person.get("age", 25)
    shot = payload.angle.strip() or "Raw candid 35mm photograph, full body editorial shot"
    subject = f"{age}yo woman {name}"
    costume = payload.costume.strip() or "designer minimalist swimwear"
    expression = payload.expression.strip() or "confident editorial gaze"
    location = payload.location.strip() or "sunlit Mediterranean terrace"
    custom = f", {payload.custom_direction.strip()}" if payload.custom_direction.strip() else ""

    primary = f"{shot} of {subject}, wearing {costume}, {expression}, {location}{custom}."

    appearance = person.get("appearance", "")
    anchor_bits = []
    if "crescent" in appearance.lower():
        anchor_bits.append("fictional tiny crescent freckle below left eye")
    if "hazel" in appearance.lower() or "green" in appearance.lower():
        anchor_bits.append("hazel-green eyes with amber flecks")
    if "chestnut" in appearance.lower() or "dark" in appearance.lower():
        anchor_bits.append("wavy dark chestnut hair")
    if "cheekbones" in appearance.lower() or "oval" in appearance.lower():
        anchor_bits.append("defined cheekbones, soft oval face")

    anchor_str = (", ".join(anchor_bits) + ".") if anchor_bits else "natural realistic facial features."
    tech_suffix = "Sharp focus on eyes and natural skin pores, natural skin texture, soft diffused golden hour lighting, 8k dslr, photographic masterpiece, 35mm film grain, masterpiece, highly detailed."

    full_prompt = f"{primary} {anchor_str} {tech_suffix}"
    negative_prompt = (
        "anime, cartoon, graphic, 3d render, cgi, illustration, drawing, painting, "
        "stylized, doll, plastic skin, oversaturated, deformed iris, blurry, bad anatomy, "
        "bad hands, missing fingers, extra limbs, extra fingers, watermark, text, signature, "
        "low quality, child, teenager, minor, real-person likeness"
    )
    return full_prompt, negative_prompt


@app.get("/api/photo-studio/presets")
def get_photo_studio_presets():
    return PHOTO_STUDIO_PRESETS


@app.post("/api/photo-studio/compile-prompt")
def compile_photo_studio_prompt(payload: PhotoStudioPromptIn):
    person = must_persona(payload.persona_id)
    prompt, negative_prompt = build_photo_studio_prompt(person, payload)
    return {
        "persona_id": person["id"],
        "persona_name": person["name"],
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "token_estimate": len(prompt.split()),
        "model_id": payload.model_id,
    }


@app.post("/api/photo-studio/generate", status_code=201)
async def photo_studio_generate(payload: PhotoStudioGenerateIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    person = must_persona(payload.persona_id)
    if not payload.rights_confirmed:
        raise HTTPException(400, "Rights confirmation required")
    seed = payload.seed if payload.seed is not None else secrets.randbelow(1_000_000_000)
    version = PersonaRepository.current_version(person["id"])
    job_id, reused = _start_direct_job(
        person=person,
        workflow_id="photo_studio_generation",
        kind="image",
        prompt=payload.prompt,
        payload=payload,
        lineage={"execution_mode": "photo_studio", "persona_version_id": version["id"] if version else None, "model": payload.model, "seed": seed},
        idempotency_key=idempotency_key,
    )
    if reused is not None:
        return reused

    async def run_photo_studio():
        from types import SimpleNamespace
        from .free_cli import make_image

        destination = Path(tempfile.gettempdir()) / f"studio_photo_{job_id}.png"
        args = SimpleNamespace(
            prompt=payload.prompt,
            negative_prompt=payload.negative_prompt or "anime, cartoon, 3d render, illustration, blurry, bad anatomy, plastic skin",
            model=payload.model,
            width=payload.width,
            height=payload.height,
            steps=payload.steps,
            guidance=payload.guidance,
            seed=seed,
            output=str(destination),
            reference=None,
            cpu_offload=False,
            offline=True,
        )
        try:
            await asyncio.to_thread(make_image, args)
            if not destination.is_file():
                raise RuntimeError("Image generation produced no output file")
            raw = destination.read_bytes()
        except Exception as exc:
            logger.exception("photo_studio_generate_failed", extra=_log_data({"persona_id": person.get("id"), "job_id": job_id}))
            raise HTTPException(500, f"Image generation failed: {str(exc)[:300]}") from exc
        finally:
            destination.unlink(missing_ok=True)

        disclosure = person.get("disclosure") or AI_DISCLOSURE
        asset = register_media_asset(
            persona_id=person["id"],
            persona_version_id=version["id"] if version else None,
            job_id=job_id,
            kind="image",
            prompt=payload.prompt,
            raw=raw,
            disclosure=disclosure,
            rights_confirmed=payload.rights_confirmed,
            original_filename="photo_studio.png",
            lineage={"job_id": job_id, "execution_mode": "photo_studio", "seed": seed},
        )
        aid = asset["id"]
        filename = asset["filename"]
        rid = uid()
        label = f"Photo Studio: {payload.prompt[:35]}..."
        content_class = "adult_glamour" if any(term in payload.prompt.lower() for term in ("adult", "boudoir", "lingerie", "glamour", "intimate")) else "identity"
        db.write(
            "INSERT INTO reference_images (id, persona_id, filename, label, created_at, asset_id, persona_version_id, role, content_class, review, rights_confirmed, metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, person["id"], filename, label, now(), aid, version["id"] if version else None, "supporting", content_class, "pending", 1, json.dumps({"source": "photo_studio_generation", "job_id": job_id})),
        )
        return {
            "id": aid,
            "job_id": job_id,
            "reference_id": rid,
            "filename": filename,
            "url": f"/api/assets/{aid}/file",
            "prompt": payload.prompt,
            "negative_prompt": payload.negative_prompt,
            "seed": seed,
            "width": payload.width,
            "height": payload.height,
            "model": payload.model,
            "created_at": now(),
        }

    return await _finish_direct_job(job_id, run_photo_studio)


# =====================================================================
# PERSONA ORCHESTRATION PIPELINE API
# =====================================================================

@app.get("/api/orchestrator/presets")
def orchestrator_presets():
    return orchestrator.get_orchestrator_presets()


@app.get("/api/orchestrator/personas")
def orchestrator_list_personas():
    with db.connection() as con:
        rows = con.execute("SELECT id, name, age, description, appearance, disclosure, characteristics_json, identity_locked, locked_at FROM personas ORDER BY created_at DESC").fetchall()
        personas = []
        for r in rows:
            pid = r[0]
            # Check for locked master anchor in reference_images
            ref_row = con.execute("SELECT id, filename, label FROM reference_images WHERE persona_id = ? AND (label LIKE '%Master%' OR label LIKE '%Anchor%') ORDER BY created_at DESC LIMIT 1", (pid,)).fetchone()
            anchor_info = None
            if ref_row:
                anchor_info = {
                    "id": ref_row[0],
                    "filename": ref_row[1],
                    "label": ref_row[2],
                    "url": f"/api/references/{ref_row[0]}/file"
                }
            try:
                chars = json.loads(r[6]) if r[6] else {}
            except Exception:
                chars = {}
            personas.append({
                "id": pid,
                "name": r[1],
                "age": r[2],
                "description": r[3],
                "appearance": r[4],
                "disclosure": r[5],
                "characteristics": chars,
                "identity_locked": bool(r[7]),
                "locked_at": r[8],
                "master_anchor": anchor_info
            })
        return personas


@app.post("/api/orchestrator/compile-persona-prompt")
def orchestrator_compile_persona(payload: OrchestratorCompilePersonaIn):
    dna = {
        "name": payload.name,
        "age": payload.age,
        "country": payload.country,
        "region": payload.region,
        "facial_identity": payload.facial_identity,
        "body_physics": {
            "body_type": payload.body_type,
            "measurements": payload.measurements,
            "height": payload.height,
            "skin_tone": payload.skin_tone,
            "breast_shape": payload.breast_shape,
        },
        "content_mode": payload.content_mode,
        "aspect_ratio": payload.aspect_ratio,
        "quality": payload.quality,
    }
    return orchestrator.compile_persona_master_prompt(dna)


@app.post("/api/orchestrator/create-persona", status_code=201)
def orchestrator_create_persona(payload: OrchestratorCreatePersonaIn):
    pid = uid()
    chars = {
        "country": payload.country,
        "region": payload.region,
        "facial_identity": payload.facial_identity,
        "body_physics": payload.body_physics,
        "content_mode": payload.content_mode,
        "master_prompt": payload.master_prompt,
        "negative_prompt": payload.negative_prompt,
        "aspect_ratio": payload.aspect_ratio,
        "quality": payload.quality,
    }
    chars_json = json.dumps(chars)
    appearance = f"{payload.country} ({payload.region}), {payload.facial_identity}, {payload.body_physics.get('measurements', '')} {payload.body_physics.get('body_type', '')}"
    description = f"Fictional adult persona {payload.name}, {payload.age}yo from {payload.region}, {payload.country}."
    disclosure = f"Fictional adult persona: {payload.name}. AI-generated synthetic media."

    db.write(
        "INSERT INTO personas (id, name, age, description, appearance, disclosure, created_at, characteristics_json, identity_locked) VALUES (?,?,?,?,?,?,?,?,0)",
        (pid, payload.name, payload.age, description, appearance, disclosure, now(), chars_json)
    )
    return {
        "id": pid,
        "name": payload.name,
        "age": payload.age,
        "country": payload.country,
        "region": payload.region,
        "characteristics": chars,
        "created_at": now()
    }


@app.post("/api/orchestrator/render-anchor", status_code=201)
async def orchestrator_render_anchor(payload: OrchestratorRenderAnchorIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    person = must_persona(payload.persona_id)
    width, height = orchestrator.ASPECT_RATIOS.get(payload.aspect_ratio, (768, 1152))
    seed = payload.seed if payload.seed is not None else secrets.randbelow(1_000_000_000)
    version = PersonaRepository.current_version(person["id"])
    job_id, reused = _start_direct_job(
        person=person,
        workflow_id="orchestrator_anchor_generation",
        kind="image",
        prompt=payload.prompt,
        payload=payload,
        lineage={"execution_mode": "orchestrator_anchor", "persona_version_id": version["id"] if version else None, "model": payload.model, "seed": seed},
        idempotency_key=idempotency_key,
    )
    if reused is not None:
        return reused

    async def run_anchor():
        try:
            dest_path = await asyncio.to_thread(
                orchestrator.generate_orchestrator_image,
                prompt=payload.prompt,
                negative_prompt=payload.negative_prompt,
                model_id=payload.model,
                width=width,
                height=height,
                seed=seed,
                quality=payload.quality,
            )
            raw = dest_path.read_bytes()
        except Exception as exc:
            logger.exception("orchestrator_render_anchor_failed", extra=_log_data({"persona_id": person.get("id"), "job_id": job_id}))
            raise HTTPException(500, f"Master Anchor generation failed: {str(exc)[:300]}") from exc
        finally:
            if "dest_path" in locals():
                dest_path.unlink(missing_ok=True)

        disclosure = person.get("disclosure") or AI_DISCLOSURE
        asset = register_media_asset(
            persona_id=person["id"],
            persona_version_id=version["id"] if version else None,
            job_id=job_id,
            kind="image",
            prompt=payload.prompt,
            raw=raw,
            disclosure=disclosure,
            rights_confirmed=True,
            original_filename=dest_path.name,
            lineage={"job_id": job_id, "execution_mode": "orchestrator_anchor", "seed": seed},
        )
        return {
            "asset_id": asset["id"],
            "job_id": job_id,
            "filename": asset["filename"],
            "url": f"/api/assets/{asset['id']}/file",
            "prompt": payload.prompt,
            "negative_prompt": payload.negative_prompt,
            "seed": seed,
            "width": width,
            "height": height,
            "quality": payload.quality,
            "model": payload.model,
        }

    return await _finish_direct_job(job_id, run_anchor)


@app.post("/api/orchestrator/lock-anchor")
def orchestrator_lock_anchor(payload: OrchestratorLockAnchorIn):
    person = must_persona(payload.persona_id)
    with db.connection() as con:
        asset_row = con.execute("SELECT * FROM assets WHERE id = ? AND persona_id = ?", (payload.asset_id, person["id"])).fetchone()
        if not asset_row:
            raise HTTPException(404, "Asset not found")
        if asset_row["review"] != "approved":
            raise HTTPException(409, "Approve the asset before locking it as a master anchor")
        if not asset_row["rights_confirmed"]:
            raise HTTPException(409, "Master anchor asset is missing rights confirmation")
        asset = dict(asset_row)
        filename = asset["filename"]
    try:
        resolve_asset_file(asset)
    except FileNotFoundError:
        raise HTTPException(404, "Master anchor media file is missing") from None

    rid = uid()
    label = f"Master Persona Anchor: {person['name']}"
    db.write(
        "INSERT INTO reference_images (id, persona_id, filename, label, created_at, asset_id, persona_version_id, role, content_class, review, rights_confirmed, metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, person["id"], filename, label, now(), payload.asset_id, asset["persona_version_id"], "identity_anchor", "identity", "approved", 1, json.dumps({"source": "approved_asset_lock", "asset_id": payload.asset_id})),
    )
    PersonaRepository.freeze(person["id"], now())

    return {
        "status": "locked",
        "persona_id": person["id"],
        "reference_id": rid,
        "filename": filename,
        "url": f"/api/references/{rid}/file",
        "label": label,
    }


@app.post("/api/orchestrator/synthesize-scenes")
def orchestrator_synthesize_scenes(payload: OrchestratorSynthesizeScenesIn):
    person = must_persona(payload.persona_id)
    try:
        chars = json.loads(person.get("characteristics_json") or "{}")
    except Exception:
        chars = {}

    dna = {
        "name": person["name"],
        "age": person["age"],
        "country": chars.get("country", ""),
        "region": chars.get("region", ""),
        "facial_identity": chars.get("facial_identity", person.get("appearance", "")),
        "body_physics": chars.get("body_physics", {}),
        "content_mode": chars.get("content_mode", "adult"),
    }

    result = orchestrator.synthesize_scene_variations(
        persona_dna=dna,
        narrative=payload.narrative,
        category_id=payload.category,
        batch_count=payload.batch_count,
        aspect_ratio=payload.aspect_ratio,
        quality=payload.quality
    )

    if payload.model_override:
        result["model_id"] = payload.model_override
        result["routing_reason"] = f"Manual override to {payload.model_override}"

    return result


@app.post("/api/orchestrator/generate-batch", status_code=201)
async def orchestrator_generate_batch(payload: OrchestratorBatchGenerateIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    person = must_persona(payload.persona_id)
    if not payload.rights_confirmed:
        raise HTTPException(400, "Rights confirmation required")

    width, height = orchestrator.ASPECT_RATIOS.get(payload.aspect_ratio, (768, 1152))
    version = PersonaRepository.current_version(person["id"])
    job_id, reused = _start_direct_job(
        person=person,
        workflow_id="orchestrator_batch_generation",
        kind="image_batch",
        prompt="\n".join(scene.prompt for scene in payload.scenes)[:3000],
        payload=payload,
        lineage={"execution_mode": "orchestrator_batch", "persona_version_id": version["id"] if version else None, "model": payload.model, "scene_count": len(payload.scenes)},
        idempotency_key=idempotency_key,
    )
    if reused is not None:
        return reused

    async def run_batch():
        generated_assets = []
        disclosure = person.get("disclosure") or AI_DISCLOSURE
        for i, scene in enumerate(payload.scenes):
            seed = secrets.randbelow(1_000_000_000)
            dest_path = None
            try:
                dest_path = await asyncio.to_thread(
                    orchestrator.generate_orchestrator_image,
                    prompt=scene.prompt,
                    negative_prompt=scene.negative_prompt,
                    model_id=payload.model,
                    width=width,
                    height=height,
                    seed=seed,
                    quality=payload.quality,
                    steps=payload.steps,
                    guidance=payload.guidance,
                )
                raw = dest_path.read_bytes()
            except Exception as exc:
                logger.exception("orchestrator_batch_scene_failed", extra=_log_data({"persona_id": person.get("id"), "job_id": job_id, "scene_index": i}))
                raise HTTPException(500, f"Generation failed at scene {i+1}: {str(exc)[:300]}") from exc
            finally:
                if dest_path:
                    dest_path.unlink(missing_ok=True)

            asset = register_media_asset(
                persona_id=person["id"],
                persona_version_id=version["id"] if version else None,
                job_id=job_id,
                kind="image",
                prompt=scene.prompt,
                raw=raw,
                disclosure=disclosure,
                rights_confirmed=payload.rights_confirmed,
                original_filename=dest_path.name if dest_path else "orchestrator_batch.png",
                lineage={"job_id": job_id, "execution_mode": "orchestrator_batch", "seed": seed, "scene_index": i},
            )

            generated_assets.append({
                "asset_id": asset["id"],
                "job_id": job_id,
                "filename": asset["filename"],
                "url": f"/api/assets/{asset['id']}/file",
                "title": scene.title,
                "location": scene.location,
                "costume": scene.costume,
                "expression": scene.expression,
                "shot": scene.shot,
                "prompt": scene.prompt,
                "negative_prompt": scene.negative_prompt,
                "seed": seed,
                "width": width,
                "height": height,
                "quality": payload.quality,
                "created_at": now(),
            })

        return {
            "job_id": job_id,
            "persona_id": person["id"],
            "persona_name": person["name"],
            "total_generated": len(generated_assets),
            "assets": generated_assets,
        }

    return await _finish_direct_job(job_id, run_batch)


@app.get("/api/orchestrator/export-json/{persona_id}")
def orchestrator_export_json(persona_id: str):
    person = must_persona(persona_id)
    try:
        chars = json.loads(person.get("characteristics_json") or "{}")
    except Exception:
        chars = {}

    with db.connection() as con:
        ref_row = con.execute("SELECT id, filename, label FROM reference_images WHERE persona_id = ? AND (label LIKE '%Master%' OR label LIKE '%Anchor%') ORDER BY created_at DESC LIMIT 1", (person["id"],)).fetchone()

    payload = {
        "version": "1.0",
        "name": person["name"],
        "age": person["age"],
        "demographics": {
            "country": chars.get("country", ""),
            "region": chars.get("region", ""),
        },
        "facial_identity": chars.get("facial_identity", person.get("appearance", "")),
        "body_physics": chars.get("body_physics", {}),
        "content_mode": chars.get("content_mode", "adult"),
        "master_prompt": chars.get("master_prompt", ""),
        "negative_prompt": chars.get("negative_prompt", ""),
        "aspect_ratio": chars.get("aspect_ratio", "2:3"),
        "quality": chars.get("quality", "4K"),
        "master_anchor_file": ref_row[1] if ref_row else None,
        "exported_at": now()
    }
    return JSONResponse(content=payload, headers={"Content-Disposition": f'attachment; filename="persona_{person["name"].lower().replace(" ", "_")}.json"'})


@app.post("/api/orchestrator/import-json", status_code=201)
async def orchestrator_import_json(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(400, "Invalid JSON payload") from exc

    name = body.get("name") or "Imported Persona"
    age = int(body.get("age", 23))
    demographics = body.get("demographics", {})
    country = demographics.get("country") or body.get("country") or "Germany"
    region = demographics.get("region") or body.get("region") or "Bavaria"
    facial = body.get("facial_identity") or body.get("appearance") or ""
    body_phys = body.get("body_physics") or {}

    chars = {
        "country": country,
        "region": region,
        "facial_identity": facial,
        "body_physics": body_phys,
        "content_mode": body.get("content_mode", "adult"),
        "master_prompt": body.get("master_prompt", ""),
        "negative_prompt": body.get("negative_prompt", ""),
        "aspect_ratio": body.get("aspect_ratio", "2:3"),
        "quality": body.get("quality", "4K"),
    }

    pid = uid()
    appearance = f"{country} ({region}), {facial}, {body_phys.get('measurements', '')} {body_phys.get('body_type', '')}"
    description = f"Imported fictional persona {name}, {age}yo from {region}, {country}."
    disclosure = f"Fictional adult persona: {name}. AI-generated synthetic media."

    db.write(
        "INSERT INTO personas (id, name, age, description, appearance, disclosure, created_at, characteristics_json, identity_locked) VALUES (?,?,?,?,?,?,?,?,0)",
        (pid, name, age, description, appearance, disclosure, now(), json.dumps(chars))
    )

    return {
        "id": pid,
        "name": name,
        "age": age,
        "country": country,
        "region": region,
        "characteristics": chars,
        "status": "imported",
        "created_at": now()
    }


