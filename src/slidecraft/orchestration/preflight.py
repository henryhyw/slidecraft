"""Build the human approval summary and detailed generation package."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolved_field(value: Any, source: str) -> dict[str, Any]:
    return {"value": value, "source": source}


def resolve_slide_chrome(deck: dict[str, Any], slide: dict[str, Any]) -> dict[str, Any]:
    configured = deck.get("deck_chrome", {})
    explicit = slide.get("chrome_content", {})
    proposed = slide.get("chrome_content_proposal", {})
    context = slide.get("run_context", {})
    configured_header = configured.get("header", {})
    configured_footer = configured.get("footer", {})
    explicit_header = explicit.get("header", {})
    explicit_footer = explicit.get("footer", {})
    proposed_header = proposed.get("header", {})
    proposed_footer = proposed.get("footer", {})

    project_name = context.get("project_name", slide.get("objective", "Project"))
    organization = context.get("organization", "")
    confidentiality = context.get("confidentiality", "")
    date = context.get("date", "")
    slide_number = context.get("slide_number", "{slide_number}")
    exact_title = slide.get("exact_content", {}).get("title", "")
    fallbacks = {
        "header.left_text": str(project_name).upper(),
        "header.right_text": str(exact_title).upper(),
        "footer.left_text": " | ".join(value for value in (organization, confidentiality) if value),
        "footer.center_text": str(project_name),
        "footer.right_text_format": " | ".join(value for value in (str(date), str(slide_number)) if value),
    }

    def choose(explicit_values: dict[str, Any], proposed_values: dict[str, Any], configured_values: dict[str, Any], key: str, path: str) -> dict[str, Any]:
        if key in explicit_values:
            return _resolved_field(explicit_values[key], "user_provided")
        if key in proposed_values:
            return _resolved_field(proposed_values[key], "framework_proposed")
        if key in configured_values:
            return _resolved_field(configured_values[key], "legacy_configured_default")
        return _resolved_field(fallbacks[path], "framework_derived_fallback")

    return {
        "variant": _resolved_field(
            explicit.get("variant", proposed.get("variant", configured.get("current_slide_variant", "content_slide"))),
            "user_provided" if "variant" in explicit else "framework_proposed" if "variant" in proposed else "framework_derived_fallback",
        ),
        "geometry": {
            "header_height_px": deck["exclusions_px"]["header"],
            "footer_height_px": deck["exclusions_px"]["footer"],
            "source": "deck_design_configuration",
            "user_confirmation_frequency": "when deck design configuration changes",
        },
        "header": {
            "left_text": choose(explicit_header, proposed_header, configured_header, "left_text", "header.left_text"),
            "right_text": choose(explicit_header, proposed_header, configured_header, "right_text", "header.right_text"),
        },
        "footer": {
            "left_text": choose(explicit_footer, proposed_footer, configured_footer, "left_text", "footer.left_text"),
            "center_text": choose(explicit_footer, proposed_footer, configured_footer, "center_text", "footer.center_text"),
            "right_text_format": choose(explicit_footer, proposed_footer, configured_footer, "right_text_format", "footer.right_text_format"),
        },
    }


def build_generation_preflight(
    deck: dict[str, Any],
    slide: dict[str, Any],
    intake: dict[str, Any],
    semantic_design: dict[str, Any],
    guidance_profile: dict[str, Any],
    canvas: dict[str, Any],
    assets: dict[str, Any],
    visual_references: list[dict[str, Any]],
    preflight_config: dict[str, Any],
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    chrome = resolve_slide_chrome(deck, slide)
    mandatory_assets = [item for item in assets["assets"] if item.get("required_usage")]
    missing_assets = [
        item["internal"]["asset_id"]
        for item in mandatory_assets
        if not item["internal"].get("canonical_file") and item["internal"].get("attachment_status") != "available"
    ]
    blocking = []
    if not intake["source_atoms"]:
        blocking.append({"code": "missing_authoritative_content", "message": "No authoritative source atoms are available."})
    if intake["quality"]["requires_user_resolution"]:
        blocking.append({"code": "unresolved_hard_constraint", "ids": intake["unresolved_constraint_ids"]})
    if missing_assets:
        blocking.append({"code": "missing_mandatory_asset", "asset_ids": missing_assets})

    exact = slide["exact_content"]
    slide_record = {
        "slide_id": slide["slide_id"],
        "objective": slide["objective"],
        "governing_message": semantic_design["main_message"],
        "title": exact.get("title", ""),
        "subtitle": exact.get("subtitle", ""),
        "route": slide.get("generation_route", "image_generation"),
        "chrome": chrome,
        "source_coverage": {
            "authoritative_source_atoms": intake["quality"]["authoritative_source_atom_count"],
            "materials": intake["quality"]["material_count"],
            "required_materials": sum(item.get("required_usage", False) for item in intake["materials"]),
            "unallocated_required_sources": [],
        },
        "constraints": intake["constraint_register"],
        "unresolved_assumptions": [
            {"type": "constraint", "id": item_id}
            for item_id in intake["unresolved_constraint_ids"]
        ],
    }
    asset_records = [{
        "asset_id": item["internal"]["asset_id"],
        "name": item["name"],
        "semantic_role": item["internal"]["semantic_role"],
        "usage": "mandatory" if item.get("required_usage") else "optional",
        "provenance": item["internal"].get("provenance"),
        "canonical_file": item["internal"].get("canonical_file"),
        "status": "ready" if item["internal"].get("canonical_file") else item["internal"].get("attachment_status", "pending"),
    } for item in assets["assets"]]
    reference_records = [{
        "reference_id": item["reference_id"],
        "name": item["name"],
        "purpose": "whole-slide visual precedent only",
        "content_reuse_allowed": False,
    } for item in visual_references]
    system_configuration = {
        "deck_design_config_id": deck["config_id"],
        "guidance_profile": guidance_profile["profile_id"],
        "density_profile": deck.get("density_profile", "high_consulting"),
        "generation_model": "GPT Image 2",
        "full_slide_px": canvas["full_slide_px"],
        "generation_canvas_px": canvas["generation_canvas_px"],
        "header_footer_geometry_px": [canvas["header_exclusion_px"], canvas["footer_exclusion_px"]],
        "title_system": deck["title"],
        "style_system": deck["style"],
        "long_term_configuration": True,
    }
    detail_package = {
        "schema_version": "1.0.0",
        "run_id": f"{slide['slide_id']}_generation",
        "system_configuration": system_configuration,
        "slide_request": slide,
        "intake_manifest": intake,
        "semantic_design": semantic_design,
        "resolved_chrome": chrome,
        "normalized_assets": assets,
        "visual_references": visual_references,
        "generation_canvas": canvas,
    }
    fingerprint = _fingerprint(detail_package)
    approval_mode = slide.get("approval_mode", preflight_config["default_approval_mode"])
    ready = not blocking
    auto_approved = ready and approval_mode in {"policy_auto_approval", "explicit_delegation"}
    status = "approved" if auto_approved else "blocked" if blocking else "awaiting_user_confirmation"
    preflight = {
        "schema_version": "1.0.0",
        "run_id": detail_package["run_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval": {
            "required": bool(preflight_config["require_approval_before_external_generation"]),
            "mode": approval_mode,
            "status": status,
            "fingerprint": fingerprint,
            "generation_released": auto_approved,
        },
        "system_configuration": system_configuration,
        "slides": [slide_record],
        "assets": asset_records,
        "visual_references": reference_records,
        "quality": {
            "ready_for_approval": ready,
            "blocking_issues": blocking,
            "warnings": [],
        },
        "detail_files": {
            "generation_package": str((output_dir / "generation_package.json").resolve()),
            "draft_image_prompt": str((output_dir / "imagegen_prompt.txt").resolve()),
        },
    }
    lines = [
        "# Generation preflight",
        "",
        f"Approval status: {status}",
        f"Run fingerprint: `{fingerprint}`",
        "",
        "## Slide summary",
        "",
        f"- Slide: {slide['slide_id']}",
        f"- Objective: {slide['objective']}",
        f"- Governing message: {semantic_design['main_message']}",
        f"- Title: {exact.get('title', '')}",
        f"- Subtitle: {exact.get('subtitle', '')}",
        f"- Route: {slide_record['route']}",
        f"- Generation model: {system_configuration['generation_model']}",
        f"- Density profile: {system_configuration['density_profile']}",
        "",
        "## Proposed header and footer",
        "",
        f"- Header left: {chrome['header']['left_text']['value']} ({chrome['header']['left_text']['source']})",
        f"- Header right: {chrome['header']['right_text']['value']} ({chrome['header']['right_text']['source']})",
        f"- Footer left: {chrome['footer']['left_text']['value']} ({chrome['footer']['left_text']['source']})",
        f"- Footer center: {chrome['footer']['center_text']['value']} ({chrome['footer']['center_text']['source']})",
        f"- Footer right: {chrome['footer']['right_text_format']['value']} ({chrome['footer']['right_text_format']['source']})",
        f"- Geometry: {canvas['header_exclusion_px']} px header and {canvas['footer_exclusion_px']} px footer from long-term deck design configuration",
        "",
        "## Assets",
        "",
    ]
    for item in asset_records:
        lines.append(f"- {item['name']} | {item['usage']} | {item['status']} | {item['semantic_role']}")
    lines.extend(["", "## Visual references", ""])
    for item in reference_records:
        lines.append(f"- {item['reference_id']} | {item['name']} | visual precedent only")
    lines.extend(["", "## Source and constraint checks", ""])
    lines.append(f"- Authoritative source atoms: {intake['quality']['authoritative_source_atom_count']}")
    lines.append(f"- Hard constraints: {intake['quality']['hard_constraint_count']}")
    for item in intake["constraint_register"]:
        if item["strength"] == "hard" and item["status"] == "active":
            lines.append(f"- {item['constraint_id']}: {item['text']}")
    lines.append(f"- Blocking issues: {len(blocking)}")
    lines.append(f"- Unresolved assumptions: {len(slide_record['unresolved_assumptions'])}")
    lines.extend(["", "## External generation disclosure", ""])
    lines.append("- Exact slide content, semantic design, asset descriptions, and visual reference images are prepared for the external image-generation request.")
    lines.append("- Canonical user-uploaded logo files remain internal for later reconstruction under the current description-only asset policy.")
    lines.append("- Cost estimate is unavailable until the selected image provider exposes a pricing adapter.")
    lines.extend(["", "## Approval effect", "", "Approval releases the current fingerprint for external image generation. Any material change to authoritative content, hard constraints, mandatory assets, title, chrome content, route, or deck design configuration invalidates the approval.", ""])
    return preflight, detail_package, "\n".join(lines)
