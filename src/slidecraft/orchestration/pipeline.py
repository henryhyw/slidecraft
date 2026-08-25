"""Generation orchestration and reconstruction handoff assembly."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from .asset_ingestion import apply_ingested_asset_manifest
from .guidance_profiles import resolve_guidance_profile
from .intake import normalize_intake
from .naming import migrate_deck_and_slide
from .preflight import build_generation_preflight
from .resource_selection import resolve_resource_selection
from .review_prompt import build_review_prompt
from .semantic_planning import resolve_semantic_design

DIMENSION_POLICIES = {
    "primary_stage_icon": {"height_fraction": 0.068, "max_width_fraction": 0.040},
    "branch_icon": {"height_fraction": 0.045, "max_width_fraction": 0.030},
    "module_icon": {"height_fraction": 0.052, "max_width_fraction": 0.034},
    "output_icon": {"height_fraction": 0.070, "max_width_fraction": 0.045},
    "technology_logo": {"height_fraction": 0.050, "max_width_fraction": 0.075},
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _resolve_from(base: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _packaged_default(name: str) -> Path:
    return Path(str(files("slidecraft.defaults").joinpath(name)))


def _resolve_policy_file(base: Path, value: str | None, default_name: str) -> Path:
    if not value or value.startswith("packaged:"):
        return _packaged_default(value.split(":", 1)[1] if value and ":" in value else default_name)
    candidate = _resolve_from(base, value)
    return candidate if candidate.is_file() else _packaged_default(default_name)


def _identity(path: Path, reference_id: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "reference_id": reference_id,
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(data).hexdigest(),
        "role": "fixed_visual_reference_page",
        "usage": "whole-page visual precedent only",
        "must_not_be_copied_as_layout": True,
    }


def resolve_exclusions(deck: dict[str, Any], adaptive_values: dict[str, int] | None = None) -> tuple[int, int, str]:
    """Resolve exclusions through a stable boundary that can accept adaptive values later."""
    resolution = deck.get("exclusion_resolution", {"mode": "configured"})
    mode = resolution["mode"]
    configured = deck.get("exclusions_px")
    if mode == "configured":
        if configured is None:
            raise ValueError("Configured exclusion mode requires exclusions_px")
        return int(configured["header"]), int(configured["footer"]), "configured"
    if mode == "adaptive":
        if adaptive_values is None:
            raise ValueError("Adaptive exclusion mode requires values from an exclusion-derivation adapter")
        return int(adaptive_values["header"]), int(adaptive_values["footer"]), "adaptive_adapter"
    if mode == "configured_with_adaptive_fallback":
        values = configured or adaptive_values
        if values is None:
            raise ValueError("No configured or adaptively derived exclusions are available")
        source = "configured" if configured else "adaptive_adapter"
        return int(values["header"]), int(values["footer"]), source
    raise ValueError(f"Unknown exclusion resolution mode: {mode}")


def derive_canvas(deck: dict[str, Any], adaptive_values: dict[str, int] | None = None) -> dict[str, Any]:
    full = deck["full_slide_px"]
    resolution = deck.get("exclusion_resolution", {"mode": "configured"})
    header, footer, resolved_from = resolve_exclusions(deck, adaptive_values)
    if header < 0 or footer < 0 or header + footer >= full[1]:
        raise ValueError("Invalid configured header or footer exclusion")
    return {
        "full_slide_px": full,
        "header_exclusion_px": header,
        "footer_exclusion_px": footer,
        "generation_region_px": [0, header, full[0], full[1] - header - footer],
        "generation_canvas_px": [full[0], full[1] - header - footer],
        "generation_offset_y_px": header,
        "title_is_inside_generation_canvas": True,
        "header_and_footer_are_generated": False,
        "derivation": "mechanical_from_deck_design_configuration",
        "exclusion_resolution": resolution,
        "exclusions_resolved_from": resolved_from,
    }


def _svg_intrinsic_size(path: Path) -> tuple[float, float] | None:
    text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
    view_box = re.search(r"viewBox=[\"']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)", text)
    if view_box:
        return float(view_box.group(1)), float(view_box.group(2))
    return None


def _intrinsic_size(asset: dict[str, Any]) -> tuple[float, float]:
    path_value = asset.get("canonical_file")
    if path_value:
        path = Path(path_value)
        if path.suffix.lower() == ".svg" and path.exists():
            size = _svg_intrinsic_size(path)
            if size:
                return size
        if path.exists():
            from PIL import Image
            with Image.open(path) as image:
                return float(image.width), float(image.height)
    ratio = float(asset.get("intrinsic_aspect_ratio", 1.0))
    return ratio, 1.0


def _calculate_dimensions(asset: dict[str, Any], canvas: dict[str, Any], slot_config: dict[str, Any]) -> dict[str, Any]:
    role = asset.get("dimension_role", "module_icon")
    policy = DIMENSION_POLICIES.get(role, DIMENSION_POLICIES["module_icon"])
    canvas_width, canvas_height = canvas["generation_canvas_px"]
    max_width = max(1, round(canvas_width * policy["max_width_fraction"]))
    max_height = max(1, round(canvas_height * policy["height_fraction"]))
    intrinsic_width, intrinsic_height = _intrinsic_size(asset)
    scale = min(max_width / intrinsic_width, max_height / intrinsic_height)
    width = max(1, round(intrinsic_width * scale))
    height = max(1, round(intrinsic_height * scale))
    inset_fraction = float(slot_config["default_inset_fraction"])
    inset_x = max(int(slot_config["minimum_inset_px"]), round(width * inset_fraction))
    inset_y = max(int(slot_config["minimum_inset_px"]), round(height * inset_fraction))
    slot_width = width + 2 * inset_x
    slot_height = height + 2 * inset_y
    return {
        "dimension_role": role,
        "target_visual_footprint_px": [width, height],
        "containing_box_px": [slot_width, slot_height],
        "icon_slot": {
            "size_px": [slot_width, slot_height],
            "center_alignment": slot_config["alignment"],
            "inset_px": {"left": inset_x, "top": inset_y, "right": inset_x, "bottom": inset_y},
            "maximum_glyph_area_px": [width, height],
            "fit": slot_config["fit"],
            "allow_stretch": slot_config["allow_stretch"],
            "authoritative_for_placement": True,
            "generated_glyph_authoritative": False,
            "minimum_external_clearance_px": slot_config["minimum_external_clearance_px"],
            "generation_rendering": slot_config["generation_rendering"],
            "reconstruction_rendering": slot_config["reconstruction_rendering"],
        },
        "intrinsic_aspect_ratio": round(intrinsic_width / intrinsic_height, 5),
        "preserve_aspect_ratio": True,
        "prompt_tolerance_percent": slot_config["generation_tolerance_percent"],
        "calculation": {
            "generation_canvas_px": canvas["generation_canvas_px"],
            "maximum_glyph_height_fraction": policy["height_fraction"],
            "maximum_glyph_width_fraction": policy["max_width_fraction"],
            "intrinsic_aspect_ratio_applied_before_slot_padding": True,
            "slot_derivation": "proportionally fitted canonical glyph size plus configured four-side inset",
            "fit": slot_config["fit"],
            "sizing_subject": "authoritative_icon_slot",
        },
    }


def normalized_assets(icon_package: dict[str, Any], user_assets: list[dict[str, Any]], canvas: dict[str, Any], deck: dict[str, Any]) -> dict[str, Any]:
    slot_config = deck["icon_slots"]
    user_policy = deck["user_asset_policy"]
    exact_user_roles = {
        asset["semantic_role"]
        for asset in user_assets
        if asset.get("canonical_file") and asset.get("semantic_role")
    }
    assets = []
    for index, asset in enumerate(icon_package["assets"], start=1):
        if asset.get("semantic_role") in exact_user_roles:
            continue
        record = {
            "prompt_id": f"ASSET_{len(assets) + 1:02d}",
            "name": asset["prompt_name"],
            "description": asset["prompt_description"],
            "required_usage": bool(asset.get("required_usage", False)),
            "internal": asset,
        }
        record["internal"]["source_kind"] = "library_icon"
        record["internal"]["placement"] = "icon_slot"
        record["internal"]["attach_to_generation"] = False
        record["dimensions"] = _calculate_dimensions(asset, canvas, slot_config)
        assets.append(record)
    for user_asset in user_assets:
        canonical_file = user_asset.get("canonical_file")
        internal = {
            "asset_id": user_asset["asset_id"],
            "semantic_role": user_asset["semantic_role"],
            "dimension_role": user_asset.get("dimension_role", "technology_logo"),
            "source_kind": "project_visual",
            "visual_kind": user_asset.get("visual_kind", "other"),
            "media_type": user_asset.get("media_type"),
            "placement": user_asset.get("placement", "image_region"),
            "selection_mode": "exact_upstream_asset",
            "provenance": "user_provided",
            "canonical_file": str(Path(canonical_file).resolve()) if canonical_file else None,
            "attachment_status": user_asset.get("attachment_status", "available"),
            "intrinsic_aspect_ratio": user_asset.get("intrinsic_aspect_ratio", 1.0),
            "image_input_label": user_asset.get("image_input_label"),
            "generation_attachment_mode": user_asset.get("generation_attachment_mode", user_policy["generation_attachment_mode"]),
            "mandatory": bool(
                user_asset.get("mandatory", user_asset["asset_id"] in user_policy.get("mandatory_asset_ids", []))
            ),
            "attach_to_generation": bool(canonical_file),
            "preserve_exact_content": bool(user_asset.get("preserve_exact_content", True)),
            "preserve_aspect_ratio": bool(user_asset.get("preserve_aspect_ratio", True)),
            "sha256": user_asset.get("sha256"),
        }
        record = {
            "prompt_id": f"ASSET_{len(assets) + 1:02d}",
            "name": user_asset["name"],
            "description": user_asset["description"],
            "required_usage": user_asset.get("required_usage", False),
            "internal": internal,
        }
        if internal["placement"] == "icon_slot":
            record["dimensions"] = _calculate_dimensions(internal, canvas, slot_config)
            internal["intrinsic_aspect_ratio"] = record["dimensions"]["intrinsic_aspect_ratio"]
        else:
            intrinsic_width, intrinsic_height = _intrinsic_size(internal)
            internal["intrinsic_aspect_ratio"] = round(intrinsic_width / intrinsic_height, 6)
            record["dimensions"] = {
                "intrinsic_size": [intrinsic_width, intrinsic_height],
                "intrinsic_aspect_ratio": internal["intrinsic_aspect_ratio"],
                "preserve_aspect_ratio": True,
                "fit": "contain",
                "sizing_subject": "exact_project_image",
            }
        assets.append(record)
    return {
        "schema_version": "1.1.0",
        "asset_prompt_mode": user_policy["generation_attachment_mode"],
        "icon_slot_policy": slot_config,
        "assets": assets,
    }


def validate_connector_configuration(deck: dict[str, Any]) -> dict[str, Any]:
    config = deck["connectors"]
    stroke_width = float(config["stroke"]["width_px"])
    arrow_length = float(config["arrowhead"]["length_px"])
    ratio = arrow_length / stroke_width
    low, high = config["qa"]["arrowhead_length_to_stroke_ratio"]
    checks = {
        "arrowhead_to_stroke_ratio": {"value": round(ratio, 3), "range": [low, high], "passed": low <= ratio <= high},
        "clear_segment_for_arrowhead": {
            "value_px": config["arrowhead"]["minimum_clear_segment_px"],
            "required_minimum_px": arrow_length * 1.5,
            "passed": config["arrowhead"]["minimum_clear_segment_px"] >= arrow_length * 1.5,
        },
        "branch_route_is_configured": {
            "value": config["branch_route"],
            "passed": config["branch_route"] in {"straight_shared_junction", "elbow_shared_junction", "curved_shared_junction"},
        },
        "endpoint_is_visibly_sized": {
            "value_px": config["arrowhead"]["width_px"],
            "required_minimum_px": config["arrowhead"]["minimum_visible_endpoint_px"],
            "passed": config["arrowhead"]["width_px"] >= config["arrowhead"]["minimum_visible_endpoint_px"],
        },
        "native_connector_only_policy": {
            "value": config["qa"]["native_connector_objects_only"],
            "passed": bool(config["qa"]["native_connector_objects_only"] and config["qa"]["forbid_separate_arrowhead_shapes"]),
        },
    }
    if not all(check["passed"] for check in checks.values()):
        raise ValueError(f"Connector configuration failed QA: {checks}")
    return {"style_id": config["style_id"], "checks": checks, "status": "passed"}


def _render_exact_content(slide: dict[str, Any]) -> str:
    return json.dumps(slide["exact_content"], indent=2, ensure_ascii=False)


def assemble_prompt(
    deck: dict[str, Any],
    canvas: dict[str, Any],
    slide: dict[str, Any],
    intake: dict[str, Any],
    plan: dict[str, Any],
    guidance_profile: dict[str, Any],
    assets: dict[str, Any],
    references: list[dict[str, Any]],
) -> str:
    title = deck["title"]
    style = deck["style"]
    icon_lines = []
    project_visual_lines = []
    attached_project_visuals = [
        asset for asset in assets["assets"] if asset.get("internal", {}).get("attach_to_generation")
    ]
    attached_index = {
        asset["internal"]["asset_id"]: len(references) + index
        for index, asset in enumerate(attached_project_visuals, start=1)
    }
    for asset in assets["assets"]:
        dimensions = asset["dimensions"]
        internal = asset["internal"]
        requirement = "mandatory on this slide" if asset.get("required_usage") else "optional on this slide"
        if internal.get("source_kind") == "project_visual":
            ratio = dimensions["intrinsic_aspect_ratio"]
            lines = [
                asset["prompt_id"],
                f"Name: {asset['name']}",
                f"Purpose: {asset['description']}",
                f"Attached image input: {attached_index[internal['asset_id']]}",
                f"Usage: {requirement}.",
                f"Placement treatment: {internal['placement']}.",
                f"Intrinsic aspect ratio: {ratio}:1.",
                "Content protection: preserve the supplied image exactly. Do not redraw, restyle, recolor, retouch, alter text, replace details, or generate a lookalike.",
                "Geometry protection: scale uniformly and preserve the supplied aspect ratio. Do not stretch, skew, or rotate it. Do not crop it unless an explicit human constraint requests cropping.",
            ]
            if internal["placement"] == "icon_slot":
                width, height = dimensions["target_visual_footprint_px"]
                slot_width, slot_height = dimensions["icon_slot"]["size_px"]
                inset = dimensions["icon_slot"]["inset_px"]
                lines.extend([
                    f"Authoritative icon slot: {slot_width} × {slot_height} px, with up to ±{dimensions['prompt_tolerance_percent']}% dimensional tolerance.",
                    f"Required internal inset: {inset['left']} px left, {inset['top']} px top, {inset['right']} px right, and {inset['bottom']} px bottom.",
                    f"Maximum visible asset footprint: {width} × {height} px after proportional contain fitting and centering.",
                ])
            else:
                lines.append("The body composition may choose the image region's location and scale. Keep the full image visible and use its boundary as the placement region.")
            project_visual_lines.extend([*lines, ""])
            continue
        width, height = dimensions["target_visual_footprint_px"]
        slot_width, slot_height = dimensions["icon_slot"]["size_px"]
        inset = dimensions["icon_slot"]["inset_px"]
        icon_lines.extend([
            asset["prompt_id"],
            f"Name: {asset['name']}",
            f"Description: {asset['description']}",
            f"Usage: {requirement}.",
            f"Authoritative icon slot: {slot_width} × {slot_height} px, with up to ±{dimensions['prompt_tolerance_percent']}% dimensional tolerance.",
            f"Required internal inset: {inset['left']} px left, {inset['top']} px top, {inset['right']} px right, and {inset['bottom']} px bottom.",
            f"Maximum visible glyph footprint after proportional contain fitting: {width} × {height} px.",
            "Center the icon in its slot. Scale it uniformly until it is as large as possible inside the inset area. Never stretch, crop, rotate, or let it overflow.",
            "The slot controls position, clearance, and spacing. The generated glyph is semantic evidence for later canonical icon restoration.",
            "",
        ])
    reference_lines = [f"- {item['reference_id']}: use as a whole-page visual precedent only" for item in references]
    hard_constraints = [item for item in intake["constraint_register"] if item["strength"] == "hard" and item["status"] == "active"]
    relationships = plan.get("semantic_relationships", plan.get("relationships", []))
    hierarchy = plan.get("hierarchy", {})
    required_assets = [
        asset
        for asset in assets["assets"]
        if asset.get("required_usage") and asset.get("internal", {}).get("source_kind") == "project_visual"
    ]
    required_asset_names = [asset["name"] for asset in required_assets]
    profile_name = guidance_profile.get("name", guidance_profile["profile_id"])
    return f"""Create one polished consulting presentation slide image for the generation canvas only.

