"""VS Code runnable control panel for ComfyUI-based fictional influencer creation.

Local-first by default. Configure ``STUDIO_AUTH_TOKEN`` before binding outside
loopback or using a shared cloud worker.
"""
from __future__ import annotations

import asyncio
from io import BytesIO
import importlib.util
import json
import os
import re
import secrets
import shutil
import sys
import uuid
import logging
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_CATALOG = ROOT / "config" / "workflow_catalog.json"
DEFAULT_WORKFLOW_LABELS = {
    "default_image_api": ("Default image API · checkpoint", "Built-in ComfyUI API starter graph; choose an installed checkpoint before queueing."),
    "wan22_ti2v_5b_default_api": ("Wan2.2 TI2V 5B · default image-to-video API", "Built-in official-style Wan2.2 TI2V graph; requires the matching diffusion model, text encoder and VAE."),
}
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from . import database as db
from .brief import PersonaBrief, PersonaCharacteristics, brief_dict, parse_brief_bytes, parse_persona_bytes
from .comfy import ComfyClient, output_files, render_graph, validate_graph
from .engines import get as get_engine, rows as engine_rows
from .media import extension_for, read_limited, validate_image_bytes, validate_media_signature
from .model_registry import get as get_model, rows as model_rows, workflow_model
from .policies import AI_DISCLOSURE
from .preflight import workflow_preflight
from .provenance import manifest, media_metadata, quality_report, sha256_bytes
from .repositories import JobRepository, PersonaRepository, SeriesRepository
from .schemas import JobIn, LinkIn, PersonaIn, ReviewIn, SeriesEpisodeIn, SeriesIn, SeriesQueueIn, VoiceIn
from .settings import get_settings

logger = logging.getLogger("studio")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uid():
    return uuid.uuid4().hex


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    app.state.job_tasks = set()
    app.state.job_task_map = {}
    logger.info("studio_started", extra={"data_dir": str(db.DATA)})
    try:
        yield
    finally:
        tasks = list(getattr(app.state, "job_tasks", set()))
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("studio_stopped", extra={"cancelled_tasks": len(tasks)})

