from __future__ import annotations

from unittest.mock import Mock, patch

from slidecraft.credentials import SERVICE_NAME, delete_credential, resolve_provider_credential, set_credential


def test_credentials_are_stored_outside_configuration_and_resolved_for_provider(monkeypatch) -> None:
    backend = Mock()
    backend.get_password.return_value = "saved-secret"
    with patch("slidecraft.credentials._keyring", return_value=backend):
        stored = set_credential("providers.image_generation", " saved-secret ")
        resolved = resolve_provider_credential(
            {"credential_id": "providers.image_generation", "api_key_env": "TEST_IMAGE_KEY"}
        )

    backend.set_password.assert_called_once_with(SERVICE_NAME, "providers.image_generation", "saved-secret")
    assert stored["storage"] == "system_keychain"
    assert "secret" not in stored
    assert resolved["source"] == "system_keychain"
    assert resolved["secret"] == "saved-secret"


def test_environment_credential_remains_available_without_keychain(monkeypatch) -> None:
    monkeypatch.setenv("TEST_IMAGE_KEY", "environment-secret")
    backend = Mock()
    backend.get_password.return_value = None
    with patch("slidecraft.credentials._keyring", return_value=backend):
        resolved = resolve_provider_credential(
            {"credential_id": "providers.image_generation", "api_key_env": "TEST_IMAGE_KEY"}
        )
        deleted = delete_credential("providers.image_generation")

    assert resolved["source"] == "environment"
    assert resolved["secret"] == "environment-secret"
    assert deleted["stored"] is False
