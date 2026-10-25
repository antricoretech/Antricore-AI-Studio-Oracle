"""Local publishing-policy contracts.

This module deliberately stops at deterministic readiness evaluation. It does
not authenticate, contact, or publish to an external platform. Those side
effects belong to the Phase 8 account and delivery integration.
"""
from __future__ import annotations

from copy import deepcopy


PLATFORM_POLICIES = {
    "local_export": {
        "label": "Local export",
        "execution_status": "available",
        "account_type": None,
        "formats": {
            "image": {"kind": "image", "requires_public_media_url": False},
            "video": {"kind": "video", "requires_public_media_url": False},
            "audio": {"kind": "audio", "requires_public_media_url": False},
        },
        "external_requirements": [],
    },
    "instagram": {
        "label": "Instagram",
        "execution_status": "deferred_phase_8",
        "account_type": "professional",
        "formats": {
            "feed_image": {"kind": "image", "requires_public_media_url": True},
            "reel": {"kind": "video", "requires_public_media_url": True},
        },
        "external_requirements": [
            "professional_account",
            "platform_account_binding",
            "external_permission_scope",
            "public_media_url",
        ],
    },
}


def catalog() -> dict:
    """Return a safe copy for a read-only API response."""

    return deepcopy(PLATFORM_POLICIES)


def infer_format(platform: str, kind: str) -> str:
    if platform == "local_export":
        return kind
    return {"image": "feed_image", "video": "reel"}.get(kind, "")


def evaluate(
    platform: str,
    format_name: str,
    *,
    asset_kind: str,
    base_ready: bool,
    destination_policy: str,
    public_media_url: bool = False,
    account_bound: bool = False,
    permissions_configured: bool = False,
    professional_account: bool = False,
) -> dict:
    """Evaluate a platform contract without making external calls."""

    policy = PLATFORM_POLICIES.get(platform)
    if not policy:
        raise ValueError(f"Unsupported publishing platform: {platform}")
    format_policy = policy["formats"].get(format_name)
    if not format_policy:
        raise ValueError(f"Unsupported {platform} format: {format_name}")

    checks = [
        {
            "id": "asset_readiness",
            "status": "ready" if base_ready else "blocked",
            "detail": "Asset passed the local review and identity readiness gate" if base_ready else "Resolve the local asset review and identity readiness gates first",
        },
        {
            "id": "format_kind",
            "status": "ready" if format_policy["kind"] == asset_kind else "error",
            "detail": "Asset kind matches the selected publishing format" if format_policy["kind"] == asset_kind else f"{format_name} requires a {format_policy['kind']} asset",
        },
        {
            "id": "destination_policy",
            "status": "ready" if destination_policy == "eligible" else "blocked",
            "detail": "Asset is explicitly eligible for external publishing" if destination_policy == "eligible" else "Destination policy must be eligible for external publishing",
        },
    ]
    if platform != "local_export":
        checks.extend([
            {
                "id": "professional_account",
                "status": "ready" if professional_account else "blocked",
                "detail": "Professional-account verification is recorded" if professional_account else "Professional-account verification is not recorded",
            },
            {
                "id": "platform_account_binding",
                "status": "ready" if account_bound else "blocked",
                "detail": "A platform account is bound to this persona" if account_bound else "No platform account is bound; Phase 8 OAuth/account binding is not active",
            },
            {
                "id": "external_permission_scope",
                "status": "ready" if permissions_configured else "blocked",
                "detail": "Required external permission scope is configured" if permissions_configured else "External publishing permissions are not configured; no OAuth call was made",
            },
            {
                "id": "public_media_url",
                "status": "ready" if public_media_url else "blocked",
                "detail": "Media has a public URL available to the platform" if public_media_url else "A publicly reachable media URL is required at publish time; local-only storage is not sufficient",
            },
        ])
    ready = all(check["status"] == "ready" for check in checks)
    return {
        "platform": platform,
        "format": format_name,
        "execution_status": policy["execution_status"],
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "checks": checks,
    }
