"""Mechanical normalization of Agent-authored slide evidence and traceability."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _walk(value: Any, path: str) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")
    else:
        yield path, value


def _material_record(material: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    path_value = material.get("path")
    path = (base_dir / path_value).resolve() if path_value and not Path(path_value).is_absolute() else Path(path_value).resolve() if path_value else None
    record = {
        "material_id": material["material_id"],
        "modality": material["modality"],
        "role": material.get("role", "supporting_evidence"),
        "description": material.get("description", ""),
        "authority": material.get("authority", "supporting"),
        "required_usage": bool(material.get("required_usage", False)),
        "path": str(path) if path else None,
        "agent_content_present": "content" in material,
        "content": material.get("content"),
        "provenance": material.get("provenance", "user_upload"),
    }
    if path:
        if not path.exists():
            raise FileNotFoundError(f"Input material is missing: {path}")
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        record["size_bytes"] = path.stat().st_size
    return record


def normalize_intake(slide: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    source_atoms = []
    for atom in slide.get("source_atoms", []):
        locator = atom.get("locator") or atom.get("source_path")
        material_id = atom.get("material_id") or atom.get("citation", {}).get("material_id")
        if not locator or not material_id or "authority" not in atom or "required_usage" not in atom:
            raise ValueError(
                "Agent-authored source atoms require a material reference, locator, authority, and required_usage"
            )
        source_atoms.append({
            **atom,
            "source_path": atom.get("source_path", locator),
            "citation": atom.get("citation", {"material_id": material_id, "locator": locator}),
            "provenance": atom.get("provenance", "agent_authored_from_source"),
        })
    if not source_atoms:
        for index, (path, value) in enumerate(_walk(slide["exact_content"], "exact_content"), start=1):
            source_atoms.append({
                "atom_id": f"SOURCE_{index:03d}",
                "source_path": path,
                "modality": "structured_text",
                "value": value,
                "authority": "authoritative",
                "required_usage": True,
                "citation": {"material_id": "SLIDE_EXACT_CONTENT", "locator": path},
                "provenance": "agent_authored_exact_content",
            })

        for index, note in enumerate(slide.get("user_notes", []), start=1):
            source_atoms.append({
                "atom_id": f"NOTE_{index:03d}",
                "source_path": f"user_notes[{index - 1}]",
                "modality": "text",
                "value": note,
                "authority": "intent_evidence",
                "required_usage": False,
                "citation": {"material_id": "USER_NOTES", "locator": f"note:{index}"},
                "provenance": "agent_authored_user_intent",
            })

    constraints = []
    raw_constraints = slide.get("explicit_human_constraints", [])
    for index, raw in enumerate(raw_constraints, start=1):
        if not isinstance(raw, dict) or not raw.get("text") or not raw.get("strength"):
            raise TypeError("Slide constraints require Agent-authored text and strength")
        record = {
            **raw,
            "constraint_id": raw.get("constraint_id", f"CONSTRAINT_{index:03d}"),
            "category": raw.get("category", "general"),
            "target": raw.get("target", "slide"),
            "source": raw.get("source", f"explicit_human_constraints[{index - 1}]"),
            "confidence": float(raw.get("confidence", 1.0)),
            "status": raw.get("status", "active"),
            "classification_source": raw.get("classification_source", "agent_reasoning"),
        }
        constraints.append(record)

    materials = [_material_record(material, base_dir) for material in slide.get("materials", [])]
    for asset in slide.get("user_provided_assets", []):
        path = Path(asset["canonical_file"])
        resolved = (base_dir.parent / path).resolve() if not path.is_absolute() else path.resolve()
        if not resolved.exists():
            resolved = (Path.cwd() / path).resolve()
        materials.append({
            "material_id": asset["asset_id"],
            "modality": "canonical_asset",
            "role": asset["semantic_role"],
            "description": asset["description"],
            "authority": "authoritative_asset",
            "required_usage": bool(asset.get("mandatory", asset.get("required_usage", False))),
            "path": str(resolved),
            "agent_content_present": False,
            "content": None,
            "provenance": "user_upload",
            "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest() if resolved.exists() else None,
            "size_bytes": resolved.stat().st_size if resolved.exists() else None,
        })

    unresolved = [item["constraint_id"] for item in constraints if item["status"] == "needs_resolution"]
    return {
        "schema_version": "1.0.0",
        "slide_id": slide["slide_id"],
        "objective": slide["objective"],
        "source_atoms": source_atoms,
        "constraint_register": constraints,
        "materials": materials,
        "conflict_register": [],
        "unresolved_constraint_ids": unresolved,
        "hard_constraint_ids": [item["constraint_id"] for item in constraints if item["strength"] == "hard"],
        "quality": {
            "authoritative_source_atom_count": sum(item["authority"] == "authoritative" for item in source_atoms),
            "material_count": len(materials),
            "hard_constraint_count": sum(item["strength"] == "hard" for item in constraints),
            "requires_user_resolution": bool(unresolved),
        },
    }


def build_multimodal_intake_prompt(slide: dict[str, Any], material_manifest: list[dict[str, Any]]) -> str:
    return f"""Read the slide materials and author the evidence needed for slide planning.

SLIDE REQUEST
{json.dumps(slide, indent=2, ensure_ascii=False)}

MATERIAL FILES AND PROVENANCE
{json.dumps(material_manifest, indent=2, ensure_ascii=False)}

Use your document, data, and visual understanding to identify relevant source facts and exact content. Preserve stable source locators. Decide authority, required use, supporting evidence, exclusions, and whether the material supports credible planning. Classify user instructions as hard constraints, soft constraints, or preferences. Record conflicts that require user resolution. Return the Agent-authored intake manifest.
"""