GENERATION TASK AND CANVAS
Generate a {canvas['generation_canvas_px'][0]} × {canvas['generation_canvas_px'][1]} pixel image. This image represents the configured title and main-content region of a {canvas['full_slide_px'][0]} × {canvas['full_slide_px'][1]} slide. The header exclusion is {canvas['header_exclusion_px']} px and the footer exclusion is {canvas['footer_exclusion_px']} px. Do not draw any header, footer, page number, footer rule, or content outside this generation canvas. The orchestration layer will place this image at y = {canvas['generation_offset_y_px']} px on the full slide.

CONFIGURED TITLE RULES
The title is inside this generation canvas. Use the exact title below. Anchor it near x = {title['anchor_px'][0]} px and y = {title['anchor_px'][1]} px. Its maximum width is {title['max_width_px']} px. Use {title['font_family']}, {title['weight']}, approximately {title['nominal_size_px']} px, color {title['color']}, aligned {title['alignment']}. Allow {title['allowed_lines'][0]} or {title['allowed_lines'][1]} lines. If the title wraps to two lines, let it use the required vertical space. Begin the main composition below the rendered title with at least {title['minimum_gap_to_body_px']} px of clear separation.

SEMANTIC DESIGN INTENT
Main message: {plan['main_message']}
Reading logic: {plan['reading_logic']}
Relationships to communicate: {json.dumps(relationships, ensure_ascii=False)}
Hierarchy: {json.dumps(hierarchy, ensure_ascii=False)}
Visual intent: {plan['visual_intent']['structure']} {plan['visual_intent']['emphasis']}

