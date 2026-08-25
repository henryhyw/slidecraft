"""Mechanical normalization of Agent-authored deck evidence and provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(value: str, base_dir: Path) -> Path:
    candidate = Path(value).expanduser()
    path = candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _material_record(material: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    if not material.get("material_id"):
        raise ValueError("Every material requires a material_id")
    if not material.get("modality"):
        raise ValueError(f"Material {material['material_id']} requires a modality")
    path = _resolve_path(material["path"], base_dir) if material.get("path") else None
    if path is None and "content" not in material:
        raise ValueError(f"Material {material['material_id']} has no path or Agent-authored content")
    return {
        **material,
        "path": str(path) if path else None,
        "sha256": _hash(path) if path else None,
        "size_bytes": path.stat().st_size if path else None,
        "agent_content_present": "content" in material,
    }


def _atoms_from_agent_content(material: dict[str, Any]) -> list[dict[str, Any]]:
    if "content" not in material:
        return []
    content = material["content"]
    values = content if isinstance(content, list) else [content]
    authority = material.get("authority", "supporting_evidence")
    if authority == "supporting":
        authority = "supporting_evidence"
    return [
        {
            "atom_id": f"{material['material_id']}_ATOM_{index:03d}",
            "material_id": material["material_id"],
            "locator": f"agent_content:{index}",
            "modality": material["modality"],
            "value": value,
            "authority": authority,
            "required_usage": bool(material.get("required_usage", False)),
            "provenance": material.get("provenance", "agent_authored_from_source"),
        }
        for index, value in enumerate(values, start=1)
    ]


def _normalize_authored_atoms(
    authored_atoms: list[dict[str, Any]],
    materials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for atom in authored_atoms:
        required = {"atom_id", "material_id", "locator", "modality", "value", "authority", "required_usage"}
        missing = sorted(required - set(atom))
        if missing:
            raise ValueError(f"Agent-authored source atom is missing fields: {missing}")
        atom_id = atom["atom_id"]
        if atom_id in seen:
            raise ValueError(f"Duplicate source atom ID: {atom_id}")
        if atom["material_id"] not in materials and atom["material_id"] != "USER_CLARIFICATIONS":
            raise ValueError(f"Source atom {atom_id} refers to unknown material {atom['material_id']}")
        if atom["authority"] not in {"authoritative", "supporting_evidence", "intent_evidence"}:
            raise ValueError(f"Source atom {atom_id} has unsupported authority {atom['authority']!r}")
        seen.add(atom_id)
        normalized.append({
            **atom,
            "required_usage": bool(atom["required_usage"]),
            "provenance": atom.get("provenance", "agent_authored_from_source"),
        })
    return normalized


def _normalize_constraints(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    for index, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise TypeError("Constraints must be Agent-authored records with explicit text and strength")
        if not value.get("text") or not value.get("strength"):
            raise ValueError("Every constraint requires Agent-authored text and strength")
        constraints.append({
            **value,
            "constraint_id": value.get("constraint_id", f"DECK_CONSTRAINT_{index:03d}"),
            "target": value.get("target", "deck"),
            "status": value.get("status", "active"),
            "classification_source": value.get("classification_source", "agent_reasoning"),
        })
    return constraints


def normalize_deck_intake(request: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Record files and normalize decisions already authored by the host Agent.

    This function never opens a source to interpret its contents. The host Agent
    reads the materials, decides what they mean, and supplies source atoms,
    authority, required usage, exclusions, and constraint classifications.
    """

    material_records = [_material_record(material, base_dir) for material in request.get("materials", [])]
    materials_by_id = {material["material_id"]: material for material in material_records}
    if len(materials_by_id) != len(material_records):
        raise ValueError("Material IDs must be unique")

    explicit_atoms = request.get("source_atoms")
    if explicit_atoms is not None:
        atoms = _normalize_authored_atoms(explicit_atoms, materials_by_id)
    else:
        generated = [atom for material in material_records for atom in _atoms_from_agent_content(material)]
        atoms = _normalize_authored_atoms(generated, materials_by_id)

    constraints = _normalize_constraints(request.get("constraints", []))
    return {
        "schema_version": "1.0.0",
        "deck_id": request["deck_id"],
        "source_atoms": atoms,
        "materials": material_records,
        "constraint_register": constraints,
        "hard_constraint_ids": [
            item["constraint_id"]
            for item in constraints
            if item["strength"] == "hard" and item["status"] == "active"
        ],
        "quality": {
            "material_count": len(material_records),
            "source_atom_count": len(atoms),
            "authoritative_source_atom_count": sum(atom["authority"] == "authoritative" for atom in atoms),
            "required_source_atom_count": sum(bool(atom["required_usage"]) for atom in atoms),
            "materials_with_agent_content": sum(bool(material["agent_content_present"]) for material in material_records),
            "path_only_material_count": sum(not material["agent_content_present"] for material in material_records),
        },
    }
