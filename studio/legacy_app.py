"""Standalone legacy AI Influencer Studio application entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("STUDIO_APP_SURFACE", "legacy")
# Preserve the existing legacy database and media layout by default.
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))
os.environ.setdefault("STUDIO_GENERATED_DIR", str(ROOT / "generated"))

from .app import app as _combined_app  # noqa: E402
from .application_surface import ApplicationSurface  # noqa: E402


app = ApplicationSurface(_combined_app, "legacy")
