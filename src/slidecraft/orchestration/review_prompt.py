"""Configuration-driven generation review prompt assembly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _asset_review_records(assets: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for asset in assets["assets"]:
        width, height = asset["dimensions"]["target_visual_footprint_px"]
        slot = asset["dimensions"]["icon_slot"]
        tolerance = asset["dimensions"]["prompt_tolerance_percent"] / 100
        slot_width, slot_height = slot["size_px"]
        records.append({
            "prompt_id": asset["prompt_id"],
            "name": asset["name"],
            "semantic_role": asset["internal"].get("semantic_role"),
            "description": asset["description"],
            "required": bool(asset.get("required_usage", False)),
            "target_visual_footprint_px": [width, height],
            "authoritative_icon_slot_px": [slot_width, slot_height],
            "acceptable_slot_range_px": {
                "width": [round(slot_width * (1 - tolerance)), round(slot_width * (1 + tolerance))],
                "height": [round(slot_height * (1 - tolerance)), round(slot_height * (1 + tolerance))],
            },
            "slot_inset_px": slot["inset_px"],
            "fit": slot["fit"],
            "center_alignment": slot["center_alignment"],
            "generated_glyph_authoritative": False,
            "preserve_aspect_ratio": asset["dimensions"]["preserve_aspect_ratio"],
            "canonical_file": asset["internal"].get("canonical_file"),
            "provenance": asset["internal"].get("provenance", asset["internal"].get("library")),
        })
    return records


def build_review_input_manifest(state: dict[str, Any], generated_image: str | None) -> dict[str, Any]:
    references = state["reference_retrieval"]["visual_references"]
    candidate = {
        "path": str(Path(generated_image).resolve()) if generated_image else None,
        "role": "review target and later edit target",
        "status": "available" if generated_image else "attach_at_review_time",
        "expected_dimensions_px": state["derived_canvas"]["generation_canvas_px"],
    }
    if generated_image:
        image_path = Path(generated_image).resolve()
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        from PIL import Image
        with Image.open(image_path) as image:
            actual_dimensions = list(image.size)
        candidate["actual_dimensions_px"] = actual_dimensions
        candidate["dimension_compliant"] = actual_dimensions == candidate["expected_dimensions_px"]
    return {
        "generated_candidate": {
            **candidate,
        },
        "visual_reference_images": [
            {"reference_id": item["reference_id"], "path": item["path"], "role": "style precedent only"}
            for item in references
        ],
        "attached_canonical_assets": [],
        "canonical_asset_policy": "Selected project visuals are attached to generation with exact-content and aspect-ratio protection. Review mandatory presence, visual fidelity, and icon-slot compliance where applicable. Editable reconstruction restores the exact canonical files.",
        "recommended_attachment_order": [
            "generated candidate",
            "three visual reference images",
        ],
    }


def build_review_prompt(state: dict[str, Any], review_config: dict[str, Any], generated_image: str | None = None) -> tuple[str, dict[str, Any]]:
    canvas = state["derived_canvas"]
    title = state["deck_design_configuration"]["title"]
    semantic = state["semantic_design"]
    guidance = state["guidance_profile"]
    exact = state["slide_input"]["exact_content"]
    constraints = state["intake_manifest"]["constraint_register"]
    assets = _asset_review_records(state["normalized_available_assets"])
    references = state["reference_retrieval"]["visual_references"]
    style = state["deck_design_configuration"]["style"]
    manifest = build_review_input_manifest(state, generated_image)
    generated = manifest["generated_candidate"]

    prompt = f"""Review the attached generated consulting-slide image before it is accepted as the final visual target.

Your job is to identify only material problems and, when necessary, return the smallest concrete edit delta. The main orchestration flow will add all preservation constraints and authoritative configuration after your response.

AUTOMATICALLY CONFIGURED REVIEW INPUTS

Generated candidate
{_json(generated)}

Attachment roles
{_json(manifest)}

Canvas configuration
{_json(canvas)}

Title configuration
{_json(title)}

Semantic design intent
{_json(semantic)}

Selected communication guidance profile
{_json(guidance)}

Exact authoritative slide content
{_json(exact)}

Active human constraints
{_json([item for item in constraints if item['status'] == 'active'])}

Available canonical roles and authoritative icon-slot dimensions
{_json(assets)}

Visual references
{_json(references)}

Configured style system
{_json(style)}

Review thresholds and policy
{_json(review_config)}

REVIEW PRINCIPLE

Evaluate the slide as an audience member seeing it for the first time.

Do not search for improvements merely because another design is possible. Identify an issue only when it materially reduces communication clarity, information hierarchy, relationship clarity, scanability, content fidelity, visual-reference fidelity, design-system fidelity, legibility, visual quality, or compliance with configured constraints.

