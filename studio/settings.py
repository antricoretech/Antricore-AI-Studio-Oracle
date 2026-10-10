"""Centralised runtime settings for the local-first studio.

The application intentionally remains usable on loopback without a token.  A
token becomes mandatory as soon as ``STUDIO_AUTH_TOKEN`` is configured, which
keeps the safe local workflow backwards compatible while making an SSH/cloud
deployment explicit instead of accidental.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(1, value)


@dataclass(frozen=True)
class Settings:
    auth_token: str = os.getenv("STUDIO_AUTH_TOKEN", "").strip()
    brief_max_bytes: int = _int_env("STUDIO_MAX_BRIEF_BYTES", 1 * 1024 * 1024)
    workflow_max_bytes: int = _int_env("STUDIO_MAX_WORKFLOW_BYTES", 1 * 1024 * 1024)
    reference_max_bytes: int = _int_env("STUDIO_MAX_REFERENCE_BYTES", 20 * 1024 * 1024)
    asset_max_bytes: int = _int_env("STUDIO_MAX_ASSET_BYTES", 500 * 1024 * 1024)
    output_max_bytes: int = _int_env("STUDIO_MAX_OUTPUT_BYTES", 200 * 1024 * 1024)
    strict_media_validation: bool = os.getenv("STUDIO_STRICT_MEDIA", "0").lower() in {"1", "true", "yes"}
    job_timeout_seconds: int = _int_env("STUDIO_JOB_TIMEOUT_SECONDS", 60 * 60)


def get_settings() -> Settings:
    """Read settings at call time so tests and process supervisors can update env."""

    return Settings(
        auth_token=os.getenv("STUDIO_AUTH_TOKEN", "").strip(),
        brief_max_bytes=_int_env("STUDIO_MAX_BRIEF_BYTES", 1 * 1024 * 1024),
        workflow_max_bytes=_int_env("STUDIO_MAX_WORKFLOW_BYTES", 1 * 1024 * 1024),
        reference_max_bytes=_int_env("STUDIO_MAX_REFERENCE_BYTES", 20 * 1024 * 1024),
        asset_max_bytes=_int_env("STUDIO_MAX_ASSET_BYTES", 500 * 1024 * 1024),
        output_max_bytes=_int_env("STUDIO_MAX_OUTPUT_BYTES", 200 * 1024 * 1024),
        strict_media_validation=os.getenv("STUDIO_STRICT_MEDIA", "0").lower() in {"1", "true", "yes"},
        job_timeout_seconds=_int_env("STUDIO_JOB_TIMEOUT_SECONDS", 60 * 60),
    )
