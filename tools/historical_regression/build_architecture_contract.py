#!/usr/bin/env python3
"""Build the slide understanding to editable reconstruction contract for the architecture slide."""

from __future__ import annotations

import json
from pathlib import Path

import cv2

from text_authoring import authored_text, logical_paragraphs


ROOT = Path(__file__).resolve().parent
STEP4 = ROOT / "outputs/architecture_full_workflow/step4/slide_entities.json"
SOURCE = ROOT / "inputs/architecture_slide.png"
OUT_DIR = ROOT / "outputs/architecture_full_workflow/contract"


UNIT_SPECS = [
    ("T_title", "native_textbox", ["T_title"]),
    ("T_subtitle", "native_textbox", ["T_subtitle"]),
    ("G_stage1", "standard_powerpoint_shape_connector_composition", ["S_stage1", "B_stage1", "T_badge1", "T_stage1_title", "T_stage1_body"]),
    ("I_stage1", "canonical_icon_or_image_asset", ["I_stage1"]),
    ("G_stage2", "standard_powerpoint_shape_connector_composition", ["S_stage2", "B_stage2", "T_badge2", "T_stage2_title"]),
    ("G_ref1", "known_reusable_element", ["S_ref1", "I_ref1", "T_ref1_title", "T_ref1_body"]),
    ("G_ref2", "known_reusable_element", ["S_ref2", "I_ref2", "T_ref2_title", "T_ref2_body"]),
    ("G_ref3", "known_reusable_element", ["S_ref3", "I_ref3", "T_ref3_title", "T_ref3_body"]),
    ("G_ref4", "known_reusable_element", ["S_ref4", "I_ref4", "T_ref4_title", "T_ref4_body"]),
    ("G_stage3", "standard_powerpoint_shape_connector_composition", ["S_stage3", "B_stage3", "T_badge3", "T_stage3_title", "T_stage3_model", "T_stage3_body"]),
    ("I_stage3", "canonical_icon_or_image_asset", ["I_stage3"]),
    ("G_stage4", "standard_powerpoint_shape_connector_composition", ["S_stage4", "B_stage4", "T_badge4", "T_stage4_title"]),
    ("G_understand1", "known_reusable_element", ["S_understand1", "T_understand1_title", "I_understand1", "T_understand1_body"]),
    ("G_understand2", "known_reusable_element", ["S_understand2", "T_understand2_title", "I_understand2", "T_understand2_body"]),
    ("G_stage5", "standard_powerpoint_shape_connector_composition", ["S_stage5", "B_stage5", "T_badge5", "T_stage5_title"]),
    ("G_reconstruct1", "known_reusable_element", ["S_reconstruct1", "T_reconstruct1_title", "I_reconstruct1", "T_reconstruct1_body"]),
    ("G_reconstruct2", "known_reusable_element", ["S_reconstruct2", "T_reconstruct2_title", "I_reconstruct2", "T_reconstruct2_body"]),
    ("G_output", "known_reusable_element", ["I_output", "T_output"]),
    ("C_stage1_stage2", "standard_powerpoint_shape_connector_composition", ["C_stage1_stage2"]),
    ("C_stage2_stage3", "standard_powerpoint_shape_connector_composition", ["C_stage2_stage3"]),
    ("C_stage3_stage4", "standard_powerpoint_shape_connector_composition", ["C_stage3_stage4"]),
    ("C_stage4_stage5", "standard_powerpoint_shape_connector_composition", ["C_stage4_stage5"]),
    ("C_stage5_output", "standard_powerpoint_shape_connector_composition", ["C_stage5_output"]),
    ("T_page", "native_textbox", ["T_page"]),
]


ROUTE_COLORS = {
    "native_textbox": (238, 126, 32),
    "known_reusable_element": (42, 156, 210),
    "standard_powerpoint_shape_connector_composition": (57, 176, 85),
    "canonical_icon_or_image_asset": (153, 89, 210),
}


