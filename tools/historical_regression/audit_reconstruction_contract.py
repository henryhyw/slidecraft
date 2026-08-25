#!/usr/bin/env python3
"""Audit and strengthen the contract between slide understanding and editable reconstruction."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent
SOURCE_JSON = ROOT / "outputs/sample_slide/slide_entities.json"
SEMANTIC_MAP = ROOT / "semantic_map.json"
SOURCE_IMAGE = ROOT / "sample slide.png"
SOURCE_DEBUG = ROOT / "outputs/sample_slide/debug_overlay.png"
OUT_DIR = ROOT / "outputs/reconstruction_contract"

ROUTES = {
    "native_textbox": "native textbox",
    "native_table": "native table",
    "native_editable_chart": "native/editable chart",
    "canonical_icon_or_image_asset": "canonical icon or image asset",
    "known_reusable_element": "known reusable element",
    "standard_powerpoint_shape_connector_composition": "standard PowerPoint shape / connector composition",
    "custom_fitted_geometry": "custom fitted geometry",
    "raster_fallback": "raster fallback",
}

ROUTE_COLORS = {
    "native_textbox": (242, 132, 31),
    "native_table": (30, 186, 205),
    "canonical_icon_or_image_asset": (232, 160, 45),
    "known_reusable_element": (75, 75, 75),
    "standard_powerpoint_shape_connector_composition": (58, 180, 92),
    "custom_fitted_geometry": (191, 68, 211),
    "raster_fallback": (80, 80, 220),
}

TABLE_TEXT = {
    "T_h_step", "T_h_req", "T_h_cap", "T_h_diff",
    "T_num1", "T_label1", "T_req1", "T_cap1", "T_diff1",
    "T_num2", "T_label2", "T_req2", "T_cap2", "T_diff2",
    "T_num3", "T_label3", "T_req3a", "T_req3b", "T_cap3a", "T_cap3b", "T_diff3a", "T_diff3b",
    "T_num4", "T_label4", "T_req4", "T_cap4", "T_diff4",
}
TABLE_UNDERLAYS = {"S_header_fill", "S_step1", "S_step2", "S_step3", "S_step4"}
ICON_IDS = {"I_step1", "I_step2", "I_step3", "I_step4"}
INSIGHT_TEXT = {"T_key_label", "T_insight_num1", "T_insight1", "T_insight_num2", "T_insight2", "T_insight_num3", "T_insight3"}


def load() -> tuple[dict[str, Any], dict[str, Any], np.ndarray]:
    source = json.loads(SOURCE_JSON.read_text())
    semantic = json.loads(SEMANTIC_MAP.read_text())
    image = cv2.imread(str(SOURCE_IMAGE))
    if image is None:
        raise FileNotFoundError(SOURCE_IMAGE)
    return source, semantic, image


def entity_map(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entity["id"]: entity for entity in source["entities"]}


def semantic_line_boxes(entity: dict[str, Any]) -> list[list[int]]:
    """Split the measured mask using semantic line breaks as the stable line count."""
    text = entity.get("text", "")
    lines = text.split("\n")
    box = entity["measurement"]["layout_bbox"]["px"]
    x, y, w, h = box
    mask_path = SOURCE_JSON.parent / entity["measurement"]["opencv_mask"]
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return []
    results = []
    for index in range(len(lines)):
        top = y + round(index * h / len(lines))
        bottom = y + round((index + 1) * h / len(lines))
        local = mask[top:bottom, x : x + w]
        ys, xs = np.where(local > 0)
        if len(xs):
            results.append([int(x + xs.min()), int(top + ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)])
        else:
            results.append([x, top, w, max(1, bottom - top)])
    return results


def cell(row: str, col: str, bbox: list[int], content: list[str], **extra: Any) -> dict[str, Any]:
    result = {"address": f"{row}.{col}", "row": row, "column": col, "bbox_px": bbox, "content_nodes": content}
    result.update(extra)
    return result


def table_contract() -> dict[str, Any]:
    rows = {
        "H": [183, 232], "R1": [232, 350], "R2": [350, 474],
        "R3A": [474, 583], "R3B": [583, 683], "R4": [683, 784],
    }
    cols = {
        "step_number": [36, 98], "step_visual": [98, 380], "requirement": [380, 839],
        "capability": [839, 1227], "difficulty": [1227, 1638],
    }

    def bb(row: str, col: str) -> list[int]:
        rx = rows[row]
        cx = cols[col]
        return [cx[0], rx[0], cx[1] - cx[0], rx[1] - rx[0]]

    cells = [
        cell("H", "step", [36, 183, 344, 49], ["T_h_step"], merge="H.step_number:H.step_visual", transparent_for_underlay="S_header_fill"),
        cell("H", "requirement", bb("H", "requirement"), ["T_h_req"], transparent_for_underlay="S_header_fill"),
        cell("H", "capability", bb("H", "capability"), ["T_h_cap"], transparent_for_underlay="S_header_fill"),
        cell("H", "difficulty", bb("H", "difficulty"), ["T_h_diff"], transparent_for_underlay="S_header_fill"),
    ]
    row_content = {
        "R1": {"step_number": ["T_num1"], "step_visual": ["I_step1", "T_label1"], "requirement": ["T_req1"], "capability": ["T_cap1"], "difficulty": ["T_diff1"]},
        "R2": {"step_number": ["T_num2"], "step_visual": ["I_step2", "T_label2"], "requirement": ["T_req2"], "capability": ["T_cap2"], "difficulty": ["T_diff2"]},
        "R3A": {"step_number": ["T_num3"], "step_visual": ["I_step3", "T_label3"], "requirement": ["T_req3a"], "capability": ["T_cap3a"], "difficulty": ["T_diff3a"]},
        "R3B": {"requirement": ["T_req3b"], "capability": ["T_cap3b"], "difficulty": ["T_diff3b"]},
        "R4": {"step_number": ["T_num4"], "step_visual": ["I_step4", "T_label4"], "requirement": ["T_req4"], "capability": ["T_cap4"], "difficulty": ["T_diff4"]},
    }
    underlays = {"R1": "S_step1", "R2": "S_step2", "R3A": "S_step3", "R4": "S_step4"}
    for row, mapping in row_content.items():
        for col, content in mapping.items():
            extra: dict[str, Any] = {}
            if col == "step_number" and row in underlays:
                extra["transparent_for_underlay"] = underlays[row]
            if row == "R3A" and col in {"step_number", "step_visual"}:
                merged_bbox = [cols[col][0], rows["R3A"][0], cols[col][1] - cols[col][0], rows["R3B"][1] - rows["R3A"][0]]
                extra["merge"] = f"R3A.{col}:R3B.{col}"
                cells.append(cell(row, col, merged_bbox, content, **extra))
            else:
                cells.append(cell(row, col, bb(row, col), content, **extra))
    return {
        "id": "TABLE_main",
        "selected_route": "native_table",
        "ppt_object_count": 1,
        "bbox_px": [36, 183, 1602, 601],
        "columns": [{"id": key, "x0": value[0], "x1": value[1], "width_px": value[1] - value[0]} for key, value in cols.items()],
        "rows": [{"id": key, "y0": value[0], "y1": value[1], "height_px": value[1] - value[0]} for key, value in rows.items()],
        "corrected_merges": ["H.step_number:H.step_visual", "R3A.step_number:R3B.step_number", "R3A.step_visual:R3B.step_visual"],
        "cells": cells,
        "render_policy": {
            "cell_text_nodes_are_owned_content": True,
            "icons_are_overlay_groups": True,
            "gradient_regions_are_underlay_shapes": True,
            "body_cells_use_white_fill": True,
            "header_and_step_number_cells_are_transparent": True,
            "row3_divider_is_a_native_table_border": True,
        },
        "readiness": "partial",
        "missing": [
            "Exact border widths, dash pattern, and per-edge colors",
            "Per-cell internal margins and vertical alignment",
            "Reliable font family, size, weight, italic, and run-level style",
            "Gradient stop positions and angle for the underlay shapes",
        ],
    }


def assignment(entity: dict[str, Any]) -> dict[str, Any]:
    eid = entity["id"]
    result = {
        "id": eid,
        "semantic_kind": entity["kind"],
        "semantic_role": entity["role"],
        "bbox_px": entity["measurement"]["layout_bbox"]["px"],
        "measurement_evidence": {
            "visible_bbox_px": entity["measurement"]["visible_bbox"]["px"],
            "mask": entity["measurement"]["selected_mask"],
            "contours_are_evidence_only": True,
            "edge_segments_are_evidence_only": True,
            "dominant_colors_are_evidence_only": True,
        },
    }
    if entity["kind"] == "image":
        image_object = entity["measurement"]["image_object"]
        upstream_asset = entity.get("upstream_asset_mapping")
        result.update(
            selected_route="canonical_icon_or_image_asset" if upstream_asset else "raster_fallback",
            alternate_route="raster_fallback" if upstream_asset else "canonical_icon_or_image_asset",
            node_class="reconstruction_unit",
            emits_ppt_object=True,
            ppt_object_form="embedded_picture",
            render_owner=eid,
            confidence="high",
            image_contract={
                "exact_upstream_asset": upstream_asset,
                "screenshot_crop": image_object["screenshot_crop_absolute"],
                "crop_mode": image_object["crop_mode"],
                "rotation_degrees": image_object["rotation_degrees"],
                "preserve_aspect_ratio": image_object["preserve_aspect_ratio"],
                "internal_pixels_are_not_entities": True,
            },
        )
    elif eid == "TABLE_main":
        result.update(selected_route="native_table", node_class="reconstruction_unit", emits_ppt_object=True, render_owner=eid, confidence="high")
    elif eid in TABLE_TEXT:
        result.update(selected_route="native_table", node_class="owned_content", emits_ppt_object=False, render_owner="TABLE_main", confidence="medium")
    elif eid == "L_row3_split":
        result.update(selected_route="native_table", node_class="measurement_evidence", emits_ppt_object=False, render_owner="TABLE_main", confidence="high")
    elif eid in TABLE_UNDERLAYS:
        result.update(selected_route="standard_powerpoint_shape_connector_composition", node_class="reconstruction_unit", emits_ppt_object=True, render_owner=eid, confidence="high", z_layer="table_underlay")
    elif eid in ICON_IDS:
        result.update(
            selected_route="standard_powerpoint_shape_connector_composition",
            alternate_route="canonical_icon_or_image_asset",
            fallback_route="raster_fallback",
            node_class="reconstruction_unit",
            emits_ppt_object=True,
            ppt_object_form="group_of_shapes_and_connectors",
            render_owner=eid,
            confidence="medium",
            z_layer="table_overlay",
        )
    elif eid in {"T_title", "T_subtitle"} | INSIGHT_TEXT:
        result.update(selected_route="native_textbox", node_class="reconstruction_unit", emits_ppt_object=True, render_owner=eid, confidence="medium")
    elif eid == "S_insights_bg":
        result.update(selected_route="standard_powerpoint_shape_connector_composition", node_class="reconstruction_unit", emits_ppt_object=True, render_owner=eid, confidence="high", z_layer="insights_background")
    elif eid == "S_key_shape":
        result.update(
            selected_route="custom_fitted_geometry",
            alternate_route="standard_powerpoint_shape_connector_composition",
            fallback_route="raster_fallback",
            node_class="reconstruction_unit",
            emits_ppt_object=True,
            render_owner=eid,
            confidence="high",
            z_layer="insights_accent",
            geometry_policy="Use the four-point SAM contour as a fitted closed freeform. No Bezier control points are needed for the observed straight edges.",
        )
    elif eid in {"L_insight_sep1", "L_insight_sep2"}:
        result.update(selected_route="standard_powerpoint_shape_connector_composition", node_class="reconstruction_unit", emits_ppt_object=True, ppt_object_form="straight_connector", render_owner=eid, confidence="high")
    else:
        raise ValueError(f"No route for {eid}")
    return result


def text_contracts(entities: dict[str, dict[str, Any]], table: dict[str, Any]) -> list[dict[str, Any]]:
    cell_for: dict[str, dict[str, Any]] = {}
    for cell_def in table["cells"]:
        for node in cell_def["content_nodes"]:
            if node.startswith("T_"):
                cell_for[node] = cell_def
    results = []
    for entity in entities.values():
        if entity["kind"] != "text":
            continue
        eid = entity["id"]
        record = {
            "id": eid,
            "semantic_text": entity["text"],
            "authoritative_line_count": entity["text"].count("\n") + 1,
            "measured_line_boxes_px": semantic_line_boxes(entity),
            "layout_bbox_px": entity["measurement"]["layout_bbox"]["px"],
            "visible_bbox_px": entity["measurement"]["visible_bbox"]["px"],
            "explicit_line_breaks": True,
            "style_readiness": "partial",
            "missing_style": ["exact font family", "exact font size", "line spacing", "paragraph spacing", "run-level formatting"],
        }
        if eid in cell_for:
            c = cell_for[eid]
            tx, ty, tw, th = record["layout_bbox_px"]
            cx, cy, cw, ch = c["bbox_px"]
            record.update(
                owner_type="native_table_cell",
                owner_id="TABLE_main",
                cell_address=c["address"],
                observed_insets_px=[tx - cx, ty - cy, cx + cw - (tx + tw), cy + ch - (ty + th)],
                recommended_vertical_alignment="middle",
            )
        else:
            record.update(owner_type="native_textbox", owner_id=eid, recommended_vertical_alignment="top")
        results.append(record)
    return results


def hierarchy() -> dict[str, Any]:
    return {
        "id": "SLIDE_ROOT",
        "node_class": "semantic_group",
        "selected_route": "known_reusable_element",
        "emits_ppt_object": False,
        "children": [
            {
                "id": "G_header",
                "node_class": "semantic_group",
                "selected_route": "known_reusable_element",
                "emits_ppt_object": False,
                "children": ["T_title", "T_subtitle"],
            },
            {
                "id": "G_capability_matrix",
                "node_class": "semantic_group",
                "selected_route": "known_reusable_element",
                "emits_ppt_object": False,
                "children": [
                    "S_header_fill", "S_step1", "S_step2", "S_step3", "S_step4",
                    {
                        "id": "TABLE_main",
                        "node_class": "reconstruction_unit",
                        "selected_route": "native_table",
                        "emits_ppt_object": True,
                        "children": [
                            {"id": "G_table_header", "node_class": "logical_group", "emits_ppt_object": False, "children": ["T_h_step", "T_h_req", "T_h_cap", "T_h_diff"]},
                            {"id": "G_row1", "node_class": "logical_group", "emits_ppt_object": False, "children": ["T_num1", "I_step1", "T_label1", "T_req1", "T_cap1", "T_diff1"]},
                            {"id": "G_row2", "node_class": "logical_group", "emits_ppt_object": False, "children": ["T_num2", "I_step2", "T_label2", "T_req2", "T_cap2", "T_diff2"]},
                            {"id": "G_row3", "node_class": "logical_group", "emits_ppt_object": False, "children": ["T_num3", "I_step3", "T_label3", "T_req3a", "T_req3b", "T_cap3a", "T_cap3b", "T_diff3a", "T_diff3b", "L_row3_split"]},
                            {"id": "G_row4", "node_class": "logical_group", "emits_ppt_object": False, "children": ["T_num4", "I_step4", "T_label4", "T_req4", "T_cap4", "T_diff4"]}
                        ]
                    }
                ],
            },
            {
                "id": "G_insights",
                "node_class": "semantic_group",
                "selected_route": "known_reusable_element",
                "emits_ppt_object": False,
                "children": [
                    "S_insights_bg", "S_key_shape", "T_key_label",
                    {"id": "G_insight1", "node_class": "logical_group", "selected_route": "known_reusable_element", "emits_ppt_object": False, "children": ["T_insight_num1", "T_insight1"]},
                    {"id": "G_insight2", "node_class": "logical_group", "selected_route": "known_reusable_element", "emits_ppt_object": False, "children": ["T_insight_num2", "T_insight2"]},
                    {"id": "G_insight3", "node_class": "logical_group", "selected_route": "known_reusable_element", "emits_ppt_object": False, "children": ["T_insight_num3", "T_insight3"]},
                    "L_insight_sep1", "L_insight_sep2",
                ],
            },
        ],
    }


def validate_contract(contract: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    assignments = contract["reconstruction_units"]
    source_ids = {entity["id"] for entity in source["entities"]}
    assignment_ids = [item["id"] for item in assignments]
    assert len(assignment_ids) == len(set(assignment_ids))
    assert set(assignment_ids) == source_ids

    table = contract["native_table_contract"]
    table_content = [node for cell_def in table["cells"] for node in cell_def["content_nodes"]]
    mapped_table_text = [node for node in table_content if node.startswith("T_")]
    assert set(mapped_table_text) == TABLE_TEXT
    assert len(mapped_table_text) == len(set(mapped_table_text))
    assert set(table["corrected_merges"]) == {
        "H.step_number:H.step_visual",
        "R3A.step_number:R3B.step_number",
        "R3A.step_visual:R3B.step_visual",
    }

    text_contract_list = contract["text_contracts"]
    for text_item in text_contract_list:
        assert text_item["authoritative_line_count"] == len(text_item["measured_line_boxes_px"])
        if text_item["id"] in TABLE_TEXT:
            assert text_item["owner_id"] == "TABLE_main"
            assert text_item["owner_type"] == "native_table_cell"

    emitted = [item for item in assignments if item["emits_ppt_object"]]
    assert len(emitted) == 23
    non_emitting = [item for item in assignments if not item["emits_ppt_object"]]
    assert len(non_emitting) == 28
    assert all(item["node_class"] in {"owned_content", "measurement_evidence"} for item in non_emitting)

    key_shape = next(entity for entity in source["entities"] if entity["id"] == "S_key_shape")
    largest_contour = key_shape["measurement"]["contours_px"][0]
    assert len(largest_contour) == 4
    return {
        "status": "passed",
        "checks": [
            "all 51 semantic entities have exactly one route assignment",
            "all 27 table text nodes have exactly one cell owner",
            "row 3 vertical merges are separated by step column",
            "all semantic text lines have one measured line box",
            "23 nodes emit PowerPoint reconstruction units",
            "28 nodes remain owned content or evidence",
            "the fitted accent has a four-point contour",
        ],
    }


def render_debug(image: np.ndarray, source: dict[str, Any], assignments: list[dict[str, Any]], output: Path) -> None:
    canvas = image.copy()
    overlay = np.full_like(canvas, 255)
    canvas = cv2.addWeighted(canvas, 0.76, overlay, 0.24, 0)
    by_id = {item["id"]: item for item in assignments}

    top_groups = [
        ("G_header", [36, 17, 1473, 154], (90, 90, 90)),
        ("G_capability_matrix", [36, 183, 1602, 601], (130, 60, 150)),
        ("G_insights", [36, 801, 1602, 122], (45, 130, 60)),
    ]
    for gid, (x, y, w, h), color in top_groups:
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, 3)
        cv2.putText(canvas, gid, (x + 5, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    for assignment_item in assignments:
        x, y, w, h = assignment_item["bbox_px"]
        if assignment_item["node_class"] == "owned_content":
            color = (145, 145, 145)
            for start in range(x, x + w, 10):
                cv2.line(canvas, (start, y), (min(start + 5, x + w), y), color, 1)
                cv2.line(canvas, (start, y + h), (min(start + 5, x + w), y + h), color, 1)
            continue
        if not assignment_item["emits_ppt_object"]:
            continue
        route = assignment_item["selected_route"]
        color = ROUTE_COLORS[route]
        thickness = 3 if assignment_item["id"] in {"TABLE_main", "S_key_shape"} else 2
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, thickness)
        label = assignment_item["id"]
        scale = 0.38
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        label_y = y - 4 if y > 18 else y + th + 4
        cv2.rectangle(canvas, (x, label_y - th - 3), (x + tw + 5, label_y + 2), color, -1)
        cv2.putText(canvas, label, (x + 2, label_y), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)

    # Row groups are logical ownership regions inside the native table.
    for gid, box in [("G_row1", [36, 232, 1602, 118]), ("G_row2", [36, 350, 1602, 124]), ("G_row3", [36, 474, 1602, 209]), ("G_row4", [36, 683, 1602, 101])]:
        x, y, w, h = box
        cv2.putText(canvas, gid + " logical", (x + 68, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 100, 100), 1, cv2.LINE_AA)

    legend_w = 510
    debug = np.full((canvas.shape[0], canvas.shape[1] + legend_w, 3), 248, np.uint8)
    debug[:, : canvas.shape[1]] = canvas
    lx = canvas.shape[1] + 18
    cv2.putText(debug, "STEP 5 CONTRACT DEBUG", (lx, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (25, 25, 25), 2, cv2.LINE_AA)
    cv2.putText(debug, "Thick outlines = top semantic groups", (lx, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.putText(debug, "Colored boxes = emitted PPT units", (lx, 94), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.putText(debug, "Gray dotted boxes = table-owned content", (lx, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1, cv2.LINE_AA)
    yy = 160
    for route in ["native_textbox", "native_table", "standard_powerpoint_shape_connector_composition", "custom_fitted_geometry"]:
        color = ROUTE_COLORS[route]
        cv2.rectangle(debug, (lx, yy - 13), (lx + 22, yy + 3), color, -1)
        cv2.putText(debug, ROUTES[route], (lx + 32, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (30, 30, 30), 1, cv2.LINE_AA)
        yy += 32
    yy += 18
    cv2.putText(debug, "EMITTED OBJECT MODEL", (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (25, 25, 25), 1, cv2.LINE_AA)
    yy += 28
    lines = [
        "9 native textboxes",
        "1 native table",
        "6 rectangular underlay/background shapes",
        "4 editable icon groups",
        "1 fitted four-point freeform",
        "2 straight connectors",
        "23 reconstruction units total",
        "28 semantic/evidence nodes emit no object",
    ]
    for line in lines:
        cv2.putText(debug, line, (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (40, 40, 40), 1, cv2.LINE_AA)
        yy += 24
    yy += 18
    cv2.putText(debug, "TABLE STACK", (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (25, 25, 25), 1, cv2.LINE_AA)
    yy += 28
    for line in ["underlay gradients", "  -> native table and owned text", "      -> editable icon groups"]:
        cv2.putText(debug, line, (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (40, 40, 40), 1, cv2.LINE_AA)
        yy += 24
    cv2.imwrite(str(output), debug)


def write_report(contract: dict[str, Any]) -> None:
    route_counts = contract["audit_summary"]["selected_route_counts"]
    report = """# slide understanding to editable reconstruction contract audit

