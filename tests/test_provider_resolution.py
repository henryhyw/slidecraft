from __future__ import annotations

from slidecraft.providers.resolution import resolve_image_generation_route


def test_agent_image_generation_is_preferred_when_available(monkeypatch) -> None:
    monkeypatch.delenv("SLIDECRAFT_TEST_IMAGE_KEY", raising=False)
    result = resolve_image_generation_route(
        {
            "selection_policy": "prefer_host",
            "configured_adapter": "openai",
            "model": "gpt-image-2",
            "api_key_env": "SLIDECRAFT_TEST_IMAGE_KEY",
        },
        host_supports_image_generation=True,
    )
    assert result["route"] == "host"
    assert result["status"] == "ready"


def test_configured_connection_is_fallback_when_agent_has_no_image_tool(monkeypatch) -> None:
    monkeypatch.setenv("SLIDECRAFT_TEST_IMAGE_KEY", "test-value")
    result = resolve_image_generation_route(
        {
            "selection_policy": "prefer_host",
            "configured_adapter": "openai",
            "model": "gpt-image-2",
            "api_key_env": "SLIDECRAFT_TEST_IMAGE_KEY",
        },
        host_supports_image_generation=False,
    )
    assert result["route"] == "configured"
    assert result["status"] == "ready"
    assert result["reason"] == "agent_image_generation_unavailable"


def test_configured_connection_can_be_forced(monkeypatch) -> None:
    monkeypatch.setenv("SLIDECRAFT_TEST_IMAGE_KEY", "test-value")
    result = resolve_image_generation_route(
        {
            "selection_policy": "force_configured",
            "configured_adapter": "openai",
            "model": "gpt-image-2",
            "api_key_env": "SLIDECRAFT_TEST_IMAGE_KEY",
        },
        host_supports_image_generation=True,
    )
    assert result["route"] == "configured"
    assert result["reason"] == "forced_configured_connection"
