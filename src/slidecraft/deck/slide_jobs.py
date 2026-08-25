"""Compile deck-plan jobs into slide-specific generation requests."""

from __future__ import annotations

from typing import Any


def build_slide_request(
    *, job: dict[str, Any], deck_request: dict[str, Any], project_assets: list[dict[str, Any]]
) -> dict[str, Any]:
    requested_ids = set(job.get("asset_ids", []))
    allocated_assets = []
    for asset in project_assets:
        required_here = (
            asset.get("usage_policy") == "required_each_slide"
            or asset["asset_id"] in requested_ids
            or job["slide_id"] in asset.get("slide_ids", [])
        )
        if asset["asset_id"] not in requested_ids and not required_here:
            continue
        allocated_assets.append({
            "asset_id": asset["asset_id"],
            "semantic_role": asset.get("semantic_role"),
            "dimension_role": asset.get("dimension_role", "module_icon"),
            "name": asset["name"],
            "description": asset.get("description") or asset.get("semantic_role") or asset["name"],
            "canonical_file": asset["stored_path"],
            "required_usage": required_here,
            "mandatory": required_here,
        })
    metadata = deck_request.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {"label": str(metadata)}
    return {
        "schema_version": "1.0.0",
        "slide_id": job["slide_id"],
        "objective": job["communication_job"],
        "exact_content": {
            "title": job["message_title"],
            "subtitle": job["communication_job"],
            "content": [atom["value"] for atom in job.get("source_atoms", [])],
            "relationships": job.get("relationships", []),
        },
        "explicit_human_constraints": deck_request.get("constraints", []),
        "user_provided_assets": allocated_assets,
        "generation_route": "image_generation",
        "approval_mode": deck_request.get(
            "approval_mode",
            "explicit_delegation" if deck_request.get("delegated_execution") else "interactive_required",
        ),
        "run_context": {
            "project_name": deck_request.get("project_name", deck_request.get("objective", "")),
            "organization": metadata.get("organization", ""),
            "confidentiality": metadata.get("confidentiality", ""),
            "date": metadata.get("date", ""),
            "slide_number": job["ordinal"],
            "section_id": job.get("section_id"),
        },
        "chrome_content_proposal": job.get(
            "chrome_content_proposal", deck_request.get("chrome_content_proposal", {})
        ),
        "deck_job": {
            "role": job.get("role"),
            "dependencies": job.get("dependencies", []),
            "terminology": job.get("terminology", []),
            "cross_slide_requirements": job.get("cross_slide_requirements", []),
        },
    }
