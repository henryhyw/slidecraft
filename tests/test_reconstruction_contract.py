from __future__ import annotations

from slidecraft.reconstruction.contract import build_reconstruction_contract


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
                "reconstruction_significance": "independent_object",
                "measurement": {"layout_bbox": {"px": [10, 10, 300, 50]}},
            },
            {
                "id": "E1",
                "kind": "shape",
                "role": "edge_fragment",
                "reconstruction_significance": "measurement_evidence",
                "measurement": {"layout_bbox": {"px": [1, 1, 2, 2]}},
            },
        ],
    }
    contract = build_reconstruction_contract(measured, {})
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

    contract = build_reconstruction_contract(measured, {})

    assert contract["deck_chrome_configuration"]["header"]["left_text"] == "PROJECT"
    assert contract["deck_chrome_configuration"]["header"]["right_text"] == "SLIDE TITLE"
    assert contract["deck_chrome_configuration"]["footer"]["left_text"] == "INTERNAL"
    assert contract["deck_chrome_configuration"]["footer"]["center_text"] == "Project"
    assert contract["deck_chrome_configuration"]["footer"]["right_text"] == "25 August 2026 | 2"
