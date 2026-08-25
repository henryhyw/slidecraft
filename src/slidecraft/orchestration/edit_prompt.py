"""Compose an image-edit prompt from a reviewer delta and authoritative state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_review_result(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)


def validate_review_result(result: dict[str, Any], review_config: dict[str, Any]) -> None:
    if result.get("decision") not in review_config["decision_values"]:
        raise ValueError("Review decision must be PASS or EDIT")
    issues = result.get("material_issues")
    delta = result.get("edit_delta")
    if not isinstance(issues, list) or not isinstance(delta, list):
        raise TypeError("material_issues and edit_delta must be lists")
    if len(issues) > review_config["maximum_material_issues"]:
        raise ValueError("Review returned too many material issues")
    if result["decision"] == "PASS" and (issues or delta):
        raise ValueError("PASS must have empty material_issues and edit_delta")
    if result["decision"] == "EDIT" and (not issues or not delta):
        raise ValueError("EDIT requires material issues and an edit delta")
    allowed_categories = set(review_config["review_categories"])
    for issue in issues:
        if issue.get("category") not in allowed_categories:
            raise ValueError(f"Unknown review category: {issue.get('category')}")
        if issue.get("severity") not in {"high", "medium"}:
            raise ValueError("Issue severity must be high or medium")
        for field in ("element", "problem", "correction"):
            if not str(issue.get(field, "")).strip():
                raise ValueError(f"Issue field is missing: {field}")
    for edit in delta:
        if not str(edit.get("element", "")).strip() or not str(edit.get("instruction", "")).strip():
            raise ValueError("Every edit delta needs an element and instruction")


def _asset_constraints(state: dict[str, Any]) -> list[dict[str, Any]]:
    constraints = []
    for asset in state["normalized_available_assets"]["assets"]:
        constraints.append({
            "prompt_id": asset["prompt_id"],
            "name": asset["name"],
            "required": bool(asset.get("required_usage", False)),
            "semantic_role": asset["internal"].get("semantic_role"),
            "target_visual_footprint_px": asset["dimensions"]["target_visual_footprint_px"],
            "authoritative_icon_slot": asset["dimensions"]["icon_slot"],
            "tolerance_percent": asset["dimensions"]["prompt_tolerance_percent"],
            "preserve_aspect_ratio": asset["dimensions"]["preserve_aspect_ratio"],
            "canonical_file": asset["internal"].get("canonical_file"),
        })
    return constraints


def build_edit_input_manifest(state: dict[str, Any], review_result: dict[str, Any], candidate_image: str | None) -> dict[str, Any]:
    categories = {issue["category"] for issue in review_result["material_issues"]}
    references = state["reference_retrieval"]["visual_references"]
    issue_text = " ".join(
        str(value)
        for issue in review_result["material_issues"]
        for value in (issue.get("element"), issue.get("problem"), issue.get("correction"))
    ).lower()
    needs_visual_reference_support = (
        "visual_reference_fidelity" in categories
        or ("semantic_content_fidelity" in categories and "reference" in issue_text)
    )
    return {
        "edit_target": {
            "path": str(Path(candidate_image).resolve()) if candidate_image else None,
            "role": "image to edit in place",
            "status": "available" if candidate_image else "attach_at_edit_time",
        },
        "supporting_visual_references": [
            {"reference_id": item["reference_id"], "path": item["path"], "role": "style precedent only"}
            for item in references
        ] if needs_visual_reference_support else [],
        "supporting_canonical_assets": [],
        "canonical_asset_policy": "Description-only during generation and image editing. Editable reconstruction restores exact canonical SVGs inside measured icon slots.",
        "attachment_policy": "Attach the edit target first. Attach only the supporting inputs listed for the detected issue categories.",
    }


def build_edit_prompt(state: dict[str, Any], review_result: dict[str, Any], candidate_image: str | None) -> tuple[str | None, dict[str, Any]]:
    manifest = build_edit_input_manifest(state, review_result, candidate_image)
    if review_result["decision"] == "PASS":
        return None, manifest

    canvas = state["derived_canvas"]
    deck = state["deck_design_configuration"]
    exact = state["slide_input"]["exact_content"]
    constraints = state["intake_manifest"]["constraint_register"]
    semantic = state["semantic_design"]
    guidance = state["guidance_profile"]
    assets = _asset_constraints(state)
    input_roles = {
        "edit_target": "The generated candidate is the only image to edit in place.",
        "visual_references": [
            {
                "reference_id": item["reference_id"],
                "role": "style and identity comparison only",
                "content_reuse_forbidden": True,
            }
            for item in manifest["supporting_visual_references"]
        ],
        "canonical_assets": [],
    }
    prompt = f"""Edit the attached generated slide in place.

Apply only these reviewer-approved corrections.
{json.dumps(review_result['edit_delta'], indent=2, ensure_ascii=False)}

INPUT IMAGE ROLES
{json.dumps(input_roles, indent=2, ensure_ascii=False)}
Never place a visual reference image inside the edited slide as content. Use visual references only to recognize mistaken content and preserve the established visual language. Canonical assets are not attached during image editing.

The correction list above is the complete edit scope. The configuration below is an invariant envelope. Use it to constrain the edit and preserve unaffected content. Do not treat invariant fields as requests for additional changes.

CANVAS INVARIANTS
Keep the output at {canvas['generation_canvas_px'][0]} × {canvas['generation_canvas_px'][1]} px. This is the title and main-content generation region at full-slide y = {canvas['generation_offset_y_px']} px. Do not add a header, footer, page number, footer rule, or excluded-region content.

TITLE INVARIANTS
{json.dumps(deck['title'], indent=2, ensure_ascii=False)}
Use the exact title text: {exact['title']}
Change the title only when it is named in the reviewer-approved corrections.

AUTHORITATIVE CONTENT INVARIANTS
{json.dumps(exact, indent=2, ensure_ascii=False)}
Preserve all authoritative content that is not explicitly named in the correction list. If a correction fixes missing or incorrect text, use the exact wording above.

HUMAN CONSTRAINT INVARIANTS
{json.dumps([item for item in constraints if item['status'] == 'active'], indent=2, ensure_ascii=False)}
Preserve every active hard constraint. Apply soft constraints and preferences where they remain compatible with the approved edit and all hard requirements.

SEMANTIC INVARIANTS
Main message: {semantic['main_message']}
Reading logic: {semantic['reading_logic']}
Relationships: {json.dumps(semantic['semantic_relationships'], ensure_ascii=False)}
Preserve every semantic relationship that is not explicitly named in the correction list.

COMMUNICATION GUIDANCE INVARIANTS
Profile: {guidance['profile_id']} version {guidance['version']}
{json.dumps(guidance['visual_communication'], indent=2, ensure_ascii=False)}
Preserve communication intent and design freedom from the selected profile. Do not turn profile principles into new unrequested layout edits.

STYLE INVARIANTS
{json.dumps(deck['style'], indent=2, ensure_ascii=False)}
Preserve the existing composition, typography, color system, spacing system, component language, and whitespace wherever the correction list does not require a local change.

ASSET INVARIANTS
{json.dumps(assets, indent=2, ensure_ascii=False)}
Preserve unaffected semantic icon roles and their authoritative rectangular slots. When an approved correction concerns an icon, keep the configured slot dimensions, center the recognizable placeholder inside it, preserve aspect ratio, and contain-fit it without overflow or distortion. Exact canonical assets are restored during editable reconstruction.

EDIT BOUNDARY
Make no unrequested layout changes. Make no aesthetic alternatives. Preserve every region and detail that is already correct. Return only the edited slide-region image.
"""
    return prompt, manifest
