"""Deck planning prompt, routing, and coherence validation."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from slidecraft.orchestration.guidance_profiles import resolve_guidance_profile


def load_deck_plan_schema() -> dict[str, Any]:
    return json.loads(files("slidecraft.schemas").joinpath("deck_plan_minimal.schema.json").read_text(encoding="utf-8"))


def _packaged_guidance_root() -> Path:
    return Path(str(files("slidecraft").joinpath("guidance_profiles")))


def _resolve_planning_guidance(design: dict[str, Any]) -> dict[str, Any]:
    reference = design.get("guidance_profile", {})
    profile_id = reference.get("profile_id", "base") if isinstance(reference, dict) else str(reference)
    profile_ref = reference.get("path") if isinstance(reference, dict) else None
    root_ref = reference.get("inheritance_root") if isinstance(reference, dict) else None
    packaged_root = _packaged_guidance_root()
    if profile_ref and not str(profile_ref).startswith("packaged:"):
        profile_path = Path(profile_ref).expanduser().resolve()
    else:
        profile_path = packaged_root / f"{profile_id}.json"
    if root_ref and not str(root_ref).startswith("packaged:"):
        profile_root = Path(root_ref).expanduser().resolve()
    else:
        profile_root = packaged_root
    resolved = resolve_guidance_profile(profile_path, profile_root)
    return {
        "profile_id": resolved["profile_id"],
        "name": resolved["name"],
        "description": resolved["description"],
        "deck_reasoning": resolved["deck_reasoning"],
        "writing": resolved["writing"],
        "review": resolved["review"],
        "anti_patterns": resolved["anti_patterns"],
        "design_freedom": resolved["design_freedom"],
    }


def _resolve_density_guidance(request: dict[str, Any], design: dict[str, Any]) -> dict[str, Any]:
    selected = request.get("density_profile", design.get("density_profile", "high_consulting"))
    if isinstance(selected, dict):
        return selected
    policy = _load_routing_policy()
    profile = policy.get("density", {}).get("profiles", {}).get(selected)
    if profile is None:
        raise ValueError(f"Density profile {selected!r} is unavailable")
    return {"profile_id": selected, **profile}


def build_deck_prompt(request: dict[str, Any], intake: dict[str, Any], design: dict[str, Any]) -> str:
    count_instruction = (
        "Treat preferred_slide_count as an active length contract. Stay inside its range and aim at its target."
        if request.get("preferred_slide_count")
        else "Propose the smallest credible deck length after resolving evidence volume, density, storyline needs, and structural pages."
    )
    guidance = _resolve_planning_guidance(design)
    density = _resolve_density_guidance(request, design)
    return f"""Plan a coherent presentation deck using the selected communication guidance and density profile.

DECK REQUEST
{json.dumps(request, indent=2, ensure_ascii=False)}

NORMALIZED SOURCE ATOMS AND CONSTRAINTS
{json.dumps(intake, indent=2, ensure_ascii=False)}

FROZEN DECK DESIGN SYSTEM
{json.dumps(design, indent=2, ensure_ascii=False)}

RESOLVED COMMUNICATION GUIDANCE
{json.dumps(guidance, indent=2, ensure_ascii=False)}

RESOLVED DENSITY GUIDANCE
{json.dumps(density, indent=2, ensure_ascii=False)}