## Verdict

The slide understanding output is semantically strong enough to plan editable reconstruction, though its original entity list mixes PowerPoint reconstruction units, table-owned content, logical groups, and pixel evidence. The revised contract keeps all 51 semantic records and reduces the expected emitted object model to 23 reconstruction units.

The current output is suitable for a faithful first reconstruction after the missing style and table-format fields are supplied. It is not yet sufficient for typography-perfect or border-perfect reproduction without image-guided iteration.

## Reconstruction hierarchy and routes

| Node or group | Semantic role | Expected editable reconstruction route | Emits object | Notes |
| --- | --- | --- | --- | --- |
| `SLIDE_ROOT` | Complete slide composition | Known reusable element | No | Owns the three top-level regions |
| `G_header` | Title region | Known reusable element composed of textboxes | No | Contains two native textboxes |
| `T_title` | Slide title | Native textbox | Yes | Two authoritative semantic lines |
| `T_subtitle` | Subtitle | Native textbox | Yes | One line |
| `G_capability_matrix` | Capability matrix | Known reusable element | No | New parent added around table, underlays, row groups, and icons |
| `S_header_fill` | Red header backing | Standard PowerPoint rectangle | Yes | Sits behind transparent native table header cells |
| `S_step1` to `S_step4` | Red number bands | Standard PowerPoint rectangles | Yes | Sit behind transparent step-number cells |
| `TABLE_main` | Grid, merged cells, borders, and cell text | Native table | Yes | Owns 27 text nodes and the row 3 dashed border |
| `G_table_header` | Header ownership group | Native table content | No | Logical group retained for semantics |
| `G_row1` to `G_row4` | Process-row ownership groups | Known reusable row pattern inside native table | No | These groups organize content and do not require PowerPoint group objects |
| `I_step1` to `I_step4` | Four line-art icons | Standard shape and connector composition | Yes | Each emits one editable PowerPoint group. Canonical assets remain an alternate route |
| Table text nodes | Cell text and labels | Native table-owned content | No | They populate cells and must not become separate textbox objects |
| `L_row3_split` | Dashed subrow divider | Native table border | No | Measurement evidence for one per-edge border rule |
| `G_insights` | Bottom insights band | Known reusable element | No | Composite of shapes, textboxes, and connectors |
| `S_insights_bg` | Pale band background | Standard PowerPoint rectangle | Yes | Back layer |
| `S_key_shape` | Red single-slanted accent | Custom fitted geometry | Yes | Four-point closed freeform measured by SAM 2 |
| `T_key_label` | Accent label | Native textbox | Yes | Front of the fitted accent |
| `G_insight1` to `G_insight3` | Repeated insight groups | Known reusable element | No | Each owns a number textbox and body textbox |
| Insight number and body nodes | Insight copy | Native textbox | Yes | Six textbox objects |
| `L_insight_sep1` and `L_insight_sep2` | Vertical separators | Standard PowerPoint connectors | Yes | Straight gray lines |
| Chart route | No chart detected | Native editable chart | No | Route unused on this slide |
| Raster route | Last-resort fallback | Raster fallback | No | Retained only for icon or freeform failure |