def union_bbox(boxes: list[list[int]]) -> list[int]:
    x0 = min(box[0] for box in boxes)
    y0 = min(box[1] for box in boxes)
    x1 = max(box[0] + box[2] for box in boxes)
    y1 = max(box[1] + box[3] for box in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    step4 = json.loads(STEP4.read_text())
    entities = {entity["id"]: entity for entity in step4["entities"]}
    groups = {group["id"]: group for group in step4["groups"]}

    units = []
    owned_ids = set()
    for unit_id, route, children in UNIT_SPECS:
        boxes = [entities[child]["measurement"]["layout_bbox"]["px"] for child in children]
        bbox = groups[unit_id]["bbox_hint"] if unit_id in groups else union_bbox(boxes)
        units.append(
            {
                "id": unit_id,
                "selected_route": route,
                "node_class": "reconstruction_unit",
                "emits_ppt_object": True,
                "bbox_px": bbox,
                "owned_entities": children,
                "measurement_evidence": {
                    "source_entities": children,
                    "contours_are_evidence_only": True,
                    "edge_segments_are_evidence_only": True,
                    "ocr_words_are_evidence_only": True,
                },
            }
        )
        owned_ids.update(children)

    evidence = []
    for entity_id, entity in entities.items():
        evidence.append(
            {
                "id": entity_id,
                "owner": next(unit["id"] for unit in units if entity_id in unit["owned_entities"]),
                "semantic_kind": entity["kind"],
                "semantic_role": entity["role"],
                "bbox_px": entity["measurement"]["layout_bbox"]["px"],
                "visible_bbox_px": entity["measurement"]["visible_bbox"]["px"],
                "mask": entity["measurement"]["selected_mask"],
                "reconstruction_route": (
                    "canonical_icon_or_image_asset" if entity["kind"] == "icon"
                    else "raster_fallback" if entity["kind"] == "image"
                    else None
                ),
            }
        )

    text_contracts = []
    for entity in entities.values():
        if entity["kind"] != "text":
            continue
        logical_text, preserved_breaks = authored_text(entity)
        text_contracts.append(
            {
                "id": entity["id"],
                "source_text_raw": entity["text"],
                "authored_text": logical_text,
                "logical_paragraphs": logical_paragraphs(logical_text),
                "preserved_explicit_breaks": preserved_breaks,
                "rendered_line_count_evidence": entity["text"].count("\n") + 1,
                "layout_bbox_px": entity["measurement"]["layout_bbox"]["px"],
                "measured_line_boxes_px": entity["measurement"]["text_geometry"]["line_boxes_px"],
                "font_policy": "explicit configured family and size",
                "wrap_policy": "native PowerPoint wrapping within immutable outer geometry",
                "autofit_policy": "none",
                "paragraph_spacing_policy": "explicit zero before and after",
            }
        )

    contract = {
        "schema_version": "0.2.0",
        "source_step4": str(STEP4),
        "source_image": str(SOURCE),
        "canvas_px": [1672, 941],
        "reconstruction_unit_count": len(units),
        "reconstruction_units": units,
        "owned_entity_evidence": evidence,
        "text_contracts": text_contracts,
        "hierarchy": {
            "id": "SLIDE_ROOT",
            "children": [
                "T_title", "T_subtitle", "G_stage1", "I_stage1", "G_stage2",
                "G_ref1", "G_ref2", "G_ref3", "G_ref4", "G_stage3", "I_stage3",
                "G_stage4", "G_understand1", "G_understand2", "G_stage5",
                "G_reconstruct1", "G_reconstruct2", "G_output", "T_page"
            ],
        },
        "z_order": [
            "connectors",
            "stage containers",
            "module and reference card backgrounds",
            "badges and canonical SVG icons",
            "text",
        ],
        "explicit_relationships": step4["relationships"],
        "style_contract": {
            "display_font": "Georgia",
            "body_font": "Arial",
            "font_source": "synthetic PwC-inspired fallback and target appearance",
            "primary_orange": "#E84912",
            "dark_text": "#111111",
            "border_gray": "#D8D8D8",
            "stage3_fill": "#FFF7F2",
        },
        "missing_or_inferred": [
            "Exact upstream brand font configuration was unavailable.",
            "Subtle orange gradient stops are inferred from the target image.",
            "Upstream icon asset IDs were unavailable, so the prototype selects a coherent set from the configured canonical SVG library.",
        ],
    }
    assert len(units) == 24
    assert owned_ids == set(entities)
    (OUT_DIR / "reconstruction_contract.json").write_text(json.dumps(contract, indent=2) + "\n")

    lines = [
        "# Reconstruction route audit",
        "",
        f"The 67 slide understanding entities resolve into {len(units)} reconstruction units.",
        "Masks, OCR words, contours, and edge fragments remain evidence only.",
        "",
        "| Unit | Route | Owned semantic entities |",
        "|---|---|---|",
    ]
    for unit in units:
        lines.append(f"| {unit['id']} | {unit['selected_route']} | {', '.join(unit['owned_entities'])} |")
    lines.extend(
        [
            "",
            "## Contract readiness",
            "",
            "Parent and child ownership is explicit for every measured entity.",
            "Connector ordering is explicit and connectors render behind stage containers.",
            "Every text block carries authoritative content, line count, geometry, wrap policy, and autofit policy.",
            "No chart or table route is needed for this slide.",
        ]
    )
    (OUT_DIR / "reconstruction_route_report.md").write_text("\n".join(lines) + "\n")

    canvas = cv2.imread(str(SOURCE))
    for unit in units:
        x, y, w, h = unit["bbox_px"]
        color = ROUTE_COLORS[unit["selected_route"]]
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, 2)
        cv2.putText(canvas, unit["id"], (x + 3, max(y + 15, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    cv2.imwrite(str(OUT_DIR / "reconstruction_units_debug.png"), canvas)
    print(json.dumps({"contract": str(OUT_DIR / "reconstruction_contract.json"), "units": len(units)}, indent=2))


if __name__ == "__main__":
    main()
