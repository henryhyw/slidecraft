"""Constructor contract coverage checks shared by every backend."""

from __future__ import annotations

import math
from typing import Any


class ConstructorConformanceError(ValueError):
    """Raised before rendering when required reconstruction policy was dropped."""


def validate_contract_consumption(
    *,
    measured_scene: dict[str, Any],
    contract: dict[str, Any],
    objects: list[dict[str, Any]],
    scale_xy: list[float],
    offset_y: int,
) -> dict[str, Any]:
    object_ids = [item["id"] for item in objects]
    duplicate_ids = sorted({identifier for identifier in object_ids if object_ids.count(identifier) > 1})
    by_id = {item["id"]: item for item in objects}
    non_emitting = {
        unit["id"] for unit in contract.get("reconstruction_units", []) if unit.get("emits_ppt_object") is False
    }
    text_ids = {entity["id"] for entity in measured_scene.get("entities", []) if entity.get("kind") == "text" and entity["id"] not in non_emitting}
    emitted_text_ids = {item["id"] for item in objects if item.get("kind") == "textbox" and not item["id"].startswith("CHROME_")}
    asset_ids = {item["entity_id"] for item in contract.get("canonical_asset_mappings", [])}
    icon_asset_ids = {
        item["entity_id"]
        for item in contract.get("canonical_asset_mappings", [])
        if item.get("asset_kind", "icon_slot") == "icon_slot"
    }
    emitted_asset_ids = {item["id"] for item in objects if item.get("kind") == "image" and item.get("selected_asset_id")}
    connector_ids = {item["entity_id"] for item in contract.get("connector_reconstruction_plans", [])}
    emitted_connector_ids = {item["id"] for item in objects if item.get("kind") == "connector_graph"}
    missing_surfaces = sorted(identifier for identifier in icon_asset_ids if f"{identifier}.icon_slot_surface" not in by_id)
    icon_containment_failures = []
    for identifier in sorted(asset_ids & emitted_asset_ids):
        surface = by_id.get(f"{identifier}.icon_slot_surface")
        glyph = by_id.get(identifier)
        if not surface or not glyph:
            continue
        sx, sy, sw, sh = surface["bbox_px"]
        gx, gy, gw, gh = glyph["bbox_px"]
        if gx < sx or gy < sy or gx + gw > sx + sw or gy + gh > sy + sh:
            icon_containment_failures.append(identifier)

    entity_by_id = {entity["id"]: entity for entity in measured_scene.get("entities", [])}
    group_by_id = {group["id"]: group for group in measured_scene.get("groups", [])}

    def attachment_entity(identifier: str) -> dict[str, Any] | None:
        if identifier in entity_by_id:
            return entity_by_id[identifier]
        group = group_by_id.get(identifier)
        if not group:
            return None
        for child in group.get("children", []):
            entity = entity_by_id.get(child)
            if entity and entity.get("kind") in {"shape", "novel_visual"}:
                return entity
        for child in group.get("children", []):
            nested = attachment_entity(child)
            if nested:
                return nested
        return None

    def owner_box(identifier: str) -> list[float] | None:
        entity = entity_by_id.get(identifier)
        if entity:
            return entity.get("measurement", {}).get("layout_bbox", {}).get("px")
        group = group_by_id.get(identifier)
        return group.get("bbox_hint") if group else None

    connector_endpoint_failures = []
    connector_clearance_failures = []
    connector_topology_failures = []
    connector_axis_failures = []
    connector_junction_semantics_failures = []
    connector_optimality_failures = []
    allowed_routes = set(contract.get("connector_configuration", {}).get("allowed_routing_types", []))
    minimum_terminal = float(contract.get("connector_configuration", {}).get("arrowhead", {}).get("minimum_clear_segment_px", 34))
    for plan in contract.get("connector_reconstruction_plans", []):
        intent = plan.get("relationship_intent", {})
        sources = intent.get("source_entities", [])
        targets = intent.get("target_entities", [])
        source_anchors = plan.get("approximate_start_anchors_px", [])
        anchors = plan.get("approximate_end_anchors_px", [])
        junctions = plan.get("junction_positions_px", [])
        route = plan.get("configured_route")
        is_shared = len(sources) > 1 or len(targets) > 1
        if not sources or not targets:
            connector_topology_failures.append({"connector": plan["entity_id"], "reason": "missing_semantic_endpoint"})
        if len(source_anchors) != len(sources) or len(anchors) != len(targets):
            connector_topology_failures.append({
                "connector": plan["entity_id"],
                "reason": "anchor_cardinality_mismatch",
                "sources": len(sources),
                "source_anchors": len(source_anchors),
                "targets": len(targets),
                "target_anchors": len(anchors),
            })
        if is_shared and not junctions:
            connector_topology_failures.append({"connector": plan["entity_id"], "reason": "shared_graph_missing_junction"})
        if is_shared and route and "shared_junction" not in route:
            connector_topology_failures.append({"connector": plan["entity_id"], "reason": "shared_graph_route_is_not_shared", "route": route})
        if allowed_routes and route not in allowed_routes:
            connector_topology_failures.append({"connector": plan["entity_id"], "reason": "route_not_allowed", "route": route})
        orientation = str(plan.get("routing_orientation") or "").lower()
        if len(source_anchors) == 1 and len(anchors) == 1 and route == "straight":
            if orientation.startswith("horizontal") and abs(source_anchors[0][1] - anchors[0][1]) > 1:
                connector_axis_failures.append({"connector": plan["entity_id"], "reason": "horizontal_peer_flow_is_sloped"})
            if orientation.startswith("vertical") and abs(source_anchors[0][0] - anchors[0][0]) > 1:
                connector_axis_failures.append({"connector": plan["entity_id"], "reason": "vertical_peer_flow_is_sloped"})
        junction_treatment = plan.get("junction_treatment", {})
        if junction_treatment.get("style") not in {None, "none"} and not intent.get("junction_semantic_role"):
            connector_junction_semantics_failures.append({
                "connector": plan["entity_id"],
                "reason": "visible_junction_has_no_independent_semantic_role",
            })
        if junctions:
            junction = junctions[0]
            tolerance = float(contract.get("connector_configuration", {}).get("routing", {}).get("axis_alignment_tolerance_px", 8))
            if orientation.startswith("horizontal") or "horizontal_inputs" in orientation or "horizontal_curves" in orientation:
                if len(sources) == 1 and source_anchors:
                    box = owner_box(sources[0])
                    if box and box[1] <= junction[1] <= box[1] + box[3] and abs(source_anchors[0][1] - junction[1]) > tolerance:
                        connector_optimality_failures.append({"connector": plan["entity_id"], "reason": "avoidable_source_terminal_bend"})
                if len(targets) == 1 and anchors:
                    box = owner_box(targets[0])
                    if box and box[1] <= junction[1] <= box[1] + box[3] and abs(anchors[0][1] - junction[1]) > tolerance:
                        connector_optimality_failures.append({"connector": plan["entity_id"], "reason": "avoidable_target_terminal_bend"})
            if orientation.startswith("vertical"):
                if len(sources) == 1 and source_anchors:
                    box = owner_box(sources[0])
                    if box and box[0] <= junction[0] <= box[0] + box[2] and abs(source_anchors[0][0] - junction[0]) > tolerance:
                        connector_optimality_failures.append({"connector": plan["entity_id"], "reason": "avoidable_source_terminal_bend"})
                if len(targets) == 1 and anchors:
                    box = owner_box(targets[0])
                    if box and box[0] <= junction[0] <= box[0] + box[2] and abs(anchors[0][0] - junction[0]) > tolerance:
                        connector_optimality_failures.append({"connector": plan["entity_id"], "reason": "avoidable_target_terminal_bend"})
        for target_id, anchor in zip(targets, anchors):
            target = attachment_entity(target_id)
            if not target:
                connector_endpoint_failures.append({"connector": plan["entity_id"], "target": target_id, "reason": "missing_attachment_surface"})
                continue
            x, y, width, height = target["measurement"]["layout_bbox"]["px"]
            if x <= anchor[0] <= x + width and y <= anchor[1] <= y + height:
                depth = min(anchor[0] - x, x + width - anchor[0], anchor[1] - y, y + height - anchor[1])
                if depth > 2:
                    connector_endpoint_failures.append({"connector": plan["entity_id"], "target": target_id, "inside_depth_px": depth})
        if (len(targets) > 1 or len(plan.get("relationship_intent", {}).get("source_entities", [])) > 1) and plan.get("junction_positions_px"):
            junction = plan["junction_positions_px"][0]
            for target_id, anchor in zip(targets, anchors):
                distance = math.hypot(anchor[0] - junction[0], anchor[1] - junction[1])
                if distance < minimum_terminal:
                    connector_clearance_failures.append({"connector": plan["entity_id"], "target": target_id, "terminal_length_px": round(distance, 2), "minimum_px": minimum_terminal})
    chrome_required = bool(contract.get("deck_chrome_configuration", {}).get("enabled"))
    chrome_ids = {identifier for identifier in object_ids if identifier.startswith("CHROME_")}
    required_chrome = {
        "CHROME_HEADER.left", "CHROME_HEADER.right", "CHROME_HEADER.rule", "CHROME_HEADER.accent",
        "CHROME_FOOTER.left", "CHROME_FOOTER.center", "CHROME_FOOTER.right", "CHROME_FOOTER.rule",
    } if chrome_required else set()
    failures = {
        "duplicate_object_ids": duplicate_ids,
        "missing_text_entities": sorted(text_ids - emitted_text_ids),
        "missing_canonical_assets": sorted(asset_ids - emitted_asset_ids),
        "missing_icon_slot_surfaces": missing_surfaces,
        "icon_glyphs_outside_slots": icon_containment_failures,
        "missing_connector_graphs": sorted(connector_ids - emitted_connector_ids),
        "connector_endpoint_attachment": connector_endpoint_failures,
        "connector_terminal_clearance": connector_clearance_failures,
        "connector_topology_contract": connector_topology_failures,
        "connector_axis_alignment": connector_axis_failures,
        "connector_junction_semantics": connector_junction_semantics_failures,
        "connector_route_optimality": connector_optimality_failures,
        "missing_deck_chrome": sorted(required_chrome - chrome_ids),
    }
    failures = {key: value for key, value in failures.items() if value}
    report = {
        "passed": not failures,
        "coordinate_transform": {"scale_xy": scale_xy, "offset_y_px": offset_y, "applied": True},
        "required_counts": {
            "text_entities": len(text_ids),
            "canonical_assets": len(asset_ids),
            "icon_slot_surfaces": len(icon_asset_ids),
            "connector_graphs": len(connector_ids),
            "deck_chrome_objects": len(required_chrome),
        },
        "emitted_counts": {
            "text_entities": len(text_ids & emitted_text_ids),
            "canonical_assets": len(asset_ids & emitted_asset_ids),
            "icon_slot_surfaces": len(icon_asset_ids) - len(missing_surfaces),
            "connector_graphs": len(connector_ids & emitted_connector_ids),
            "deck_chrome_objects": len(required_chrome & chrome_ids),
        },
        "failures": failures,
    }
    if failures:
        raise ConstructorConformanceError(f"Constructor contract coverage failed: {failures}")
    return report


def validate_backend_capabilities(scene: dict[str, Any], supported_kinds: set[str]) -> dict[str, Any]:
    required = {item["kind"] for item in scene.get("objects", [])}
    unsupported = sorted(required - supported_kinds)
    if unsupported:
        raise ConstructorConformanceError(
            f"The selected constructor backend does not support these required routes: {unsupported}"
        )
    return {"passed": True, "required_kinds": sorted(required), "supported_kinds": sorted(supported_kinds)}
