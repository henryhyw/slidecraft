"""Host-agent bridge for schema-constrained JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FileStructuredVisionProvider:
    """Read a VLM result produced by Codex, another agent host, or a fixture.

    This provider is also the stable boundary used by the future MCP server. The
    host performs the model call, saves the strict JSON artifact, and the local
    Slidecraft process performs validation and deterministic compilation.
    """

    provider_id = "host_file"

    def __init__(self, result_path: Path):
        self.result_path = result_path.resolve()
        payload = json.loads(self.result_path.read_text(encoding="utf-8"))
        self.supports_connector_audit = "operation_results" in payload

    def extract(
        self,
        *,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any],
        operation: str,
    ) -> dict[str, Any]:
        del image_path, prompt, schema
        payload = json.loads(self.result_path.read_text(encoding="utf-8"))
        if "operation_results" in payload:
            return payload["operation_results"][operation]
        return payload


class FileStructuredReasoningProvider:
    """Read a strict planning artifact emitted by an external agent host."""

    provider_id = "host_file"

    def __init__(self, result_path: Path):
        self.result_path = result_path.resolve()

    def reason(self, *, prompt: str, schema: dict[str, Any], operation: str) -> dict[str, Any]:
        del prompt, schema, operation
        return json.loads(self.result_path.read_text(encoding="utf-8"))


class HostImageGenerationProvider:
    """Emit a host-agent generation request without requiring an API key."""

    provider_id = "host_artifact_request"

    def __init__(self, request_path: Path):
        self.request_path = request_path.resolve()

    def generate(
        self,
        *,
        prompt: str,
        output_path: Path,
        reference_images: list[Path],
        canvas_px: tuple[int, int],
    ) -> dict[str, Any]:
        request = {
            "schema_version": "1.0.0",
            "operation": "image_generation",
            "prompt": prompt,
            "reference_images": [str(path.resolve()) for path in reference_images],
            "canvas_px": list(canvas_px),
            "expected_output_path": str(output_path.resolve()),
            "status": "awaiting_host_generation",
        }
        self.request_path.parent.mkdir(parents=True, exist_ok=True)
        self.request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return request
