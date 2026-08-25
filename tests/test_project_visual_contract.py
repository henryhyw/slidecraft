from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from slidecraft.deck.slide_jobs import build_slide_request
from slidecraft.orchestration.pipeline import (
    _generation_image_inputs,
    assemble_prompt,
    derive_canvas,
    normalized_assets,
)

ROOT = Path(__file__).resolve().parents[1]


def test_slide_allocation_preserves_optional_and_mandatory_usage(tmp_path: Path) -> None:
    image = tmp_path / "project.png"
    Image.new("RGB", (800, 400), "white").save(image)
    asset = {
        "asset_id": "PROJECT_IMAGE",
        "name": image.name,
        "stored_path": str(image),
        "semantic_role": "product screenshot",
        "usage_policy": "available",
        "slide_ids": [],
        "media_type": "image/png",
        "visual_kind": "raster_image",
        "intrinsic_width": 800,
        "intrinsic_height": 400,
        "intrinsic_aspect_ratio": 2.0,
        "sha256": "test",
    }
    job = {
        "slide_id": "S1",
        "ordinal": 1,
        "communication_job": "Show the product",
        "message_title": "The product is ready",
        "source_atoms": [],
        "relationships": [],
        "asset_allocations": [{
            "asset_id": "PROJECT_IMAGE",
            "usage": "optional",
            "placement": "image_region",
            "reason": "Useful visual proof",
        }],
    }
    request = build_slide_request(job=job, deck_request={}, project_assets=[asset])
    selected = request["user_provided_assets"][0]
    assert selected["mandatory"] is False
    assert selected["placement"] == "image_region"
    assert selected["intrinsic_aspect_ratio"] == 2.0

    job["asset_allocations"][0]["usage"] = "mandatory"
    required = build_slide_request(job=job, deck_request={}, project_assets=[asset])
    assert required["user_provided_assets"][0]["mandatory"] is True


def test_generation_package_attaches_exact_project_visual_after_references(tmp_path: Path) -> None:
    image = tmp_path / "project.png"
    reference = tmp_path / "reference.png"
    Image.new("RGB", (800, 400), "white").save(image)
    Image.new("RGB", (400, 300), "white").save(reference)
    deck = json.loads((ROOT / "src/slidecraft/defaults/deck_design.json").read_text(encoding="utf-8"))
    canvas = derive_canvas(deck)
    assets = normalized_assets({"assets": []}, [{
        "asset_id": "PROJECT_IMAGE",
        "semantic_role": "product screenshot",
        "name": "Product screenshot",
        "description": "Exact product interface",
        "canonical_file": str(image),
        "media_type": "image/png",
        "visual_kind": "raster_image",
        "placement": "image_region",
        "required_usage": True,
        "mandatory": True,
        "intrinsic_aspect_ratio": 2.0,
    }], canvas, deck)
    references = [{"reference_id": "REF_1", "path": str(reference), "name": "Reference"}]
    inputs = _generation_image_inputs(references, assets)

    assert [item["input_role"] for item in inputs] == ["visual_reference", "project_visual"]
    assert inputs[1]["asset_id"] == "PROJECT_IMAGE"
    assert inputs[1]["intrinsic_aspect_ratio"] == 2.0
    assert inputs[1]["preserve_exact_content"] is True
    assert inputs[1]["preserve_aspect_ratio"] is True

    prompt = assemble_prompt(
        deck,
        canvas,
        {
            "slide_id": "S1",
            "objective": "Show product",
            "exact_content": {"title": "Product", "subtitle": "", "content": []},
        },
        {"constraint_register": []},
        {
            "main_message": "The product is ready",
            "reading_logic": "Read the proof",
            "visual_intent": {"structure": "Evidence-led", "emphasis": "Product image"},
        },
        {
            "profile_id": "consulting",
            "name": "Consulting",
            "version": "1",
            "slide_reasoning": {"principles": []},
            "visual_communication": {"principles": []},
            "writing": {"principles": []},
            "design_freedom": {},
        },
        assets,
        references,
    )
    assert "Attached image input: 2" in prompt
    assert "preserve the supplied image exactly" in prompt
    assert "Intrinsic aspect ratio: 2.0:1" in prompt
