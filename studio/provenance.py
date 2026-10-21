"""Asset integrity, quality flags and export-manifest helpers."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from .policies import AI_DISCLOSURE


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def media_metadata(raw: bytes, kind: str, filename: str) -> dict:
    metadata = {"bytes": len(raw), "filename": filename, "extension": Path(filename).suffix.lower()}
    if kind == "image":
        try:
            with Image.open(BytesIO(raw)) as image:
                metadata.update({"format": image.format, "width": image.width, "height": image.height})
        except Exception as exc:
            metadata["decode_error"] = str(exc)[:180]
    return metadata


def quality_report(path: Path, kind: str, disclosure: str, *, lineage: dict | None = None, expected_sha256: str | None = None) -> dict:
    checks = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {"status": "error", "checks": [{"id": "file", "status": "error", "detail": str(exc)[:180]}]}
    checks.append({"id": "file", "status": "ready" if raw else "error", "detail": f"{len(raw)} bytes" if raw else "File is empty"})
    if expected_sha256:
        actual = sha256_bytes(raw)
        checks.append({"id": "hash", "status": "ready" if actual == expected_sha256 else "error", "detail": "SHA-256 matches recorded asset hash" if actual == expected_sha256 else "SHA-256 mismatch; file changed after import"})
    if kind == "image":
        try:
            with Image.open(BytesIO(raw)) as image:
                image.verify()
            checks.append({"id": "decode", "status": "ready", "detail": "Image container decoded successfully"})
        except Exception as exc:
            checks.append({"id": "decode", "status": "error", "detail": f"Image decode failed: {str(exc)[:140]}"})
    if len((disclosure or "").strip()) < 20:
        checks.append({"id": "disclosure", "status": "warning", "detail": "Add a clear synthetic-media disclosure before export"})
    else:
        checks.append({"id": "disclosure", "status": "ready", "detail": "Disclosure text present"})
    if lineage:
        checks.append({"id": "lineage", "status": "ready", "detail": "Source and generation lineage recorded"})
    else:
        checks.append({"id": "lineage", "status": "warning", "detail": "No linked generation lineage recorded"})
    statuses = [item["status"] for item in checks]
    overall = "error" if "error" in statuses else "warning" if "warning" in statuses else "ready"
    return {"status": overall, "checks": checks}


def manifest(asset: dict, *, job: dict | None = None, persona: dict | None = None, quality: dict | None = None) -> dict:
    def parse(value):
        if isinstance(value, dict):
            return value
        try:
            return json.loads(value or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}

    return {
        "schema_version": "asset-manifest-1.0",
        "asset": {
            "id": asset.get("id"), "filename": asset.get("filename"), "kind": asset.get("kind"),
            "sha256": asset.get("sha256"), "metadata": parse(asset.get("metadata_json")),
            "review": asset.get("review"), "reviewed_at": asset.get("reviewed_at"),
            "reviewer": asset.get("reviewer"), "review_reason": asset.get("review_reason"),
            "disclosure": asset.get("disclosure") or AI_DISCLOSURE,
        },
        "persona": {
            "id": (persona or {}).get("id", asset.get("persona_id")),
            "name": (persona or {}).get("name"),
            "identity_version": (persona or {}).get("identity_version"),
        },
        "job": {
            "id": (job or {}).get("id"), "workflow_id": (job or {}).get("workflow_id"),
            "request": parse((job or {}).get("request_json")),
            "lineage": parse((job or {}).get("lineage_json")),
            "attempt": (job or {}).get("attempt"),
        },
        "quality": quality or parse(asset.get("quality_json")),
    }