SELECTED COMMUNICATION GUIDANCE
Profile: {profile_name} ({guidance_profile['profile_id']}) version {guidance_profile['version']}
Slide reasoning principles: {json.dumps(guidance_profile['slide_reasoning']['principles'], ensure_ascii=False)}
Visual communication principles: {json.dumps(guidance_profile['visual_communication']['principles'], ensure_ascii=False)}
Writing principles: {json.dumps(guidance_profile['writing']['principles'], ensure_ascii=False)}
Design freedom: {json.dumps(guidance_profile['design_freedom'], ensure_ascii=False)}

VISUAL OBLIGATIONS
The visual composition must make these semantic facts recoverable without prescribing a specific layout.
{json.dumps(plan.get('visual_obligations', []), indent=2, ensure_ascii=False)}

ACTIVE HARD HUMAN CONSTRAINTS
The following constraints are mandatory. Preserve their IDs for review traceability.
{json.dumps(hard_constraints, indent=2, ensure_ascii=False)}

EXACT AUTHORITATIVE SLIDE CONTENT
Use the wording below as the content source. Do not paraphrase, omit, or invent content.

{_render_exact_content(slide)}

AVAILABLE ICON ROLES AND AUTHORITATIVE SLOT DIMENSIONS
The following icon roles are available as semantic visual ingredients. Mandatory roles must appear. Optional roles may be omitted when the design does not need them. Keep every used role recognizable.

