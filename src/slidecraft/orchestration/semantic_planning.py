"""Generic semantic-planning contract, prompt, loader, and validation."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def build_semantic_planning_prompt(
    slide: dict[str, Any],
    intake_manifest: dict[str, Any] | None = None,
    guidance_profile: dict[str, Any] | None = None,
) -> str:
    """Build a provider-neutral prompt for a managed or host reasoning model."""
    return f"""Design the semantic communication structure for one presentation slide.

SLIDE OBJECTIVE
{slide['objective']}

EXACT AUTHORITATIVE CONTENT
{json.dumps(slide['exact_content'], indent=2, ensure_ascii=False)}

EXPLICIT HUMAN CONSTRAINTS
{json.dumps(slide.get('explicit_human_constraints', []), indent=2, ensure_ascii=False)}

NORMALIZED INTAKE AND CONSTRAINT REGISTER
{json.dumps(intake_manifest or {}, indent=2, ensure_ascii=False)}

SELECTED COMMUNICATION GUIDANCE PROFILE
{json.dumps(guidance_profile or {}, indent=2, ensure_ascii=False)}

TASK
1. Build semantic units that map every required source item through JSON-style source paths.
2. Identify sequence, grouping, hierarchy, comparison, causality, dependency, parallelism, convergence, and input-output relationships where supported.
3. Propose at least three materially different communication structures.
4. Score every candidate from 0 to 5 for objective alignment, content coverage, relationship clarity, hierarchy clarity, density feasibility, and compliance with explicit constraints.
5. Select the strongest structure and explain its reading logic.
6. Produce layout-agnostic visual intent. Do not specify coordinates, column widths, exact cards, or detailed page geometry unless the user explicitly requested them.
7. Identify useful asset roles without selecting glyphs or drawing components.
8. Verify source traceability and flag density or ambiguity risks.
9. Treat active hard constraints as mandatory semantic requirements. Preserve their constraint IDs so generation and review can verify them.

CONTENT RULES
Exact source content remains authoritative. Do not silently omit, invent, or replace source content. Semantic labels may summarize meaning for planning, while the exact source remains separately available to generation and reconstruction.

OUTPUT
Return strict JSON conforming to semantic_design.schema.json.
"""


def _source_paths(slide: dict[str, Any]) -> set[str]:
    paths: set[str] = set()

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        else:
            paths.add(path)

    walk(slide["exact_content"], "exact_content")
    return paths


def validate_semantic_design(plan: dict[str, Any], slide: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads(
        files("slidecraft.schemas").joinpath("semantic_design.schema.json").read_text(encoding="utf-8")
    )
    errors = sorted(Draft202012Validator(schema).iter_errors(plan), key=lambda error: list(error.path))
    if errors:
        summary = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:8])
        raise ValueError(f"Agent semantic design failed schema validation: {summary}")
    if plan["exact_content_is_authoritative"] is not True:
        raise ValueError("Semantic design must preserve exact source authority")
    if plan["visual_intent"].get("layout_agnostic") is not True:
        raise ValueError("Semantic visual intent must remain layout-agnostic")
    if len(plan["candidate_structures"]) < 2:
        raise ValueError("Semantic planning must compare at least two candidate structures")
    candidate_ids = {candidate["id"] for candidate in plan["candidate_structures"]}
    if plan["selected_structure_id"] not in candidate_ids:
        raise ValueError("Selected semantic structure is absent from candidate structures")

    unit_ids = {unit["id"] for unit in plan["semantic_units"]}
    if len(unit_ids) != len(plan["semantic_units"]):
        raise ValueError("Semantic unit IDs must be unique")
    traceability = {record["source_path"]: record for record in plan["source_traceability"]}
    expected_paths = _source_paths(slide)
    unmapped = sorted(path for path in expected_paths if path not in traceability)
    if unmapped:
        raise ValueError(f"Exact source paths are missing semantic traceability: {unmapped}")
    invalid_units = sorted({unit_id for record in traceability.values() for unit_id in record["semantic_unit_ids"] if unit_id not in unit_ids})
    if invalid_units:
        raise ValueError(f"Traceability refers to unknown semantic units: {invalid_units}")
    if not plan["quality_evaluation"].get("passed"):
        raise ValueError("Semantic design failed its quality evaluation")
    return {
        "status": "passed",
        "source_path_count": len(expected_paths),
        "mapped_source_path_count": len(expected_paths),
        "semantic_unit_count": len(plan["semantic_units"]),
        "relationship_count": len(plan["semantic_relationships"]),
        "candidate_count": len(plan["candidate_structures"]),
        "selected_structure_id": plan["selected_structure_id"],
    }


def resolve_semantic_design(slide: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    """Resolve a supplied host-brain or managed-brain result through one contract."""
    if "semantic_design" in slide:
        plan = slide["semantic_design"]
    elif "semantic_design_path" in slide:
        path = Path(slide["semantic_design_path"])
        if not path.is_absolute() and base_dir is not None:
            path = (base_dir / path).resolve()
        else:
            path = path.resolve()
        plan = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(
            "No semantic design is available. Use build_semantic_planning_prompt() with the host Agent, "
            "then supply its semantic_design_path."
        )
    validation = validate_semantic_design(plan, slide)
    return {**plan, "contract_validation": validation}
