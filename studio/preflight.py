"""Read-only render preflight checks used before queueing a job."""

from __future__ import annotations

import json
import shutil
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from . import database as db
from .engines import supports as engine_supports
from .model_registry import get as get_model, is_installed, match as match_model
from .settings import get_settings

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
    """Best-effort GPU memory probe (CUDA or Apple Silicon unified memory)."""
    try:
        if importlib.util.find_spec("torch") is None:
            return None
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            import subprocess
            res = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return round(int(res.stdout.strip()) / (1024 ** 3), 1)
        return None
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
        checks.append({"id": "model_vram", "status": "warning", "detail": f"Need at least {required} GiB VRAM; GPU memory could not be detected", "required_vram_gb": required})
    elif required and actual < required:
        checks.append({"id": "model_vram", "status": "error", "detail": f"Detected {actual:.1f} GiB memory; model requires at least {required} GiB", "required_vram_gb": required, "vram_gb": actual})
    elif required:
        checks.append({"id": "model_vram", "status": "ready", "detail": f"Detected {actual:.1f} GiB unified/GPU memory (minimum {required} GiB)", "required_vram_gb": required, "vram_gb": actual})
    return checks


def _memory_snapshot() -> tuple[int | None, int | None]:
    """Best-effort total/available system memory without adding a dependency."""

    total = available = None
    try:
        import psutil  # Optional when already present; never installed by preflight.
        memory = psutil.virtual_memory()
        return int(memory.total), int(memory.available)
    except Exception:
        pass
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total_pages = int(os.sysconf("SC_PHYS_PAGES"))
        available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        total = page_size * total_pages
        available = page_size * available_pages
    except (AttributeError, OSError, ValueError):
        pass
    if sys.platform == "darwin":
        try:
            result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                total = int(result.stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return total, available


def resource_preflight(workflow_id: str | None = None, width: int | None = None,
                       height: int | None = None, task: str | None = None):
    """Estimate local disk/memory pressure before a generation Job is queued."""

    settings = get_settings()
    width = max(1, int(width or 768))
    height = max(1, int(height or 1152))
    label = (task or workflow_id or "image").lower()
    kind = "video" if any(token in label for token in ("video", "wan", "motion")) else "audio" if any(token in label for token in ("audio", "voice", "narration")) else "image"
    frames = settings.job_video_frames if kind == "video" else 1
    pixels = width * height
    # This is intentionally conservative and model-agnostic. The actual model
    # may require more; model-specific VRAM checks remain a separate gate.
    estimated_output_bytes = max(
        8 * 1024 * 1024,
        pixels * 4 * frames * (2 if kind == "video" else 1),
    )
    estimated_working_set_gb = {
        "image": 4.0,
        "video": 6.0,
        "audio": 3.0,
    }[kind] + min(2.0, (pixels / 1_000_000) * 0.5)
    try:
        usage = shutil.disk_usage(db.DATA)
        free_gb = usage.free / (1024 ** 3)
        required_disk_gb = settings.job_min_free_disk_gb + (estimated_output_bytes / (1024 ** 3)) + settings.job_resource_margin_gb
        disk_ok = free_gb >= required_disk_gb
        disk_status = "ready" if disk_ok else "error"
        disk_detail = f"{free_gb:.1f} GiB free; estimated job need {required_disk_gb:.1f} GiB including safety margin"
        disk_check = {"id": "resource_disk", "status": disk_status, "detail": disk_detail,
                      "free_gb": round(free_gb, 2), "required_gb": round(required_disk_gb, 2),
                      "estimated_output_gb": round(estimated_output_bytes / (1024 ** 3), 3), "kind": kind}
    except OSError as exc:
        disk_check = {"id": "resource_disk", "status": "error", "detail": str(exc)[:200], "kind": kind}

    total_bytes, available_bytes = _memory_snapshot()
    required_memory_gb = min(settings.job_memory_budget_gb, estimated_working_set_gb + settings.job_resource_margin_gb)
    if total_bytes is None:
        memory_check = {"id": "resource_memory", "status": "warning", "detail": "System memory could not be measured; run a smaller job or verify free memory before generation", "required_gb": round(required_memory_gb, 2), "kind": kind}
    else:
        total_gb = total_bytes / (1024 ** 3)
        available_gb = available_bytes / (1024 ** 3) if available_bytes is not None else None
        capacity_ok = total_gb >= required_memory_gb and (available_gb is None or available_gb >= required_memory_gb)
        memory_check = {
            "id": "resource_memory",
            "status": "ready" if capacity_ok else "error",
            "detail": f"{available_gb:.1f} GiB available of {total_gb:.1f} GiB total; estimated job need {required_memory_gb:.1f} GiB" if available_gb is not None else f"{total_gb:.1f} GiB total; estimated job need {required_memory_gb:.1f} GiB",
            "total_gb": round(total_gb, 2),
            "available_gb": round(available_gb, 2) if available_gb is not None else None,
            "required_gb": round(required_memory_gb, 2),
            "kind": kind,
        }
    return [disk_check, memory_check]


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
    elif backend == "direct-cli":
        checks.append({"id": "workflow", "status": "ready", "detail": f"Direct CLI workflow '{workflow_id}' engine ready"})
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

    checks.extend(resource_preflight(workflow_id=workflow_id, width=width, height=height, task=task))

    if task and ("audio" in task or "assembly" in task or "video" in task):
        ffmpeg = shutil.which("ffmpeg")
        checks.append({"id": "ffmpeg", **check(bool(ffmpeg), ffmpeg or "FFmpeg is not on PATH")})
    return checks

# End of read-only preflight helpers.
__all__ = ["resource_preflight", "workflow_preflight"]