For every used icon role, create a clear rectangular icon slot at exactly the stated dimensions within the allowed tolerance. Use a subtle pale neutral or warm-tint design container, without dashed guides or measurement annotations. Keep external spacing relative to the slot boundary. The generated glyph does not define placement geometry.

These dimensions are calculated by the orchestration layer from the generation canvas, the icon's semantic size role, the canonical asset's intrinsic aspect ratio, and the configured inset. They are design constraints, not arbitrary suggestions. Do not independently resize the slots.

{chr(10).join(icon_lines).rstrip() or "No library icon roles were selected for this slide."}

ATTACHED PROJECT VISUALS
The project visuals below are supplied as ordered image inputs after the visual-reference pages. Mandatory visuals must appear. Optional visuals may be omitted when they do not strengthen the composition. If an optional visual is used, all content and geometry protection rules still apply.

{chr(10).join(project_visual_lines).rstrip() or "No project visuals were allocated to this slide."}

VISUAL REFERENCE GUIDANCE
The attached reference images are visual precedents selected for this slide.
{chr(10).join(reference_lines)}
Learn from their visual language, information density, whitespace, alignment, hierarchy, diagram language, and component polish. Do not copy their content or page layout.

MANDATORY PROJECT VISUALS
The mandatory project visuals for this slide are {json.dumps(required_asset_names, ensure_ascii=False)}. Use their attached source images directly and follow their individual placement treatment. Exact canonical files are retained for editable PowerPoint reconstruction.

