"""Provider boundary for publishing integrations.

The only provider enabled in the current phase is a deterministic local
dry-run adapter. It never reads secrets, opens a network connection, or
claims that an external account is verified.
"""
from __future__ import annotations

from copy import deepcopy
import base64
import hashlib
import json
import os
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .secrets import SecretStoreUnavailable, catalog as secret_storage_catalog, get_store


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
        token_exchange_enabled = os.getenv("STUDIO_ENABLE_INSTAGRAM_TOKEN_EXCHANGE", "0").lower() in {"1", "true", "yes"}
        account_verification_enabled = os.getenv("STUDIO_ENABLE_INSTAGRAM_ACCOUNT_VERIFICATION", "0").lower() in {"1", "true", "yes"}
        secret_ref = os.getenv("STUDIO_INSTAGRAM_CLIENT_SECRET_REF", "").strip()
        client_id = os.getenv("STUDIO_INSTAGRAM_CLIENT_ID", "").strip()
        redirect_uri = os.getenv("STUDIO_INSTAGRAM_REDIRECT_URI", "").strip()
        storage = secret_storage_catalog()
        configured = enabled and bool(client_id and secret_ref and redirect_uri and storage["write_enabled"])
        return {
            "enabled": enabled,
            "configured": configured,
            "token_exchange_enabled": token_exchange_enabled and configured,
            "account_verification_enabled": account_verification_enabled and configured and token_exchange_enabled,
            "client_id": client_id,
            "secret_ref": secret_ref,
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
            "implementation_status": "token_exchange_boundary" if config["token_exchange_enabled"] else "authorization_plan_only",
            "external_calls": False,
            "supports_oauth": config["configured"],
            "supports_token_exchange": config["token_exchange_enabled"],
            "supports_token_refresh": config["token_exchange_enabled"],
            "supports_account_verification": config["account_verification_enabled"],
            "supports_publish": False,
            "configuration": {
                "enabled": config["enabled"],
                "configured": config["configured"],
                "client_id_present": bool(config["client_id"]),
                "client_secret_ref_present": config["client_secret_ref_present"],
                "redirect_uri_present": bool(config["redirect_uri"]),
                "secret_storage_ready": config["secret_storage_ready"],
                "token_exchange_enabled": config["token_exchange_enabled"],
                "account_verification_enabled": config["account_verification_enabled"],
            },
            "auth_modes": {
                mode: {"required_scopes": list(details["scopes"])}
                for mode, details in self._AUTH_MODES.items()
            },
        }

    def token_exchange_enabled(self) -> bool:
        return bool(self._config()["token_exchange_enabled"])

    def account_verification_enabled(self) -> bool:
        return bool(self._config()["account_verification_enabled"])

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
            "token_exchange_enabled": config["token_exchange_enabled"],
        }

    @staticmethod
    def _post_form(url: str, form: dict) -> dict:
        request = Request(
            url, data=urlencode(form).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = response.read(1_000_000)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError("Meta token request failed") from exc
        try:
            result = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Meta token response was not valid JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Meta token response was invalid")
        if result.get("error"):
            raise RuntimeError("Meta token request was rejected")
        return result

    def _token_endpoint(self, auth_mode: str) -> str:
        version = os.getenv("STUDIO_META_API_VERSION", "v25.0")
        if auth_mode == "instagram_login":
            return os.getenv("STUDIO_INSTAGRAM_TOKEN_ENDPOINT", "https://api.instagram.com/oauth/access_token")
        if auth_mode == "facebook_login":
            return os.getenv("STUDIO_META_TOKEN_ENDPOINT", f"https://graph.facebook.com/{version}/oauth/access_token")
        raise ValueError(f"Unsupported Meta Instagram authorization mode: {auth_mode}")

    @staticmethod
    def _token_payload(payload: dict) -> dict:
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("Meta token response did not include an access token")
        result = {
            "access_token": access_token,
            "refresh_token": payload.get("refresh_token") if isinstance(payload.get("refresh_token"), str) else None,
            "token_type": str(payload.get("token_type") or "bearer")[:40],
            "scope": str(payload.get("scope") or "")[:1000],
        }
        try:
            result["expires_in"] = max(0, int(payload.get("expires_in", 0)))
        except (TypeError, ValueError):
            result["expires_in"] = 0
        return result

    def exchange_code(self, *, auth_mode: str, redirect_uri: str, code: str,
                      code_verifier: str, request_fn=None) -> dict:
        config = self._config()
        if not config["token_exchange_enabled"]:
            raise ProviderDisabled("Meta token exchange is disabled by configuration")
        if redirect_uri != config["redirect_uri"]:
            raise ValueError("redirect_uri does not match the configured Meta provider callback")
        if not code or len(code) > 4096 or not code_verifier:
            raise ValueError("Authorization code and PKCE verifier are required")
        try:
            client_secret = get_store().get(config["secret_ref"])
        except SecretStoreUnavailable as exc:
            raise ProviderDisabled("OS keychain is unavailable for Meta token exchange") from exc
        if not client_secret:
            raise ProviderDisabled("Meta client secret is not available in the OS keychain")
        form = {
            "client_id": config["client_id"],
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }
        payload = (request_fn or self._post_form)(self._token_endpoint(auth_mode), form)
        return self._token_payload(payload)

    def refresh_token(self, *, auth_mode: str, refresh_token: str, request_fn=None) -> dict:
        config = self._config()
        if not config["token_exchange_enabled"]:
            raise ProviderDisabled("Meta token refresh is disabled by configuration")
        if not refresh_token or len(refresh_token) > 4096:
            raise ValueError("A refresh token is required")
        try:
            client_secret = get_store().get(config["secret_ref"])
        except SecretStoreUnavailable as exc:
            raise ProviderDisabled("OS keychain is unavailable for Meta token refresh") from exc
        if not client_secret:
            raise ProviderDisabled("Meta client secret is not available in the OS keychain")
        form = {
            "client_id": config["client_id"],
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": os.getenv("STUDIO_META_REFRESH_GRANT_TYPE", "refresh_token"),
        }
        payload = (request_fn or self._post_form)(self._token_endpoint(auth_mode), form)
        return self._token_payload(payload)

    @staticmethod
    def _get_json(url: str, query: dict) -> dict:
        endpoint = f"{url}?{urlencode(query)}"
        request = Request(endpoint, headers={"Accept": "application/json"}, method="GET")
        try:
            with urlopen(request, timeout=20) as response:
                payload = response.read(1_000_000)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError("Meta account verification request failed") from exc
        try:
            result = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Meta account verification response was not valid JSON") from exc
        if not isinstance(result, dict) or result.get("error"):
            raise RuntimeError("Meta account verification response was invalid")
        return result

    def verify_account(self, *, auth_mode: str, access_token: str, request_fn=None) -> dict:
        config = self._config()
        if not config["account_verification_enabled"]:
            raise ProviderDisabled("Meta account verification is disabled by configuration")
        if not access_token or len(access_token) > 4096:
            raise ValueError("An access token is required for account verification")
        version = os.getenv("STUDIO_META_API_VERSION", "v25.0")
        if auth_mode == "instagram_login":
            endpoint = os.getenv("STUDIO_INSTAGRAM_VERIFY_ENDPOINT", "https://graph.instagram.com/me")
            fields = "id,username,account_type,user_type"
        elif auth_mode == "facebook_login":
            endpoint = os.getenv("STUDIO_META_VERIFY_ENDPOINT", f"https://graph.facebook.com/{version}/me")
            fields = "id,name,username,account_type,user_type"
        else:
            raise ValueError(f"Unsupported Meta Instagram authorization mode: {auth_mode}")
        query = {"access_token": access_token, "fields": fields}
        payload = (request_fn or self._get_json)(endpoint, query)
        external_id = payload.get("id")
        if not isinstance(external_id, str) or not external_id:
            raise RuntimeError("Meta account verification did not return an account id")
        account_type = str(payload.get("account_type") or payload.get("user_type") or "").strip().lower()
        handle = str(payload.get("username") or "").strip() or None
        return {"external_account_id": external_id[:160], "handle": handle[:120] if handle else None, "account_type": account_type[:40]}

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
