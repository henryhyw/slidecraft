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


def search_icons(
    library_root: Path,
    asset_needs: list[dict[str, Any]] | None = None,
    excluded_semantic_roles: set[str] | None = None,
) -> dict[str, Any]:
    """Return canonical icon candidates for Agent selection."""
    manifest, catalog = _load_catalog(library_root)
    excluded = excluded_semantic_roles or set()
    requests = asset_needs or []
    candidate_sets = []
    for request in requests:
        role = request["semantic_role"]
        if role in excluded:
            continue
        dimension_role = request.get("dimension_role", "module_icon")
        description = " ".join([request.get("purpose", ""), request.get("query", ""), " ".join(request.get("concepts", []))]).strip()
        candidates = _rank(description, catalog)
        records = []
        for candidate in candidates:
            asset_path = (library_root / candidate["file"]).resolve()
            if not asset_path.exists():
                continue
            records.append({
                **candidate,
                "asset_id": f"TABLER_OUTLINE_{candidate['icon_id'].upper().replace('-', '_')}",
                "canonical_file": str(asset_path),
            })
        candidate_sets.append({
            "semantic_role": role,
            "semantic_intent": description,
            "dimension_role": dimension_role,
            "required_usage": request.get("requirement") == "mandatory",
            "candidates": records,
        })
    return {
        "provider": "tabler_outline_local_semantic_index",
        "provider_interface": "canonical_icon_search_v1",
        "manifest": str((library_root / "semantic_manifest.json").resolve()),
        "retrieval_mode": "semantic_metadata_first",
        "style_family": manifest["style_family"],
        "decision_owner": "host_agent",
        "candidate_sets": candidate_sets,
    }
