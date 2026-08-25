from __future__ import annotations

from slidecraft.reconstruction.contract import build_reconstruction_contract
from slidecraft.reconstruction.scene import build_reconstruction_scene


def _empty_refinement_plan() -> dict:
    return {
        "schema_version": "1.0.0",
        "authored_by": "agent_reasoning",
        "coordinate_space": "generation_region_px",
        "decision_rationale": "No bounded normalization corrections are needed for this fixture.",
        "alignment_groups": [],
    }


def test_contract_routes_semantic_entities_without_emitting_evidence() -> None:
    measured = {
        "source": {"width_px": 1000, "height_px": 500, "path": "/tmp/slide.png"},
        "upstream_handoff": {
            "full_slide_dimensions_px": [1000, 562],
            "generation_region": {"offset_y_px": 31, "dimensions_px": [1000, 500]},
        },
        "entities": [
            {
                "id": "T1",
                "kind": "text",
                "role": "body",
                "reconstruction_route": "native_textbox",
                "reconstruction_significance": "independent_object",
                "measurement": {"layout_bbox": {"px": [10, 10, 300, 50]}},
            },
            {
                "id": "E1",
                "kind": "shape",
                "role": "edge_fragment",
                "reconstruction_route": "standard_powerpoint_shape_connector_composition",
                "reconstruction_significance": "measurement_evidence",
                "measurement": {"layout_bbox": {"px": [1, 1, 2, 2]}},
            },
        ],
    }
    contract = build_reconstruction_contract(measured, {}, _empty_refinement_plan())
    units = {item["id"]: item for item in contract["reconstruction_units"]}
    assert units["T1"]["selected_route"] == "native_textbox"
    assert units["T1"]["emits_ppt_object"] is True
    assert units["E1"]["emits_ppt_object"] is False
    assert contract["coordinate_transform_to_full_slide"]["translation_px"] == [0, 31]


def test_contract_merges_resolved_header_and_footer_content_into_chrome() -> None:
    measured = {
        "source": {"width_px": 1000, "height_px": 500, "path": "/tmp/slide.png"},
        "upstream_handoff": {
            "full_slide_dimensions_px": [1000, 562],
            "generation_region": {"offset_y_px": 31, "dimensions_px": [1000, 500]},
            "deck_chrome_configuration": {
                "enabled": True,
                "header": {"font_size_px": 13},
                "footer": {"font_size_px": 12},
            },
            "resolved_chrome_content": {
                "variant": {"value": "content_slide"},
                "header": {
                    "left_text": {"value": "PROJECT"},
                    "right_text": {"value": "SLIDE TITLE"},
                },
                "footer": {
                    "left_text": {"value": "INTERNAL"},
                    "center_text": {"value": "Project"},
                    "right_text_format": {"value": "25 August 2026 | 2"},
                },
            },
        },
        "entities": [],
    }

    contract = build_reconstruction_contract(measured, {}, _empty_refinement_plan())

    assert contract["deck_chrome_configuration"]["header"]["left_text"] == "PROJECT"
    assert contract["deck_chrome_configuration"]["header"]["right_text"] == "SLIDE TITLE"
    assert contract["deck_chrome_configuration"]["footer"]["left_text"] == "INTERNAL"
    assert contract["deck_chrome_configuration"]["footer"]["center_text"] == "Project"
    assert contract["deck_chrome_configuration"]["footer"]["right_text"] == "25 August 2026 | 2"


def test_project_image_uses_canonical_file_without_an_icon_slot_surface(tmp_path) -> None:
    from PIL import Image

    canonical = tmp_path / "product.png"
    Image.new("RGB", (800, 400), "white").save(canonical)
    measured = {
        "source": {"width_px": 1000, "height_px": 500, "path": str(tmp_path / "slide.png")},
        "upstream_handoff": {
            "full_slide_dimensions_px": [1000, 500],
            "generation_region": {"offset_y_px": 0, "dimensions_px": [1000, 500]},
            "selected_assets": [{
                "internal": {
                    "asset_id": "PROJECT_IMAGE",
                    "canonical_file": str(canonical),
                    "selection_mode": "exact_upstream_asset",
                }
            }],
        },
        "groups": [],
        "relationships": [],
        "entities": [{
            "id": "P_product",
            "kind": "image",
            "role": "product screenshot",
            "upstream_asset_id": "PROJECT_IMAGE",
            "reconstruction_route": "canonical_icon_or_image_asset",
            "reconstruction_significance": "independent_object",
            "measurement": {
                "layout_bbox": {"px": [100, 100, 500, 300]},
                "image_object": {"screenshot_crop_absolute": str(tmp_path / "crop.png")},
            },
        }],
    }
    contract = build_reconstruction_contract(measured, {}, _empty_refinement_plan())
    assert contract["canonical_asset_mappings"][0]["asset_kind"] == "project_image"
    scene = build_reconstruction_scene(
        measured_scene=measured,
        contract=contract,
        design={"normalization": {"constraints": {}}},
        slide_id="S1",
    )
    by_id = {item["id"]: item for item in scene["objects"]}
    assert by_id["P_product"]["source_path"] == str(canonical)
    assert by_id["P_product"]["fit"] == "contain"
    assert by_id["P_product"]["bbox_px"] == [100, 125, 500, 250]
    assert "P_product.icon_slot_surface" not in by_id
