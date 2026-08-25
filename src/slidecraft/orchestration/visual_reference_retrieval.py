"""Metadata-first local visual-reference retrieval with diversity and a hard top-k cap."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _query_text(plan: dict[str, Any], deck: dict[str, Any]) -> str:
    relationships = " ".join(item["type"] for item in plan["semantic_relationships"])
    selected = next(item for item in plan["candidate_structures"] if item["id"] == plan["selected_structure_id"])
    style = deck["style"]
    return " ".join([
        plan["communication_archetype"],
        selected["archetype"],
        selected["description"],
        relationships,
        style["density"],
        style["visual_conventions"],
        style["diagram_conventions"],
        " ".join(style.get("brand_inspiration", {}).get("personality", [])),
    ])


def _load_manifest(location: Path) -> tuple[dict[str, Any], Path]:
    manifest_path = location / ".slidecraft-library.json" if location.is_dir() else location
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(manifest.get("items"), dict):
        normalized = []
        for relative_path, metadata in manifest["items"].items():
            tags = metadata.get("tags", [])
            normalized.append({
                "reference_id": "VISUAL_" + hashlib.sha256(relative_path.encode()).hexdigest()[:12].upper(),
                "path": relative_path,
                "name": metadata.get("name") or Path(relative_path).stem.replace("_", " ").title(),
                "description": metadata.get("description", ""),
                "slide_roles": metadata.get("semantic_roles", tags),
                "communication_archetypes": tags,
                "relationship_patterns": metadata.get("relationship_patterns", []),
                "content_density": metadata.get("content_density", "unspecified"),
                "structural_family": metadata.get("structural_family", Path(relative_path).stem),
                "style_tags": tags,
                "visual_traits": metadata.get("visual_traits", tags),
                "usage": "whole-page visual precedent only",
                "content_reuse_allowed": False,
            })
        manifest = {"schema_version": manifest.get("schema_version", "1.0.0"), "items": normalized}
    return manifest, manifest_path


def retrieve_visual_references(manifest_path: Path, plan: dict[str, Any], deck: dict[str, Any], max_results: int = 3) -> dict[str, Any]:
    if max_results < 1 or max_results > 3:
        raise ValueError("Visual-reference retrieval must return between one and three pages")
    manifest, manifest_path = _load_manifest(manifest_path)
    query = _query_text(plan, deck)
    query_tokens = _tokens(query)
    ranked = []
    for item in manifest["items"]:
        metadata_text = " ".join([
            item["name"], item["description"],
            " ".join(item["slide_roles"]),
            " ".join(item["communication_archetypes"]),
            " ".join(item["relationship_patterns"]),
            " ".join(item["style_tags"]),
            " ".join(item["visual_traits"]),
        ])
        overlap = sorted(query_tokens & _tokens(metadata_text))
        relationship_matches = sorted({rel["type"] for rel in plan["semantic_relationships"]} & set(item["relationship_patterns"]))
        score = 2.0 * len(overlap) + 5.0 * len(relationship_matches)
        ranked.append({**item, "semantic_score": score, "matched_terms": overlap, "matched_relationships": relationship_matches})
    ranked.sort(key=lambda item: (-item["semantic_score"], item["reference_id"]))

    selected = []
    used_families: set[str] = set()
    remaining = list(ranked)
    while remaining and len(selected) < max_results:
        for candidate in remaining:
            candidate["diversity_adjusted_score"] = candidate["semantic_score"] - (6.0 if candidate["structural_family"] in used_families else 0.0)
        remaining.sort(key=lambda item: (-item["diversity_adjusted_score"], item["reference_id"]))
        chosen = remaining.pop(0)
        used_families.add(chosen["structural_family"])
        path = (manifest_path.parent / chosen["path"]).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Visual reference is missing: {path}")
        selected.append({
            **chosen,
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "role": "retrieved_visual_reference_page",
            "must_not_be_copied_as_layout": True,
            "retrieval_reason": f"Matched semantic structure through {', '.join(chosen['matched_terms'][:8]) or 'library fallback'} and added structural-family diversity.",
        })
    return {
        "schema_version": "1.0.0",
        "provider_interface": "visual_reference_retriever_v1",
        "retrieval_mode": "metadata_first_semantic",
        "visual_files_opened_before_ranking": False,
        "query": query,
        "maximum_results": max_results,
        "selected": selected,
        "ranked_metadata": ranked,
    }