## Semantic granularity

The 51 records are at a useful semantic granularity. The issue was classification, not fragmentation. Text blocks correspond to meaningful copy regions, each icon is one semantic object, and the red accent is one fitted shape. No glyph, contour, SAM mask, edge fragment, or OCR word should emit a PowerPoint object.

The revised contract adds `node_class`, `render_owner`, `emits_ppt_object`, and `selected_route`. This prevents 27 table text records and the row 3 divider from being rebuilt as separate shapes. Masks, contours, line segments, dominant colors, visible bounds, and OCR words remain measurement evidence attached to their semantic owner.

## Grouping and ownership

The original hierarchy lacked a parent that owned the table, row groups, gradient underlays, and icon overlays. `G_capability_matrix` now supplies that parent. The header, table rows, and insight cards remain logical semantic groups. They guide reconstruction and optional grouping while avoiding unnecessary nested PowerPoint group objects.

The table cell map now assigns every table text node and icon to a named row and column. It also corrects the row 3 merge model. The step-number and step-visual columns each span `R3A` and `R3B`. They are not merged with each other.

## Overlap and z-order

The original overlap data covered only the insights background and accent. The revised contract defines deterministic stacks.

- Table underlay gradient shapes sit behind the native table.
- The native table owns grid lines and cell text.
- Icon groups sit above the table inside the step-visual cells.
- The insights background sits behind the fitted red accent.
- Separators and native textboxes sit above the insight backgrounds.

