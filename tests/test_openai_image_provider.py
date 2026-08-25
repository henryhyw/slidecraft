from __future__ import annotations

import base64
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from slidecraft.providers.openai import OpenAIImageGenerationProvider


def _png_payload(size: tuple[int, int]) -> str:
    stream = io.BytesIO()
    Image.new("RGB", size, "#d94f14").save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode("ascii")


def test_image_generation_uses_openai_image_api_and_restores_requested_canvas(tmp_path: Path) -> None:
    client = Mock()
    client.images.generate.return_value = SimpleNamespace(
        data=[SimpleNamespace(b64_json=_png_payload((1024, 1024)), url=None)]
    )
    with patch("openai.OpenAI", return_value=client):
        provider = OpenAIImageGenerationProvider(model="gpt-image-2", api_key="test-key")
        output = tmp_path / "generated.png"
        result = provider.generate(
            prompt="A precise presentation canvas",
            output_path=output,
            reference_images=[],
            canvas_px=(1600, 900),
        )

    client.images.generate.assert_called_once_with(
        model="gpt-image-2",
        prompt="A precise presentation canvas",
        size="1600x900",
        quality="high",
        output_format="png",
    )
    with Image.open(output) as image:
        assert image.size == (1600, 900)
    assert result["canvas_px"] == [1600, 900]
    assert result["reference_image_count"] == 0


def test_connection_check_uses_configured_model_without_generating() -> None:
    client = Mock()
    client.models.retrieve.return_value = SimpleNamespace(id="gpt-image-2")
    with patch("openai.OpenAI", return_value=client):
        provider = OpenAIImageGenerationProvider(
            model="gpt-image-2",
            api_key="test-key",
            base_url="https://images.example.test/v1",
        )
        result = provider.test_connection()

    client.models.retrieve.assert_called_once_with("gpt-image-2")
    client.images.generate.assert_not_called()
    assert result == {"status": "ready", "provider": "openai_images", "model": "gpt-image-2"}


def test_image_edit_receives_every_ordered_generation_input(tmp_path: Path) -> None:
    first = tmp_path / "reference.png"
    second = tmp_path / "project-visual.png"
    Image.new("RGB", (400, 300), "white").save(first)
    Image.new("RGB", (800, 400), "white").save(second)
    client = Mock()
    client.images.edit.return_value = SimpleNamespace(
        data=[SimpleNamespace(b64_json=_png_payload((1024, 1024)), url=None)]
    )
    with patch("openai.OpenAI", return_value=client):
        provider = OpenAIImageGenerationProvider(model="gpt-image-2", api_key="test-key")
        result = provider.generate(
            prompt="Use the ordered visual inputs",
            output_path=tmp_path / "generated.png",
            reference_images=[first, second],
            canvas_px=(1600, 900),
        )

    call = client.images.edit.call_args.kwargs
    assert [Path(stream.name).name for stream in call["image"]] == ["reference.png", "project-visual.png"]
    assert call["prompt"] == "Use the ordered visual inputs"
    assert result["reference_image_count"] == 2
