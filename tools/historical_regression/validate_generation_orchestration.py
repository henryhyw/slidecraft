#!/usr/bin/env python3
"""Validate generation preparation state before a prompt is sent to image generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/architecture_generation_orchestration")
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    state = json.loads((output_dir / "generation_context.json").read_text(encoding="utf-8"))
    handoff = json.loads((output_dir / "reconstruction_handoff.json").read_text(encoding="utf-8"))
    prompt = (output_dir / "imagegen_prompt.txt").read_text(encoding="utf-8")

    canvas = state["derived_canvas"]
    full_width, full_height = canvas["full_slide_px"]
    expected_height = full_height - canvas["header_exclusion_px"] - canvas["footer_exclusion_px"]
    assert canvas["generation_canvas_px"] == [full_width, expected_height]
    assert canvas["generation_offset_y_px"] == canvas["header_exclusion_px"]
    assert canvas["title_is_inside_generation_canvas"] is True
    assert canvas["header_and_footer_are_generated"] is False
    assert handoff["generation_region"]["dimensions_px"] == canvas["generation_canvas_px"]
    assert handoff["exact_source_content"] == state["slide_input"]["exact_content"]
    assert handoff["exact_title_text"] == state["slide_input"]["exact_content"]["title"]
    assert canvas["header_exclusion_px"] == 41
    assert canvas["footer_exclusion_px"] == 41
    assert state["generation"]["attached_asset_paths"] == []
    assert state["generation"]["asset_prompt_mode"] == "description_only"
    preflight = state["generation_preflight"]
    assert preflight["approval"]["status"] == "awaiting_user_confirmation"
    assert preflight["approval"]["generation_released"] is False
    assert preflight["quality"]["ready_for_approval"] is True
    assert state["generation"]["execution"] == "blocked_until_preflight_approval"
    assert state["generation"]["prompt_status"] == "draft_pending_approval"
    assert handoff["generation_authorization"]["fingerprint"] == preflight["approval"]["fingerprint"]
    assert handoff["target_image"]["status"] == "generation_blocked_pending_approval"
    assert (output_dir / "generation_preflight.md").exists()
    assert (output_dir / "generation_package.json").exists()

    guidance = state["guidance_profile"]
    assert guidance["profile_id"] == "consulting"
    assert guidance["resolution"]["lineage_child_to_parent"] == ["consulting", "base"]
    assert handoff["guidance_profile"] == guidance
    assert "fonts" in guidance["exclusions"]

    intake = state["intake_manifest"]
    assert intake["quality"]["authoritative_source_atom_count"] > 0
    assert intake["quality"]["hard_constraint_count"] > 0
    assert intake["quality"]["requires_user_resolution"] is False
    assert handoff["intake_manifest"] == intake

    references = state["reference_retrieval"]["visual_references"]
    assert len(references) == 3
    visual_reference_retrieval = state["reference_retrieval"]["visual_reference_retrieval"]
    assert visual_reference_retrieval["retrieval_mode"] == "metadata_first_semantic"
    assert visual_reference_retrieval["visual_files_opened_before_ranking"] is False
    assert visual_reference_retrieval["maximum_results"] == 3
    for reference in references:
        path = Path(reference["path"])
        assert path.exists()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == reference["sha256"]
        assert reference["must_not_be_copied_as_layout"] is True
        assert reference["retrieval_reason"]

    icon_retrieval = state["reference_retrieval"]["icon_retrieval"]
    assert icon_retrieval["retrieval_mode"] == "semantic_metadata_first"
    assert Path(icon_retrieval["manifest"]).exists()
    component_retrieval = state["reference_retrieval"]["known_component_retrieval"]
    assert component_retrieval["retrieval_mode"] == "semantic_metadata_first"

    assets = state["normalized_available_assets"]["assets"]
    assert assets
    for asset in assets:
        canonical_file = asset["internal"].get("canonical_file")
        if canonical_file:
            assert Path(canonical_file).exists()
        else:
            assert asset["internal"].get("attachment_status") == "pending_file_binding"
        width, height = asset["dimensions"]["target_visual_footprint_px"]
        assert width > 0 and height > 0
        assert asset["dimensions"]["preserve_aspect_ratio"] is True
        slot = asset["dimensions"]["icon_slot"]
        assert slot["authoritative_for_placement"] is True
        assert slot["generated_glyph_authoritative"] is False
        assert slot["fit"] == "contain"
        assert slot["allow_stretch"] is False
        assert all(value > 0 for value in slot["size_px"])
        assert slot["size_px"][0] >= width and slot["size_px"][1] >= height

    mandatory = [asset for asset in assets if asset.get("required_usage")]
    expected_mandatory = set(state["deck_design_configuration"]["user_asset_policy"]["mandatory_asset_ids"])
    assert {asset["internal"]["asset_id"] for asset in mandatory} == expected_mandatory
    assert all(asset["internal"]["generation_attachment_mode"] == "description_only" for asset in mandatory)
    assert handoff["icon_slot_configuration"]["authoritative_placement_object"] == "slot_box"
    assert handoff["connector_configuration_qa"]["status"] == "passed"

    forbidden = [
        "reconstruction object id",
        "scene ir",
        "sam reconstruction logic",
        "opencv reconstruction logic",
        "z-order reconstruction",
        "reconstruction schema",
    ]
    lowered = prompt.lower()
    assert "authoritative icon slot" in lowered
    assert "make the slot itself match the stated width and height" in lowered
    assert "never stretch" in lowered
    assert "source svg files are not attached" in lowered
    assert state["deck_design_configuration"]["connectors"]["branch_route"] in lowered
    assert "active hard human constraints" in lowered
    assert "selected communication guidance" in lowered
    assert "consulting" in lowered
    for constraint_id in intake["hard_constraint_ids"]:
        assert constraint_id.lower() in lowered
    for phrase in forbidden:
        assert phrase not in lowered, f"Downstream implementation detail leaked into prompt: {phrase}"

    report = {
        "status": "passed",
        "generation_canvas_px": canvas["generation_canvas_px"],
        "generation_offset_y_px": canvas["generation_offset_y_px"],
        "reference_count": len(references),
        "authoritative_source_atom_count": intake["quality"]["authoritative_source_atom_count"],
        "hard_constraint_count": intake["quality"]["hard_constraint_count"],
        "canonical_asset_count": len(assets),
        "dimensioned_asset_count": len(assets),
        "authoritative_icon_slot_count": len(assets),
        "mandatory_description_only_asset_count": len(mandatory),
        "connector_configuration_qa": handoff["connector_configuration_qa"],
        "pending_user_asset_bindings": [asset["internal"]["asset_id"] for asset in assets if not asset["internal"].get("canonical_file")],
        "exact_content_preserved": True,
        "downstream_prompt_leakage_detected": False,
        "generation_preflight_status": preflight["approval"]["status"],
        "generation_released": preflight["approval"]["generation_released"],
    }
    (output_dir / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
