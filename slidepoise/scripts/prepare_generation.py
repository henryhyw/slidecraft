#!/usr/bin/env python3
"""Compile resolved SlidePoise decisions into one authoritative image-generation handoff.

This script does not design the slide or judge visual quality. It only prevents the
host Agent from dropping resolved content, profile rules, design constraints,
resource obligations, or canvas geometry on the first image-generation call.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from approval_utils import require_approved
from component_preview import ensure_preview


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def build_style_context(config: dict[str, Any]) -> dict[str, Any]:
    """Capture resolved visual decisions without choosing or judging them."""
    profile = config.get("resolved_profile", {})
    guidance_keys = ("hard_rules", "visual_principles", "writing_principles", "reasoning_principles",
                     "anti_patterns", "asset_policy", "modes", "review_questions")
    return json.loads(json.dumps({
        "profile": {key: profile.get(key) for key in ("profile_id", "name", "purpose")},
        "style_agency": profile.get("style_agency", {}),
        "design": config.get("design", {}),
        "frame": config.get("frame", {}),
        "canvas": config.get("derived", {}).get("generation_region_px"),
        "guidance": {key: profile[key] for key in guidance_keys if key in profile},
    }))


def require_object(record: dict[str, Any], key: str, *, owner: str) -> Any:
    if key not in record:
        raise SystemExit(f"{owner} is missing required field: {key}")
    return record[key]


def augment_profile_core_references(
    profile: dict[str, Any],
    resources: dict[str, Any],
    libraries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ensure an active profile's always-on visual precedents reach the first image call.

    This is generic profile machinery: profiles nominate reference IDs; the catalog
    supplies their canonical files. It does not choose slide-specific references.
    """
    result = json.loads(json.dumps(resources))
    required = list(profile.get("always_attach_visual_references") or [])
    if not required:
        return result
    catalog_value = ((libraries or {}).get("visual_references") or {}).get("catalog")
    if not catalog_value:
        raise SystemExit("Resolved profile visual-reference catalog is required for always-on references")
    catalog_path = Path(str(catalog_value)).expanduser().resolve()
    catalog = load(catalog_path)
    by_id = {str(item.get("id")): (filename, item) for filename, item in (catalog.get("items") or {}).items()}
    selected = list(result.get("selected_visual_references") or [])
    selected_ids = {str(item.get("id")) for item in selected}
    for ref_id in required:
        ref_id = str(ref_id)
        if ref_id in selected_ids:
            continue
        if ref_id not in by_id:
            raise SystemExit(f"Profile requires missing visual reference catalog id: {ref_id}")
        filename, record = by_id[ref_id]
        canonical = catalog_path.parent / str(record.get("path") or filename)
        if not canonical.is_file():
            raise SystemExit(f"Profile visual reference file is missing: {canonical}")
        selected.append({
            "id": ref_id,
            "canonical_file": str(canonical.resolve()),
            "reason": f"Always-on visual precedent required by profile {profile.get('profile_id')}: {record.get('description', '')}",
            "source": "profile_core_reference",
        })
        selected_ids.add(ref_id)
    result["selected_visual_references"] = selected
    return result




