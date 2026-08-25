"""Deck planning prompt, routing, and coherence validation."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator

from slidecraft.providers.base import StructuredReasoningProvider

STRUCTURAL_ROLES = {"title_slide", "agenda", "section_divider", "quote_or_statement", "closing", "appendix_divider"}


def load_deck_plan_schema() -> dict[str, Any]:
    return json.loads(files("slidecraft.schemas").joinpath("deck_plan_minimal.schema.json").read_text(encoding="utf-8"))


def build_deck_prompt(request: dict[str, Any], intake: dict[str, Any], design: dict[str, Any]) -> str:
    count_instruction = (
        "Treat preferred_slide_count as an active length contract. Stay inside its range and aim at its target."
        if request.get("preferred_slide_count")
        else "Propose the smallest credible deck length after resolving evidence volume, density, storyline needs, and structural pages."
    )
    return f"""Plan a coherent presentation deck using the selected communication guidance and density profile.

DECK REQUEST
{json.dumps(request, indent=2, ensure_ascii=False)}

NORMALIZED SOURCE ATOMS AND CONSTRAINTS
{json.dumps(intake, indent=2, ensure_ascii=False)}

FROZEN DECK DESIGN SYSTEM
{json.dumps(design, indent=2, ensure_ascii=False)}

PLANNING METHOD
1. Resolve the audience decision, governing thought, source authority, hard constraints, selected guidance profile, and density before allocating slides.
2. Build two or three plausible storylines. Evaluate them for answer quality, evidence flow, section logic, source coverage, audience fit, density, and requested length. Select the strongest one.
3. Organize the selected storyline into purposeful argument phases. Use section dividers only when they materially clarify a new phase.
4. Give every information-bearing slide one governing message supported by several semantic or evidence units. Avoid duplicate messages and sparse content slides that violate the density profile.
5. Allocate every authoritative source atom to a slide, appendix, or explicit exclusion with a reason. Preserve exact content and provenance.
6. Use deterministic system layouts only for low-information structural slides. Use image generation for every information-bearing slide so the image model can choose its visual form.
7. Record dependencies, terminology obligations, repeated component roles, and cross-slide data consistency requirements.
8. Consider project assets by semantic role. An available asset may be unused. A preferred asset should be used when it strengthens a relevant slide. Required-somewhere assets need at least one suitable slide. Never interpret a deck-level requirement as use on every slide. Record chosen asset IDs on their assigned slides and in asset_allocation.
9. {count_instruction}
10. Self-evaluate storyline coherence, source coverage, slide-job clarity, route fidelity, and cross-slide coherence. Return the requested JSON object only when these checks pass.
"""


def _route(slide: dict[str, Any]) -> tuple[str, str | None]:
    role = slide["role"]
    if role in STRUCTURAL_ROLES:
        defaults = {
            "title_slide": "title_slide_minimal_v1",
            "agenda": "agenda_clean_v1",
            "section_divider": "section_divider_slanted_blocks_v1",
            "quote_or_statement": "statement_slide_v1",
            "closing": "closing_next_steps_v1",
            "appendix_divider": "section_divider_slanted_blocks_v1",
        }
        return "system_layout", slide.get("system_layout_id") or defaults[role]
    return "image_generation", None


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
        route, layout = _route(slide)
        normalized.append({**slide, "route": route, "system_layout_id": layout})
    if not plan["quality_evaluation"]["passed"]:
        raise ValueError("Deck planner marked its own result as failed")
    used_atoms = {atom for slide in normalized for atom in slide["source_atom_ids"]}
    authoritative = {atom["atom_id"] for atom in intake.get("source_atoms", []) if atom.get("authority") == "authoritative"}
    missing_authoritative = sorted(authoritative - used_atoms)
    project_assets = {item["asset_id"]: item for item in (request or {}).get("project_assets", [])}
    used_assets = {asset_id for slide in normalized for asset_id in slide.get("asset_ids", [])}
    unknown_assets = sorted(used_assets - set(project_assets))
    if unknown_assets:
        raise ValueError(f"Deck plan refers to unknown project assets: {unknown_assets}")
    missing_required_assets = sorted(
        asset_id for asset_id, asset in project_assets.items()
        if asset.get("usage_policy") == "required_somewhere" and asset_id not in used_assets
    )
    report = {
        "slide_count": len(normalized),
        "section_count": len(known_sections),
        "system_slide_count": sum(slide["route"] == "system_layout" for slide in normalized),
        "generated_slide_count": sum(slide["route"] == "image_generation" for slide in normalized),
        "missing_authoritative_source_atoms": missing_authoritative,
        "missing_required_assets": missing_required_assets,
        "slide_count_contract": _validate_requested_slide_count(request or {}, len(normalized)),
        "passed": not missing_authoritative and not missing_required_assets,
    }
    if missing_authoritative:
        raise ValueError(f"Authoritative source atoms are unallocated: {missing_authoritative}")
    if missing_required_assets:
        raise ValueError(f"Required project assets are unallocated: {missing_required_assets}")
    return {**plan, "slides": normalized}, report


def plan_deck(
    provider: StructuredReasoningProvider,
    *,
    request: dict[str, Any],
    intake: dict[str, Any],
    design: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = provider.reason(
        prompt=build_deck_prompt(request, intake, design),
        schema=load_deck_plan_schema(),
        operation="slidecraft_deck_plan",
    )
    return validate_and_normalize_plan(plan, intake, request)