CONFIGURED STYLE SYSTEM
Use a {style['background']} background. Use {style['display_font']} for display typography and {style['body_font']} for body typography. Use black or near-black text with a restrained orange accent family led by {style['accent_colors'][0]}, {style['accent_colors'][1]}, and {style['accent_colors'][2]}. Use {style['density']} information density. Maintain {style['whitespace']} whitespace. Render icons with {style['icon_treatment']}. Follow these diagram conventions: {style['diagram_conventions']}.

Apply the selected deck design configuration as a flexible visual language without copying a fixed layout. The configured style object is authoritative: {json.dumps(style, ensure_ascii=False)}

CONNECTOR SYSTEM
Use {deck['connectors']['default_route']} connectors for ordinary one-to-one relationships when practical. Use a clean {deck['connectors']['branch_route']} structure for branch and merge relationships. Use stroke color {deck['connectors']['stroke']['color']} at approximately {deck['connectors']['stroke']['width_px']} px, with {deck['connectors']['arrowhead']['type']} arrowheads approximately {deck['connectors']['arrowhead']['length_px']} × {deck['connectors']['arrowhead']['width_px']} px. Keep at least {deck['connectors']['routing']['minimum_clearance_px']} px clearance from text and peer components. Keep arrowheads clearly visible, attach endpoints cleanly, normalize peer routing, and avoid unnecessary bends or crossings.

Before drawing any connector, decide the conceptual source, conceptual target, direction, and whether the relationship is one-to-one, branch, merge, or many-to-many through a shared junction. Connect to the boundary of the conceptual owner. Do not attach a stage-level output to only one child module. Keep logical junctions separate from visible nodes. Show a junction dot only when the node itself is meaningful. Use straight horizontal or vertical routes for peer stages. Use a clean shared bus for multi-edge graphs when curves would cross or become ambiguous. Avoid decorative arrows, raster-like fragments, tiny arrowheads, diagonal peer flows, redundant terminal bends, and lines that disappear under containers.

DESIGN RESPONSIBILITY
You own the genuine visual design decisions for the body, including spatial organization, grouping, relative scale, component design, connector representation, asset adaptation, whitespace, and detailed composition. Follow the semantic structure while keeping the layout open. Create a coherent designed system instead of a collection of unrelated objects.

