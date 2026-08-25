"""Build visual-analysis instructions for the host Agent."""

from __future__ import annotations

import json
from typing import Any


def _compact_upstream(handoff: dict[str, Any]) -> dict[str, Any]:
    return {
        "generation_region": handoff.get("generation_region"),
        "exact_title_text": handoff.get("exact_title_text"),
        "exact_source_content": handoff.get("exact_source_content"),
        "semantic_design": handoff.get("semantic_design"),
        "selected_assets": [
            {
                "asset_id": item.get("internal", item).get("asset_id"),
                "semantic_role": item.get("internal", item).get("semantic_role"),
                "source_kind": item.get("internal", item).get("source_kind"),
                "visual_kind": item.get("internal", item).get("visual_kind"),
                "placement": item.get("internal", item).get("placement"),
                "intrinsic_aspect_ratio": item.get("internal", item).get("intrinsic_aspect_ratio"),
                "prompt_name": item.get("name"),
                "required_usage": item.get("required_usage"),
            }
            for item in handoff.get("selected_assets", [])
        ],
        "style_configuration": handoff.get("style_configuration"),
        "icon_slot_configuration": handoff.get("icon_slot_configuration"),
        "connector_configuration": handoff.get("connector_configuration"),
    }


def build_semantic_mapping_prompt(
    *,
    canvas_px: tuple[int, int],
    upstream_handoff: dict[str, Any],
) -> str:
    return f"""Compile this generated presentation image into a semantic scene draft for editable PowerPoint reconstruction.

COORDINATE CONTRACT
The image is {canvas_px[0]} by {canvas_px[1]} pixels. Report every box and point in normalized integer coordinates from 0 to 1000. A box is [x, y, width, height]. Include visible authored objects and meaningful groups. Do not emit raw contours, OCR words, edge fragments, individual letters, or decorative pixels as entities.

UPSTREAM GENERATION KNOWLEDGE
{json.dumps(_compact_upstream(upstream_handoff), ensure_ascii=False, indent=2)}

SEMANTIC GRANULARITY
1. Treat one logical authored text block as one text entity.
2. Treat repeated modules as groups with meaningful child objects.
3. Treat a native table as one table entity with row, column, merged-region, and subrow structure. Do not emit its cell borders as independent entities.
4. Treat charts as chart entities when authoritative data can be mapped upstream.
5. Treat replaceable icons and logos as icon_slot entities. The slot is placement authority. The generated glyph is evidence only.
6. Treat ordinary arrows and lines that communicate relationships as connector entities. Capture source and target objects, topology, direction, junctions, routing family, corridor, stroke, and arrowheads. Do not trace raster imperfections.
7. Treat a meaningful photograph, illustration, screenshot, or embedded preview as one image entity. Decide whether it is an exact supplied project visual or image content created by the image model.
8. Use shape or novel_visual only for independently authored visual objects. Mark irregular filled silhouettes with an appropriate segmentation_role.

RECONSTRUCTION ROUTING
For every meaningful entity, select its intended editable reconstruction route. Use native textboxes, tables, and charts when their authored structure is recoverable. Use the exact selected canonical asset for icon slots and supplied project images. Use a known reusable element only when the upstream component identity is supported. Use standard PowerPoint primitives and connectors for ordinary shapes and relationships. Use custom fitted geometry only when standard primitives cannot express a meaningful designed object. Use raster fallback for image content created by the image model or when editability cannot preserve the visual meaning.

SOURCE GROUNDING
Map text entities to authoritative_source_path whenever upstream source contains the text. Preserve visible text separately so deterministic validation can compare them. Map every icon slot to the exact upstream asset ID selected before generation. For every image entity, reason from its visible content, upstream semantic role, and selected asset list. When it is a supplied project visual, set upstream_asset_id to that exact selected asset and use canonical_icon_or_image_asset. When it is image content created by the image model, leave upstream_asset_id null and use raster_fallback. Never infer a match from bounding-box similarity alone. If the evidence is ambiguous, record the uncertainty instead of silently replacing the image with a project file.

RELATIONSHIPS AND STACKING
Return containment through groups. Return explicit flow, contribution, comparison, sequence, branch, merge, overlap, and back-to-front relationships where visible or supported by upstream intent. Every connector endpoint must reference an existing entity or group.

CONNECTOR ENDPOINT OWNERSHIP AUDIT
For every connector, reason about the conceptual producer and consumer before assigning endpoints. The nearest visible box or raster line endpoint is not automatically the semantic owner. If an output is produced by a whole stage, process, or grouped system, connect from that parent group. If distinct child modules independently contribute, connect from those children. Reconcile each endpoint with containment, sibling participation, reading logic, exact source content, and upstream semantic design. Treat raster endpoints as approximate routing evidence only.

CONNECTOR ROUTE AUDIT
Choose the cleanest standard connector system that expresses the resolved graph. Keep logical junctions separate from visible junction markers. A merge bus may have an invisible logical junction. Use a visible node only when the node itself is meaningful in the design. Prefer clear horizontal or vertical routing and avoid crossings, redundant bends, ambiguous curves, and attachment points that imply the wrong semantic owner.

QUALITY CHECK
Before returning, check meaningful granularity, source coverage, relationship completeness, duplicate objects, missing visible modules, and unsupported assumptions. Record genuine uncertainty instead of inventing precision.
"""


def build_connector_audit_prompt(*, scene_draft: dict[str, Any], upstream_handoff: dict[str, Any]) -> str:
    compact_scene = {
        "slide": scene_draft["slide"],
        "groups": scene_draft["groups"],
        "entities": [
            {
                "id": entity["id"],
                "kind": entity["kind"],
                "role": entity["role"],
                "bbox_norm": entity["bbox_norm"],
                "connector_intent": entity.get("connector_intent"),
                "visual_constraints": entity.get("visual_constraints"),
            }
            for entity in scene_draft["entities"]
        ],
        "relationships": scene_draft["relationships"],
    }
    return f"""Audit only the connector system in this generated slide. Preserve the identified components, groups, and overall layout.

UPSTREAM KNOWLEDGE
{json.dumps(_compact_upstream(upstream_handoff), ensure_ascii=False, indent=2)}

IDENTIFIED SEMANTIC SCENE
{json.dumps(compact_scene, ensure_ascii=False, indent=2)}

For every connector entity, independently determine the conceptual source owners, target owners, relationship type, direction, and topology. Reconcile endpoints with containment, sibling participation, reading logic, exact source content, and upstream semantic intent. An output owned by a complete stage must connect from the stage group, even if the raster line appears nearest to one child.

Choose the cleanest feasible standard connector graph within the existing layout. Prefer horizontal and vertical routing. Minimize bends. Avoid crossings, slopes between peer components, redundant terminal turns, hidden arrowheads, and attachment points that imply the wrong owner. Treat raster paths as soft evidence.

Logical buses and junctions are normally invisible. Set a visible junction treatment only when the junction is an independently meaningful semantic node. Return one audit for every connector ID and do not redesign other objects.
"""
