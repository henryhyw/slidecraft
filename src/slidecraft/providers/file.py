"""Load structured results authored by the host Agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RecordedVisualAnalysis:
    """Read visual analysis produced by an Agent or stored in a test fixture.

    The Agent performs the interpretation. Slidecraft validates and compiles the
    recorded result into deterministic downstream contracts.
    """

    source_id = "agent_record"

    def __init__(self, result_path: Path):
        self.result_path = result_path.resolve()
        payload = json.loads(self.result_path.read_text(encoding="utf-8"))
        self.supports_connector_audit = "operation_results" in payload

    def result_for(self, operation: str) -> dict[str, Any]:
        payload = json.loads(self.result_path.read_text(encoding="utf-8"))
        if "operation_results" in payload:
            return payload["operation_results"][operation]
        return payload


class RecordedDeckPlan:
    """Read a deck plan authored by the host Agent."""

    source_id = "agent_record"

    def __init__(self, result_path: Path):
        self.result_path = result_path.resolve()

    def read(self) -> dict[str, Any]:
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
