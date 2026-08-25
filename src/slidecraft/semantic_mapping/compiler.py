"""Validate and compile an Agent-authored visual analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from PIL import Image

from slidecraft.providers.file import RecordedVisualAnalysis
from slidecraft.segmentation.policy import decide_segmentation


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "schemas" / "semantic_scene_draft.schema.json"


def load_schema() -> dict[str, Any]:
    return json.loads(_schema_path().read_text(encoding="utf-8"))


def load_connector_audit_schema() -> dict[str, Any]:
    path = _schema_path().with_name("connector_audit.schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["$defs"] = load_schema().get("$defs", {})
    for item in schema["properties"]["connector_audits"]["items"]["properties"].values():
        if isinstance(item, dict) and isinstance(item.get("$ref"), str) and item["$ref"].startswith("semantic_scene_draft.schema.json#"):
            item["$ref"] = item["$ref"].split("#", 1)[1]
    return schema


def _audit_connectors(analysis: RecordedVisualAnalysis, image_path: Path, draft: dict[str, Any], handoff: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    connector_ids = [entity["id"] for entity in draft["entities"] if entity["kind"] == "connector"]
    if not connector_ids or not analysis.supports_connector_audit:
        return draft, None
    schema = load_connector_audit_schema()
    result = analysis.result_for("slidecraft_connector_audit")
    errors = sorted(Draft202012Validator(schema).iter_errors(result), key=lambda error: list(error.path))
    if errors:
        summary = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:8])
        raise ValueError(f"Connector audit failed JSON Schema validation: {summary}")
    audits = {item["connector_id"]: item for item in result["connector_audits"]}
    if set(audits) != set(connector_ids):
        raise ValueError("Connector audit must return exactly one record for every connector entity")
    for entity in draft["entities"]:
        if entity["id"] not in audits:
            continue
        entity["connector_intent"] = audits[entity["id"]]["connector_intent"]
        entity["visual_constraints"] = audits[entity["id"]]["visual_constraints"]
    return draft, result


def _scale_box(box: list[int], width: int, height: int) -> list[int]:
    x = round(box[0] * width / 1000)
    y = round(box[1] * height / 1000)
    w = max(1, round(box[2] * width / 1000))
    h = max(1, round(box[3] * height / 1000))
    x = min(max(0, x), width - 1)
    y = min(max(0, y), height - 1)
    return [x, y, min(w, width - x), min(h, height - y)]


def _scale_point(point: list[int], width: int, height: int) -> list[int]:
    return [min(width - 1, max(0, round(point[0] * width / 1000))), min(height - 1, max(0, round(point[1] * height / 1000)))]


def _resolve_source_path(value: Any, path: str | None) -> Any:
    if not path:
        return None
    current = value
    for token in path.replace("]", "").replace("[", ".").split("."):
        if not token:
            continue
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            return None
    return current


def _text_similarity(left: str, right: str) -> float:
    import difflib

    def normalize(text: str) -> str:
        return " ".join(text.lower().split())

    return difflib.SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def _validate_graph(draft: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entity_ids = [entity["id"] for entity in draft["entities"]]
    group_ids = [group["id"] for group in draft["groups"]]
    if len(entity_ids) != len(set(entity_ids)):
        errors.append("duplicate_entity_ids")
    if len(group_ids) != len(set(group_ids)):
        errors.append("duplicate_group_ids")
    known = set(entity_ids) | set(group_ids)
    for group in draft["groups"]:
        missing = sorted(set(group["children"]) - known)
        if missing:
            errors.append(f"group:{group['id']}:unknown_children:{','.join(missing)}")
    for entity in draft["entities"]:
        if entity["kind"] != "connector":
            continue
        intent = entity.get("connector_intent")
        visual = entity.get("visual_constraints")
        if not intent or not visual:
            errors.append(f"connector:{entity['id']}:missing_intent_or_visual_constraints")
            continue
        endpoints = set(intent["source_entities"]) | set(intent["target_entities"])
        missing = sorted(endpoints - known)
        if missing:
            errors.append(f"connector:{entity['id']}:unknown_endpoints:{','.join(missing)}")
    return errors


@dataclass
class SemanticMapCompiler:
    analysis: RecordedVisualAnalysis
    segmentation_mode: str = "auto"

    def compile(
        self,
        *,
        image_path: Path,
        upstream_handoff: dict[str, Any],
    ) -> dict[str, Any]:
        image_path = image_path.resolve()
        with Image.open(image_path) as image:
            width, height = image.size
        schema = load_schema()
        draft = self.analysis.result_for("slidecraft_semantic_scene")
        errors = sorted(Draft202012Validator(schema).iter_errors(draft), key=lambda error: list(error.path))
        if errors:
            summary = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:8])
            raise ValueError(f"Semantic scene failed JSON Schema validation: {summary}")
        graph_errors = _validate_graph(draft)
        if graph_errors:
            raise ValueError(f"Semantic scene graph is invalid: {graph_errors}")
        quality = {
            "meaningful_granularity": 1.0,
            "source_coverage": 1.0,
            "relationship_completeness": 1.0,
            "uncertainties": [],
            **draft.get("quality", {}),
        }
        draft["quality"] = quality
        draft, connector_audit = _audit_connectors(self.analysis, image_path, draft, upstream_handoff)
        graph_errors = _validate_graph(draft)
        if graph_errors:
            raise ValueError(f"Audited connector graph is invalid: {graph_errors}")

        exact_source = upstream_handoff.get("exact_source_content", {})
        assets = {
            item.get("internal", item).get("asset_id"): item.get("internal", item)
            for item in upstream_handoff.get("selected_assets", [])
            if item.get("internal", item).get("asset_id")
        }
        source_checks: list[dict[str, Any]] = []
        connector_audits: list[dict[str, Any]] = []
        entities: list[dict[str, Any]] = []
        for raw in draft["entities"]:
            entity = {key: value for key, value in raw.items() if not key.endswith("_norm")}
            entity["bbox_hint"] = _scale_box(raw["bbox_norm"], width, height)
            if raw["kind"] == "text":
                source_value = _resolve_source_path(exact_source, raw.get("authoritative_source_path"))
                if source_value is not None and not isinstance(source_value, (dict, list)):
                    authored_text = str(source_value)
                    similarity = _text_similarity(raw.get("visible_text", ""), authored_text)
                    entity["authored_text"] = authored_text
                    entity["text"] = authored_text
                    source_checks.append({
                        "entity_id": raw["id"],
                        "source_path": raw.get("authoritative_source_path"),
                        "visible_to_authoritative_similarity": round(similarity, 4),
                        "status": "grounded",
                    })
                else:
                    entity["text"] = raw.get("visible_text", "")
                    entity["authored_text"] = raw.get("visible_text", "")
                    source_checks.append({"entity_id": raw["id"], "status": "visible_text_fallback"})
            if raw["kind"] == "icon_slot":
                entity["slot_bbox_hint"] = _scale_box(raw.get("slot_bbox_norm", raw["bbox_norm"]), width, height)
                if raw.get("generated_glyph_bbox_norm"):
                    entity["generated_glyph_bbox_hint"] = _scale_box(raw["generated_glyph_bbox_norm"], width, height)
                requested = raw.get("upstream_asset_id")
                candidates = [candidate for candidate in raw.get("candidate_asset_ids", []) if candidate in assets]
                if requested and requested in assets:
                    entity["upstream_asset_id"] = requested
                    entity["asset_mapping_status"] = "exact_agent_selected_asset"
                elif candidates:
                    entity["asset_mapping_status"] = "agent_resolution_required"
                    entity["available_upstream_candidate_ids"] = candidates
                else:
                    entity["asset_mapping_status"] = "unresolved_canonical_asset"
            if raw["kind"] == "image":
                requested = raw.get("upstream_asset_id")
                if requested and requested in assets:
                    selected = assets[requested]
                    canonical_file = selected.get("canonical_file")
                    if not canonical_file:
                        raise ValueError(f"Mapped project visual {requested} has no canonical file")
                    entity["upstream_asset_id"] = requested
                    entity["upstream_asset_mapping"] = {
                        "asset_id": requested,
                        "canonical_file": canonical_file,
                        "mapping_status": "exact_agent_selected_project_visual",
                        "preserve_exact_content": True,
                        "preserve_aspect_ratio": True,
                    }
                    entity["asset_mapping_status"] = "exact_agent_selected_project_visual"
                elif requested:
                    raise ValueError(
                        f"Image entity {raw['id']} maps to {requested}, which was not selected for this slide"
                    )
                elif raw["reconstruction_route"] == "canonical_icon_or_image_asset":
                    raise ValueError(
                        f"Image entity {raw['id']} uses the canonical asset route without an Agent-selected upstream asset"
                    )
                else:
                    entity["asset_mapping_status"] = "generated_image_screenshot_fallback"
            if raw["kind"] == "connector":
                visual = dict(raw["visual_constraints"])
                visual["start_anchors_px"] = [_scale_point(point, width, height) for point in visual.pop("start_anchors_norm")]
                visual["end_anchors_px"] = [_scale_point(point, width, height) for point in visual.pop("end_anchors_norm")]
                visual["junctions_px"] = [_scale_point(point, width, height) for point in visual.pop("junctions_norm")]
                visual["routing_corridor_px"] = _scale_box(visual.pop("routing_corridor_norm"), width, height)
                entity["visual_constraints"] = visual
                connector_audits.append({
                    "entity_id": raw["id"],
                    "resolved_source_entities": raw["connector_intent"]["source_entities"],
                    "resolved_target_entities": raw["connector_intent"]["target_entities"],
                    "topology": raw["connector_intent"]["structure_membership"],
                    "endpoint_ownership_reasoning": raw["connector_intent"]["endpoint_ownership_reasoning"],
                    "layout_feasibility": raw["connector_intent"]["layout_feasibility"],
                    "audit_confidence": raw["connector_intent"]["audit_confidence"],
                    "recommended_route": visual["routing_type"],
                    "junction_treatment": visual.get("junction_treatment", {"style": "none"}),
                })
            decision = decide_segmentation(raw, mode=self.segmentation_mode)
            entity["sam_prompt"] = decision.use_segmentation
            entity["segmentation_policy_reason"] = decision.reason
            entities.append(entity)

        groups = [
            {**{key: value for key, value in group.items() if key != "bbox_norm"}, "bbox_hint": _scale_box(group["bbox_norm"], width, height)}
            for group in draft["groups"]
        ]
        reading_order = draft["slide"]["reading_order"]
        return {
            "schema_version": "1.0.0",
            "slide": {"intent": draft["slide"]["intent"], "canvas_px": [width, height], "reading_order": reading_order},
            "ambiguities": quality["uncertainties"],
            "groups": groups,
            "entities": entities,
            "relationships": draft["relationships"],
            "semantic_mapping_runtime": {
                "authored_by": self.analysis.source_id,
                "schema": "semantic_scene_draft.schema.json",
                "coordinate_compilation": "normalized_0_to_1000_to_pixels",
                "quality": quality,
                "source_grounding_checks": source_checks,
                "connector_semantic_audits": connector_audits,
                "focused_connector_audit_pass": {
                    "executed": connector_audit is not None,
                    "authored_by": self.analysis.source_id if connector_audit is not None else None,
                    "quality": connector_audit.get("quality") if connector_audit else None,
                },
                "eligible_sam_entity_ids": [entity["id"] for entity in entities if entity["sam_prompt"]],
            },
        }


def compile_semantic_map(
    *,
    analysis: RecordedVisualAnalysis,
    image_path: Path,
    upstream_handoff: dict[str, Any],
    segmentation_mode: str = "auto",
) -> dict[str, Any]:
    return SemanticMapCompiler(analysis=analysis, segmentation_mode=segmentation_mode).compile(
        image_path=image_path,
        upstream_handoff=upstream_handoff,
    )
