"""Multimodal intake normalization, constraint register, and source traceability."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

HARD_PREFIXES = (
    "must ",
    "use ",
    "show ",
    "keep ",
    "include ",
    "do not ",
    "don't ",
    "never ",
    "require ",
    "required ",
    "i want ",
    "we want ",
)
SOFT_MARKERS = ("prefer", "ideally", "if possible", "would like", "could", "maybe")


def _walk(value: Any, path: str) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")
    else:
        yield path, value


def _constraint_category(text: str) -> str:
    lowered = text.lower()
    categories = {
        "content_form": ("table", "chart", "map", "timeline", "matrix", "diagram"),
        "layout": ("layout", "left", "right", "column", "row", "position", "stage", "flow"),
        "asset": ("asset", "icon", "logo", "image", "photo"),
        "typography": ("font", "title", "text", "typeface"),
        "style": ("style", "color", "brand", "pwc", "visual"),
        "deck_chrome": ("header", "footer", "page number", "confidential"),
        "content_fidelity": ("exact", "do not paraphrase", "wording", "content"),
    }
    for category, markers in categories.items():
        if any(marker in lowered for marker in markers):
            return category
    return "general"


def _constraint_strength(text: str) -> tuple[str, float]:
    lowered = text.strip().lower()
    if lowered.startswith(HARD_PREFIXES) or any(marker in lowered for marker in ("must", "mandatory", "required", "do not", "never")):
        return "hard", 0.94
    if any(marker in lowered for marker in SOFT_MARKERS):
        return "preference", 0.82
    return "soft", 0.72


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
        "extraction_status": "inline" if "content" in material else "pending_adapter",
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
    for index, (path, value) in enumerate(_walk(slide["exact_content"], "exact_content"), start=1):
        source_atoms.append({
            "atom_id": f"SOURCE_{index:03d}",
            "source_path": path,
            "modality": "structured_text",
            "value": value,
            "authority": "authoritative",
            "citation": {"material_id": "SLIDE_EXACT_CONTENT", "locator": path},
        })

    for index, note in enumerate(slide.get("user_notes", []), start=1):
        source_atoms.append({
            "atom_id": f"NOTE_{index:03d}",
            "source_path": f"user_notes[{index - 1}]",
            "modality": "text",
            "value": note,
            "authority": "intent_evidence",
            "citation": {"material_id": "USER_NOTES", "locator": f"note:{index}"},
        })

    constraints = []
    raw_constraints = slide.get("explicit_human_constraints", [])
    for index, raw in enumerate(raw_constraints, start=1):
        if isinstance(raw, str):
            strength, confidence = _constraint_strength(raw)
            record = {
                "constraint_id": f"CONSTRAINT_{index:03d}",
                "text": raw,
                "strength": strength,
                "category": _constraint_category(raw),
                "target": "slide",
                "source": f"explicit_human_constraints[{index - 1}]",
                "confidence": confidence,
                "status": "active",
            }
        else:
            record = {
                "constraint_id": raw.get("constraint_id", f"CONSTRAINT_{index:03d}"),
                "text": raw["text"],
                "strength": raw.get("strength", "hard"),
                "category": raw.get("category", _constraint_category(raw["text"])),
                "target": raw.get("target", "slide"),
                "source": raw.get("source", f"explicit_human_constraints[{index - 1}]"),
                "confidence": float(raw.get("confidence", 1.0)),
                "status": raw.get("status", "active"),
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
            "extraction_status": "canonical_asset_ready",
            "content": None,
            "provenance": "user_upload",
            "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest() if resolved.exists() else None,
            "size_bytes": resolved.stat().st_size if resolved.exists() else None,
        })

    unresolved = [item["constraint_id"] for item in constraints if item["confidence"] < 0.75]
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
    return f"""Normalize multimodal slide input into authoritative source atoms, supporting evidence, assets, and constraints.

SLIDE REQUEST
{json.dumps(slide, indent=2, ensure_ascii=False)}

EXTRACTED MATERIAL MANIFEST
{json.dumps(material_manifest, indent=2, ensure_ascii=False)}

Classify every instruction as hard, soft, or preference. Preserve its source locator. Hard constraints include explicit required content forms, mandatory assets, prohibited treatments, exact wording, and explicit layout requirements. Detect conflicts and ambiguities. Do not silently weaken a hard constraint. Return a validated intake manifest.
"""