Preserve portions that already work. The goal is to correct genuine failures while retaining a strong generated design.

1. CONFIGURATION COMPLIANCE

Check that the candidate is the configured {canvas['generation_canvas_px'][0]} × {canvas['generation_canvas_px'][1]} generation region. It maps to y = {canvas['generation_offset_y_px']} on the {canvas['full_slide_px'][0]} × {canvas['full_slide_px'][1]} full slide.

The candidate must contain no header, footer, page number, footer rule, or excluded-region content. Do not infer or modify header or footer dimensions.

Verify the exact configured title, anchor, maximum width, family, weight, color, scale, alignment, allowed line count, and minimum gap to body. If the title wraps, the body must begin below the rendered title.

2. SEMANTIC AND CONTENT FIDELITY

Verify that all authoritative content is represented without unsupported claims, categories, or relationships. The audience must recover the intended main message, hierarchy, reading logic, sequence, grouping, parallel branches, dependencies, and convergence. Treat exact authoritative content as the source of truth. Do not rewrite content for stylistic preference.

Verify every active hard constraint. A hard constraint failure is material even when the slide is otherwise visually strong.

3. VISUAL STRUCTURE AND COMMUNICATION

Assess the slide as one coherent consulting composition. Check rapid comprehension, natural reading path, intentional parallelism, correct dependency connections, repeated-structure consistency, balanced density, balanced whitespace, and appropriate emphasis. Do not require imitation of a reference layout.

Apply the selected guidance profile's review questions and anti-patterns. Treat guidance as communication-quality criteria. Do not use it to infer fonts, colors, dimensions, library choices, or reconstruction mechanics.

4. VISUAL REFERENCE AND DESIGN-SYSTEM FIDELITY

Use the three visual reference pages as visual precedents. Use the configured deck design system as the governing rule set. Review typography, information density, whitespace, alignment, color usage, hierarchy, diagram language, component styling, and overall polish. Configured rules take precedence over incidental reference details.

5. ICON SLOT AND CANONICAL ROLE USE

For every asset marked required, verify visible semantic presence, recognizable meaning, correct placement, and a rectangular icon slot within the configured dimensional range when visually measurable. For optional assets, do not require use. If used, they must remain semantically appropriate and recognizable.

Treat the icon slot as the placement object. Verify consistent internal padding, centered contain fitting, preserved glyph aspect ratio, and clearance from neighboring text, logos, and components. Do not judge placement from the irregular visible glyph bounds. The OpenAI, OpenCV, and Microsoft PowerPoint roles are mandatory semantic placeholders. Their exact canonical SVGs are restored downstream and are not attached to this review.

6. LEGIBILITY AND LOCAL CONSISTENCY

Flag material text clipping, collisions, unreadably small text, peer-style inconsistency, repeated-component misalignment, off-center elements where centering is clearly intended, inconsistent spacing, malformed icon slots, glyph overflow, awkward connector attachment, illegible arrowheads, unclear branch junctions, unnecessary bends, accidental overlap, distorted asset proportions, or inconsistent visual weight.

Do not pursue pixel-perfect normalization of harmless differences.

7. UNNECESSARY VISUAL EXPLANATION

Flag a legend, arrow label, branch label, icon, connector, decoration, or explanatory note only when it explains something already self-evident and adds material visual weight.

DECISION

Return PASS when no material edit is required. Return EDIT when one or more material issues should be corrected.

IF EDIT

For each issue provide the affected element, audience-facing problem, and smallest effective correction. Report no more than {review_config['maximum_material_issues']} issues, ordered by severity.

Then return a minimal edit delta. Describe only the affected elements and concrete changes. Do not repeat canvas, title, exact-content, style, asset, or preservation constraints. The orchestrator owns that invariant envelope.

Do not begin the delta with an image-edit command. Do not include generic preservation language. Do not use vague instructions such as make it cleaner, improve the layout, make it more professional, or redesign this section. Do not propose a new layout unless the current layout itself is the material failure.

OUTPUT FORMAT

Return valid JSON only, without a Markdown code fence.

For PASS return:
{{
  "decision": "PASS",
  "material_issues": [],
  "edit_delta": []
}}

For EDIT return:
{{
  "decision": "EDIT",
  "material_issues": [
    {{
      "category": "one configured review category",
      "severity": "high or medium",
      "element": "specific affected element",
      "problem": "audience-facing material problem",
      "correction": "smallest effective correction"
    }}
  ],
  "edit_delta": [
    {{
      "element": "specific affected element",
      "instruction": "concrete local change only"
    }}
  ]
}}

Keep the review concise. Do not provide alternatives, optional improvements, or a preservation envelope.
"""
    return prompt, manifest
