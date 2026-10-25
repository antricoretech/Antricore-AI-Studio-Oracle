"""Secret-storage boundary for external publishing credentials.

SQLite stores only opaque references. The optional keyring adapter delegates
secret material to the operating-system credential store; no environment
fallback or plaintext-file fallback is provided.
"""
from __future__ import annotations

import importlib.util
import os
import re
from typing import Protocol


SERVICE_NAME = "ai-influencer-studio"
_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{3,200}$")


class SecretStoreUnavailable(RuntimeError):
    pass


class SecretStore(Protocol):
    def put(self, reference: str, value: str) -> None: ...
    def get(self, reference: str) -> str | None: ...
    def delete(self, reference: str) -> None: ...


def _validate_reference(reference: str) -> str:
    value = (reference or "").strip()
    if not _REFERENCE_PATTERN.fullmatch(value):
        raise ValueError("Secret reference must be a bounded opaque identifier")
    return value


def keyring_available() -> bool:
    return importlib.util.find_spec("keyring") is not None


class KeyringSecretStore:
    def __init__(self, service_name: str = SERVICE_NAME):
        if not keyring_available():
            raise SecretStoreUnavailable("Python keyring is not installed")
        import keyring
        self._keyring = keyring
        self._service_name = service_name

    def put(self, reference: str, value: str) -> None:
        reference = _validate_reference(reference)
        if not isinstance(value, str) or not value:
            raise ValueError("Secret value must be a non-empty string")
        self._keyring.set_password(self._service_name, reference, value)

    def get(self, reference: str) -> str | None:
        return self._keyring.get_password(self._service_name, _validate_reference(reference))

    def delete(self, reference: str) -> None:
        try:
            self._keyring.delete_password(self._service_name, _validate_reference(reference))
        except Exception as exc:
            if exc.__class__.__name__ not in {"PasswordDeleteError", "CredentialNotFoundError"}:
                raise


class InMemorySecretStore:
    """Test-only store; never selected by runtime configuration."""

    def __init__(self):
        self._values: dict[str, str] = {}

    def put(self, reference: str, value: str) -> None:
        reference = _validate_reference(reference)
        if not isinstance(value, str) or not value:
            raise ValueError("Secret value must be a non-empty string")
        self._values[reference] = value

    def get(self, reference: str) -> str | None:
        return self._values.get(_validate_reference(reference))

    def delete(self, reference: str) -> None:
        self._values.pop(_validate_reference(reference), None)


def catalog() -> dict:
    configured = os.getenv("STUDIO_PUBLISHING_SECRET_STORAGE", "keyring").strip().lower() or "keyring"
    available = keyring_available()
    return {
        "configured_backend": configured,
        "keyring_available": available,
        "write_enabled": configured == "keyring" and available,
        "plaintext_fallback": False,
        "database_stores_secret_values": False,
    }


def get_store() -> SecretStore:
    configured = os.getenv("STUDIO_PUBLISHING_SECRET_STORAGE", "keyring").strip().lower() or "keyring"
    if configured != "keyring":
        raise SecretStoreUnavailable("Only the OS keyring backend is supported")
    return KeyringSecretStore()
