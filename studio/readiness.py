"""Deployment readiness policy built on top of the read-only monitor snapshot."""

from __future__ import annotations

import os


def _items(snapshot: dict, key: str) -> dict[str, dict]:
    return {str(item.get("id")): item for item in snapshot.get(key, []) if isinstance(item, dict)}


def evaluate(snapshot: dict, profile: str = "local", required_models: list[str] | None = None) -> dict:
    """Convert monitor warnings into explicit deployment blockers.

    Local development tolerates absent GPU/model files.  The cloud profile is
    intentionally stricter and requires authentication, CUDA, FFmpeg and the
    selected model weights to be ready.  No inference is started here.
    """
    profile = profile if profile in {"local", "cloud"} else "local"
    required = required_models
    if required is None:
        raw = os.getenv("STUDIO_REQUIRED_MODELS", "")
        required = [item.strip() for item in raw.split(",") if item.strip()]
    if profile == "cloud" and not required:
        required = ["flux2-klein-4b", "wan22-ti2v-5b"]

    blockers: list[dict] = []
    warnings: list[dict] = []

    def require(condition: bool, code: str, detail: str, **extra):
        target = blockers if not condition else warnings
        target.append({"code": code, "detail": detail, **extra}) if not condition else None

    security = snapshot.get("security", {})
    if profile == "cloud":
        require(security.get("status") == "ready", "auth", "STUDIO_AUTH_TOKEN must be configured for cloud use")
    elif security.get("status") != "ready":
        warnings.append({"code": "auth", "detail": "Authentication is disabled; keep local profile on loopback or use an SSH tunnel"})

    runtime = _items(snapshot, "runtime")
    if profile == "cloud":
        gpu = runtime.get("gpu", {})
        ffmpeg = runtime.get("ffmpeg", {})
        require(gpu.get("status") == "ready", "cuda", gpu.get("detail", "CUDA GPU is not ready"))
        require(ffmpeg.get("status") == "ready", "ffmpeg", ffmpeg.get("detail", "FFmpeg is not ready"))

    models = _items(snapshot, "models")
    for model_id in required:
        model = models.get(model_id)
        if not model:
            blockers.append({"code": "model_missing", "detail": f"Required model is not in the monitor inventory: {model_id}", "model": model_id})
            continue
        require(model.get("status") == "ready", "model_weights", f"Required model is not ready: {model.get('detail', model_id)}", model=model_id)
        require(bool(model.get("revision_pinned")), "model_revision", f"Required model revision is unpinned: {model_id}", model=model_id)

    for key in ("api", "database", "storage"):
        item = snapshot.get(key, {})
        if profile == "cloud":
            require(item.get("status") == "ready", key, item.get("detail", f"{key} is not ready"))
        elif item.get("status") == "error":
            blockers.append({"code": key, "detail": item.get("detail", f"{key} check failed")})

    status = "blocked" if blockers else "warning" if warnings or snapshot.get("overall", {}).get("status") == "degraded" else "ready"
    return {
        "profile": profile,
        "status": status,
        "ready": not blockers,
        "required_models": required,
        "blockers": blockers,
        "warnings": warnings,
        "checked_at": snapshot.get("checked_at"),
        "detail": "Deployment prerequisites are satisfied" if not blockers else "Resolve deployment blockers before starting a render session",
    }
