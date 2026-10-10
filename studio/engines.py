"""Small adapter catalogue for render backends.

The heavy renderer implementations remain in their existing modules for now.
This interface gives the control plane one vocabulary for selecting and
monitoring them, so a durable worker can be introduced without changing the
workflow contract.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineAdapter:
    id: str
    label: str
    categories: tuple[str, ...]
    description: str
    local_only: bool = True


ADAPTERS = {
    "direct-cli": EngineAdapter(
        "direct-cli", "Direct local CLI", ("image", "video", "audio", "assembly"),
        "Runs the approved Python/FFmpeg pipeline with local weights and no inference API credits.",
    ),
    "comfyui": EngineAdapter(
        "comfyui", "ComfyUI API bridge", ("image", "video", "audio"),
        "Queues a verified API-format graph through the optional local ComfyUI service.",
    ),
}


def get(engine_id: str | None) -> EngineAdapter | None:
    return ADAPTERS.get(engine_id or "")


def rows() -> list[dict]:
    return [{"id": item.id, "label": item.label, "categories": list(item.categories),
             "description": item.description, "local_only": item.local_only}
            for item in ADAPTERS.values()]


def supports(engine_id: str | None, category: str | None = None) -> bool:
    adapter = get(engine_id)
    return bool(adapter and (not category or category in adapter.categories))
