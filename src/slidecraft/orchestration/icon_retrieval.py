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
        normalized_name = record["icon_id"].replace("-", " ")
        if f" {normalized_name} " in f" {description.lower()} ":
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
    online_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return canonical icon candidates for Agent selection."""
    manifest, catalog = _load_catalog(library_root)
    excluded = excluded_semantic_roles or set()
    requests = asset_needs or []
    candidate_sets = []
    policy = online_policy or {}
    online_enabled = bool(policy.get("allow_online_retrieval", False))
    online_status: dict[str, Any] = {
        "enabled": online_enabled,
        "provider": policy.get("provider", "tabler"),
        "status": "disabled" if not online_enabled else "ready",
    }
    for request in requests:
        role = request["semantic_role"]
        if role in excluded:
            continue
        dimension_role = request.get("dimension_role", "module_icon")
        description = " ".join([request.get("purpose", ""), request.get("query", ""), " ".join(request.get("concepts", []))]).strip()
        candidates = [candidate for candidate in _rank(description, catalog) if candidate["score"] > 0][:12]
        records = []
        for candidate in candidates:
            asset_path = (library_root / candidate["file"]).resolve()
            if not asset_path.exists():
                continue
            records.append({
                **candidate,
                "asset_id": f"TABLER_OUTLINE_{candidate['icon_id'].upper().replace('-', '_')}",
                "canonical_file": str(asset_path),
                "provenance": "local_icon_collection",
            })
        if online_enabled:
            try:
                from slidecraft.orchestration.tabler_icons import retrieve_tabler_candidates

                remote = retrieve_tabler_candidates(
                    query=description,
                    library_root=library_root,
                    release=str(policy.get("release", "latest")),
                    limit=int(policy.get("max_online_candidates_per_role", 8)),
                )
                online_status.update(status="ready", release=remote["release"], source=remote["source"])
                by_asset_id = {item["asset_id"]: item for item in records}
                for candidate in remote["candidates"]:
                    by_asset_id[candidate["asset_id"]] = candidate
                records = sorted(by_asset_id.values(), key=lambda item: (-item["score"], item["icon_id"]))
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
                online_status.update(status="unavailable", reason=str(error))
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
        "search_scope": "local_and_online" if online_enabled else "local_only",
        "online_retrieval": online_status,
        "candidate_sets": candidate_sets,
    }
