"""Compile measured scene evidence and the reconstruction contract into a constructor scene."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from slidecraft.reconstruction.conformance import validate_contract_consumption
from slidecraft.reconstruction.text_fit import finalize_fitted_text_entities, fit_text_entities
from slidecraft.refinement.constrained_normalization import solve_plan

Z_BY_KIND = {"connector": 10, "shape": 20, "novel_visual": 30, "table": 35, "chart": 36, "image": 40, "icon": 50, "icon_slot": 50, "text": 60}


def _transform_box(box: list[int], scale_xy: list[float], offset_y: int) -> list[int]:
    scale_x, scale_y = scale_xy
    return [round(box[0] * scale_x), round(box[1] * scale_y + offset_y), round(box[2] * scale_x), round(box[3] * scale_y)]


def _transform_point(point: list[float], scale_xy: list[float], offset_y: int) -> list[float]:
    return [point[0] * scale_xy[0], point[1] * scale_xy[1] + offset_y]


def _svg_ratio(path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="ignore")[:6000]
    match = re.search(r"viewBox=[\"']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)", text)
    if match and float(match.group(2)):
        return float(match.group(1)) / float(match.group(2))
    return 1.0


def _image_ratio(path: Path) -> float:
    if path.suffix.lower() == ".svg":
        return _svg_ratio(path)
    from PIL import Image

    with Image.open(path) as image:
        return image.width / image.height if image.height else 1.0


def _contain(box: list[int], ratio: float, inset_fraction: float = 0.14) -> list[int]:
    x, y, width, height = box
    available_width = width * (1 - 2 * inset_fraction)
    available_height = height * (1 - 2 * inset_fraction)
    final_width = min(available_width, available_height * ratio)
    final_height = final_width / ratio
    return [round(x + (width - final_width) / 2), round(y + (height - final_height) / 2), round(final_width), round(final_height)]


def _text_style(entity: dict[str, Any], fitted: dict[str, Any] | None, design: dict[str, Any], scale_y: float = 1.0) -> dict[str, Any]:
    hint = entity.get("style_hint", {})
    measurement = entity.get("measurement", {}).get("text_geometry", {})
    role = entity.get("role", "body")
    defaults = design.get("style", {})
    role_policies = design.get("text_reconstruction", {}).get("semantic_role_policies", {})
    role_policy = role_policies.get(role, role_policies.get("default", {}))
    family = hint.get("font_family") or role_policy.get("font_family") or defaults.get("body_font", "Arial")
    estimated = measurement.get("estimated_font_size_pt")
    size_range = role_policy.get("font_size_range_px", [10, 20])
    size_px = float(fitted.get("font_size_px")) if fitted else (
        float(estimated) * 96 / 72 if estimated else float(size_range[1])
    )
    insets = fitted.get("insets_px", {}) if fitted else {}
    return {
        "font_family": fitted.get("font_family", family) if fitted else family,
        "font_size_px": size_px * scale_y,
        "font_size_pt": fitted.get("font_size_pt") if fitted else None,
        "font_weight": "bold" if (fitted.get("bold") if fitted else hint.get("font_weight", 400) in {"bold", 600, 700, 800, 900}) else "regular",
        "italic": bool(fitted.get("italic", False)) if fitted else bool(hint.get("italic", False)),
        "color": fitted.get("color", hint.get("color", "#111111")) if fitted else hint.get("color", "#111111"),
        "alignment": fitted.get("alignment", hint.get("alignment", "left")) if fitted else hint.get("alignment", "left"),
        "vertical_alignment": fitted.get("vertical_alignment", "top") if fitted else hint.get("vertical_alignment", "top"),
        "margins_px": [insets.get("left", 0) * scale_y, insets.get("top", 0) * scale_y, insets.get("right", 0) * scale_y, insets.get("bottom", 0) * scale_y],
        "line_spacing_multiple": fitted.get("line_spacing", 1.0) if fitted else 1.0,
        "paragraph_spacing_px": fitted.get("paragraph_space_after_px", 0) if fitted else 0,
        "autofit": "none",
        "outer_geometry_is_fixed": True,
    }


def _apply_agent_alignment_plan(
    objects: list[dict[str, Any]],
    refinement_plan: dict[str, Any],
    design: dict[str, Any],
    scale_xy: list[float],
) -> dict[str, Any]:
    """Apply an Agent-authored normalization plan through deterministic movement constraints."""
    if refinement_plan.get("authored_by") != "agent_reasoning":
        raise ValueError("Reconstruction refinement requires an Agent-authored plan")
    config = design.get("normalization", {}).get("constraints", design.get("normalization", {}))
    report = solve_plan(refinement_plan, config)
    by_id = {item["id"]: item for item in objects}
    coordinate_space = refinement_plan.get("coordinate_space", "generation_region_px")
    if coordinate_space not in {"generation_region_px", "full_slide_px"}:
        raise ValueError(f"Unsupported refinement coordinate space {coordinate_space!r}")
    applied = []
    for decision in report["decisions"]:
        if decision["status"] != "accepted":
            continue
        for correction in decision["corrections"]:
            dx, dy = correction["delta_px"]
            if coordinate_space == "generation_region_px":
                dx *= scale_xy[0]
                dy *= scale_xy[1]
            for entity_id in correction["member_entity_ids"]:
                if entity_id not in by_id:
                    raise ValueError(f"Refinement plan refers to unknown constructor object {entity_id}")
                by_id[entity_id]["bbox_px"][0] += dx
                by_id[entity_id]["bbox_px"][1] += dy
            applied.append(correction)
    return {**report, "correction_count": len(applied), "corrections": applied}


def _deck_chrome(contract: dict[str, Any], dimensions: list[int]) -> list[dict[str, Any]]:
    chrome = contract.get("deck_chrome_configuration", {})
    if not chrome.get("enabled"):
        return []
    width, height = dimensions
    generation = contract.get("generation_region", {})
    header_height = int(generation.get("offset_y_px", 0))
    generation_height = int(generation.get("dimensions_px", [width, height - header_height])[1])
    footer_top = header_height + generation_height
    footer_height = max(0, height - footer_top)
    outer = int(chrome.get("outer_padding_px", 40))
    family = chrome.get("font_family", "Arial")
    header = chrome.get("header", {})
    footer = chrome.get("footer", {})
    objects: list[dict[str, Any]] = []

    def text_object(identifier: str, text: str, box: list[int], config: dict[str, Any], alignment: str, weight_key: str = "font_weight") -> dict[str, Any]:
        return {
            "id": identifier,
            "kind": "textbox",
            "bbox_px": box,
            "text": text,
            "style": {
                "font_family": family,
                "font_size_px": config.get("font_size_px", 12),
                "font_weight": "bold" if config.get(weight_key) == "bold" else "regular",
                "color": config.get("text_color", "#4A4A4A"),
                "alignment": alignment,
                "vertical_alignment": "middle",
                "margins_px": [0, 0, 0, 0],
                "line_spacing_multiple": 1,
                "paragraph_spacing_px": 0,
                "autofit": "none",
            },
            "semantic_role": "deck_chrome",
            "z": 100,
        }

    header_text_height = max(18, header_height - 12)
    header_top = max(2, round((header_height - header_text_height) / 2 - 1))
    objects.append(text_object("CHROME_HEADER.left", header.get("left_text", ""), [outer, header_top, round(width * 0.48), header_text_height], header, "left"))
    right_header = dict(header)
    right_header["text_color"] = header.get("secondary_text_color", header.get("text_color", "#4A4A4A"))
    objects.append(text_object("CHROME_HEADER.right", header.get("right_text", ""), [round(width * 0.52), header_top, round(width * 0.48) - outer, header_text_height], right_header, "right"))
    objects.extend([
        {"id": "CHROME_HEADER.rule", "kind": "shape", "shape": "line", "bbox_px": [outer, max(0, header_height - 1), width - 2 * outer, 0], "style": {"fill": "none", "stroke": header.get("rule_color", "#DED7CF"), "stroke_width_px": header.get("rule_width_px", 1)}, "z": 99},
        {"id": "CHROME_HEADER.accent", "kind": "shape", "shape": "line", "bbox_px": [outer, max(0, header_height - 1), header.get("accent_rule_width_px", 120), 0], "style": {"fill": "none", "stroke": header.get("accent_color", "#D93900"), "stroke_width_px": 2}, "z": 100},
        {"id": "CHROME_FOOTER.rule", "kind": "shape", "shape": "line", "bbox_px": [outer, footer_top, width - 2 * outer, 0], "style": {"fill": "none", "stroke": footer.get("rule_color", "#DED7CF"), "stroke_width_px": footer.get("rule_width_px", 1)}, "z": 99},
    ])
    footer_text_height = max(18, footer_height - 12)
    footer_text_top = footer_top + max(3, round((footer_height - footer_text_height) / 2 + 1))
    objects.append(text_object("CHROME_FOOTER.left", footer.get("left_text", ""), [outer, footer_text_top, 420, footer_text_height], footer, "left", "left_font_weight"))
    center_footer = dict(footer)
    center_footer["text_color"] = footer.get("secondary_text_color", footer.get("text_color", "#4A4A4A"))
    objects.append(text_object("CHROME_FOOTER.center", footer.get("center_text", ""), [round((width - 600) / 2), footer_text_top, 600, footer_text_height], center_footer, "center"))
    right_text = str(footer.get("right_text", footer.get("right_text_template", "")))
    objects.append(text_object("CHROME_FOOTER.right", right_text, [width - outer - 460, footer_text_top, 460, footer_text_height], center_footer, "right"))
    return objects


def _apply_explicit_z_order(objects: list[dict[str, Any]], relations: list[dict[str, Any]]) -> None:
    by_id = {item["id"]: item for item in objects}
    usable = [item for item in relations if item.get("back") in by_id and item.get("front") in by_id]
    for _ in range(len(usable) + 1):
        changed = False
        for relation in usable:
            back = by_id[relation["back"]]
            front = by_id[relation["front"]]
            if front["z"] <= back["z"]:
                front["z"] = back["z"] + 1
                changed = True
        if not changed:
            return
    raise ValueError("Explicit stacking relationships contain a cycle")


def build_reconstruction_scene(
    *,
    measured_scene: dict[str, Any],
    contract: dict[str, Any],
    design: dict[str, Any],
    slide_id: str,
) -> dict[str, Any]:
    dimensions = list(contract.get("full_slide_dimensions_px") or [measured_scene["source"]["width_px"], measured_scene["source"]["height_px"]])
    transform = contract.get("coordinate_transform_to_full_slide", {})
    offset_y = int((transform.get("translation_px") or transform.get("full_slide_offset_px") or [0, 0])[1])
    scale_xy = [float(value) for value in transform.get("scale_xy", [1, 1])]
    asset_mappings = {mapping["entity_id"]: mapping for mapping in contract.get("canonical_asset_mappings", [])}
    connector_plans = {plan["entity_id"]: plan for plan in contract.get("connector_reconstruction_plans", [])}
    connector_configuration = contract.get("connector_configuration", design.get("connectors", {}))
    fitted_text = {record["id"]: record for record in contract.get("fitted_text_contracts", [])}
    if not fitted_text:
        fitted_text, _ = fit_text_entities(measured_scene["entities"], design)
    points_per_px = scale_xy[1] * 13.333333 * 72 / dimensions[0]
    text_policy = design.get("text_reconstruction", {})
    fitted_text, text_fit_report = finalize_fitted_text_entities(
        measured_scene["entities"],
        design,
        fitted_text,
        points_per_px=points_per_px,
        quantization_step_pt=float(text_policy.get("font_size_quantization_pt", 0.5)),
        absolute_minimum_pt=float(text_policy.get("absolute_minimum_font_size_pt", 5.0)),
    )
    units = {unit["id"]: unit for unit in contract.get("reconstruction_units", [])}
    objects: list[dict[str, Any]] = []
    for entity in measured_scene["entities"]:
        entity_id = entity["id"]
        unit = units.get(entity_id)
        if unit and unit.get("emits_ppt_object") is False:
            continue
        kind = entity["kind"]
        box = _transform_box(entity["measurement"]["layout_bbox"]["px"], scale_xy, offset_y)
        z = Z_BY_KIND.get(kind, 30)
        if kind == "text":
            objects.append({
                "id": entity_id,
                "kind": "textbox",
                "bbox_px": box,
                "text": fitted_text.get(entity_id, {}).get("authored_text", entity.get("authored_text", entity.get("text", ""))),
                "style": _text_style(entity, fitted_text.get(entity_id), design, scale_xy[1]),
                "paragraphs": fitted_text.get(entity_id, {}).get("authored_text", entity.get("authored_text", entity.get("text", ""))).split("\n"),
                "bullet_style": entity.get("bullet_style"),
                "semantic_role": entity.get("role"),
                "z": z,
            })
        elif kind in {"icon", "icon_slot"}:
            mapping = asset_mappings.get(entity_id)
            if not mapping:
                raise ValueError(f"Icon entity {entity_id} has no canonical asset mapping")
            path = Path(mapping.get("selected_asset_path", ""))
            if not path.exists():
                raise FileNotFoundError(f"Canonical asset for {entity_id} does not exist: {path}")
            slot = _transform_box(mapping.get("target_bbox_source_px", entity["measurement"]["layout_bbox"]["px"]), scale_xy, offset_y)
            selected_asset_id = str(mapping.get("selected_asset_id", ""))
            protected = selected_asset_id.startswith("USER_") or bool(entity.get("style_hint", {}).get("preserve_canonical_color"))
            slot_style = design.get("icon_slots", {}).get("standard_pictogram_surface", {})
            surface_fill = entity.get("style_hint", {}).get("slot_fill") or ("#FFFFFF" if protected else slot_style.get("fill", "#FCE4D6"))
            objects.append({
                "id": f"{entity_id}.icon_slot_surface",
                "kind": "shape",
                "shape": "rectangle",
                "bbox_px": slot,
                "style": {"fill": surface_fill, "stroke": "#D6D6D6" if entity_id == "I_opencv" else "none", "stroke_width_px": 1},
                "semantic_role": "icon_slot_surface",
                "z": z - 1,
            })
            objects.append({
                "id": entity_id,
                "kind": "image",
                "bbox_px": _contain(slot, _svg_ratio(path), design.get("icon_slots", {}).get("default_inset_fraction", 0.14)),
                "source_path": str(path.resolve()),
                "recolor": None if protected else (entity.get("style_hint", {}).get("glyph_color") or slot_style.get("glyph_color", "#D93900")),
                "selected_asset_id": selected_asset_id,
                "fit": "contain",
                "preserve_aspect_ratio": True,
                "semantic_role": entity.get("role"),
                "z": z,
            })
        elif kind == "image":
            image = entity["measurement"].get("image_object", {})
            mapping = asset_mappings.get(entity_id)
            source = mapping.get("selected_asset_path") if mapping else image.get("screenshot_crop_absolute")
            if source:
                source_path = Path(source)
                target_box = _contain(box, _image_ratio(source_path), 0) if mapping else box
                objects.append({
                    "id": entity_id,
                    "kind": "image",
                    "bbox_px": target_box,
                    "source_path": str(source_path.resolve()),
                    "selected_asset_id": mapping.get("selected_asset_id") if mapping else None,
                    "fit": "contain" if mapping else image.get("crop_mode", "fill"),
                    "preserve_aspect_ratio": True,
                    "semantic_role": entity.get("role"),
                    "z": z,
                })
        elif kind == "connector":
            plan = connector_plans.get(entity_id)
            if plan:
                stroke_style = dict(plan.get("stroke_style", {}))
                configured_stroke = connector_configuration.get("stroke", {})
                stroke_style["color"] = configured_stroke.get("color", stroke_style.get("color", "#D93900"))
                arrowhead_config = connector_configuration.get("arrowhead", {})
                minimum_endpoint = float(arrowhead_config.get("minimum_visible_endpoint_px", 18))
                minimum_stroke_for_endpoint = minimum_endpoint / 4.0
                stroke_style["width_px"] = max(
                    float(stroke_style.get("width_px", 0)),
                    float(configured_stroke.get("width_px", 4)),
                    minimum_stroke_for_endpoint,
                )
                objects.append({
                    "id": entity_id,
                    "kind": "connector_graph",
                    "sources_px": [_transform_point(point, scale_xy, offset_y) for point in plan["approximate_start_anchors_px"]],
                    "targets_px": [_transform_point(point, scale_xy, offset_y) for point in plan["approximate_end_anchors_px"]],
                    "junctions_px": [_transform_point(point, scale_xy, offset_y) for point in plan.get("junction_positions_px", [])],
                    "route": plan["configured_route"],
                    "routing_orientation": plan.get("routing_orientation"),
                    "style": stroke_style,
                    "arrowhead_treatment": plan.get("arrowhead_treatment", "triangle_at_target"),
                    "arrowhead": arrowhead_config or {"type": "triangle", "powerpoint_size": "lg", "minimum_visible_endpoint_px": 18},
                    "junction_style": plan.get("junction_treatment") or connector_configuration.get("junction", {"style": "filled_circle", "diameter_px": 10}),
                    "routing_constraints": connector_configuration.get("routing", {}),
                    "semantic_intent": plan["relationship_intent"],
                    "z": z,
                })
        elif kind == "table":
            objects.append({"id": entity_id, "kind": "table", "bbox_px": box, "structure": entity.get("structure") or entity.get("table_structure") or {}, "style": entity.get("style_hint", {}), "z": z})
        elif kind == "chart":
            objects.append({"id": entity_id, "kind": "chart", "bbox_px": box, "structure": entity.get("chart_structure") or {}, "style": entity.get("style_hint", {}), "z": z})
        else:
            shape = entity.get("shape", "rectangle")
            shape = {"rounded_rect": "rounded_rectangle", "circle": "ellipse"}.get(shape, shape)
            if shape in {"rectangle", "line", "parallelogram", "trapezoid", "ellipse", "rounded_rectangle", "slanted_tab", "slanted_banner"}:
                objects.append({"id": entity_id, "kind": "shape", "shape": shape, "bbox_px": box, "style": entity.get("style_hint", {}), "z": z})
            else:
                objects.append({"id": entity_id, "kind": "freeform", "bbox_px": box, "contours_px": entity["measurement"].get("contours_px", []), "style": entity.get("style_hint", {}), "z": z})
    objects.extend(_deck_chrome(contract, dimensions))
    _apply_explicit_z_order(objects, contract.get("z_order_relations", []))
    source_by_entity = {
        entity["id"]: entity.get("authoritative_source_path")
        for entity in measured_scene.get("entities", [])
        if entity.get("authoritative_source_path")
    }
    for item in objects:
        source_path = source_by_entity.get(item["id"])
        if source_path:
            item["source_references"] = [{"authoritative_source_path": source_path}]
    objects = sorted(objects, key=lambda item: item["z"])
    normalization_report = _apply_agent_alignment_plan(
        objects,
        contract.get("reasoned_refinement_plan", {}),
        design,
        scale_xy,
    )
    conformance = validate_contract_consumption(
        measured_scene=measured_scene,
        contract=contract,
        objects=objects,
        scale_xy=scale_xy,
        offset_y=offset_y,
    )
    sources = []
    source_image = measured_scene.get("source", {}).get("path") or measured_scene.get("source", {}).get("image_path")
    if source_image:
        sources.append(f"Generated target visual: {source_image}")
    for mapping in contract.get("canonical_asset_mappings", []):
        asset_path = mapping.get("selected_asset_path")
        asset_id = mapping.get("selected_asset_id")
        if asset_path:
            sources.append(f"Canonical asset {asset_id}: {asset_path}")
    for entity_id, source_path in sorted(source_by_entity.items()):
        sources.append(f"Object {entity_id}: authoritative source {source_path}")
    return {
        "schema_version": "1.0.0",
        "slide_id": slide_id,
        "dimensions_px": dimensions,
        "background": design.get("style", {}).get("background", "#FFFFFF"),
        "design_config_id": design.get("config_id"),
        "objects": objects,
        "sources": list(dict.fromkeys(sources)),
        "compiler_report": {
            "measured_entity_count": len(measured_scene["entities"]),
            "emitted_object_count": len(objects),
            "evidence_objects_emitted": 0,
            "connector_graph_count": sum(item["kind"] == "connector_graph" for item in objects),
            "canonical_asset_count": sum(item["kind"] == "image" and bool(item.get("semantic_role")) for item in objects),
            "text_fitting": text_fit_report,
            "alignment_normalization": normalization_report,
            "contract_conformance": conformance,
        },
    }