This is sufficient for editable reconstruction object ordering. Pixel-level bbox overlap remains diagnostic evidence and no longer acts as the z-order authority.

## Text readiness

Every text node has authoritative semantic text, explicit line breaks, layout bounds, visible bounds, and revised line boxes based on the semantic line count. This is sufficient to create and fit native text containers.

Exact typography remains incomplete. The raster does not reliably establish the source font, point size, line spacing, paragraph spacing, kerning, or mixed formatting runs. Important mixed runs include the bold `A. Existing components` and `B. New components` labels and the italic prerequisite line in row 4.

## Native table readiness

The grid has five columns and six logical rows including the header and two row 3 subrows. The contract now provides cell addresses, content ownership, corrected merges, overlay ownership, and transparency rules for the gradient underlays.

Native table reconstruction still needs exact internal margins, vertical alignment, border widths, border colors, dash pattern, and reliable per-run text styling. These fields are required for high-fidelity reconstruction even though the overall table structure is now unambiguous.

## Novel geometry readiness

The key-insights accent has a stable four-point SAM contour. All observed edges are straight, so a closed PowerPoint freeform is sufficient and Bezier fitting is unnecessary. Its mask and edge segments remain geometric evidence for the fitted shape.

## Information still missing for editable reconstruction

- Exact font families and font substitution policy
- Point sizes derived from a calibrated font-rendering loop
- Run-level bold and italic ranges
- Paragraph alignment, line spacing, and paragraph spacing
- Native textbox and native table internal margins
- Exact table border width, color, and dash pattern per edge
- Gradient angle, stop positions, stop colors, and transparency
- Canonical source IDs or editable primitive recipes for the four icons
- Exact corner radius and stroke width for icon primitives
- Slide theme mapping and reusable style-token names
- A fidelity tolerance policy for deciding when raster fallback is allowed

