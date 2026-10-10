"""Approved model inventory and capability matching.

The registry is intentionally declarative.  It describes public model metadata
and local installation expectations, while never downloading or executing a
model.  Renderers can use this module to decide whether a workflow is a
reasonable fit before a GPU job is queued.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "approved_models.json"
MODEL_ROOT = ROOT / "models"


def load_registry() -> dict[str, dict]:
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def model_path(model_id: str) -> Path:
    return MODEL_ROOT / model_id


def is_installed(model_id: str) -> bool:
    directory = model_path(model_id)
    try:
        return directory.is_dir() and any(directory.iterdir())
    except OSError:
        return False


def runtime_status(model_id: str, metadata: dict) -> tuple[str, str]:
    if model_id == "ffmpeg":
        executable = shutil.which("ffmpeg")
        return ("ready", executable or "FFmpeg found on PATH") if executable else ("warning", "FFmpeg is not on PATH")
    if is_installed(model_id):
        return "ready", "Local weights directory detected"
    return "warning", "Weights not downloaded"


def rows() -> list[dict]:
    """Return safe, UI-ready inventory rows without exposing secrets."""
    result = []
    for model_id, metadata in load_registry().items():
        status, detail = runtime_status(model_id, metadata)
        revision = metadata.get("revision")
        if status == "ready" and not revision:
            status = "warning"
            detail += "; registry revision is unpinned"
        revision = metadata.get("revision")
        result.append({
            "id": model_id,
            "label": metadata.get("label") or metadata.get("role") or model_id,
            "status": status,
            "detail": detail,
            "path": str(model_path(model_id)),
            "hf": metadata.get("hf", ""),
            "github": metadata.get("github", ""),
            "license": metadata.get("license", "verify model card"),
            "license_url": metadata.get("license_url", ""),
            "role": metadata.get("role", ""),
            "gpu": metadata.get("gpu", "hardware dependent"),
            "min_vram_gb": metadata.get("min_vram_gb"),
            "recommended_vram_gb": metadata.get("recommended_vram_gb"),
            "capabilities": metadata.get("capabilities", []),
            "backends": metadata.get("backends", []),
            "revision": revision,
            "revision_pinned": bool(revision),
            "status_policy": metadata.get("status", "approved"),
            "default": bool(metadata.get("default", False)),
        })
    return result


def get(model_id: str | None) -> dict | None:
    if not model_id:
        return None
    metadata = load_registry().get(model_id)
    if metadata is None:
        return None
    return {"id": model_id, **metadata}


def match(model_id: str, task: str | None = None, backend: str | None = None) -> tuple[bool, str]:
    metadata = get(model_id)
    if not metadata:
        return False, f"Model '{model_id}' is not in the approved registry"
    if backend and backend not in metadata.get("backends", []):
        return False, f"Model '{model_id}' does not support the {backend} backend"
    if task and task not in metadata.get("capabilities", []):
        return False, f"Model '{model_id}' does not advertise capability '{task}'"
    return True, "Capability match confirmed"


def candidates(task: str | None = None, backend: str | None = None) -> list[dict]:
    result = []
    for item in rows():
        if task and task not in item.get("capabilities", []):
            continue
        if backend and backend not in item.get("backends", []):
            continue
        result.append(item)
    return result


def workflow_model(workflow: dict) -> tuple[str | None, str | None, str | None]:
    """Extract model, backend and capability from a catalog/workflow row."""
    category = workflow.get("category")
    task = workflow.get("task")
    if not task:
        task = {"image": "image.text_to_image", "video": "video.image_to_video", "audio": "audio.text_to_speech"}.get(category)
    return workflow.get("model"), workflow.get("backend"), task
