"""Provider boundary for publishing integrations.

The only provider enabled in the current phase is a deterministic local
dry-run adapter. It never reads secrets, opens a network connection, or
claims that an external account is verified.
"""
from __future__ import annotations

from copy import deepcopy
import base64
import hashlib
import os
from urllib.parse import urlencode

from .secrets import catalog as secret_storage_catalog


class ProviderDisabled(RuntimeError):
    pass


class LocalDryRunProvider:
    name = "local_dry_run"

    def catalog(self) -> dict:
        return {
            "id": self.name,
            "label": "Local dry-run provider",
            "execution_status": "available",
            "external_calls": False,
            "supports_oauth": False,
            "supports_publish": False,
            "supports_account_verification": False,
            "secret_storage": secret_storage_catalog(),
        }

    def dry_run(self, *, platform: str, format_name: str, checks: list[dict], account_id: str) -> dict:
        snapshot = deepcopy(checks)
        ready = all(check.get("status") == "ready" for check in snapshot)
        return {
            "provider": self.name,
            "execution_status": "dry_run_only",
            "external_calls": False,
            "account_id": account_id,
            "platform": platform,
            "format": format_name,
            "dry_run": True,
            "ready": ready,
            "status": "ready" if ready else "blocked",
            "checks": snapshot,
        }


class MetaInstagramProvider:
    name = "meta_instagram"
    _AUTH_MODES = {
        "instagram_login": {
            "authorization_endpoint": "https://www.instagram.com/oauth/authorize",
            "scopes": ("instagram_business_basic", "instagram_business_content_publish"),
        },
        "facebook_login": {
            "authorization_endpoint": "https://www.facebook.com/{version}/dialog/oauth",
            "scopes": ("instagram_basic", "instagram_content_publish", "pages_show_list", "pages_read_engagement"),
        },
    }

    def _config(self) -> dict:
        enabled = os.getenv("STUDIO_ENABLE_INSTAGRAM_PROVIDER", "0").lower() in {"1", "true", "yes"}
        secret_ref = os.getenv("STUDIO_INSTAGRAM_CLIENT_SECRET_REF", "").strip()
        client_id = os.getenv("STUDIO_INSTAGRAM_CLIENT_ID", "").strip()
        redirect_uri = os.getenv("STUDIO_INSTAGRAM_REDIRECT_URI", "").strip()
        storage = secret_storage_catalog()
        configured = enabled and bool(client_id and secret_ref and redirect_uri and storage["write_enabled"])
        return {
            "enabled": enabled,
            "configured": configured,
            "client_id": client_id,
            "client_secret_ref_present": bool(secret_ref),
            "redirect_uri": redirect_uri,
            "secret_storage_ready": storage["write_enabled"],
        }

    def catalog(self) -> dict:
        config = self._config()
        return {
            "id": self.name,
            "label": "Meta Instagram provider",
            "execution_status": "configured" if config["configured"] else "disabled",
            "implementation_status": "authorization_plan_only",
            "external_calls": False,
            "supports_oauth": config["configured"],
            "supports_publish": False,
            "supports_account_verification": False,
            "configuration": {
                "enabled": config["enabled"],
                "configured": config["configured"],
                "client_id_present": bool(config["client_id"]),
                "client_secret_ref_present": config["client_secret_ref_present"],
                "redirect_uri_present": bool(config["redirect_uri"]),
                "secret_storage_ready": config["secret_storage_ready"],
            },
            "auth_modes": {
                mode: {"required_scopes": list(details["scopes"])}
                for mode, details in self._AUTH_MODES.items()
            },
        }

    def authorization_plan(self, *, auth_mode: str, redirect_uri: str, state: str, code_verifier: str,
                           requested_scopes: list[str]) -> dict:
        config = self._config()
        if not config["configured"]:
            raise ProviderDisabled("Meta Instagram provider is disabled or incompletely configured")
        mode = self._AUTH_MODES.get(auth_mode)
        if not mode:
            raise ValueError(f"Unsupported Meta Instagram authorization mode: {auth_mode}")
        if redirect_uri != config["redirect_uri"]:
            raise ValueError("redirect_uri does not match the configured Meta provider callback")
        scopes = list(dict.fromkeys(requested_scopes or mode["scopes"]))
        unknown = [scope for scope in scopes if scope not in mode["scopes"]]
        if unknown:
            raise ValueError("Requested scopes are not allowed for the selected Meta authorization mode")
        endpoint = mode["authorization_endpoint"].format(version=os.getenv("STUDIO_META_API_VERSION", "v25.0"))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).rstrip(b"=").decode("ascii")
        query = urlencode({
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(scopes),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        return {
            "authorization_url": f"{endpoint}?{query}",
            "scopes": scopes,
            "auth_mode": auth_mode,
            "code_challenge_method": "S256",
            "code_verifier": code_verifier,
        }

    def dry_run(self, *, platform: str, format_name: str, checks: list[dict], account_id: str) -> dict:
        return {
            "provider": self.name,
            "execution_status": "authorization_plan_only",
            "external_calls": False,
            "account_id": account_id,
            "platform": platform,
            "format": format_name,
            "dry_run": True,
            "ready": False,
            "status": "blocked",
            "checks": deepcopy(checks) + [{"id": "provider_publish", "status": "blocked", "detail": "Meta publishing execution is not implemented"}],
        }


_PROVIDERS = {LocalDryRunProvider.name: LocalDryRunProvider(), MetaInstagramProvider.name: MetaInstagramProvider()}


def catalog() -> list[dict]:
    return [provider.catalog() for provider in _PROVIDERS.values()]


def get(name: str):
    provider = _PROVIDERS.get((name or "").strip().lower())
    if not provider:
        raise ValueError(f"Unsupported publishing provider: {name}")
    return provider
