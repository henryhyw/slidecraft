"""Load and resolve inheritable communication guidance profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _merge(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            merged[key] = _merge(merged[key], value) if key in merged else value
        return merged
    if isinstance(base, list) and isinstance(overlay, list):
        result = list(base)
        for item in overlay:
            if item not in result:
                result.append(item)
        return result
    return overlay


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_guidance_profile(profile_path: Path, profile_root: Path | None = None) -> dict[str, Any]:
    profile_path = profile_path.resolve()
    root = (profile_root or profile_path.parent).resolve()
    profile = _load(profile_path)
    lineage = [profile["profile_id"]]
    seen = {profile["profile_id"]}
    current = profile
    resolved = profile
    while current.get("extends"):
        parent_id = current["extends"]
        if parent_id in seen:
            raise ValueError(f"Guidance profile inheritance cycle: {parent_id}")
        seen.add(parent_id)
        parent_path = root / f"{parent_id}.json"
        if not parent_path.exists():
            raise FileNotFoundError(f"Parent guidance profile is missing: {parent_path}")
        parent = _load(parent_path)
        lineage.append(parent_id)
        resolved = _merge(parent, resolved)
        current = parent
    resolved["resolution"] = {
        "selected_profile_path": str(profile_path),
        "lineage_child_to_parent": lineage,
        "merge_policy": "recursive dictionaries and de-duplicated ordered lists",
    }
    return resolved


def guidance_prompt_section(profile: dict[str, Any]) -> str:
    public = {key: value for key, value in profile.items() if key != "resolution"}
    return json.dumps(public, indent=2, ensure_ascii=False)
