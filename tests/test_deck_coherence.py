from __future__ import annotations

from copy import deepcopy

from slidecraft.deck.coherence import validate_constructor_deck


def _scene(slide_id: str) -> dict:
    return {
        "slide_id": slide_id,
        "dimensions_px": [1000, 562],
        "background": "#FFFFFF",
        "design_config_id": "design_1",
        "objects": [
            {"id": "CHROME_HEADER.left", "kind": "textbox", "bbox_px": [20, 4, 400, 20], "style": {"font_family": "Arial", "font_weight": "bold", "color": "#444444", "alignment": "left"}},
            {"id": "CHROME_FOOTER.left", "kind": "textbox", "bbox_px": [20, 540, 300, 18], "style": {"font_family": "Arial", "font_weight": "bold", "color": "#444444", "alignment": "left"}},
            {"id": f"{slide_id}_title", "kind": "textbox", "semantic_role": "slide_title", "bbox_px": [30, 40, 700, 70], "style": {"font_family": "Georgia", "font_weight": "regular", "color": "#111111", "alignment": "left"}},
        ],
    }


def test_constructor_deck_accepts_a_shared_visual_system() -> None:
    scenes = [_scene("S1"), _scene("S2")]
    planned = [
        {"slide_id": "S1", "ordinal": 1, "route": "image_generation"},
        {"slide_id": "S2", "ordinal": 2, "route": "image_generation"},
    ]
    design = {
        "config_id": "design_1",
        "full_slide_px": [1000, 562],
        "style": {"background": "#FFFFFF"},
        "deck_chrome": {"enabled": True},
    }

    result = validate_constructor_deck(scenes=scenes, planned_slides=planned, deck_design=design)

    assert result["passed"] is True


def test_constructor_deck_rejects_chrome_and_typography_drift() -> None:
    scenes = [_scene("S1"), _scene("S2")]
    scenes[1] = deepcopy(scenes[1])
    scenes[1]["objects"][0]["bbox_px"][0] += 3
    scenes[1]["objects"][2]["style"]["font_family"] = "Arial"
    planned = [
        {"slide_id": "S1", "ordinal": 1, "route": "image_generation"},
        {"slide_id": "S2", "ordinal": 2, "route": "image_generation"},
    ]
    design = {
        "config_id": "design_1",
        "full_slide_px": [1000, 562],
        "style": {"background": "#FFFFFF"},
        "deck_chrome": {"enabled": True},
    }

    result = validate_constructor_deck(scenes=scenes, planned_slides=planned, deck_design=design)

    assert result["passed"] is False
    categories = {item["category"] for item in result["issues"] if item["severity"] == "high"}
    assert {"deck_chrome", "typography"} <= categories