app = FastAPI(title="AI Influencer Studio", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


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
    if not person.get("identity_locked"):
        db.write("UPDATE personas SET identity_locked=1, identity_version=MAX(identity_version, 1), locked_at=? WHERE id=?", (now(), pid))
    return persona_response(db.row("SELECT * FROM personas WHERE id=?", (pid,)))


@app.get("/api/personas/{pid}/references")
def list_references(pid: str):
    return db.all_rows("SELECT id, persona_id, label, created_at FROM reference_images WHERE persona_id=? ORDER BY created_at DESC", (pid,))


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
    sid = uid()
    episodes = []
    for index, episode in enumerate(payload.episodes, start=1):
        prompt = f"{payload.shared_prompt.strip()}\nEpisode direction: {episode.prompt.strip()}"
        video_prompt = f"{payload.shared_prompt.strip()}\nEpisode motion: {episode.video_prompt.strip()}"
        episodes.append((uid(), index, episode.title.strip(), prompt, video_prompt, now()))
    SeriesRepository.create(series_id=sid, persona_id=person["id"], title=payload.title.strip(),
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
    if not payload.reference_id:
        latest = db.row("SELECT id, 'reference' AS source, created_at FROM reference_images WHERE persona_id=? UNION ALL SELECT id, 'asset' AS source, created_at FROM assets WHERE persona_id=? AND kind='image' AND review='approved' ORDER BY created_at DESC LIMIT 1", (row["persona_id"], row["persona_id"]))
        if latest:
            if latest["source"] == "reference":
                payload.reference_id = latest["id"]
            else:
                payload.source_asset_id = latest["id"]
    job = JobIn(persona_id=row["persona_id"], workflow_id=payload.workflow_id, checkpoint=payload.checkpoint,
                reference_id=payload.reference_id, source_asset_id=payload.source_asset_id, audio_asset_id=payload.audio_asset_id,
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
    rid = uid()
    filename = rid + extension
    (db.UPLOADS / filename).write_bytes(raw)
    db.write("INSERT INTO reference_images VALUES (?,?,?,?,?)", (rid, pid, filename, label[:100], now()))
    return {"id": rid, "label": label, "url": f"/api/references/{rid}/file"}


@app.get("/api/references/{rid}/file")
def reference_file(rid: str):
    row = db.row("SELECT filename FROM reference_images WHERE id=?", (rid,))
    if not row:
        raise HTTPException(404)
    return FileResponse(db.UPLOADS / row["filename"])


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


async def execute_job(job_id, payload: JobIn, person: dict):
    try:
        db.write("UPDATE jobs SET status='running', updated_at=? WHERE id=?", (now(), job_id))
        logger.info("job_started", extra={"data": {"job_id": job_id, "persona_id": person.get("id"), "workflow_id": payload.workflow_id}})
        graph = json.loads(workflow_path(payload.workflow_id).read_text(encoding="utf8"))
        creative_prompt = payload.video_prompt if (payload.video_prompt and ("video" in payload.workflow_id.lower() or "wan" in payload.workflow_id.lower())) else payload.prompt
        profile_text = persona_characteristics_text(person)
        values = {"PROMPT": f"Fictional adult character {person['name']} ({person['age']} years old), {person['appearance']}. {person['description']}. {profile_text} {creative_prompt}",
                  "NEGATIVE_PROMPT": payload.negative_prompt, "CHECKPOINT": payload.checkpoint,
                  "WIDTH": payload.width, "HEIGHT": payload.height, "SEED": payload.seed,
                  "REFERENCE_IMAGE": "", "AUDIO_FILENAME": ""}
        async with ComfyClient() as client:
            if payload.reference_id or payload.source_asset_id:
                if payload.reference_id:
                    ref = db.row("SELECT * FROM reference_images WHERE id=? AND persona_id=?", (payload.reference_id, payload.persona_id))
                    if not ref:
                        raise ValueError("Reference does not belong to this persona")
                    content = (db.UPLOADS / ref["filename"]).read_bytes()
                    filename = ref["filename"]
                else:
                    source = db.row("SELECT * FROM assets WHERE id=? AND persona_id=?", (payload.source_asset_id, payload.persona_id))
                    if not source or source["kind"] != "image":
                        raise ValueError("Source asset not found or is not an image")
                    content = (db.OUTPUTS / source["filename"]).read_bytes()
                    filename = source["filename"]
                values["REFERENCE_IMAGE"] = await client.upload_reference(content, filename)
            if payload.audio_asset_id:
                audio = db.row("SELECT * FROM assets WHERE id=? AND persona_id=? AND kind='audio'", (payload.audio_asset_id, payload.persona_id))
                if not audio:
                    raise ValueError("Selected audio asset does not belong to this persona")
                values["AUDIO_FILENAME"] = await client.upload_audio((db.OUTPUTS / audio["filename"]).read_bytes(), audio["filename"])
            graph = render_graph(graph, values)
            prompt_id = await client.submit(graph)
            db.write("UPDATE jobs SET status='submitted', comfy_prompt_id=?, updated_at=? WHERE id=?", (prompt_id, now(), job_id))
            outputs = await asyncio.wait_for(client.wait(prompt_id), timeout=get_settings().job_timeout_seconds)
            files = output_files(outputs)
            if not files:
                raise RuntimeError("Workflow completed but no SaveImage / SaveVideo or compatible output was detected")
            for item in files[:20]:
                content = await client.download(item)
                if len(content) > get_settings().output_max_bytes:
                    raise ValueError("Generated output exceeds 200MB safety limit")
                ext = Path(item["filename"]).suffix.lower()
                if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm", ".wav", ".mp3", ".flac"}:
                    continue
                aid = uid()
                dest = aid + ext
                (db.OUTPUTS / dest).write_bytes(content)
                kind = "video" if ext in {".mp4", ".webm", ".gif"} else "audio" if ext in {".wav", ".mp3", ".flac"} else "image"
                disclosure = person.get("disclosure") or AI_DISCLOSURE
                metadata = media_metadata(content, kind, dest)
                quality = quality_report(db.OUTPUTS / dest, kind, disclosure, lineage={"job_id": job_id})
                db.write("INSERT INTO assets (id,persona_id,job_id,filename,kind,prompt,rights_confirmed,disclosure,created_at,sha256,metadata_json,quality_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (aid, person["id"], job_id, dest, kind, payload.prompt, 1, disclosure, now(), sha256_bytes(content), json.dumps(metadata), json.dumps(quality)))
            db.write("UPDATE jobs SET status='completed', finished_at=?, updated_at=? WHERE id=?", (now(), now(), job_id))
            db.write("UPDATE series_episodes SET status='completed' WHERE job_id=?", (job_id,))
            logger.info("job_completed", extra={"data": {"job_id": job_id, "outputs": len(files)}})
    except Exception as e:
        logger.exception("job_failed", extra={"data": {"job_id": job_id}})
        db.write("UPDATE jobs SET status='failed', error=?, finished_at=?, updated_at=? WHERE id=?", (str(e)[:1500], now(), now(), job_id))
        db.write("UPDATE series_episodes SET status='failed' WHERE job_id=?", (job_id,))


@app.post("/api/jobs", status_code=202)
async def create_job(payload: JobIn):
    person = must_persona(payload.persona_id)
    if not payload.rights_confirmed:
        raise HTTPException(400, "Confirm all inputs and likeness rights before starting generation")
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
    jid = uid()
    category = "video" if "video" in payload.workflow_id.lower() or "wan" in payload.workflow_id.lower() else "image"
    try:
        request_json = payload.model_dump_json()
    except AttributeError:  # Pydantic v1 compatibility for older local installs.
        request_json = payload.json()
    created = now()
    lineage = {
        "persona_id": person["id"],
        "persona_version": person.get("identity_version", 1),
        "workflow_id": payload.workflow_id,
        "checkpoint": payload.checkpoint,
        "reference_id": payload.reference_id,
        "source_asset_id": payload.source_asset_id,
        "audio_asset_id": payload.audio_asset_id,
        "seed": payload.seed,
        "width": payload.width,
        "height": payload.height,
    }
    JobRepository.create(job_id=jid, persona_id=person["id"], workflow_id=payload.workflow_id,
                         kind=category, prompt=payload.prompt, request_json=request_json,
                         lineage_json=json.dumps(lineage, separators=(",", ":")), created_at=created)
    _job_task(jid, payload, person)
    logger.info("job_queued", extra={"data": {"job_id": jid, "persona_id": person["id"], "workflow_id": payload.workflow_id}})
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


def _job_task(job_id: str, payload: JobIn, person: dict):
    task = asyncio.create_task(execute_job(job_id, payload, person), name=f"studio-job-{job_id}")
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
    task.add_done_callback(finished)
    return task


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = db.row("SELECT id,status FROM jobs WHERE id=?", (job_id,))
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] in {"completed", "failed", "cancelled"}:
        raise HTTPException(409, f"Job is already {job['status']}")
    db.write("UPDATE jobs SET status='cancelled', cancel_requested=1, finished_at=?, updated_at=?, error=? WHERE id=?",
             (now(), now(), "Cancelled by operator", job_id))
    task = getattr(app.state, "job_task_map", {}).get(job_id)
    if task and not task.done():
        task.cancel()
    logger.info("job_cancelled", extra={"data": {"job_id": job_id}})
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
    db.write("UPDATE jobs SET status='queued', attempt=?, cancel_requested=0, error=NULL, finished_at=NULL, updated_at=? WHERE id=?",
             (attempt, now(), job_id))
    _job_task(job_id, payload, person)
    logger.info("job_retried", extra={"data": {"job_id": job_id, "attempt": attempt}})
    return {"id": job_id, "status": "queued", "attempt": attempt}


@app.get("/api/jobs")
def get_jobs():
    rows = db.all_rows("SELECT jobs.*,personas.name AS persona_name FROM jobs JOIN personas ON personas.id=jobs.persona_id ORDER BY jobs.created_at DESC LIMIT 100")
    for item in rows:
        try:
            item["lineage"] = json.loads(item.pop("lineage_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            item["lineage"] = {}
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
    try:
        raw = await read_limited(file, get_settings().asset_max_bytes)
        suffix = extension_for(kind, file.filename or "")
        if kind == "image":
            # Images are always decoded so a renamed executable cannot enter the media vault.
            suffix = validate_image_bytes(raw)
        else:
            validate_media_signature(raw, kind, strict=get_settings().strict_media_validation)
    except ValueError as exc:
        raise HTTPException(413 if "exceeds" in str(exc) else 400, str(exc)) from exc
    aid = uid()
    destination = aid + suffix
    db.OUTPUTS.mkdir(parents=True, exist_ok=True)
    (db.OUTPUTS / destination).write_bytes(raw)
    disclosure = disclosure.strip()[:300]
    metadata = media_metadata(raw, kind, destination)
    quality = quality_report(db.OUTPUTS / destination, kind, disclosure)
    db.write("INSERT INTO assets (id,persona_id,job_id,filename,kind,prompt,rights_confirmed,disclosure,created_at,sha256,metadata_json,quality_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
             (aid, person["id"], None, destination, kind, prompt.strip()[:3000], 1, disclosure, now(), sha256_bytes(raw), json.dumps(metadata), json.dumps(quality)))
    return {"id": aid, "kind": kind, "review": "pending", "url": f"/api/assets/{aid}/file"}


@app.get("/api/assets/{aid}/file")
def asset_file(aid: str):
    asset = db.row("SELECT filename FROM assets WHERE id=?", (aid,))
    if not asset:
        raise HTTPException(404, "Asset not found")
    return FileResponse(db.OUTPUTS / asset["filename"])


def _asset_bundle(aid: str):
    asset = db.row("SELECT * FROM assets WHERE id=?", (aid,))
    if not asset:
        raise HTTPException(404, "Asset not found")
    job = db.row("SELECT * FROM jobs WHERE id=?", (asset.get("job_id"),)) if asset.get("job_id") else None
    person = db.row("SELECT * FROM personas WHERE id=?", (asset["persona_id"],))
    quality = quality_report(db.OUTPUTS / asset["filename"], asset["kind"], asset.get("disclosure") or AI_DISCLOSURE,
                             lineage={"job_id": asset.get("job_id")} if asset.get("job_id") else None,
                             expected_sha256=asset.get("sha256"))
    return asset, job, person, quality


@app.get("/api/assets/{aid}/manifest")
def asset_manifest(aid: str):
    asset, job, person, quality = _asset_bundle(aid)
    return manifest(asset, job=job, persona=person, quality=quality)


@app.get("/api/assets/{aid}/quality")
def asset_quality(aid: str):
    _asset, _job, _person, quality = _asset_bundle(aid)
    return quality


@app.get("/api/assets/{aid}/package")
def asset_package(aid: str):
    asset, job, person, quality = _asset_bundle(aid)
    if asset["review"] != "approved":
        raise HTTPException(409, "Approve the asset before exporting a package")
    if quality["status"] == "error":
        raise HTTPException(409, "Quality checks found an integrity error; resolve it before export")
    payload = manifest(asset, job=job, persona=person, quality=quality)
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(asset["filename"], (db.OUTPUTS / asset["filename"]).read_bytes())
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
    if payload.review == "approved":
        asset, job, _person, quality = _asset_bundle(aid)
        if quality["status"] == "error":
            raise HTTPException(409, "Quality checks found an integrity error; inspect the asset before approving")
        db.write("UPDATE assets SET review=?, quality_json=? WHERE id=?", (payload.review, json.dumps(quality), aid))
        return {"id": aid, "review": payload.review, "quality": quality}
    db.write("UPDATE assets SET review=? WHERE id=?", (payload.review, aid))
    return {"id": aid, "review": payload.review}


@app.post("/api/voice", status_code=202)
async def create_voice(payload: VoiceIn):
    person = must_persona(payload.persona_id)
    aid = uid()
    destination = db.OUTPUTS / (aid + ".wav")
    from .voice import synthesize
    try:
        await asyncio.to_thread(synthesize, payload.text, payload.voice, destination)
    except Exception as e:
        raise HTTPException(503, f"Voice generation unavailable: {str(e)[:250]}") from e
    raw = destination.read_bytes()
    disclosure = person.get("disclosure") or AI_DISCLOSURE
    metadata = media_metadata(raw, "audio", aid + ".wav")
    quality = quality_report(destination, "audio", disclosure)
    db.write("INSERT INTO assets (id,persona_id,job_id,filename,kind,prompt,rights_confirmed,disclosure,created_at,sha256,metadata_json,quality_json) VALUES (?,?,NULL,?,?,?,?,?,?,?,?,?)",
             (aid, person["id"], aid + ".wav", "audio", payload.text, 1, disclosure, now(), sha256_bytes(raw), json.dumps(metadata), json.dumps(quality)))
    return {"id": aid, "url": f"/api/assets/{aid}/file"}


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
