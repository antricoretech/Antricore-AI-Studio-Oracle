"""Read-only render preflight checks used before queueing a job."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import database as db


def check(ok: bool, detail: str, **extra):
    return {"status": "ready" if ok else "warning", "detail": detail, **extra}


def workflow_preflight(workflow_id: str | None = None):
    checks = []
    try:
        usage = shutil.disk_usage(db.DATA)
        checks.append({"id": "storage", **check(usage.free > 10 * 1024 ** 3, f"{usage.free / (1024 ** 3):.1f} GiB free", free_gb=round(usage.free / (1024 ** 3), 2))})
    except OSError as exc:
        checks.append({"id": "storage", "status": "error", "detail": str(exc)[:200]})

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

    ffmpeg = shutil.which("ffmpeg")
    checks.append({"id": "ffmpeg", **check(bool(ffmpeg), ffmpeg or "FFmpeg is not on PATH")})
    return checks

