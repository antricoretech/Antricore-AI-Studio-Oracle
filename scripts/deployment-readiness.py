#!/usr/bin/env python3
"""Validate a running Studio instance before cloud rendering.

This check is read-only.  It never downloads weights, queues jobs or invokes a
model.  Use ``--url`` against the private SSH-tunnel URL after starting the
application, or omit it for a source/dependency sanity check.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def fetch(url: str) -> dict:
    headers = {}
    token = os.getenv("STUDIO_AUTH_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(url.rstrip("/") + "/api/readiness?profile=cloud", headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf8"))
    except HTTPError as exc:
        raise RuntimeError(f"Studio readiness endpoint returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot reach Studio readiness endpoint: {exc}") from exc


def source_checks() -> dict:
    checks = []
    for relative in ("config/approved_models.json", "config/workflow_catalog.json", "studio/app.py", "static/index.html"):
        path = ROOT / relative
        checks.append({"id": relative, "status": "ready" if path.is_file() else "error", "detail": str(path)})
    checks.append({"id": "python", "status": "ready" if sys.version_info >= (3, 10) else "warning", "detail": sys.version.split()[0]})
    ffmpeg = shutil.which("ffmpeg")
    checks.append({"id": "ffmpeg", "status": "ready" if ffmpeg else "warning", "detail": ffmpeg or "FFmpeg not found on PATH"})
    try:
        import torch
        cuda = bool(torch.cuda.is_available())
        checks.append({"id": "cuda", "status": "ready" if cuda else "warning", "detail": torch.cuda.get_device_name(0) if cuda else "CUDA unavailable"})
    except Exception as exc:
        checks.append({"id": "cuda", "status": "warning", "detail": "PyTorch unavailable: " + str(exc)[:160]})
    status = "error" if any(item["status"] == "error" for item in checks) else "warning" if any(item["status"] == "warning" for item in checks) else "ready"
    return {"profile": "source", "status": status, "ready": status == "ready", "checks": checks,
            "blockers": [item for item in checks if item["status"] == "error"], "warnings": [item for item in checks if item["status"] == "warning"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only AI Influencer Studio deployment readiness check")
    parser.add_argument("--url", help="Running Studio base URL, for example http://127.0.0.1:8000")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print machine-readable JSON")
    parser.add_argument("--allow-warnings", action="store_true", help="Exit zero when checks are warning-only")
    args = parser.parse_args(argv)
    try:
        result = fetch(args.url) if args.url else source_checks()
    except RuntimeError as exc:
        result = {"profile": "cloud", "status": "blocked", "ready": False, "detail": str(exc), "blockers": [{"code": "endpoint", "detail": str(exc)}], "warnings": []}
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Profile: {result.get('profile')}\nStatus: {result.get('status')}\n{result.get('detail', '')}")
        for item in result.get("blockers", []):
            print("BLOCKER:", item.get("code", item.get("id", "check")), "-", item.get("detail", ""))
        for item in result.get("warnings", []):
            print("WARNING:", item.get("code", item.get("id", "check")), "-", item.get("detail", ""))
    if result.get("ready"):
        return 0
    if args.allow_warnings and result.get("status") == "warning":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
