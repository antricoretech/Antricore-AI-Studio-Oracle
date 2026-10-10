"""Read-only render preflight checks used before queueing a job."""

from __future__ import annotations

import json
import shutil
import importlib.util
from pathlib import Path

from . import database as db
from .engines import supports as engine_supports
from .model_registry import get as get_model, is_installed, match as match_model

ROOT = Path(__file__).resolve().parents[1]


def check(ok: bool, detail: str, **extra):
    return {"status": "ready" if ok else "warning", "detail": detail, **extra}


def _catalog_item(workflow_id: str | None):
    if not workflow_id:
        return None
    try:
        catalog = json.loads((ROOT / "config" / "workflow_catalog.json").read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError):
        return None
    return next((item for item in catalog if isinstance(item, dict) and item.get("id") == workflow_id), None)


def _runtime_vram_gb() -> float | None:
    """Best-effort CUDA memory probe; absent CUDA is reported as unknown."""
    try:
        if importlib.util.find_spec("torch") is None:
            return None
        import torch
        if not torch.cuda.is_available():
            return None
        return round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
    except Exception:
        return None


def _model_checks(model_id: str | None, task: str | None, backend: str | None):
    if not model_id or model_id in {"custom", "ffmpeg"}:
        return []
    metadata = get_model(model_id)
    if not metadata:
        return [{"id": "model", "status": "error", "detail": f"Model '{model_id}' is not in the approved registry"}]
    ok, detail = match_model(model_id, task=task, backend=backend)
    checks = [{"id": "model_capability", "status": "ready" if ok else "error", "detail": detail,
               "model": model_id, "task": task, "backend": backend}]
    installed = is_installed(metadata["id"])
    checks.append({"id": "model_weights", **check(bool(installed), "Local weights directory detected" if installed else "Weights not downloaded", model=model_id, path=str(ROOT / "models" / model_id))})
    revision = metadata.get("revision")
    checks.append({"id": "model_revision", "status": "ready" if revision else "warning", "detail": f"Pinned revision {revision}" if revision else "Registry revision is unpinned; record a commit or tag before production", "model": model_id})
    required = metadata.get("min_vram_gb")
    actual = _runtime_vram_gb()
    if required and actual is None:
        checks.append({"id": "model_vram", "status": "warning", "detail": f"Need at least {required} GiB VRAM; CUDA memory could not be detected", "required_vram_gb": required})
    elif required and actual < required:
        checks.append({"id": "model_vram", "status": "error", "detail": f"Detected {actual:.1f} GiB VRAM; model requires at least {required} GiB", "required_vram_gb": required, "vram_gb": actual})
    elif required:
        checks.append({"id": "model_vram", "status": "ready", "detail": f"Detected {actual:.1f} GiB VRAM (minimum {required} GiB)", "required_vram_gb": required, "vram_gb": actual})
    return checks


def workflow_preflight(workflow_id: str | None = None, model_id: str | None = None,
                       task: str | None = None, width: int | None = None,
                       height: int | None = None):
    checks = []
    try:
        usage = shutil.disk_usage(db.DATA)
        checks.append({"id": "storage", **check(usage.free > 10 * 1024 ** 3, f"{usage.free / (1024 ** 3):.1f} GiB free", free_gb=round(usage.free / (1024 ** 3), 2))})
    except OSError as exc:
        checks.append({"id": "storage", "status": "error", "detail": str(exc)[:200]})

    catalog_item = _catalog_item(workflow_id)
    if not model_id and catalog_item:
        model_id = catalog_item.get("model")
    if not task and catalog_item:
        task = catalog_item.get("task")
    backend = catalog_item.get("backend") if catalog_item else None

    if backend and not engine_supports(backend, catalog_item.get("category") if catalog_item else None):
        checks.append({"id": "engine", "status": "error", "detail": f"Unknown or incompatible render backend '{backend}'"})

    if not workflow_id:
        checks.append({"id": "workflow", **check(False, "Select a workflow to validate its placeholders")})
    else:
        if not workflow_id.replace("_", "").replace("-", "").isalnum():
            checks.append({"id": "workflow", "status": "error", "detail": "Invalid workflow id"})
        else:
            locations = [db.WORKFLOWS / f"{workflow_id}.json", Path(__file__).resolve().parents[1] / "workflows" / f"{workflow_id}.json"]
            path = next((item for item in locations if item.is_file()), None)
            if not path:
                checks.append({"id": "workflow", "status": "error", "detail": "Workflow graph is not installed"})
            else:
                try:
                    graph = json.loads(path.read_text(encoding="utf8"))
                    node_count = len(graph) if isinstance(graph, dict) else 0
                    checks.append({"id": "workflow", **check(node_count > 0, f"Verified graph with {node_count} node(s)", path=str(path), nodes=node_count)})
                except (OSError, json.JSONDecodeError) as exc:
                    checks.append({"id": "workflow", "status": "error", "detail": f"Cannot read graph: {exc}"})

    checks.extend(_model_checks(model_id, task, backend))
    if width and height:
        multiple = 16 if task and task.startswith("video.") else 8
        valid = width % multiple == 0 and height % multiple == 0
        checks.append({"id": "canvas", "status": "ready" if valid else "error",
                       "detail": f"{width}x{height} matches {multiple}px alignment" if valid else f"Width and height must be multiples of {multiple} for {task or 'this workflow'}",
                       "width": width, "height": height, "multiple": multiple})

    ffmpeg = shutil.which("ffmpeg")
    checks.append({"id": "ffmpeg", **check(bool(ffmpeg), ffmpeg or "FFmpeg is not on PATH")})
    return checks

