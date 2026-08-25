"""Build a reconstruction contract from measured semantic entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from slidecraft.configuration import data_root, initialize_user_environment
from slidecraft.orchestration.icon_retrieval import retrieve_icons

ROUTES = {
    "text": "native_textbox",
    "table": "native_table",
    "chart": "native_editable_chart",
    "icon": "canonical_icon_or_image_asset",
    "icon_slot": "canonical_icon_or_image_asset",
    "image": "raster_fallback",
    "connector": "standard_powerpoint_shape_connector_composition",
    "shape": "standard_powerpoint_shape_connector_composition",
    "novel_visual": "custom_fitted_geometry",
}


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
    if requested in catalog and Path(catalog[requested]["canonical_file"]).is_file():
        selected = catalog[requested]
        mode = "exact_canonical_asset"
    else:
        initialize_user_environment(force=False)
        retrieved = retrieve_icons(
            data_root() / "libraries" / "icons",
            [{
                "semantic_role": entity.get("role", entity["id"]),
                "purpose": entity.get("semantic_icon_intent") or entity.get("role", "pictogram"),
                "concepts": [entity.get("semantic_icon_intent") or "pictogram"],
                "requirement": "optional",
            }],
        )
        selected = retrieved["assets"][0]
        mode = "semantic_library_substitution"
    return {
        "entity_id": entity["id"],
        "selected_asset_id": selected["asset_id"],
        "selected_asset_path": selected["canonical_file"],
        "selection_mode": mode,
        "target_bbox_source_px": entity.get("slot_bbox_hint") or entity["measurement"]["layout_bbox"]["px"],
        "preserve_aspect_ratio": True,
        "fit": "contain",
        "alignment": "center",
        "alternative_candidates": selected.get("alternative_candidates", []),
    }


def _connector_plan(entity: dict[str, Any]) -> dict[str, Any]:
    intent = entity.get("connector_intent") or {}
    visual = entity.get("visual_constraints") or {}
    route = visual.get("routing_type") or "straight"
    if (
        len(intent.get("source_entities", [])) > 1 or len(intent.get("target_entities", [])) > 1
    ) and "shared_junction" not in route:
        orientation = "horizontal" if "horizontal" in str(visual.get("routing_orientation", route)) else "vertical"
        route = f"orthogonal_shared_junction_{orientation}"
    return {
        "entity_id": entity["id"],
        "relationship_intent": intent,
        "approximate_start_anchors_px": visual.get("start_anchors_px", []),
        "approximate_end_anchors_px": visual.get("end_anchors_px", []),
        "junction_positions_px": visual.get("junctions_px", []),
        "configured_route": route,
        "routing_orientation": visual.get("routing_orientation", route),
        "stroke_style": visual.get("stroke_style", entity.get("style_hint", {})),
        "arrowhead_treatment": visual.get("arrowhead_treatment", "triangle_at_target"),
        "junction_treatment": visual.get("junction_treatment", {"style": "none"}),
        "routing_corridor_px": visual.get("routing_corridor_px"),
    }


def build_reconstruction_contract(measured_scene: dict[str, Any], design: dict[str, Any]) -> dict[str, Any]:
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
            "selected_route": ROUTES.get(kind, "custom_fitted_geometry"),
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
        "fitted_text_contracts": [],
        "evidence_policy": {
            "masks_contours_ocr_and_edges_emit_objects": False,
            "generated_icon_glyphs_emit_objects": False,
        },
    }
