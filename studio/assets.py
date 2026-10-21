"""Canonical media storage and asset-registration boundary."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import database as db
from .media import extension_for
from .policies import AI_DISCLOSURE
from .provenance import media_metadata, quality_report, sha256_bytes


MEDIA_KINDS = {"image", "video", "audio"}


def _safe_filename(filename: str) -> str:
    candidate = str(filename or "").strip()
    path = Path(candidate)
    if not candidate or path.is_absolute() or len(path.parts) != 1 or path.name in {".", ".."}:
        raise ValueError("Media filename must be a single relative filename")
    return path.name


def media_path(filename: str) -> Path:
    """Resolve a canonical asset filename inside the configured output store."""

    safe = _safe_filename(filename)
    root = Path(db.OUTPUTS).resolve()
    resolved = (root / safe).resolve()
    if resolved.parent != root:
        raise ValueError("Media path escapes the canonical output store")
    return resolved


def reference_path(filename: str) -> Path:
    """Resolve a legacy reference filename inside the configured reference store."""

    safe = _safe_filename(filename)
    root = Path(db.UPLOADS).resolve()
    resolved = (root / safe).resolve()
    if resolved.parent != root:
        raise ValueError("Reference path escapes the configured reference store")
    return resolved


def _generated_filename(kind: str, original_filename: str | None = None) -> str:
    suffix = Path(original_filename or "").suffix.lower()
    if suffix not in {
        ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".gif", ".wav", ".mp3", ".flac",
    }:
        suffix = {"image": ".png", "video": ".mp4", "audio": ".wav"}[kind]
    return f"asset_{uuid.uuid4().hex}{suffix}"


def register_media_asset(
    *,
    persona_id: str,
    persona_version_id: str | None,
    job_id: str | None,
    kind: str,
    prompt: str,
    raw: bytes,
    disclosure: str | None = None,
    rights_confirmed: bool = False,
    original_filename: str | None = None,
    lineage: dict | None = None,
) -> dict:
    """Store bytes once and register a pending asset with complete provenance."""

    if kind not in MEDIA_KINDS:
        raise ValueError("Asset kind must be image, video, or audio")
    if not raw:
        raise ValueError("Media output is empty")

    filename = _generated_filename(kind, original_filename)
    destination = media_path(filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    disclosure_text = (disclosure or AI_DISCLOSURE).strip()[:300]
    metadata = media_metadata(raw, kind, filename)
    quality = quality_report(destination, kind, disclosure_text, lineage=lineage)
    asset_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.write(
        "INSERT INTO assets (id,persona_id,persona_version_id,job_id,filename,kind,prompt,review,rights_confirmed,disclosure,created_at,sha256,metadata_json,quality_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            asset_id,
            persona_id,
            persona_version_id,
            job_id,
            filename,
            kind,
            prompt[:3000],
            "pending",
            int(bool(rights_confirmed)),
            disclosure_text,
            created_at,
            sha256_bytes(raw),
            json.dumps(metadata, ensure_ascii=False),
            json.dumps(quality, ensure_ascii=False),
        ),
    )
    return db.row("SELECT * FROM assets WHERE id=?", (asset_id,))


def asset_file(asset: dict) -> Path:
    """Resolve a registered asset file and fail closed when it is missing."""

    path = media_path(asset.get("filename"))
    if not path.is_file():
        raise FileNotFoundError(f"Asset media file is missing: {asset.get('filename')}")
    return path


def validate_import_suffix(kind: str, filename: str) -> str:
    """Validate an import extension while keeping storage naming centralized."""

    return extension_for(kind, filename)