PLANNING METHOD
1. Establish the audience's decision, use, or consequential question. Derive a specific governing answer from the evidence and constraints.
2. Build two or three genuinely different storylines. Compare their decision value, explanatory power, evidence flow, audience fit, density, and requested length. Select the strongest one.
3. Build an argument spine in which each slide answers a distinct audience question and creates a clear reason for the next slide. Avoid a product tour or internal component inventory unless that directly serves the audience's decision.
4. Use conclusion-led message titles for information-bearing slides. The message chain alone should recover the deck's core argument. Adjacent slides must advance different claims or proof obligations.
5. Give every information-bearing slide one dominant claim supported by several source-grounded evidence units, relationships, implications, or qualifications. Integrate required topics into the argument instead of treating them as checklist pages.
6. Use the Agent-authored source authority, required-use, and exclusion decisions. Allocate every required source atom to a slide or appendix. Preserve exact content and provenance. Qualify claims when the evidence is directional, anecdotal, or incomplete.
7. Match the resolved density guidance. Consolidate overlapping ideas before adding pages, and avoid sparse concept-per-slide planning.
8. Use deterministic system layouts only for low-information structural slides. Use image generation for every information-bearing slide so the image model can choose its visual form.
9. Record dependencies, terminology obligations, repeated component roles, and cross-slide data consistency requirements.
10. Consider every project visual by semantic role, including logos, screenshots, photographs, illustrations, and diagrams. An available asset may be unused. A preferred asset should be used when it strengthens a relevant slide. Required-somewhere assets need at least one suitable slide. Never interpret a deck-level requirement as use on every slide. For each selected visual, add an asset_allocations record to the slide. Set usage to optional when the image model may use it and mandatory only when it must appear on that slide. Choose icon_slot for a compact pictogram or identity mark whose allocated placement region matters. Choose image_region for a screenshot, photograph, illustration, or other visual that should appear as the exact supplied image. Record the same decision in the deck-level asset_allocation summary.
11. Author the slide-specific header and footer content proposal for each slide when deck chrome is enabled. Choose its configured variant from the slide role and deck context. Empty text is valid only when intentional and must still be present as an explicit value.
12. {count_instruction}
13. Before returning, test the title chain, evidence support, distinction between adjacent slides, required-topic integration, and relevance to the audience decision. Return the requested JSON object only when these checks pass.
"""


def _load_routing_policy() -> dict[str, Any]:
    return json.loads(files("slidecraft.defaults").joinpath("deck_planning_config.json").read_text(encoding="utf-8"))


def _load_system_layouts() -> dict[str, dict[str, Any]]:
    payload = json.loads(files("slidecraft.defaults").joinpath("system_slide_layouts.json").read_text(encoding="utf-8"))
    return {item["system_layout_id"]: item for item in payload["layouts"]}


def _validate_agent_route(
    slide: dict[str, Any],
    *,
    routing_policy: dict[str, Any],
    system_layouts: dict[str, dict[str, Any]],
) -> None:
    role = slide["role"]
    route = slide["route"]
    role_policy = routing_policy.get("slide_roles", {}).get(role)
    if role_policy is None:
        raise ValueError(f"Slide {slide['slide_id']} uses an unconfigured role {role!r}")
    allowed_routes = {role_policy["default_route"]}
    if role_policy.get("image_generation_allowed"):
        allowed_routes.add("image_generation")
    if route not in allowed_routes:
        raise ValueError(
            f"Slide {slide['slide_id']} uses route {route!r}, which is incompatible with role {role!r}"
        )
    layout_id = slide.get("system_layout_id")
    if route == "image_generation":
        if layout_id:
            raise ValueError(f"Generated slide {slide['slide_id']} must not name a system layout")
        return
    if not layout_id:
        raise ValueError(f"System slide {slide['slide_id']} must include an agent-selected system_layout_id")
    layout = system_layouts.get(layout_id)
    if layout is None:
        raise ValueError(f"System layout {layout_id!r} is unavailable")
    if role not in layout.get("slide_roles", []):
        raise ValueError(f"System layout {layout_id!r} does not support slide role {role!r}")


def _validate_requested_slide_count(request: dict[str, Any], actual: int) -> dict[str, Any]:
    preference = request.get("preferred_slide_count")
    if not preference:
        return {"mode": "planner_proposed", "requested": None, "actual": actual, "satisfied": True}
    minimum = preference.get("minimum", preference.get("target", 1))
    maximum = preference.get("maximum", preference.get("target", minimum))
    target = preference.get("target")
    if minimum > maximum:
        raise ValueError("preferred_slide_count minimum cannot exceed maximum")
    if target is not None and not minimum <= target <= maximum:
        raise ValueError("preferred_slide_count target must fall between minimum and maximum")
    if not minimum <= actual <= maximum:
        raise ValueError(f"Deck plan has {actual} slides, outside the requested range {minimum} to {maximum}")
    return {
        "mode": "user_constrained",
        "requested": {"minimum": minimum, "target": target, "maximum": maximum},
        "actual": actual,
        "satisfied": True,
    }


def validate_and_normalize_plan(
    plan: dict[str, Any],
    intake: dict[str, Any],
    request: dict[str, Any] | None = None,
    routing_policy: dict[str, Any] | None = None,
    system_layouts: dict[str, dict[str, Any]] | None = None,
    deck_design: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = load_deck_plan_schema()
    errors = sorted(Draft202012Validator(schema).iter_errors(plan), key=lambda error: list(error.path))
    if errors:
        summary = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:8])
        raise ValueError(f"Deck plan failed schema validation: {summary}")
    slides = sorted(plan["slides"], key=lambda item: item["ordinal"])
    ids = [slide["slide_id"] for slide in slides]
    if len(ids) != len(set(ids)):
        raise ValueError("Deck plan contains duplicate slide IDs")
    if [slide["ordinal"] for slide in slides] != list(range(1, len(slides) + 1)):
        raise ValueError("Deck slide ordinals must be contiguous")
    known_sections = {section["section_id"] for section in plan["sections"]}
    known_atoms = {atom["atom_id"] for atom in intake.get("source_atoms", [])}
    policy = routing_policy or _load_routing_policy()
    layouts = system_layouts or _load_system_layouts()
    normalized = []
    for slide in slides:
        if slide["section_id"] not in known_sections:
            raise ValueError(f"Slide {slide['slide_id']} refers to an unknown section")
        unknown_atoms = sorted(set(slide["source_atom_ids"]) - known_atoms)
        if unknown_atoms:
            raise ValueError(f"Slide {slide['slide_id']} refers to unknown source atoms {unknown_atoms}")
        unknown_dependencies = sorted(set(slide.get("dependencies", [])) - set(ids))
        if unknown_dependencies:
            raise ValueError(f"Slide {slide['slide_id']} has unknown dependencies {unknown_dependencies}")
        _validate_agent_route(slide, routing_policy=policy, system_layouts=layouts)
        if (deck_design or {}).get("deck_chrome", {}).get("enabled"):
            proposal = slide.get("chrome_content_proposal")
            required_paths = (
                ("variant", proposal),
                ("header.left_text", (proposal or {}).get("header")),
                ("header.right_text", (proposal or {}).get("header")),
                ("footer.left_text", (proposal or {}).get("footer")),
                ("footer.center_text", (proposal or {}).get("footer")),
                ("footer.right_text_format", (proposal or {}).get("footer")),
            )
            missing_chrome = [path for path, container in required_paths if path.split(".")[-1] not in (container or {})]
            if missing_chrome:
                raise ValueError(
                    f"Slide {slide['slide_id']} is missing Agent-authored chrome fields: {missing_chrome}"
                )
        normalized.append(slide)
    if not plan["quality_evaluation"]["passed"]:
        raise ValueError("Deck planner marked its own result as failed")
    used_atoms = {atom for slide in normalized for atom in slide["source_atom_ids"]}
    required_atoms = {atom["atom_id"] for atom in intake.get("source_atoms", []) if atom.get("required_usage")}
    missing_required_atoms = sorted(required_atoms - used_atoms)
    project_assets = {item["asset_id"]: item for item in (request or {}).get("project_assets", [])}
    used_assets = {
        allocation["asset_id"]
        for slide in normalized
        for allocation in slide.get("asset_allocations", [])
    }
    for slide in normalized:
        allocations = slide.get("asset_allocations", [])
        allocated_ids = [item["asset_id"] for item in allocations]
        if len(allocated_ids) != len(set(allocated_ids)):
            raise ValueError(f"Slide {slide['slide_id']} allocates the same project asset more than once")
    unknown_assets = sorted(used_assets - set(project_assets))
    if unknown_assets:
        raise ValueError(f"Deck plan refers to unknown project assets: {unknown_assets}")
    mandatory_assets = {
        allocation["asset_id"]
        for slide in normalized
        for allocation in slide.get("asset_allocations", [])
        if allocation.get("usage") == "mandatory"
    }
    missing_required_assets = sorted(
        asset_id for asset_id, asset in project_assets.items()
        if asset.get("usage_policy") == "required_somewhere" and asset_id not in mandatory_assets
    )
    missing_slide_required_assets = []
    for asset_id, asset in project_assets.items():
        required_slides = set(asset.get("slide_ids", [])) if asset.get("usage_policy") == "required_on_slides" else set()
        if asset.get("usage_policy") == "required_each_slide":
            required_slides = {slide["slide_id"] for slide in normalized}
        for slide_id in sorted(required_slides):
            slide = next((item for item in normalized if item["slide_id"] == slide_id), None)
            allocations = {
                item["asset_id"]: item["usage"]
                for item in (slide or {}).get("asset_allocations", [])
            }
            if allocations.get(asset_id) != "mandatory":
                missing_slide_required_assets.append({"asset_id": asset_id, "slide_id": slide_id})
    report = {
        "slide_count": len(normalized),
        "section_count": len(known_sections),
        "system_slide_count": sum(slide["route"] == "system_layout" for slide in normalized),
        "generated_slide_count": sum(slide["route"] == "image_generation" for slide in normalized),
        "missing_required_source_atoms": missing_required_atoms,
        "missing_required_assets": missing_required_assets,
        "missing_slide_required_assets": missing_slide_required_assets,
        "slide_count_contract": _validate_requested_slide_count(request or {}, len(normalized)),
        "passed": not missing_required_atoms and not missing_required_assets and not missing_slide_required_assets,
    }
    if missing_required_atoms:
        raise ValueError(f"Required source atoms are unallocated: {missing_required_atoms}")
    if missing_required_assets:
        raise ValueError(f"Required project assets are unallocated: {missing_required_assets}")
    if missing_slide_required_assets:
        raise ValueError(f"Slide-specific required project assets are unallocated: {missing_slide_required_assets}")
    return {**plan, "slides": normalized}, report


def plan_deck(
    authored_plan: dict[str, Any],
    *,
    request: dict[str, Any],
    intake: dict[str, Any],
    design: dict[str, Any],
    routing_policy: dict[str, Any] | None = None,
    system_layouts: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return validate_and_normalize_plan(
        authored_plan,
        intake,
        request,
        routing_policy=routing_policy,
        system_layouts=system_layouts,
        deck_design=design,
    )
