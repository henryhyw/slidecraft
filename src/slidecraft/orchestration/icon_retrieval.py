"""Replaceable icon retrieval with a swappable canonical-library boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _load_catalog(library_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = library_root / "semantic_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        catalog = list(manifest["items"])
    else:
        manifest = {"schema_version": "1.0.0", "provider": "Local icon collection", "style_family": "mixed"}
        catalog = []
    metadata_path = library_root / ".slidecraft-library.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")).get("items", {}) if metadata_path.exists() else {}
    known_files = {item["file"] for item in catalog}
    for path in sorted(library_root.rglob("*.svg")):
        relative = str(path.relative_to(library_root))
        if relative in known_files:
            continue
        details = metadata.get(relative, {})
        icon_id = path.stem
        concepts = details.get("tags", []) + re.findall(r"[a-z0-9]+", icon_id.lower())
        catalog.append({
            "icon_id": icon_id,
            "file": relative,
            "description": details.get("description") or details.get("name") or icon_id.replace("-", " "),
            "concepts": sorted(set(concepts)),
        })
    manifest["items"] = catalog
    return manifest, catalog


def _rank(description: str, catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requested = _tokens(description)
    ranked = []
    for record in catalog:
        overlap = requested & set(record["concepts"])
        score = 4 * len(overlap)
        if record["icon_id"].replace("-", " ") in description.lower():
            score += 12
        ranked.append({
            "icon_id": record["icon_id"],
            "score": score,
            "matched_concepts": sorted(overlap),
            "description": record["description"],
            "file": record["file"],
        })
    return sorted(ranked, key=lambda item: (-item["score"], item["icon_id"]))


def retrieve_icons(
    library_root: Path,
    asset_needs: list[dict[str, Any]] | None = None,
    excluded_semantic_roles: set[str] | None = None,
) -> dict[str, Any]:
    """Select a distinct, coherent set and retain stable canonical SVG paths."""
    manifest, catalog = _load_catalog(library_root)
    excluded = excluded_semantic_roles or set()
    requests = asset_needs or []
    used: set[str] = set()
    selections = []
    for request in requests:
        role = request["semantic_role"]
        if role in excluded:
            continue
        dimension_role = request.get("dimension_role", "module_icon")
        description = " ".join([request.get("purpose", ""), request.get("query", ""), " ".join(request.get("concepts", []))]).strip()
        candidates = _rank(description, catalog)
        selected = next((item for item in candidates if item["icon_id"] not in used and item["score"] > 0), candidates[0])
        used.add(selected["icon_id"])
        asset_path = (library_root / selected["file"]).resolve()
        if not asset_path.exists():
            raise FileNotFoundError(f"Canonical icon is missing: {asset_path}")
        selections.append({
            "asset_id": f"TABLER_OUTLINE_{selected['icon_id'].upper().replace('-', '_')}",
            "semantic_role": role,
            "semantic_intent": description,
            "dimension_role": dimension_role,
            "selection_mode": "set_level_substitution" if len(requests) > 1 else "individual_substitution",
            "library": "Tabler Icons Outline",
            "library_icon_id": selected["icon_id"],
            "canonical_file": str(asset_path),
            "prompt_name": role.replace("_", " ").title(),
            "prompt_description": selected["description"],
            "required_usage": request.get("requirement") == "mandatory",
            "alternative_candidates": [
                {"library_icon_id": item["icon_id"], "score": item["score"], "matched_concepts": item["matched_concepts"]}
                for item in candidates
                if item["icon_id"] != selected["icon_id"]
            ][:3],
        })
    return {
        "provider": "tabler_outline_local_semantic_index",
        "provider_interface": "canonical_icon_retriever_v1",
        "manifest": str((library_root / "semantic_manifest.json").resolve()),
        "retrieval_mode": "semantic_metadata_first",
        "style_family": manifest["style_family"],
        "selection_policy": {
            "exact_upstream_asset_first": True,
            "fallback": "joint coherent set selection",
            "preserve_canonical_id_and_file": True,
        },
        "assets": selections,
    }
