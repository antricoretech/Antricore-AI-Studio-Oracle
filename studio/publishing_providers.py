"""Provider boundary for publishing integrations.

The only provider enabled in the current phase is a deterministic local
dry-run adapter. It never reads secrets, opens a network connection, or
claims that an external account is verified.
"""
from __future__ import annotations

from copy import deepcopy


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


_PROVIDERS = {LocalDryRunProvider.name: LocalDryRunProvider()}


def catalog() -> list[dict]:
    return [provider.catalog() for provider in _PROVIDERS.values()]


def get(name: str):
    provider = _PROVIDERS.get((name or "").strip().lower())
    if not provider:
        raise ValueError(f"Unsupported publishing provider: {name}")
    return provider
