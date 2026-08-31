"""Read host-authored raster choices without judging image quality."""
from __future__ import annotations


def illustration_decisions(semantic: dict) -> list[tuple[dict, dict]]:
    result = []
    for entity in semantic.get("entities", []):
        if entity.get("kind") != "image" or entity.get("visual_source_class") != "novel_illustration" or entity.get("meaningful_visible") is False:
            continue
        decision = entity.get("raster_decision", {})
        action = decision.get("action")
        if action not in {"reuse_original", "refine", "clean_plate", "preserve_composite"}:
            raise ValueError(f"{entity.get('id')}: explicit raster_decision.action required")
        if decision.get("reviewed_by") != "host_agent_visual_reasoning" or not str(decision.get("reason", "")).strip():
            raise ValueError(f"{entity.get('id')}: raster choice needs host visual reasoning")
        if action == "refine" and decision.get("occluding_native_text_ids"):
            raise ValueError(f"{entity.get('id')}: resolve editable text occlusion before isolated refinement")
        result.append((entity, decision))
    return result


def illustration_gate_errors(semantic: dict, approvals: dict) -> list[str]:
    try:
        decisions = illustration_decisions(semantic)
    except ValueError as exc:
        return [str(exc)]
    editing_ids = [str(e["id"]) for e, d in decisions if d["action"] in {"refine", "clean_plate"}]
    gate = approvals.get("illustrations", {}) or {}
    if editing_ids and gate.get("status") != "approved":
        return [f"illustration editing approval required for {editing_ids}"]
    if editing_ids and not set(editing_ids).issubset(set(gate.get("entity_ids", []))):
        return ["illustration editing approval must identify all edited entity_ids"]
    return []