## Redundant information policy

- Contours, masks, edge segments, OCR words, dominant-color samples, and visible bounds remain evidence fields.
- Automatically inferred bbox overlap is diagnostic and does not control stacking.
- Table text nodes remain semantic content records owned by `TABLE_main`.
- Logical row and insight groups remain hierarchy nodes and do not automatically emit PowerPoint group objects.
- The broad foreground mask and color sample on `TABLE_main` are low-value evidence because child regions provide more specific measurements.

## Route count

"""
    for route, count in route_counts.items():
        report += f"- {ROUTES[route]} with {count} emitted units\n"
    report += "\nThe emitted model contains 23 units. Editable icon groups will expand into several primitive objects during editable reconstruction while remaining one semantic unit each.\n"
    (OUT_DIR / "reconstruction_route_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source, semantic, image = load()
    entities = entity_map(source)
    assignments = [assignment(entity) for entity in source["entities"]]
    table = table_contract()
    emitted = [item for item in assignments if item["emits_ppt_object"]]
    route_counts = Counter(item["selected_route"] for item in emitted)
    all_route_counts = {route: route_counts.get(route, 0) for route in ROUTES}
    contract = {
        "schema_version": "0.2.0",
        "contract": "slide understanding semantic and measurement output to editable reconstruction editable PowerPoint reconstruction",
        "source_artifacts": {
            "slide_entities": str(SOURCE_JSON),
            "semantic_map": str(SEMANTIC_MAP),
            "sample_slide": str(SOURCE_IMAGE),
            "step4_debug": str(SOURCE_DEBUG),
        },
        "route_vocabulary": ROUTES,
        "contract_rules": [
            "Semantic entities may be reconstruction units, owned content, logical groups, or measurement evidence.",
            "Only nodes with emits_ppt_object true may create independent PowerPoint objects.",
            "A native table owns its cell text and border evidence.",
            "Contours, masks, edges, OCR words, and sampled colors never become objects by themselves.",
            "Explicit container z-stacks override automatically inferred bbox overlap.",
        ],
        "hierarchy": hierarchy(),
        "reconstruction_units": assignments,
        "native_table_contract": table,
        "text_contracts": text_contracts(entities, table),
        "z_order_contract": {
            "global_reading_regions": ["G_header", "G_capability_matrix", "G_insights"],
            "G_capability_matrix_back_to_front": [
                ["S_header_fill", "S_step1", "S_step2", "S_step3", "S_step4"],
                ["TABLE_main"],
                ["I_step1", "I_step2", "I_step3", "I_step4"],
            ],
            "G_insights_back_to_front": [
                ["S_insights_bg"],
                ["S_key_shape"],
                ["L_insight_sep1", "L_insight_sep2"],
                ["T_key_label", "T_insight_num1", "T_insight1", "T_insight_num2", "T_insight2", "T_insight_num3", "T_insight3"],
            ],
        },
        "evidence_policy": {
            "entity_level": ["layout_bbox", "visible_bbox", "semantic identity", "semantic text", "preferred route"],
            "measurement_only": ["masks", "contours", "edge segments", "OCR word boxes", "dominant-color samples", "automatic bbox overlaps"],
            "redundant_or_low_value": ["TABLE_main foreground mask", "TABLE_main aggregate dominant colors", "duplicate automatic bbox overlap when explicit stacking exists"],
        },
        "missing_for_step5": [
            {"field": "font_family", "scope": "all text", "severity": "high"},
            {"field": "font_size_and_metrics", "scope": "all text", "severity": "high"},
            {"field": "run_level_styles", "scope": "mixed bold and italic table text", "severity": "high"},
            {"field": "text_margins_and_spacing", "scope": "textboxes and table cells", "severity": "high"},
            {"field": "table_border_style_per_edge", "scope": "TABLE_main", "severity": "medium"},
            {"field": "gradient_stops_and_angle", "scope": "red underlays and accent", "severity": "medium"},
            {"field": "canonical_asset_or_primitive_recipe", "scope": "four icons", "severity": "medium"},
            {"field": "theme_style_tokens", "scope": "slide", "severity": "medium"},
            {"field": "fidelity_and_fallback_policy", "scope": "all reconstruction units", "severity": "medium"},
        ],
        "audit_summary": {
            "original_semantic_entity_count": len(source["entities"]),
            "semantic_entity_count_retained": len(assignments),
            "expected_emitted_reconstruction_units": len(emitted),
            "non_emitting_owned_or_evidence_nodes": len(assignments) - len(emitted),
            "selected_route_counts": all_route_counts,
            "native_editable_chart_detected": False,
            "granularity_verdict": "The semantic granularity is appropriate after separating reconstruction units from owned content and evidence.",
            "step5_readiness": "structurally ready, style incomplete",
        },
    }
    contract["validation"] = validate_contract(contract, source)
    output_json = OUT_DIR / "reconstruction_contract.json"
    output_json.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    debug_path = OUT_DIR / "debug_reconstruction_hierarchy.png"
    render_debug(image, source, assignments, debug_path)
    write_report(contract)
    print(json.dumps({
        "contract": str(output_json),
        "report": str(OUT_DIR / "reconstruction_route_report.md"),
        "debug": str(debug_path),
        "semantic_entities": len(assignments),
        "emitted_units": len(emitted),
        "route_counts": all_route_counts,
        "readiness": contract["audit_summary"]["step5_readiness"],
    }, indent=2))


if __name__ == "__main__":
    main()
