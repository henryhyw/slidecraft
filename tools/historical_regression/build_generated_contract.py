#!/usr/bin/env python3
"""Build a reconstruction contract from the measured slide understanding scene."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def normalize_connector_route(observed_route: str | None, membership: str) -> str | None:
    """Normalize slide understanding route vocabulary without discarding graph-specific evidence."""
    if not observed_route:
        return None
    shared = any(token in membership for token in ("branch", "merge", "shared_junction"))
    if not shared:
        return observed_route
    if observed_route in {"elbow", "elbow_branch", "elbow_merge", "elbow_shared_junction"}:
        return "elbow_shared_junction"
    if observed_route in {"curved", "curved_shared_junction"}:
        return "curved_shared_junction"
    if observed_route in {"straight", "straight_shared_junction"}:
        return "straight_shared_junction"
    return observed_route


def owner_boxes(step4: dict) -> dict[str, list[float]]:
    boxes = {
        entity["id"]: list(entity["measurement"]["layout_bbox"]["px"])
        for entity in step4.get("entities", [])
        if entity.get("measurement", {}).get("layout_bbox", {}).get("px")
    }
    boxes.update({group["id"]: list(group["bbox_hint"]) for group in step4.get("groups", [])})
    return boxes


def routing_axis(orientation: str | None, starts: list[list[float]], ends: list[list[float]]) -> str:
    value = (orientation or "").lower()
    if value.startswith("horizontal") or "horizontal_inputs" in value or "horizontal_curves" in value:
        return "horizontal"
    if value.startswith("vertical"):
        return "vertical"
    if starts and ends:
        source_center = [sum(point[index] for point in starts) / len(starts) for index in (0, 1)]
        target_center = [sum(point[index] for point in ends) / len(ends) for index in (0, 1)]
        return "horizontal" if abs(target_center[0] - source_center[0]) >= abs(target_center[1] - source_center[1]) else "vertical"
    return "horizontal"


def boundary_anchor(box: list[float], *, axis: str, toward_positive: bool) -> list[float]:
    x, y, width, height = box
    if axis == "horizontal":
        return [x + width if toward_positive else x, y + height / 2]
    return [x + width / 2, y + height if toward_positive else y]


def clamp_to_boundary_span(value: float, box: list[float], *, axis: str, inset: float = 2) -> float:
    if axis == "horizontal":
        lower, upper = box[1] + inset, box[1] + box[3] - inset
    else:
        lower, upper = box[0] + inset, box[0] + box[2] - inset
    if lower > upper:
        lower, upper = upper, lower
    return max(lower, min(value, upper))


def semantic_owner_anchors(
    *,
    intent: dict,
    starts: list[list[float]],
    ends: list[list[float]],
    orientation: str | None,
    boxes: dict[str, list[float]],
    junctions: list[list[float]] | None = None,
) -> tuple[list[list[float]], list[list[float]], list[dict]]:
    sources = intent.get("source_entities", [])
    targets = intent.get("target_entities", [])
    axis = routing_axis(orientation, starts, ends)
    source_centers = [boxes[item][0] + boxes[item][2] / 2 for item in sources if item in boxes]
    target_centers = [boxes[item][0] + boxes[item][2] / 2 for item in targets if item in boxes]
    if axis == "vertical":
        source_centers = [boxes[item][1] + boxes[item][3] / 2 for item in sources if item in boxes]
        target_centers = [boxes[item][1] + boxes[item][3] / 2 for item in targets if item in boxes]
    toward_positive = (sum(target_centers) / len(target_centers)) >= (sum(source_centers) / len(source_centers)) if source_centers and target_centers else True
    resolved_starts = [boundary_anchor(boxes[item], axis=axis, toward_positive=toward_positive) for item in sources if item in boxes]
    resolved_ends = [boundary_anchor(boxes[item], axis=axis, toward_positive=not toward_positive) for item in targets if item in boxes]
    junctions = junctions or []
    if junctions and axis == "horizontal":
        junction_y = junctions[0][1]
        if len(resolved_starts) == 1 and sources[0] in boxes:
            resolved_starts[0][1] = clamp_to_boundary_span(junction_y, boxes[sources[0]], axis=axis)
        if len(resolved_ends) == 1 and targets[0] in boxes:
            resolved_ends[0][1] = clamp_to_boundary_span(junction_y, boxes[targets[0]], axis=axis)
    if junctions and axis == "vertical":
        junction_x = junctions[0][0]
        if len(resolved_starts) == 1 and sources[0] in boxes:
            resolved_starts[0][0] = clamp_to_boundary_span(junction_x, boxes[sources[0]], axis=axis)
        if len(resolved_ends) == 1 and targets[0] in boxes:
            resolved_ends[0][0] = clamp_to_boundary_span(junction_x, boxes[targets[0]], axis=axis)
    if axis == "horizontal" and len(resolved_starts) == 1 and len(resolved_ends) == 1:
        observed_y = [point[1] for point in starts + ends if len(point) == 2]
        shared_y = sum(observed_y) / len(observed_y) if observed_y else (resolved_starts[0][1] + resolved_ends[0][1]) / 2
        source_box = boxes[sources[0]]
        target_box = boxes[targets[0]]
        shared_y = max(source_box[1], target_box[1], min(shared_y, source_box[1] + source_box[3], target_box[1] + target_box[3]))
        resolved_starts[0][1] = shared_y
        resolved_ends[0][1] = shared_y
    if axis == "vertical" and len(resolved_starts) == 1 and len(resolved_ends) == 1:
        source_box = boxes[sources[0]]
        target_box = boxes[targets[0]]
        lower = max(source_box[0] + 2, target_box[0] + 2)
        upper = min(source_box[0] + source_box[2] - 2, target_box[0] + target_box[2] - 2)
        if lower <= upper:
            source_center_x = source_box[0] + source_box[2] / 2
            shared_x = max(lower, min(source_center_x, upper))
            resolved_starts[0][0] = shared_x
            resolved_ends[0][0] = shared_x
    audit = [
        {
            "endpoint": item,
            "side": ("right" if toward_positive else "left") if axis == "horizontal" else ("bottom" if toward_positive else "top"),
            "ownership": "semantic_source_owner",
        }
        for item in sources
    ] + [
        {
            "endpoint": item,
            "side": ("left" if toward_positive else "right") if axis == "horizontal" else ("top" if toward_positive else "bottom"),
            "ownership": "semantic_target_owner",
        }
        for item in targets
    ]
    return resolved_starts or starts, resolved_ends or ends, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step4", required=True)
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    step4 = json.loads(Path(args.step4).resolve().read_text(encoding="utf-8"))
    handoff = json.loads(Path(args.handoff).resolve().read_text(encoding="utf-8"))
    entity_by_id = {entity["id"]: entity for entity in step4["entities"]}
    boxes_by_owner = owner_boxes(step4)
    asset_by_id = {asset["internal"]["asset_id"]: asset["internal"] for asset in handoff["selected_assets"]}

    units = []
    for group in step4["groups"]:
        route = "known_reusable_element"
        if group["id"] == "G_header":
            route = "native_textbox"
        elif group["id"] in {"G_stage1", "G_stage2", "G_stage3", "G_stage4", "G_stage5", "G_output"}:
            route = "standard_powerpoint_shape_connector_composition"
        units.append({
            "id": group["id"],
            "semantic_role": group["role"],
            "route": route,
            "entity_ids": group["children"],
            "bbox_source_px": group["bbox_hint"],
        })

    grouped_children = {child for group in step4["groups"] for child in group["children"]}
    for entity in step4["entities"]:
        if entity["id"] in grouped_children:
            continue
        route = {
            "text": "native_textbox",
            "icon": "canonical_icon_or_image_asset",
            "icon_slot": "canonical_icon_or_image_asset",
            "image": "raster_fallback",
            "table": "native_table",
            "chart": "native_editable_chart",
            "shape": "standard_powerpoint_shape_connector_composition",
            "connector": "standard_powerpoint_shape_connector_composition",
        }.get(entity["kind"], "custom_fitted_geometry")
        units.append({
            "id": entity["id"],
            "semantic_role": entity["role"],
            "route": route,
            "entity_ids": [entity["id"]],
            "bbox_source_px": entity["measurement"]["layout_bbox"]["px"],
        })

    icon_mappings = []
    for entity in step4["entities"]:
        if entity["kind"] not in {"icon", "icon_slot"}:
            continue
        requested = entity.get("upstream_asset_id")
        selected = requested
        mode = "restored_exact_canonical_asset"
        alternatives = []
        if requested not in asset_by_id:
            selected = "TABLER_OUTLINE_ICONS"
            mode = "individually_substituted_from_library"
            alternatives = ["TABLER_OUTLINE_PHOTO_SPARK", "TABLER_OUTLINE_TEMPLATE"]
        asset = asset_by_id[selected]
        slot_measurement = entity["measurement"].get("icon_slot_placement", entity["measurement"]["canonical_asset_placement"])
        slot_box = slot_measurement.get("slot_box", slot_measurement.get("target_visual_footprint"))
        icon_mappings.append({
            "entity_id": entity["id"],
            "semantic_role": entity["role"],
            "requested_asset_id": requested,
            "selected_asset_id": selected,
            "selection_mode": mode,
            "selected_asset_path": asset["canonical_file"],
            "alternative_candidates": alternatives,
            "target_bbox_source_px": slot_box["px"],
            "placement_authority": "icon_slot",
            "slot_center_px": slot_measurement.get("slot_center_px"),
            "slot_padding_estimate_px": slot_measurement.get("padding_estimate_px"),
            "nearby_related_entities": slot_measurement.get("nearby_related_entities", []),
            "target_color": slot_measurement["target_color"],
            "preserve_aspect_ratio": True,
            "fit": "contain",
            "alignment": "center",
            "allow_stretch": False,
            "generated_pixels_are_geometry_source": False
        })

    connector_config = handoff.get("connector_configuration", {})
    allowed_routes = set(connector_config.get("allowed_routing_types", []))
    connector_plans = []
    for entity in step4["entities"]:
        if entity["kind"] != "connector":
            continue
        constraints = entity["measurement"]["connector_constraints"]
        intent = constraints["intent"]
        membership = intent.get("structure_membership", "single")
        topology_route = connector_config.get("topology_routes", {}).get(membership)
        if (
            topology_route is None
            and membership == "many_to_many_shared_junction"
            and connector_config.get("routing", {}).get("prefer_axis_aligned_segments", False)
        ):
            topology_route = "elbow_shared_junction"
        observed_route = normalize_connector_route(constraints.get("routing_type"), membership)
        if topology_route and (not allowed_routes or topology_route in allowed_routes):
            configured_route = topology_route
            route_source = "configured_topology_clarity_policy"
        elif observed_route and (not allowed_routes or observed_route in allowed_routes):
            configured_route = observed_route
            route_source = "step4_visual_constraints"
        elif any(token in membership for token in ("branch", "merge", "shared_junction")):
            configured_route = connector_config.get("branch_route", "elbow_shared_junction")
            route_source = "configured_shared_graph_fallback"
        else:
            configured_route = connector_config.get("default_route", "straight")
            route_source = "configured_single_connector_fallback"
        starts = constraints.get("approximate_start_anchors_px", [])
        ends = constraints.get("approximate_end_anchors_px", [])
        starts, ends, endpoint_ownership_audit = semantic_owner_anchors(
            intent=intent,
            starts=starts,
            ends=ends,
            orientation=constraints.get("routing_orientation"),
            boxes=boxes_by_owner,
            junctions=constraints.get("junction_positions_px", []),
        )
        axis = routing_axis(constraints.get("routing_orientation"), starts, ends)
        if (
            membership == "single"
            and len(starts) == 1
            and len(ends) == 1
            and connector_config.get("routing", {}).get("avoid_redundant_terminal_bends", True)
        ):
            aligned = (
                abs(starts[0][1] - ends[0][1]) <= 1
                if axis == "horizontal"
                else abs(starts[0][0] - ends[0][0]) <= 1
            )
            if aligned and configured_route != "straight":
                configured_route = "straight"
                route_source = "deterministic_zero_bend_simplification"
        junction_treatment = constraints.get("junction_treatment", {"style": "none"})
        if not intent.get("junction_semantic_role"):
            junction_treatment = {"style": "none", "reason": "logical_junction_has_no_independent_semantic_role"}
        spans = [
            round(math.dist(start, end), 2)
            for start, end in zip(starts, ends)
            if len(start) == 2 and len(end) == 2
        ]
        required_clear = connector_config.get("arrowhead", {}).get("minimum_clear_segment_px", 0)
        connector_plans.append({
            "entity_id": entity["id"],
            "relationship_intent": intent,
            "topology": constraints.get("topology", {}),
            "configured_route": configured_route,
            "route_source": route_source,
            "measured_routing_corridor": constraints["routing_corridor"],
            "approximate_start_anchors_px": starts,
            "approximate_end_anchors_px": ends,
            "endpoint_ownership_audit": endpoint_ownership_audit,
            "raster_endpoint_role": "soft_routing_evidence_only",
            "junction_positions_px": constraints.get("junction_positions_px", []),
            "routing_orientation": constraints.get("routing_orientation"),
            "stroke_style": constraints.get("stroke_style", {}),
            "junction_treatment": junction_treatment,
            "arrowhead_treatment": constraints.get("arrowhead_treatment"),
            "anchor_spans_px": spans,
            "arrowhead_clearance_px": required_clear,
            "arrowhead_clearance_passed": all(span >= required_clear for span in spans) if spans else True,
            "qa_checks": ["endpoint_attachment", "arrowhead_legibility", "component_collision", "branch_junction_clarity", "unnecessary_bends", "peer_route_consistency"],
            "exact_raster_path_is_authoritative": False,
        })

    contract = {
        "schema_version": "0.3.0",
        "source_step4": str(Path(args.step4).resolve()),
        "source_handoff": str(Path(args.handoff).resolve()),
        "full_slide_dimensions_px": handoff["full_slide_dimensions_px"],
        "generation_region": handoff["generation_region"],
        "deck_chrome_configuration": handoff.get("deck_chrome_configuration", {}),
        "resolved_chrome_content": handoff.get("resolved_chrome_content", {}),
        "coordinate_transform_to_full_slide": handoff["coordinate_transform_to_full_slide"],
        "reconstruction_units": units,
        "canonical_asset_mappings": icon_mappings,
        "connector_reconstruction_plans": connector_plans,
        "text_policy": {
            "content_source": "authoritative upstream source text",
            "logical_textbox_policy": "one native textbox per authored block",
            "measured_outer_geometry_is_hard_constraint": True,
            "raster_line_structure_is_soft_evidence": True,
            "autofit": "none",
            "explicit_margins_spacing_and_font": True,
            "grouped_typography_normalization": True
        },
        "image_policy": {
            "meaningful_image_entity_is_one_powerpoint_picture": True,
            "internal_pixels_emit_objects": False,
            "fallback": "slide understanding screenshot crop"
        },
        "connector_policy": {
            "primary_source": "relationship intent",
            "visual_constraints": ["approximate anchors", "junction positions", "routing type", "stroke style", "arrowhead treatment", "routing corridor"],
            "ordinary_connector_route": "native PowerPoint straight, elbow, curved, branch, merge, or shared-junction composition",
            "ordinary_connector_object_type": "native_powerpoint_connector",
            "separate_arrowhead_shapes_allowed": False,
            "raster_fragment_anchor_shapes_allowed": False,
            "non_rendering_routing_ports_allowed": True,
            "routing_ports_are_reconstruction_entities": False,
            "routing_port_purpose": "attach native connectors to measured junctions or normalized centerlines when preset shape connection sites are insufficient",
            "fragment_tracing_allowed": False,
            "redundant_raster_paths_may_consolidate": True,
            "minimum_visible_arrowhead_px": connector_config.get("arrowhead", {}).get("minimum_visible_endpoint_px", 14),
            "exact_raster_path_authoritative": False,
            "peer_normalization": True,
            "terminal_route_simplification": {
                "prefer_axis_aligned_segments": True,
                "use_measured_terminal_anchor_over_container_center": True,
                "remove_final_bend_when_junction_and_terminal_anchor_share_an_axis": True,
                "maximum_ordinary_bends": connector_config.get("routing", {}).get("maximum_ordinary_bends", 2)
            },
            "custom_geometry_exception": "only when the connector is itself a meaningful designed visual"
        },
        "icon_policy": {
            "placement_authority": "measured icon slot",
            "generated_glyph_role": "semantic evidence only",
            "canonical_asset_fit": "explicit proportional contain geometry and center",
            "allow_stretch": False,
            "compute_final_width_and_height_from_source_svg_aspect_ratio": True,
            "maximize_within_padded_slot": True,
            "aspect_ratio_qa_required": True,
            "slot_surface": "remove when temporary, retain when part of final component design"
        },
        "z_order": [
            "connectors",
            "stage containers",
            "module cards and grid dividers",
            "raster image objects",
            "canonical SVG assets",
            "native textboxes"
        ],
        "style_configuration": handoff["style_configuration"],
        "icon_slot_configuration": handoff.get("icon_slot_configuration", {}),
        "connector_configuration": connector_config,
        "connector_configuration_qa": handoff.get("connector_configuration_qa", {}),
        "exact_source_content": handoff["exact_source_content"]
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
