"""Semantic retrieval over local known-component manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _tokens(value: str) -> set[str]:
    stopwords = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is", "it", "of", "on", "or", "the", "to", "use", "uses", "with"}
    return set(re.findall(r"[a-z0-9]+", value.lower())) - stopwords


def retrieve_known_components(library_root: Path, semantic_design: dict[str, Any], max_results: int = 5) -> dict[str, Any]:
    query = " ".join(
        [semantic_design["main_message"], semantic_design["communication_archetype"]]
        + [unit.get("meaning", "") + " " + unit["role"] for unit in semantic_design["semantic_units"]]
        + [relationship["type"] + " " + relationship.get("meaning", "") for relationship in semantic_design["semantic_relationships"]]
    )
    query_tokens = _tokens(query)
    candidates = []
    for manifest_path in sorted(library_root.rglob("*.component.json")):
        item = json.loads(manifest_path.read_text(encoding="utf-8"))
        semantic = item["semantic"]
        metadata = " ".join([
            item["name"], item.get("description", ""),
            " ".join(semantic["roles"]),
            " ".join(semantic["concepts"]),
            " ".join(semantic.get("aliases", [])),
            " ".join(semantic.get("required_parts", [])),
            " ".join(semantic.get("relationship_types", [])),
        ])
        overlap = sorted(query_tokens & _tokens(metadata))
        normalized_score = min(1.0, len(overlap) / max(4, len(set(semantic["concepts"]))))
        implementation = item["implementation"]
        source = implementation.get("source")
        implementation_path = (manifest_path.parent / source).resolve() if source else None
        implementation_available = bool(implementation_path and implementation_path.is_file())
        # Component manifests remain useful retrieval evidence before their
        # editable implementation route is certified by the constructor.
        runtime_supported = False
        confidence_met = normalized_score >= item["recognition"]["minimum_confidence"]
        candidates.append({
            "component_id": item["component_id"],
            "version": item["version"],
            "manifest_path": str(manifest_path.resolve()),
            "implementation": implementation,
            "implementation_path": str(implementation_path) if implementation_path else None,
            "implementation_available": implementation_available,
            "runtime_supported": runtime_supported,
            "semantic_score": round(normalized_score, 4),
            "minimum_confidence": item["recognition"]["minimum_confidence"],
            "matched_terms": overlap,
            "confidence_met": confidence_met,
            "selected": confidence_met and implementation_available and runtime_supported,
            "fallback_route": "standard_reconstruction" if confidence_met else None,
        })
    candidates.sort(key=lambda item: (-item["semantic_score"], item["component_id"]))
    return {
        "schema_version": "1.0.0",
        "provider_interface": "known_component_retriever_v1",
        "retrieval_mode": "semantic_metadata_first",
        "query": query,
        "selected": [item for item in candidates if item["selected"]][:max_results],
        "candidates": candidates[:max_results],
        "scene_requery_policy": "Requery with entity-level semantic roles, parts, topology, text bindings, and measured aspect ratio after the generated image is understood.",
    }
