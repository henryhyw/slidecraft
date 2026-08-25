"""Validate and resolve Agent-authored reusable-resource selections."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator


def _validate_selection_schema(selection: dict[str, Any]) -> None:
    schema = json.loads(
        files("slidecraft.schemas").joinpath("resource_selection.schema.json").read_text(encoding="utf-8")
    )
    errors = sorted(Draft202012Validator(schema).iter_errors(selection), key=lambda error: list(error.path))
    if errors:
        summary = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:8])
        raise ValueError(f"Agent resource selection failed schema validation: {summary}")


def _require_rationale(record: dict[str, Any], label: str) -> None:
    if not str(record.get("rationale", "")).strip():
        raise ValueError(f"{label} selection requires an Agent-authored rationale")


def resolve_resource_selection(
    selection: dict[str, Any],
    *,
    visual_search: dict[str, Any],
    icon_search: dict[str, Any],
    component_search: dict[str, Any],
    maximum_visual_references: int = 3,
) -> dict[str, Any]:
    """Resolve stable IDs from an Agent decision against current library candidates."""
    _validate_selection_schema(selection)
    if selection.get("authored_by") != "agent_reasoning":
        raise ValueError("Resource selection must declare authored_by as agent_reasoning")

    visual_catalog = {item["reference_id"]: item for item in visual_search.get("candidates", [])}
    visual_references = []
    for record in selection.get("visual_references", []):
        _require_rationale(record, "Visual reference")
        reference_id = record["reference_id"]
        if reference_id not in visual_catalog:
            raise ValueError(f"Unknown visual reference candidate {reference_id}")
        visual_references.append({
            **visual_catalog[reference_id],
            "role": "agent_selected_visual_reference",
            "selection_rationale": record["rationale"],
        })
    if len(visual_references) > maximum_visual_references:
        raise ValueError(f"Select no more than {maximum_visual_references} visual references")

    icon_sets = {item["semantic_role"]: item for item in icon_search.get("candidate_sets", [])}
    icons = []
    selected_asset_ids: set[str] = set()
    for record in selection.get("icons", []):
        _require_rationale(record, "Icon")
        role = record["semantic_role"]
        candidate_set = icon_sets.get(role)
        if candidate_set is None:
            raise ValueError(f"No icon search request exists for semantic role {role!r}")
        candidates = {item["asset_id"]: item for item in candidate_set["candidates"]}
        selected = candidates.get(record["asset_id"])
        if selected is None:
            raise ValueError(f"Unknown icon candidate {record['asset_id']} for semantic role {role!r}")
        if selected["asset_id"] in selected_asset_ids and not record.get("allow_reuse", False):
            raise ValueError(f"Icon {selected['asset_id']} is reused without an explicit allow_reuse decision")
        selected_asset_ids.add(selected["asset_id"])
        icons.append({
            "asset_id": selected["asset_id"],
            "semantic_role": role,
            "semantic_intent": candidate_set["semantic_intent"],
            "dimension_role": candidate_set["dimension_role"],
            "selection_mode": record.get("selection_mode", "agent_selected_library_asset"),
            "selection_rationale": record["rationale"],
            "library": "Tabler Icons Outline",
            "library_icon_id": selected["icon_id"],
            "canonical_file": selected["canonical_file"],
            "asset_provenance": selected.get("provenance", "local_icon_collection"),
            "source_url": selected.get("source_url"),
            "provider_release": selected.get("provider_release"),
            "prompt_name": record.get("prompt_name") or role.replace("_", " ").title(),
            "prompt_description": record.get("prompt_description") or selected["description"],
            "required_usage": candidate_set["required_usage"],
            "alternative_candidates": [
                {
                    "asset_id": item["asset_id"],
                    "library_icon_id": item["icon_id"],
                    "score": item["score"],
                    "matched_concepts": item["matched_concepts"],
                }
                for item in candidate_set["candidates"]
                if item["asset_id"] != selected["asset_id"]
            ][:3],
        })

    requested_roles = {item["semantic_role"] for item in icon_search.get("candidate_sets", []) if item["required_usage"]}
    selected_roles = {item["semantic_role"] for item in icons}
    missing_roles = sorted(requested_roles - selected_roles)
    if missing_roles:
        raise ValueError(f"Required icon roles have no Agent selection: {missing_roles}")

    component_catalog = {item["component_id"]: item for item in component_search.get("candidates", [])}
    components = []
    for record in selection.get("components", []):
        _require_rationale(record, "Reusable component")
        component_id = record["component_id"]
        candidate = component_catalog.get(component_id)
        if candidate is None:
            raise ValueError(f"Unknown component candidate {component_id}")
        if not candidate.get("eligible_for_agent_selection"):
            raise ValueError(f"Component {component_id} has no usable constructor implementation")
        components.append({**candidate, "selection_rationale": record["rationale"]})

    return {
        "schema_version": "1.0.0",
        "authored_by": "agent_reasoning",
        "decision_context": selection.get("decision_context", {}),
        "visual_references": visual_references,
        "icons": icons,
        "components": components,
        "search_evidence": {
            "visual_reference_provider": visual_search.get("provider_interface"),
            "icon_provider": icon_search.get("provider_interface"),
            "component_provider": component_search.get("provider_interface"),
        },
    }
