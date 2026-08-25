"""OS-backed credential storage for local provider connections."""

from __future__ import annotations

import os
from typing import Any

SERVICE_NAME = "ai.slidecraft"


def _keyring() -> Any:
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError(
            "Secure credential storage is unavailable. Install Slidecraft normally or provide the configured environment variable."
        ) from exc
    return keyring


def set_credential(credential_id: str, secret: str) -> dict[str, Any]:
    if not secret.strip():
        raise ValueError("Credential cannot be empty")
    _keyring().set_password(SERVICE_NAME, credential_id, secret.strip())
    return {"credential_id": credential_id, "stored": True, "storage": "system_keychain"}


def delete_credential(credential_id: str) -> dict[str, Any]:
    keyring = _keyring()
    try:
        keyring.delete_password(SERVICE_NAME, credential_id)
    except keyring.errors.PasswordDeleteError:
        pass
    return {"credential_id": credential_id, "stored": False, "storage": "system_keychain"}


def get_credential(credential_id: str) -> str | None:
    try:
        return _keyring().get_password(SERVICE_NAME, credential_id)
    except Exception:  # noqa: BLE001
        # Environment-variable credentials remain usable on systems without a working keychain backend.
        return None


def resolve_provider_credential(provider_config: dict[str, Any], role: str = "image_generation") -> dict[str, Any]:
    credential_id = provider_config.get("credential_id") or f"providers.{role}"
    stored = get_credential(credential_id)
    environment_name = provider_config.get("api_key_env", "")
    environment = os.environ.get(environment_name) if environment_name else None
    secret = stored or environment
    return {
        "credential_id": credential_id,
        "available": bool(secret),
        "source": "system_keychain" if stored else "environment" if environment else "missing",
        "secret": secret,
        "environment_name": environment_name,
    }
