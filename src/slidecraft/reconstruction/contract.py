"""Build a reconstruction contract from measured semantic entities."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def _validate_refinement_plan(plan: dict[str, Any]) -> None:
    schema = json.loads(
        files("slidecraft.schemas").joinpath("refinement_plan.schema.json").read_text(encoding="utf-8")
    )
    errors = sorted(Draft202012Validator(schema).iter_errors(plan), key=lambda error: list(error.path))
    if errors:
        summary = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:8])
        raise ValueError(f"Agent refinement plan failed schema validation: {summary}")


def _asset_catalog(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in handoff.get("selected_assets", []):
        internal = item.get("internal", item)
        if internal.get("asset_id"):
            result[internal["asset_id"]] = internal
    return result


def _resolve_icon(entity: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    catalog = _asset_catalog(handoff)
    requested = entity.get("upstream_asset_id")
    if requested not in catalog:
        raise ValueError(
            f"Icon slot {entity['id']} has no exact Agent-selected upstream asset mapping. "
            "Semantic mapping must choose from the assets retained in the generation handoff."
        )
    selected = catalog[requested]
    path = selected.get("canonical_file")
    if not path or not Path(path).is_file():
        raise FileNotFoundError(f"Canonical asset for icon slot {entity['id']} is unavailable: {path}")
    return {
        "entity_id": entity["id"],
        "selected_asset_id": selected["asset_id"],
        "selected_asset_path": selected["canonical_file"],
        "selection_mode": selected.get("selection_mode", "exact_agent_selected_asset"),
        "target_bbox_source_px": entity.get("slot_bbox_hint") or entity["measurement"]["layout_bbox"]["px"],
        "preserve_aspect_ratio": True,
        "fit": "contain",
        "alignment": "center",
        "alternative_candidates": selected.get("alternative_candidates", []),
    }


def _connector_plan(entity: dict[str, Any]) -> dict[str, Any]:
    intent = entity.get("connector_intent") or {}
    visual = entity.get("visual_constraints") or {}
    if not intent or not visual.get("routing_type"):
        raise ValueError(f"Connector {entity['id']} is missing its Agent-audited intent or route")
    route = visual["routing_type"]
    return {
        "entity_id": entity["id"],
        "relationship_intent": intent,
        "approximate_start_anchors_px": visual.get("start_anchors_px", []),
        "approximate_end_anchors_px": visual.get("end_anchors_px", []),
        "junction_positions_px": visual.get("junctions_px", []),
        "configured_route": route,
        "routing_orientation": visual.get("routing_orientation", route),
        "stroke_style": visual.get("stroke_style", entity.get("style_hint", {})),
        "arrowhead_treatment": visual["arrowhead_treatment"],
        "junction_treatment": visual["junction_treatment"],
        "routing_corridor_px": visual.get("routing_corridor_px"),
    }


def build_reconstruction_contract(
    measured_scene: dict[str, Any],
    design: dict[str, Any],
    reasoned_refinement_plan: dict[str, Any],
) -> dict[str, Any]:
    _validate_refinement_plan(reasoned_refinement_plan)
    if reasoned_refinement_plan.get("authored_by") != "agent_reasoning":
        raise ValueError("Reconstruction contract requires an Agent-authored refinement plan")
    handoff = measured_scene.get("upstream_handoff", {})
    source = measured_scene["source"]
    source_width = int(source["width_px"])
    source_height = int(source["height_px"])
    full = list(handoff.get("full_slide_dimensions_px") or [source_width, source_height])
    region = handoff.get("generation_region", {})
    region_dimensions = list(region.get("dimensions_px") or [source_width, source_height])
    offset_y = int(region.get("offset_y_px", 0))
    scale = [region_dimensions[0] / source_width, region_dimensions[1] / source_height]
    units = []
    assets = []
    connectors = []
    for entity in measured_scene.get("entities", []):
        kind = entity["kind"]
        significance = entity.get("reconstruction_significance", "independent_object")
        emits = significance not in {"measurement_evidence", "owned_content", "non_authoritative_glyph"}
        units.append({
            "id": entity["id"],
            "semantic_kind": kind,
            "semantic_role": entity.get("role"),
            "selected_route": entity["reconstruction_route"],
            "node_class": "reconstruction_unit" if emits else "measurement_evidence",
            "emits_ppt_object": emits,
            "render_owner": entity.get("render_owner", entity["id"]),
            "bbox_px": entity["measurement"]["layout_bbox"]["px"],
        })
        if emits and kind in {"icon", "icon_slot"}:
            assets.append(_resolve_icon(entity, handoff))
        if emits and kind == "connector":
            connectors.append(_connector_plan(entity))
    chrome_configuration = dict(handoff.get("deck_chrome_configuration", design.get("deck_chrome", {})))
    resolved_chrome = handoff.get("resolved_chrome_content", {})
    if resolved_chrome:
        chrome_configuration = {
            **chrome_configuration,
            "current_slide_variant": resolved_chrome.get("variant", {}).get(
                "value", chrome_configuration.get("current_slide_variant", "content_slide")
            ),
            "header": {
                **chrome_configuration.get("header", {}),
                "left_text": resolved_chrome.get("header", {}).get("left_text", {}).get("value", ""),
                "right_text": resolved_chrome.get("header", {}).get("right_text", {}).get("value", ""),
            },
            "footer": {
                **chrome_configuration.get("footer", {}),
                "left_text": resolved_chrome.get("footer", {}).get("left_text", {}).get("value", ""),
                "center_text": resolved_chrome.get("footer", {}).get("center_text", {}).get("value", ""),
                "right_text": resolved_chrome.get("footer", {}).get("right_text_format", {}).get("value", ""),
            },
        }
    return {
        "schema_version": "1.0.0",
        "source_scene_evidence": source.get("path"),
        "full_slide_dimensions_px": full,
        "generation_region": {"offset_y_px": offset_y, "dimensions_px": region_dimensions},
        "coordinate_transform_to_full_slide": {"scale_xy": scale, "translation_px": [0, offset_y]},
        "deck_chrome_configuration": chrome_configuration,
        "resolved_chrome_content": resolved_chrome,
        "reconstruction_units": units,
        "canonical_asset_mappings": assets,
        "connector_reconstruction_plans": connectors,
        "connector_configuration": handoff.get("connector_configuration", design.get("connectors", {})),
        "z_order_relations": [
            relationship
            for relationship in measured_scene.get("relationships", [])
            if relationship.get("type") == "stacking"
            and relationship.get("back")
            and relationship.get("front")
        ],
        "fitted_text_contracts": [],
        "reasoned_refinement_plan": reasoned_refinement_plan,
        "evidence_policy": {
            "masks_contours_ocr_and_edges_emit_objects": False,
            "generated_icon_glyphs_emit_objects": False,
        },
    }
