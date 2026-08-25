"""Capability-aware provider routing for image generation."""

from __future__ import annotations

from typing import Any

from slidecraft.credentials import resolve_provider_credential


def resolve_image_generation_route(
    provider_config: dict[str, Any],
    *,
    host_supports_image_generation: bool,
) -> dict[str, Any]:
    """Choose the Agent image tool or the configured API connection."""
    policy = provider_config.get("selection_policy", "prefer_host")
    if policy not in {"prefer_host", "force_configured"}:
        raise ValueError(f"Unsupported image generation selection policy: {policy}")
    if policy == "prefer_host" and host_supports_image_generation:
        return {
            "status": "ready",
            "route": "host",
            "reason": "agent_image_generation_available",
            "model": "provided_by_agent",
        }

    adapter = provider_config.get("configured_adapter", "openai")
    if adapter not in {"openai", "custom-openai-compatible"}:
        raise ValueError(f"Unsupported configured image adapter: {adapter}")
    credential = resolve_provider_credential(provider_config)
    base_url = provider_config.get("base_url", "")
    connection_ready = credential["available"] and (adapter != "custom-openai-compatible" or bool(base_url))
    return {
        "status": "ready" if connection_ready else "configuration_required",
        "route": "configured",
        "reason": "forced_configured_connection" if policy == "force_configured" else "agent_image_generation_unavailable",
        "adapter": adapter,
        "model": provider_config.get("model", "gpt-image-2"),
        "base_url": base_url,
        "api_key_env": credential["environment_name"],
        "credential_id": credential["credential_id"],
        "credential_source": credential["source"],
        "credential_available": credential["available"],
    }
