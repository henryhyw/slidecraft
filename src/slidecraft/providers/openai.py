"""OpenAI Responses API implementation of structured visual extraction."""

from __future__ import annotations

import base64
import io
import mimetypes
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from PIL import Image, ImageOps


class OpenAIStructuredVisionProvider:
    provider_id = "openai_responses"
    supports_connector_audit = True

    def __init__(self, model: str, *, api_key: str | None = None, base_url: str | None = None):
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

    @staticmethod
    def _data_url(path: Path) -> str:
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def extract(
        self,
        *,
        image_path: Path,
        prompt: str,
        schema: dict[str, Any],
        operation: str,
    ) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "You are a precise visual document compiler. Return only the requested structured artifact. "
                "Every localized object must be grounded in visible evidence and upstream context."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": self._data_url(image_path), "detail": "original"},
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": operation,
                    "schema": schema,
                    "strict": False,
                }
            },
        )
        if not response.output_text:
            raise RuntimeError(f"Structured vision provider returned no text for {operation}")
        return __import__("json").loads(response.output_text)


class OpenAIStructuredReasoningProvider:
    provider_id = "openai_responses"

    def __init__(self, model: str, *, api_key: str | None = None, base_url: str | None = None):
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

    def reason(self, *, prompt: str, schema: dict[str, Any], operation: str) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "You are the planning compiler inside a presentation system. Preserve authoritative source content, "
                "obey hard constraints, and return the requested typed artifact."
            ),
            input=prompt,
            text={"format": {"type": "json_schema", "name": operation, "schema": schema, "strict": False}},
        )
        if not response.output_text:
            raise RuntimeError(f"Structured reasoning provider returned no text for {operation}")
        return __import__("json").loads(response.output_text)


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
        try:
            if reference_images:
                opened = [path.resolve().open("rb") for path in reference_images]
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
