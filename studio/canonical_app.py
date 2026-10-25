"""Standalone canonical AI Influencer Studio application entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("STUDIO_APP_SURFACE", "canonical")
os.environ.setdefault("DATA_DIR", str(ROOT / "data" / "canonical"))
os.environ.setdefault("STUDIO_GENERATED_DIR", str(ROOT / "data" / "canonical" / "generated"))

from .app import app as _combined_app  # noqa: E402
from .application_surface import ApplicationSurface  # noqa: E402


app = ApplicationSurface(_combined_app, "canonical")