OUTPUT QUALITY
Produce a professional, presentation-ready consulting slide region with strong hierarchy, crisp typography, clear relationships, consistent spacing, self-evident connectors, and no decorative clutter. All required text must be legible. Avoid generic SaaS-dashboard styling. Avoid unnecessary legends. Return only the slide-region image.
"""


def _generation_image_inputs(
    references: list[dict[str, Any]], assets: dict[str, Any]
) -> list[dict[str, Any]]:
    inputs = [
        {
            "input_index": index,
            "input_role": "visual_reference",
            "reference_id": item["reference_id"],
            "path": item["path"],
            "preserve_exact_content": False,
        }
        for index, item in enumerate(references, start=1)
    ]
    for asset in assets["assets"]:
        internal = asset.get("internal", {})
        path = internal.get("canonical_file")
        if not internal.get("attach_to_generation") or not path:
            continue
        inputs.append({
            "input_index": len(inputs) + 1,
            "input_role": "project_visual",
            "asset_id": internal["asset_id"],
            "name": asset["name"],
            "path": path,
            "media_type": internal.get("media_type"),
            "placement": internal.get("placement"),
            "usage": "mandatory" if asset.get("required_usage") else "optional",
            "intrinsic_aspect_ratio": internal.get("intrinsic_aspect_ratio"),
            "preserve_exact_content": True,
            "preserve_aspect_ratio": True,
        })
    return inputs


def review_contract(slide: dict[str, Any]) -> dict[str, Any]:
    exact_strings: list[str] = []
    def collect(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            exact_strings.append(value)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
    collect(slide["exact_content"])
    return {
        "review_input": ["generated_candidate", "semantic_design", "exact_content", "visual_references", "style_configuration"],
        "material_failure_categories": ["communication_clarity", "hierarchy", "relationship_clarity", "content_fidelity", "visual_reference_fidelity", "legibility", "visual_quality"],
        "review_policy": "Flag material failures only. If editing is required, return a strict JSON delta containing only concrete local corrections.",
        "reviewer_owns": ["diagnosis", "materiality decision", "smallest effective correction", "edit delta"],
        "orchestrator_owns": ["edit command", "canvas invariants", "title invariants", "authoritative content", "semantic invariants", "style invariants", "asset invariants", "attachment selection"],
        "reviewer_must_not_repeat_configuration": True,
        "exact_text_to_verify": list(dict.fromkeys(exact_strings)),
    }


def _apply_user_defaults(deck: dict[str, Any], config_root: Path) -> dict[str, Any]:
    from slidecraft.configuration import data_root, initialize_user_environment, resolve_config

    initialize_user_environment(force=False)
    application, _ = resolve_config()
    preferences = application.get("design", {})
    profile_id = preferences.get("guidance_profile")
    if profile_id:
        inheritance_root = _resolve_from(config_root, deck["guidance_profile"]["inheritance_root"])
        profile_path = inheritance_root / f"{profile_id}.json"
        if profile_path.exists():
            deck["guidance_profile"].update(profile_id=profile_id, path=str(profile_path))
    density = preferences.get("density_profile")
    if density:
        deck["density_profile"] = density
        deck["style"]["density"] = {
            "low": "spacious information density with generous separation between ideas",
            "medium": "balanced information density with concise supporting evidence",
            "high_consulting": "information-rich consulting-slide density with clear hierarchy",
        }.get(density, density)
    display_font = preferences.get("display_font")
    body_font = preferences.get("body_font")
    if display_font:
        deck["style"]["display_font"] = display_font
        deck["title"]["font_family"] = display_font
    if body_font:
        deck["style"]["body_font"] = body_font
    accent_colors = [
        preferences.get("primary_color"),
        preferences.get("secondary_color"),
        preferences.get("highlight_color"),
    ]
    if all(accent_colors):
        deck["style"]["accent_colors"] = accent_colors
    text_color = preferences.get("text_color")
    surface_color = preferences.get("surface_color")
    if text_color:
        deck["title"]["color"] = text_color
        neutrals = deck["style"].get("neutral_colors", [])
        deck["style"]["neutral_colors"] = [text_color, *[color for color in neutrals if color != text_color]]
    if surface_color:
        deck["style"]["surface_color"] = surface_color
    icon_style = preferences.get("icon_style")
    if icon_style:
        deck["style"]["icon_treatment"] = {
            "tabler_warm_slot": "Tabler outline pictograms, proportionally contained and centered on a pale warm-tint rectangular slot with consistent padding",
            "tabler_plain": "Plain Tabler outline pictograms, proportionally contained with no decorative slot surface",
            "custom": "Use the configured canonical icon collection, preserve aspect ratio, and follow its recorded style metadata",
        }.get(icon_style, icon_style)
    libraries = application.get("libraries", {})
    library_root = data_root()

    def resolve_library(value: str) -> str:
        path = Path(value).expanduser()
        return str(path.resolve() if path.is_absolute() else (library_root / path).resolve())

    deck["local_libraries"].update({
        "visual_reference_manifest": resolve_library(libraries["visual_references"]),
        "icon_root": resolve_library(libraries["icons"]),
        "known_component_root": resolve_library(libraries["components"]),
    })
    deck.setdefault("resource_policy", {})["icons"] = application.get("resources", {}).get("icons", {
        "allow_online_retrieval": True,
        "provider": "tabler",
        "release": "latest",
        "max_online_candidates_per_role": 8,
    })
    return deck


def run_pipeline(
    config_path: Path,
    slide_path: Path,
    output_dir: Path,
    *,
    overrides: list[str] | None = None,
    resource_candidates: dict[str, Any],
    resource_selection: dict[str, Any],
) -> dict[str, Any]:
    config_path = config_path.resolve()
    slide_path = slide_path.resolve()
    config_root = config_path.parent
    deck = _read_json(config_path)
    deck = _apply_user_defaults(deck, config_root)
    if overrides:
        from slidecraft.configuration import apply_dotted_overrides

        deck = apply_dotted_overrides(deck, overrides)
    slide = _read_json(slide_path)
    deck, slide, naming_migration_notices = migrate_deck_and_slide(deck, slide)
    slide, asset_ingestion_notices = apply_ingested_asset_manifest(slide, slide_path.parent)
    configured_contract = deck.get("pipeline_contract")
    if configured_contract and configured_contract != "pipeline_v1.json":
        pipeline_contract_path = _resolve_from(config_root, configured_contract)
    else:
        pipeline_contract_path = Path(str(files("slidecraft.defaults").joinpath("framework_pipeline.json")))
        if configured_contract == "pipeline_v1.json":
            naming_migration_notices.append("Loaded the packaged framework pipeline for the legacy pipeline_v1.json setting.")
    pipeline_contract = _read_json(pipeline_contract_path)
    guidance_config = deck["guidance_profile"]
    guidance_root = Path(str(files("slidecraft").joinpath("guidance_profiles")))
    guidance_path_value = str(guidance_config.get("path", ""))
    if guidance_path_value.startswith("packaged:"):
        guidance_path = guidance_root / f"{guidance_config['profile_id']}.json"
        inheritance_root = guidance_root
    else:
        guidance_path = _resolve_from(config_root, guidance_path_value)
        inheritance_root = _resolve_from(config_root, guidance_config.get("inheritance_root", guidance_root))
        if not guidance_path.is_file():
            guidance_path = guidance_root / f"{guidance_config['profile_id']}.json"
            inheritance_root = guidance_root
    guidance_profile = resolve_guidance_profile(guidance_path, inheritance_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = derive_canvas(deck)
    intake = normalize_intake(slide, slide_path.parent)
    plan = resolve_semantic_design(slide, slide_path.parent)
    if plan["guidance_profile_id"] != guidance_profile["profile_id"]:
        raise ValueError("Semantic design guidance profile does not match the selected deck guidance profile")
    if resource_candidates.get("decision_owner") != "host_agent":
        raise ValueError("Resource candidates must come from the Agent-invoked search_resources operation")
    visual_reference_package = resource_candidates.get("visual_references", {})
    icon_package = resource_candidates.get("icons", {})
    component_package = resource_candidates.get("components", {})
    library_config = deck["local_libraries"]
    selected_resources = resolve_resource_selection(
        resource_selection,
        visual_search=visual_reference_package,
        icon_search=icon_package,
        component_search=component_package,
        maximum_visual_references=int(library_config["visual_reference_max_results_per_slide"]),
    )
    references = selected_resources["visual_references"]
    icon_selection = {"assets": selected_resources["icons"]}
    assets = normalized_assets(icon_selection, slide.get("user_provided_assets", []), canvas, deck)
    connector_qa = validate_connector_configuration(deck)
    prompt = assemble_prompt(deck, canvas, slide, intake, plan, guidance_profile, assets, references)
    generation_image_inputs = _generation_image_inputs(references, assets)
    preflight_config_path = _resolve_policy_file(config_root, deck.get("preflight_config"), "preflight_config.json")
    preflight_config = _read_json(preflight_config_path)
    preflight, generation_package, preflight_markdown = build_generation_preflight(
        deck,
        slide,
        intake,
        plan,
        guidance_profile,
        canvas,
        assets,
        references,
        preflight_config,
        output_dir,
    )
    generation_package["image_inputs"] = generation_image_inputs
    review = review_contract(slide)
    review_config_path = _resolve_policy_file(config_root, deck.get("generation_review_config"), "generation_review_config.json")
    review_config = _read_json(review_config_path)
    configured_review_prompt, review_manifest = build_review_prompt(
        {
            "derived_canvas": canvas,
            "deck_design_configuration": deck,
            "intake_manifest": intake,
            "guidance_profile": guidance_profile,
            "semantic_design": plan,
            "slide_input": slide,
            "normalized_available_assets": assets,
            "reference_retrieval": {"visual_references": references},
        },
        review_config,
        None,
    )
    generation_context = {
        "schema_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "naming_migration_notices": naming_migration_notices,
        "asset_ingestion_notices": asset_ingestion_notices,
        "pipeline": ["semantic_planning", "resource_retrieval", "prompt_assembly", "generation_preflight", "external_image_generation", "generation_review", "slide_understanding", "editable_reconstruction"],
        "pipeline_contract": pipeline_contract,
        "pipeline_contract_path": str(pipeline_contract_path),
        "deck_design_configuration": deck,
        "runtime_design_overrides": overrides or [],
        "guidance_profile": guidance_profile,
        "derived_canvas": canvas,
        "intake_manifest": intake,
        "slide_input": slide,
        "semantic_design": plan,
        "reference_retrieval": {
            "visual_references": references,
            "agent_resource_selection": selected_resources,
            "visual_reference_search": visual_reference_package,
            "icon_search": icon_package,
            "known_component_search": component_package,
            "style_rules_source": "deck_design_configuration"
        },
        "normalized_available_assets": assets,
        "generation_preflight": preflight,
        "connector_configuration": deck["connectors"],
        "connector_configuration_qa": connector_qa,
        "generation": {
            "model": "GPT Image 2",
            "execution": "external_user_action" if preflight["approval"]["generation_released"] else "blocked_until_preflight_approval",
            "prompt_status": "released" if preflight["approval"]["generation_released"] else "draft_pending_approval",
            "prompt_file": str((output_dir / "imagegen_prompt.txt").resolve()),
            "preflight_file": str((output_dir / "generation_preflight.json").resolve()),
            "reference_image_paths": [item["path"] for item in references],
            "attached_asset_paths": [
                item["path"] for item in generation_image_inputs if item["input_role"] == "project_visual"
            ],
            "image_inputs": generation_image_inputs,
            "asset_prompt_mode": deck["user_asset_policy"]["generation_attachment_mode"],
            "expected_output_scope": "generation_region",
            "target_image": None,
        },
        "generation_review": review,
        "generation_review_configuration": {
            "config_path": str(review_config_path),
            "prompt_file": str((output_dir / "review" / "configured_review_prompt.txt").resolve()),
            "input_manifest": str((output_dir / "review" / "review_input_manifest.json").resolve()),
        },
    }
    handoff = {
        "schema_version": "1.0.0",
        "handoff_type": "generation_to_reconstruction",
        "pipeline_contract": pipeline_contract,
        "pipeline_contract_path": str(pipeline_contract_path),
        "target_image": {"path": None, "status": "generation_blocked_pending_approval" if not preflight["approval"]["generation_released"] else "awaiting_user_generated_image", "scope": "generation_region"},
        "generation_authorization": preflight["approval"],
        "full_slide_dimensions_px": canvas["full_slide_px"],
        "header_footer_exclusions_px": {"header": canvas["header_exclusion_px"], "footer": canvas["footer_exclusion_px"]},
        "deck_chrome_configuration": deck.get("deck_chrome", {}),
        "resolved_chrome_content": preflight["slides"][0]["chrome"],
        "guidance_profile": guidance_profile,
        "generation_region": {"offset_y_px": canvas["generation_offset_y_px"], "dimensions_px": canvas["generation_canvas_px"]},
        "exact_title_text": slide["exact_content"]["title"],
        "title_configuration": deck["title"],
        "exact_source_content": slide["exact_content"],
        "intake_manifest": intake,
        "semantic_design": plan,
        "selected_assets": assets["assets"],
        "icon_slot_configuration": deck["icon_slots"],
        "user_asset_policy": deck["user_asset_policy"],
        "connector_configuration": deck["connectors"],
        "connector_configuration_qa": connector_qa,
        "style_configuration": deck["style"],
        "visual_references": references,
        "resource_selection": selected_resources,
        "visual_reference_search": visual_reference_package,
        "known_component_candidates": component_package,
        "slide_understanding_guidance": {
            "text": "Map rendered text regions to exact_source_content. OCR remains evidence only.",
            "source_traceability": "Every reconstructed content-bearing object must cite intake_manifest source atoms or an explicitly generated visual role.",
            "icons": "Detect each authoritative rectangular icon slot separately from its generated glyph. Map the glyph to selected_assets as semantic evidence. Store slot box, center, padding, nearby relationships, and semantic intent. Discard generated glyph geometry for reconstruction.",
            "icon_placement": "Editable reconstruction must proportionally contain-fit and center the canonical SVG inside the measured icon slot. Never stretch or use the generated glyph bounding box as the placement contract.",
            "project_images": "For every detected image, the Agent decides whether it maps to one of the selected project visuals. Exact matches restore the canonical project file with proportional contain fitting. Other image content uses the measured screenshot crop.",
            "connectors": "Independently audit conceptual source ownership, target ownership, direction, topology, route feasibility, junction visibility, and attachment sides against semantic groups, sibling participation, reading logic, exact source content, and upstream intent. Treat generated connector pixels as evidence. Measure approximate corridor and style, then reconstruct the audited native connector graph.",
            "coordinates": "Measure in generation-region pixels and retain generation_region.offset_y_px for full-slide reconstruction.",
            "deck_chrome": "Do not infer or reconstruct header and footer from the generated image. Editable reconstruction combines deck_chrome_configuration geometry and styling with resolved_chrome_content outside the generation region.",
        },
    }
    _write_json(output_dir / "semantic_design.json", plan)
    _write_json(output_dir / "intake_manifest.json", intake)
    _write_json(output_dir / "reference_retrieval.json", generation_context["reference_retrieval"])
    _write_json(output_dir / "normalized_assets.json", assets)
    _write_json(output_dir / "generation_preflight.json", preflight)
    _write_json(output_dir / "generation_package.json", generation_package)
    _write_json(output_dir / "connector_configuration_qa.json", connector_qa)
    _write_json(output_dir / "generation_review_contract.json", review)
    _write_json(output_dir / "generation_context.json", generation_context)
    _write_json(output_dir / "reconstruction_handoff.json", handoff)
    (output_dir / "imagegen_prompt.txt").write_text(prompt, encoding="utf-8")
    (output_dir / "generation_preflight.md").write_text(preflight_markdown, encoding="utf-8")
    review_dir = output_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "configured_review_prompt.txt").write_text(configured_review_prompt, encoding="utf-8")
    _write_json(review_dir / "review_input_manifest.json", review_manifest)
    report = f"""# Generation orchestration report