def augment_selected_components(
    resources: dict[str, Any],
    profile_id: str | None = None,
    libraries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve host-Agent-selected component IDs to packaged previews and native donor metadata.

    Components are optional design grammar. This function never chooses a component; it only
    resolves IDs the host Agent already selected so the image-generation handoff cannot lose
    the preview/native-source relationship.
    """
    result = json.loads(json.dumps(resources))
    requested = list(result.get("selected_components") or [])
    if not requested:
        result["selected_components"] = []
        return result
    component_library = (libraries or {}).get("components") or {}
    catalog_values = component_library.get("catalogs", [component_library.get("catalog")])
    catalog_values = [value for value in catalog_values if value]
    if not catalog_values:
        raise SystemExit("Resolved profile component catalog is required when a component is selected")
    by_id, origins = {}, {}
    for value in catalog_values:
        catalog_path = Path(str(value)).expanduser().resolve()
        for record in (load(catalog_path).get("items") or {}).values():
            identifier = str(record.get("id", ""))
            if identifier in by_id:
                raise SystemExit(f"Duplicate component ID across selected sets: {identifier}")
            if identifier:
                by_id[identifier], origins[identifier] = record, catalog_path
    resolved: list[dict[str, Any]] = []
    for item in requested:
        component_id = str(item.get("component_id") or item.get("id") or "")
        if not component_id:
            raise SystemExit("Every selected component requires component_id or id")
        record = by_id.get(component_id)
        if record is None:
            raise SystemExit(f"Selected component is not in the packaged component catalog: {component_id}")
        catalog_path = origins[component_id]
        donor_value = str(record.get("path") or "").strip()
        preview_value = str(record.get("preview_path") or "").strip()
        # Older imported records only stored their source path.
        if donor_value.lower().endswith(".pptx") and not preview_value:
            preview_value = str(Path(donor_value).with_suffix(".preview.png"))
        donor = catalog_path.parent / donor_value if donor_value else None
        preview = catalog_path.parent / preview_value if preview_value else None
        if donor and preview and donor.is_file():
            try:
                ensure_preview(donor, preview, int(record.get("native_source_slide_number", 1)))
            except ValueError as error:
                raise SystemExit(str(error)) from error
        if donor and not preview:
            raise SystemExit(f"Selected component {component_id} must provide both native donor and preview, or neither for grammar-only guidance")
        if donor is not None and not donor.is_file():
            raise SystemExit(f"Selected component native donor is missing: {donor}")
        if preview is not None and not preview.is_file():
            raise SystemExit(f"Selected component preview is missing: {preview}")
        reason = str(item.get("reason") or "").strip()
        if not reason:
            raise SystemExit(f"Selected component {component_id} requires a reason-for-selection")
        merged = json.loads(json.dumps(record))
        merged.update({
            "component_id": component_id,
            "reason": reason,
            "source": "selected_shared_component_set",
        })
        if donor is not None and preview is not None:
            merged["canonical_file"] = str(donor.resolve())
            merged["preview_file"] = str(preview.resolve())
            merged["native_source_slide_number"] = int(record.get("native_source_slide_number", 1))
        elif preview is not None:
            merged["preview_file"] = str(preview.resolve())
            merged["resource_form"] = "visual_precedent"
        else:
            merged["resource_form"] = "grammar_only"
        resolved.append(merged)
    result["selected_components"] = resolved
    return result



def asset_vocabulary_policy(profile: dict[str, Any]) -> dict[str, Any]:
    return dict((profile.get("hard_rules") or {}).get("asset_vocabulary") or {})


def generation_asset_descriptions(profile: dict[str, Any], resources: dict[str, Any]) -> list[dict[str, Any]]:
    policy = asset_vocabulary_policy(profile)
    closed = str(policy.get("mode") or "open").lower() == "closed"
    result: list[dict[str, Any]] = []
    for index, item in enumerate(resources.get("selected_assets") or [], start=1):
        description = str(item.get("generation_description") or item.get("description") or "").strip()
        if closed and not description:
            raise SystemExit(f"Closed asset vocabulary requires generation_description for selected asset {item.get('asset_id')}")
        result.append({
            "asset_id": item.get("asset_id"),
            "contact_sheet_label": f"A{index:02d}",
            "role": item.get("role", "selected asset"),
            "generation_description": description or str(item.get("role") or item.get("asset_id")),
            "intrinsic_aspect_ratio": item.get("intrinsic_aspect_ratio"),
            "require_exact_identity": bool(item.get("require_exact_identity") or item.get("user_required")),
        })
    return result


def _asset_is_required(item: dict[str, Any]) -> bool:
    return bool(item.get("user_required") or item.get("required_for_slide"))


def enforce_resource_budgets(config: dict[str, Any], resources: dict[str, Any]) -> None:
    policy = config.get("library_policy", {}) or {}
    max_refs = int(policy.get("maximum_visual_references_per_generation", 3))
    references = list(resources.get("selected_visual_references") or [])
    if len(references) > max_refs:
        raise SystemExit(f"Selected visual references exceed configured maximum: {len(references)} > {max_refs}")

    max_optional_assets = int(policy.get("maximum_optional_assets_per_generation", 12))
    optional_assets = [item for item in (resources.get("selected_assets") or []) if not _asset_is_required(item)]
    if len(optional_assets) > max_optional_assets:
        raise SystemExit(
            f"Optional selected assets exceed configured maximum: {len(optional_assets)} > {max_optional_assets}. "
            "Narrow retrieval to the most useful assets; user-required assets are exempt."
        )


def validate_resources(intent: dict[str, Any], resources: dict[str, Any]) -> None:
    selected_assets = list(resources.get("selected_assets") or [])
    asset_by_id = {str(item.get("asset_id")): item for item in selected_assets if item.get("asset_id")}
    for item in selected_assets:
        if not item.get("asset_id"):
            raise SystemExit("Every selected asset requires asset_id")
        if not item.get("canonical_file"):
            raise SystemExit(f"Selected asset {item['asset_id']} requires canonical_file")

    for reference in resources.get("selected_visual_references") or []:
        if not reference.get("id") or not reference.get("canonical_file"):
            raise SystemExit("Every selected visual reference requires id and canonical_file")
        if not str(reference.get("reason") or "").strip():
            raise SystemExit(f"Visual reference {reference.get('id')} requires a reason-for-attachment")

    for obligation in intent.get("user_required_assets") or []:
        asset_id = str(obligation.get("asset_id") or "")
        if not asset_id:
            raise SystemExit("Every user_required_assets record requires asset_id")
        if obligation.get("require_exact_identity") and asset_id not in asset_by_id:
            raise SystemExit(f"Exact required asset is missing from resource selection: {asset_id}")


def build_contract(config: dict[str, Any], intent: dict[str, Any], resources: dict[str, Any]) -> dict[str, Any]:
    design = require_object(config, "design", owner="resolved config")
    derived = require_object(config, "derived", owner="resolved config")
    generation = require_object(config, "generation", owner="resolved config")
    profile = require_object(config, "resolved_profile", owner="resolved config")
    title = require_object(design, "title", owner="resolved design")
    style = require_object(design, "style", owner="resolved design")
    if resources.get("style_context") is not None and resources["style_context"] != build_style_context(config):
        raise SystemExit("Style changed since the context sheet was prepared. Rebuild it and ask for style and asset approval again.")

    for key in (
        "audience_question",
        "dominant_message",
        "required_content",
        "semantic_relationships",
        "hierarchy",
        "visual_obligations",
        "explicit_user_visual_requirements",
    ):
        require_object(intent, key, owner="slide intent")

    resources = augment_profile_core_references(profile, resources, config.get("libraries"))
    resources = augment_selected_components(resources, str(profile.get("profile_id") or ""), config.get("libraries"))
    enforce_resource_budgets(config, resources)
    validate_resources(intent, resources)
    asset_policy = asset_vocabulary_policy(profile)
    asset_descriptions = generation_asset_descriptions(profile, resources)

    canvas = list(require_object(derived, "generation_region_px", owner="resolved config.derived"))
    if len(canvas) != 2 or any(float(v) <= 0 for v in canvas):
        raise SystemExit("Resolved generation_region_px must contain two positive values")

    contract = {
        "schema_version": "1.4.0",
        "purpose": "authoritative_first_image_generation_handoff",
        "generation_model_default": generation.get("default_model"),
        "host_generation_adapter": generation.get("host_adapter", {}),
        "generation_budget": {
            "maximum_candidates": int(generation.get("maximum_candidates", 1)),
            "retry_policy": generation.get("retry_policy"),
        },
        "human_approval_policy": generation.get("human_approval", {}),
        "canvas": {
            "dimensions_px": canvas,
            "aspect_ratio": derived.get("generation_aspect_ratio"),
            "full_slide_offset_y_px": derived.get("generation_offset_y_px"),
            "master_frame_excluded": True,
            "forbidden_frame_content": ["header", "footer", "page number", "master-frame rules or decorations"],
        },
        "communication_intent": json.loads(json.dumps(intent)),
        "user_language": {
            "preserve_user_language_and_wording": True,
            "reader_first": True,
            "new_copy_em_dash": "avoid",
            "new_copy_semicolon": "avoid",
            "new_copy_colon": "use_only_when_materially_clearer",
            "avoid_stock_assistant_phrasing": True,
            "avoid_meta_interface_explanations": True,
            "profile_may_extend_voice": True,
        },
        "non_negotiable_design": {
            "title": title,
            "style": style,
            "text_style_policies": design.get("text_reconstruction", {}).get("text_style_policies", {}),
            "semantic_style_tokens": design.get("semantic_style_tokens", {}),
            "data_visualization": design.get("data_visualization", {}),
            "explicit_user_visual_requirements": intent["explicit_user_visual_requirements"],
            "icon_slot_rule": (
                "For every icon, reserve a visually unambiguous bounded slot that protects its room from surrounding content. "
                "The icon may have no designed surface or may sit on a profile-approved background surface. When there is no designed surface, "
                "a subtle generation-only boundary may mark the slot for localization; that boundary is scaffolding, not a decorative container and is not reconstructed downstream. When the icon sits on a larger colored panel/card and no distinct icon tile is intended, the downstream reconstruction should keep the icon background transparent rather than turning the scaffold into a white box."
            ),
        },
        "profile": {
            "profile_id": profile.get("profile_id"),
            "name": profile.get("name"),
            "purpose": profile.get("purpose"),
            "style_agency": profile.get("style_agency", {}),
            "hard_rules": profile.get("hard_rules", {}),
            "reasoning_principles": profile.get("reasoning_principles", []),
            "visual_principles": profile.get("visual_principles", []),
            "writing_principles": profile.get("writing_principles", []),
            "review_questions": profile.get("review_questions", []),
            "anti_patterns": profile.get("anti_patterns", []),
            "visual_reference_priorities": profile.get("visual_reference_priorities", {}),
            "density_profile": derived.get("density_profile"),
            "density_guidance": derived.get("density_guidance", {}),
            "resolution_precedence": derived.get("resolution_precedence", []),
        },
        "resources": {
            "style_context": resources.get("style_context"),
            "style_direction": resources.get("style_direction", {}),
            "selected_visual_references": resources.get("selected_visual_references", []),
            "selected_assets": resources.get("selected_assets", []),
            "generation_asset_descriptions": asset_descriptions,
            "generation_context_sheet": resources.get("generation_context_sheet"),
            "asset_vocabulary_policy": asset_policy,
            "selected_components": resources.get("selected_components", []),
        },
        "composition_freedom": [
            "Choose the visual composition, grouping structure, exact object placement, connector arrangement, and emphasis system that best communicates the semantic intent.",
            "Do not force a fixed template, grid, card count, chart archetype, component precedent, or one icon treatment when another composition better supports the slide.",
            "Preserve compositional freedom without relaxing resolved design values, profile hard rules, content, asset, or canvas constraints.",
            "Density is a separate user/session control. Apply the selected density inside the profile rather than equating the profile with sparse or dense composition.",
        ],
    }
    return contract


def build_brief(contract: dict[str, Any]) -> str:
    canvas = contract["canvas"]
    intent = contract["communication_intent"]
    design = contract["non_negotiable_design"]
    profile = contract["profile"]
    resources = contract["resources"]

    lines = [
        "# SlidePoise authoritative first-generation brief",
        "",
        f"Use the host image-generation capability to create the visual target. Preferred configured model: `{contract.get('generation_model_default')}`. In ChatGPT use native image generation/editing; in Codex use the available image-generation skill/tool or bounded image-capable delegation. Do not replace this stage with Python plotting, HTML/SVG drawing, deterministic diagram generation, or a fixed template.",
        "",
        "Treat exact content, canvas, explicit user requirements, selected assets, and PROFILE HARD RULES as authoritative. Interpret palette, typography, density, and icon treatment according to PROFILE STYLE AGENCY. Session and user overrides take precedence.",
        "",
        "## NON-NEGOTIABLE: generation spending and human approval",
        "- Generate exactly one initial candidate. Do not automatically regenerate or explore alternatives.",
        "- After generation, present the actual downloaded/read candidate to the user and wait for explicit approval before semantic mapping or reconstruction.",
        "- If the user rejects the candidate and specifies changes, edit that same candidate with the same host image-generation/edit capability; preserve everything not requested to change. Do not start over.",
        "- One explicit user rejection/change request authorizes at most one targeted edit call. If the user does not specify changes, ask what to change before making another image call.",
        "- Once the user approves an image, freeze it and do not regenerate it.",
        "",
        "## NON-NEGOTIABLE: canvas and frame",
        f"- Generate exactly the substantive canvas at `{canvas['dimensions_px'][0]} x {canvas['dimensions_px'][1]}` pixels (aspect ratio `{canvas.get('aspect_ratio')}`).",
        "- This canvas excludes the Slide Master frame. Do not draw any header, footer, page number, or master-frame rule/decoration.",
        "",
        "## NON-NEGOTIABLE: exact communication content",
        f"- Audience question: {intent['audience_question']}",
        f"- Dominant message: {intent['dominant_message']}",
        "- Required content:",
        "```json",
        dump_json(intent["required_content"]),
        "```",
        "- Semantic relationships:",
        "```json",
        dump_json(intent["semantic_relationships"]),
        "```",
        "- Hierarchy:",
        "```json",
        dump_json(intent["hierarchy"]),
        "```",
        "- Visual obligations:",
        "```json",
        dump_json(intent["visual_obligations"]),
        "```",
        "",
        "## COMPLETE AGREED PLAN",
        "Preserve required facts, semantic relationships, qualifications and explicit constraints. Use optional context selectively without changing the agreed meaning. The plan describes information structure, not a required visual layout. Do not infer a numbered process from an array of content items.",
        "```json",
        dump_json(intent),
        "```",
        "",
        "## USER-FACING LANGUAGE",
        "Write slide copy for the reader. Preserve user-authored wording and the language of the agreed plan. Use direct, specific sentences. Do not add ceremonial introductions, generic assistant phrases, empty transitions, or meta commentary about the slide. Do not use an em dash in newly authored copy. Avoid semicolons. Use a colon only when it materially improves a label, quotation, data value, or short lead-in. Profile writing guidance may add character while these clarity rules remain in force.",
        "```json",
        dump_json(contract.get("user_language", {})),
        "```",
        "",
        "## RESOLVED DESIGN SYSTEM",
        "Concrete values are exact only when PROFILE STYLE AGENCY marks that dimension as `specified`. With `guided`, preserve the visual character while allowing a coherent adaptation. With `agent_decides` or `agent_decides_from_references`, use the values as reconstruction fallbacks and derive the generated visual from the profile purpose, approved references, and current content.",
        "### Title",
        "```json",
        dump_json(design["title"]),
        "```",
        "### Style",
        "```json",
        dump_json(design["style"]),
        "```",
        "### Typography size/spacing policies",
        "Use these as the resolved typography scale when the corresponding visual text style is present.",
        "```json",
        dump_json(design.get("text_style_policies", {})),
        "```",
        "### Exact semantic style tokens",
        "Use these only when the corresponding semantic treatment is appropriate; do not substitute approximate colours or fonts.",
        "```json",
        dump_json(design["semantic_style_tokens"]),
        "```",
        "### Data-visualisation defaults",
        "```json",
        dump_json(design.get("data_visualization", {})),
        "```",
        "### Explicit user visual requirements",
        "```json",
        dump_json(design["explicit_user_visual_requirements"]),
        "```",
        f"### Icon slot rule\n{design['icon_slot_rule']}",
        "",
        f"## PROFILE HARD RULES: {profile.get('name')} ({profile.get('profile_id')})",
        "These rules control the visual system but not the slide's exact composition.",
        "```json",
        dump_json(profile.get("hard_rules", {})),
        "```",
        "",
        "## PROFILE STYLE AGENCY",
        "```json",
        dump_json(profile.get("style_agency", {})),
        "```",
        "",
        "## PROFILE DESIGN GUIDANCE",
        f"- Purpose: {profile.get('purpose')}",
        f"- Density profile: {profile.get('density_profile')}",
        "- Density guidance:",
        "```json",
        dump_json(profile.get("density_guidance", {})),
        "```",
        "- Visual principles:",
        *[f"  - {item}" for item in profile.get("visual_principles", [])],
        "- Writing principles:",
        *[f"  - {item}" for item in profile.get("writing_principles", [])],
        "- Avoid:",
        *[f"  - {item}" for item in profile.get("anti_patterns", [])],
        "",
        "## Attachments and their roles",
        f"- Attach the same style and asset context sheet reviewed by the user: `{(resources.get('generation_context_sheet') or {}).get('path', '')}`.",
        "- Style swatches, typeface labels and context-sheet arrangement explain the visual vocabulary. They are not slide content or a slide-layout template. Apply the recorded creative-freedom settings.",
        "- Agreed slide-specific visual direction:",
        "```json",
        dump_json(resources.get("style_direction", {})),
        "```",
    ]

    references = resources.get("selected_visual_references", [])
    if references:
        for item in references:
            lines.extend([
                f"- Visual reference `{item.get('id')}`: attach `{item.get('canonical_file')}`.",
                f"  - Why attached: {item.get('reason')}",
                "  - Use as a visual/style/communication precedent only unless the user explicitly authorized factual-content reuse.",
            ])
    else:
        lines.append("- No visual references selected.")

    components = resources.get("selected_components", [])
    if components:
        for item in components:
            lines.extend([
                f"- Component precedent `{item.get('component_id')}`: attach preview `{item.get('preview_file')}` for image generation.",
                f"  - Why selected: {item.get('reason')}",
                f"  - Native donor for reconstruction: `{item.get('canonical_file')}`, slide {item.get('native_source_slide_number')}.",
                f"  - Grammar: {json.dumps(item.get('grammar', {}), ensure_ascii=False)}",
                "  - Adapt it. Do not copy sample text/data, sample category/series counts, sample row/column counts, exact footprint, or surrounding slide layout unless those happen to fit the current semantic need.",
                "  - Preserve only the structural/visual logic that remains useful; if the grammar is not a good fit after reasoning, do not force it.",
            ])
    else:
        lines.append("- No reusable component precedent selected; design components freely.")

    assets = resources.get("selected_assets", [])
    asset_policy = resources.get("asset_vocabulary_policy", {}) or {}
    closed_assets = str(asset_policy.get("mode") or "open").lower() == "closed"
    if assets and closed_assets:
        novel_policy = asset_policy.get("novel_illustrations", {}) or {}
        lines.extend([
            "",
            "## NON-NEGOTIABLE: approved semantic visual vocabulary + profile-governed illustration freedom",
            "- The approved generation context sheet is the visual index of selected/retrieved references, components, assets, and user uploads. The textual descriptions below remain authoritative if a thumbnail is ambiguous.",
            "- Known reusable assets, logos, icons, photographs, and user-provided images must come from the approved upstream resource pool; do not invent a substitute identity for them.",
            "- Native presentation geometry such as boxes, circles, lines, connectors, tables, charts, chart marks, and background fields remains available for composition.",
            "- The image model may create a novel illustration only when the active profile's novel-illustration guidance allows it and the illustration materially supports the message. Novel illustrations are not substitutes for a known logo/icon/user asset and will be classified explicitly downstream.",
            f"- Novel illustration mode: `{novel_policy.get('mode', 'none')}`. Guidance: {novel_policy.get('guidance', 'No novel illustrations.')}",
            "- Do not add small icon boxes, outlines, or white knockout tiles unless the accepted design truly intends a real icon background surface; a localization scaffold is not a reconstructable asset.",
        ])
        context_sheet = resources.get("generation_context_sheet") or {}
        if context_sheet.get("path"):
            lines.extend([
                f"- Attach the approved generation context sheet: `{context_sheet.get('path')}`.",
                "  - It contains the approved resource pool; use the labels/descriptions to understand what may be reused.",
            ])
        else:
            lines.append("- ERROR: the approved generation context sheet is missing; return to the style-and-assets gate before generating.")
        for item in resources.get("generation_asset_descriptions", []):
            label = item.get("contact_sheet_label") or ""
            lines.append(f"- [{label}] Asset `{item.get('asset_id')}` ({item.get('role', 'selected asset')}): {item.get('generation_description')}")
            if item.get("intrinsic_aspect_ratio") is not None:
                lines.append(f"  - Approximate intrinsic aspect ratio: {item['intrinsic_aspect_ratio']}; reserve a compatible slot.")
            if item.get("require_exact_identity"):
                lines.append("  - Preserve identity/footprint as composition guidance; the exact canonical asset is restored downstream.")
    elif assets:
        for item in assets:
            lines.append(f"- Asset `{item.get('asset_id')}`: attach `{item.get('canonical_file')}`; role: {item.get('role', 'selected asset')}.")
            if item.get("generation_instruction"):
                lines.append(f"  - Generation instruction: {item['generation_instruction']}")
            if item.get("require_exact_identity") or item.get("user_required"):
                lines.append("  - Preserve identity. The generated depiction is composition guidance; the canonical file will be restored downstream.")
            if item.get("intrinsic_aspect_ratio") is not None:
                lines.append(f"  - Intrinsic aspect ratio: {item['intrinsic_aspect_ratio']}; allocate a compatible slot and do not stretch it.")
    else:
        lines.append("- No selected canonical assets.")

    lines.extend([
        "",
        "## COMPOSITION FREEDOM",
        *[f"- {item}" for item in contract.get("composition_freedom", [])],
        "",
        (
            "Before sending the image-generation call, attach the approved generation context sheet. It already contains the selected visual references, component previews, retrieved assets, and current-chat/user uploads. Use this brief plus that sheet as the authoritative generation context."
            if str((resources.get("asset_vocabulary_policy") or {}).get("generation_representation") or "").lower() == "full_context_sheet"
            else "Before sending the image-generation call, attach every selected visual reference, component preview, and asset above that is available to the host and use this brief as the authoritative generation instruction."
        ),
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--intent", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--approvals", type=Path, required=True)
    args = parser.parse_args()

    try:
        approvals = require_approved(args.approvals, ("plan", "resources"))
    except ValueError as exc:
        raise SystemExit(str(exc))
    config = load(args.config)
    intent = load(args.intent)
    resources = load(args.resources)
    if not resources.get("style_context"):
        raise SystemExit("This resource sheet predates combined style and asset review. Run prepare_resource_context.py and ask for approval before generating.")
    contract = build_contract(config, intent, resources)
    asset_policy = contract.get("resources", {}).get("asset_vocabulary_policy", {}) or {}
    closed_assets = str(asset_policy.get("mode") or "open").lower() == "closed"
    representation = str(asset_policy.get("generation_representation") or "").lower()
    if representation == "full_context_sheet":
        context_sheet = contract.get("resources", {}).get("generation_context_sheet") or {}
        context_path = Path(str(context_sheet.get("path") or ""))
        if not context_path.is_file():
            raise SystemExit("Approved generation context sheet is missing. Run prepare_resource_context.py and complete the resource approval gate first.")
    brief = build_brief(contract)

    args.contract.parent.mkdir(parents=True, exist_ok=True)
    args.brief.parent.mkdir(parents=True, exist_ok=True)
    args.contract.write_text(dump_json(contract) + "\n", encoding="utf-8")
    args.brief.write_text(brief, encoding="utf-8")
    print(json.dumps({
        "contract": str(args.contract.resolve()),
        "brief": str(args.brief.resolve()),
        "profile": contract["profile"]["profile_id"],
        "visual_references": len(contract["resources"]["selected_visual_references"]),
        "assets": len(contract["resources"]["selected_assets"]),
        "components": len(contract["resources"].get("selected_components", [])),
        "canvas": contract["canvas"]["dimensions_px"],
    }, indent=2))


if __name__ == "__main__":
    main()
