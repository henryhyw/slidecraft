"""OpenAI image-generation provider."""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from PIL import Image, ImageOps


class OpenAIImageGenerationProvider:
    provider_id = "openai_images"

    def __init__(self, model: str = "gpt-image-2", *, api_key: str | None = None, base_url: str | None = None, quality: str = "high"):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install Slidecraft with the openai extra to use this provider") from exc
        kwargs: dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model
        self.quality = quality

    def test_connection(self) -> dict[str, Any]:
        """Validate authentication, endpoint reachability, and model access without generating an image."""
        model = self.client.models.retrieve(self.model)
        return {
            "status": "ready",
            "provider": self.provider_id,
            "model": getattr(model, "id", self.model),
        }

    @staticmethod
    def _image_bytes(datum: Any) -> bytes:
        encoded = getattr(datum, "b64_json", None)
        if encoded:
            return base64.b64decode(encoded)
        remote_url = getattr(datum, "url", None)
        if remote_url:
            with urlopen(remote_url, timeout=60) as response:
                return response.read()
        raise RuntimeError("Image provider returned no image payload")

    @staticmethod
    def _write_exact_canvas(payload: bytes, output_path: Path, canvas_px: tuple[int, int]) -> None:
        requested_width, requested_height = canvas_px
        with Image.open(io.BytesIO(payload)) as source:
            source = source.convert("RGBA")
            if source.size == canvas_px:
                final = source
            else:
                fitted = ImageOps.contain(source, canvas_px, Image.Resampling.LANCZOS)
                final = Image.new("RGBA", canvas_px, "white")
                offset = ((requested_width - fitted.width) // 2, (requested_height - fitted.height) // 2)
                final.alpha_composite(fitted, offset)
            final.convert("RGB").save(output_path, format="PNG")

    @staticmethod
    def _provider_input(path: Path, directory: Path, index: int) -> Path:
        """Create a provider-compatible preview while leaving the canonical asset untouched."""
        source = path.resolve()
        if source.suffix.lower() == ".svg":
            try:
                import cairosvg
            except ImportError as exc:
                raise RuntimeError(
                    "SVG project visuals need the Slidecraft OpenAI extra. Install slidecraft-ai[openai]."
                ) from exc
            converted = directory / f"input_{index:02d}.png"
            cairosvg.svg2png(url=str(source), write_to=str(converted))
            return converted
        if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return source
        converted = directory / f"input_{index:02d}.png"
        with Image.open(source) as image:
            image.convert("RGBA").save(converted, format="PNG")
        return converted

    def generate(
        self,
        *,
        prompt: str,
        output_path: Path,
        reference_images: list[Path],
        canvas_px: tuple[int, int],
    ) -> dict[str, Any]:
        size = f"{canvas_px[0]}x{canvas_px[1]}"
        opened = []
        with tempfile.TemporaryDirectory(prefix="slidecraft-image-inputs-") as directory_value:
            directory = Path(directory_value)
            try:
                if reference_images:
                    provider_inputs = [
                        self._provider_input(path, directory, index)
                        for index, path in enumerate(reference_images, start=1)
                    ]
                    opened = [path.open("rb") for path in provider_inputs]
                    response = self.client.images.edit(model=self.model, image=opened, prompt=prompt, size=size, quality=self.quality, output_format="png")
                else:
                    response = self.client.images.generate(model=self.model, prompt=prompt, size=size, quality=self.quality, output_format="png")
            finally:
                for stream in opened:
                    stream.close()
        datum = response.data[0]
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_exact_canvas(self._image_bytes(datum), output_path, canvas_px)
        return {
            "status": "completed",
            "provider": self.provider_id,
            "model": self.model,
            "output_path": str(output_path),
            "canvas_px": list(canvas_px),
            "reference_image_count": len(reference_images),
        }