## Result

- Semantic planning is stored separately from exact authoritative content.
- {len(references)} Agent-selected visual reference pages are retained as identified visual precedents.
- {len(assets['assets'])} selected icons and project visuals are preserved with provenance, intrinsic aspect ratios, and slide-specific usage decisions.
- Every selected project visual is attached to the generation request. Mandatory visuals must appear, while optional visuals remain available to the image model.
- Connector style configuration passed automatic ratio and clarity checks.
- Image generation follows the recorded preflight approval mode for this run.
- Slide understanding receives the saved upstream package in addition to the generated pixels.

## Configured canvas

- Full slide is {canvas['full_slide_px'][0]} × {canvas['full_slide_px'][1]} px.
- Header exclusion is {canvas['header_exclusion_px']} px.
- Footer exclusion is {canvas['footer_exclusion_px']} px.
- Generation canvas is {canvas['generation_canvas_px'][0]} × {canvas['generation_canvas_px'][1]} px at y = {canvas['generation_offset_y_px']} px.
- The title is inside the generation canvas.

## Next action

Use `generation_preflight.md` and `generation_package.json` according to the user's requested review level. Generate from `imagegen_prompt.txt` with the ordered image inputs in `generation_context.json`. After generation, register the saved image and continue with Agent-authored slide understanding.
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    return {
        "output_dir": str(output_dir.resolve()),
        "prompt": str((output_dir / "imagegen_prompt.txt").resolve()),
        "handoff": str((output_dir / "reconstruction_handoff.json").resolve()),
        "reference_count": len(references),
        "asset_count": len(assets["assets"]),
        "generation_canvas_px": canvas["generation_canvas_px"],
        "preflight": str((output_dir / "generation_preflight.md").resolve()),
        "approval_status": preflight["approval"]["status"],
    }
