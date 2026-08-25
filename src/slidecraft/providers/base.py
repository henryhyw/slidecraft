"""Image-generation contracts used by Slidecraft."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


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
