"""Verified core ComfyUI API adapter; works with exported API-format graphs."""
import asyncio
import copy
import json
import os
import re
from urllib.parse import urlsplit

import httpx

URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
TIMEOUT = int(os.getenv("JOB_TIMEOUT_SECONDS", "1800"))
POLL = float(os.getenv("JOB_POLL_SECONDS", "3"))


def validate_comfy_url():
    """Don't accidentally send private images to an arbitrary remote URL."""
    parsed = urlsplit(URL)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("COMFYUI_URL must point to local HTTP ComfyUI (localhost/127.0.0.1). Use a private tunnel locally if needed.")


def validate_graph(graph):
    if not isinstance(graph, dict) or not graph:
        raise ValueError("Workflow must be a non-empty ComfyUI API JSON object")
    for key, node in graph.items():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise ValueError(f"Invalid API node {key!r}; use ComfyUI > Export (API Format), not normal UI JSON")
    return True


def render_graph(graph, values: dict):
    """Replace {{TOKEN}} while preserving JSON number types and node links."""
    validate_graph(graph)
    exact = re.compile(r"^\{\{([A-Z_]+)\}\}$")
    replace = re.compile(r"\{\{([A-Z_]+)\}\}")
    def walk(obj):
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        if not isinstance(obj, str):
            return obj
        match = exact.match(obj)
        if match:
            name = match.group(1)
            if name not in values:
                raise ValueError(f"Missing workflow value {{{{{name}}}}}")
            return values[name]
        def sub(m):
            key = m.group(1)
            if key not in values:
                raise ValueError(f"Missing workflow value {{{{{key}}}}}")
            return str(values[key])
        return replace.sub(sub, obj)
    return walk(copy.deepcopy(graph))


class ComfyClient:
    def __init__(self, transport=None):
        validate_comfy_url()
        self.client = httpx.AsyncClient(base_url=URL, timeout=httpx.Timeout(45), transport=transport)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    async def health(self):
        response = await self.client.get("/system_stats")
        response.raise_for_status()
        return response.json()

    async def checkpoints(self):
        response = await self.client.get("/models/checkpoints")
        response.raise_for_status()
        return response.json()

    async def upload_reference(self, image_bytes: bytes, filename: str):
        response = await self.client.post("/upload/image", files={"image": (filename, image_bytes, "image/png")}, data={"type": "input", "overwrite": "false"})
        response.raise_for_status()
        name = response.json().get("name")
        if not name:
            raise RuntimeError("ComfyUI did not return an uploaded image filename")
        return name

    async def upload_audio(self, audio_bytes: bytes, filename: str):
        """Optional ComfyUI audio upload; availability depends on server version."""
        response = await self.client.post("/upload/audio", files={"audio": (filename, audio_bytes, "audio/wav")}, data={"type": "input"})
        if response.status_code == 404:
            raise RuntimeError("This ComfyUI installation has no /upload/audio endpoint; use a compatible audio-input node/extension.")
        response.raise_for_status()
        name = response.json().get("name")
        if not name:
            raise RuntimeError("ComfyUI did not return an uploaded audio filename")
        return name

    async def submit(self, graph: dict):
        validate_graph(graph)
        response = await self.client.post("/prompt", json={"prompt": graph})
        if response.is_error:
            raise RuntimeError(f"ComfyUI rejected workflow: {response.text[:1200]}")
        result = response.json()
        if not result.get("prompt_id"):
            raise RuntimeError(f"ComfyUI returned no prompt_id: {result}")
        return result["prompt_id"]

    async def interrupt(self):
        """Best-effort interruption of the active local ComfyUI execution."""
        response = await self.client.post("/interrupt")
        response.raise_for_status()

    async def history(self, prompt_id: str):
        """Return one prompt history entry, or ``None`` when it is unknown."""
        response = await self.client.get(f"/history/{prompt_id}")
        response.raise_for_status()
        return response.json().get(prompt_id)

    async def wait(self, prompt_id: str, cancel_check=None, heartbeat=None):
        elapsed = 0
        while elapsed < TIMEOUT:
            if heartbeat:
                heartbeat()
            if cancel_check and cancel_check():
                raise asyncio.CancelledError()
            entry = await self.history(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error" or status.get("completed") is False and status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI execution failed: {str(status.get('messages', []))[-1000:]}")
                if status.get("completed") is True or entry.get("outputs"):
                    return entry.get("outputs", {})
            await asyncio.sleep(POLL)
            if heartbeat:
                heartbeat()
            if cancel_check and cancel_check():
                raise asyncio.CancelledError()
            elapsed += POLL
        raise TimeoutError(f"ComfyUI did not finish job within {TIMEOUT} seconds")

    async def download(self, file: dict):
        name = file.get("filename")
        if not name:
            raise ValueError("Missing filename in output")
        response = await self.client.get("/view", params={
            "filename": name, "subfolder": file.get("subfolder", ""), "type": file.get("type", "output")
        }, timeout=120)
        response.raise_for_status()
        return response.content


def output_files(outputs):
    """Collect output file references; supports images/gifs/video/audio in custom nodes."""
    found = []
    for node in outputs.values():
        if not isinstance(node, dict):
            continue
        for key, value in node.items():
            if key not in {"images", "gifs", "videos", "video", "audio", "files"}:
                continue
            candidates = value if isinstance(value, list) else [value]
            for item in candidates:
                if isinstance(item, dict) and item.get("filename"):
                    found.append(item)
    return found
