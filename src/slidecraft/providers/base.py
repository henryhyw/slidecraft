"""Vendor-neutral model capability contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StructuredVisionProvider(Protocol):
    """Extract schema-constrained data from one image and grounded context."""

    provider_id: str

    def extract(
        self,
        *,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any],
        operation: str,
    ) -> dict[str, Any]: ...


@runtime_checkable
class StructuredReasoningProvider(Protocol):
    """Produce a schema-constrained planning or review artifact from text context."""

    provider_id: str

    def reason(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        operation: str,
    ) -> dict[str, Any]: ...


@runtime_checkable
class ImageGenerationProvider(Protocol):
    """Generate or edit a raster image from an assembled generation package."""

    provider_id: str

    def generate(
        self,
        *,
        prompt: str,
        output_path: Path,
        reference_images: list[Path],
        canvas_px: tuple[int, int],
    ) -> dict[str, Any]: ...
