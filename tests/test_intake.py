from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from slidecraft.intake import normalize_deck_intake


def test_path_only_image_waits_for_agent_visual_interpretation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        image = root / "diagram.png"
        Image.new("RGB", (64, 32), "white").save(image)
        request = {
            "deck_id": "demo",
            "materials": [{"material_id": "VISUAL_1", "modality": "image", "path": str(image), "authority": "authoritative"}],
        }

        intake = normalize_deck_intake(request, root)

    assert intake["quality"]["planning_ready"] is False
    assert intake["quality"]["pending_material_ids"] == ["VISUAL_1"]
    assert intake["source_atoms"] == []


def test_agent_interpretation_makes_visual_source_plannable() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        image = root / "diagram.png"
        Image.new("RGB", (64, 32), "white").save(image)
        request = {
            "deck_id": "demo",
            "materials": [{
                "material_id": "VISUAL_1",
                "modality": "image",
                "path": str(image),
                "content": {"source_grounded_interpretation": "Three stages converge on one outcome."},
                "authority": "authoritative",
            }],
        }

        intake = normalize_deck_intake(request, root)

    assert intake["quality"]["planning_ready"] is True
    assert intake["source_atoms"][0]["value"]["source_grounded_interpretation"] == "Three stages converge on one outcome."
