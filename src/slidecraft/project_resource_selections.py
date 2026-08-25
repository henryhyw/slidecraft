"""Durable project assignments for reusable resources.

Agent retrieval and user choices share one passive project ledger. Workflow
artifacts keep lineage, while this ledger keeps the current project assignment
stable across artifact cleanup, project restoration, and application restarts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slidecraft.library_manager import list_library_items, resolve_library_item
from slidecraft.project_events import record_project_event
from slidecraft.projects import PROJECT_FILE

RESOURCE_FILE = Path(".slidecraft/resources/project_resources.json")
LEGACY_SELECTION_FILE = Path(".slidecraft/resources/project_resource_selections.json")
RESOURCE_LIBRARIES = {
    "icons": "icons",
    "components": "components",
    "visual_references": "visual_references",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root(location: str | Path) -> Path:
    root = Path(location).expanduser().resolve()
    if not (root / PROJECT_FILE).is_file():
        raise FileNotFoundError(f"No {PROJECT_FILE} exists at {root}")
    return root


def _empty() -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "resources": [],
        "exclusions": [],
        "reconciliation": {"legacy_scan_completed": False, "sources": []},
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _identity(item: dict[str, Any]) -> str:
    digest = item.get("content_sha256") or _digest(item.get("path") or item.get("canonical_file") or item.get("manifest_path"))
    if digest:
        return f"sha256:{digest}"
    library_id = item.get("library_item_id") or item.get("item_id")
    if library_id:
        return f"library:{library_id}"
    resource_id = item.get("resource_id") or item.get("asset_id") or item.get("reference_id") or item.get("component_id")
    return f"id:{resource_id}"


def _read(root: Path) -> dict[str, Any]:
    current = _read_json(root / RESOURCE_FILE)
    if current:
        current.setdefault("resources", [])
        current.setdefault("exclusions", [])
        current.setdefault("reconciliation", {"legacy_scan_completed": True, "sources": []})
        return current
    legacy = _read_json(root / LEGACY_SELECTION_FILE)
    if not legacy:
        return _empty()
    value = _empty()
    value["resources"] = [
        {
            **item,
            "assignment_origin": "user_selection",
            "active": True,
            "canonical_identity": _identity(item),
            "assigned_at": legacy.get("updated_at") or _now(),
            "updated_at": legacy.get("updated_at") or _now(),
        }
        for item in legacy.get("included", [])
    ]
    value["exclusions"] = [
        {"resource_id": resource_id, "canonical_identity": f"id:{resource_id}", "excluded_at": _now(), "actor": "legacy_migration"}
        for resource_id in legacy.get("excluded_resource_ids", [])
    ]
    value["reconciliation"]["sources"].append(str(root / LEGACY_SELECTION_FILE))
    return value


def _write(root: Path, value: dict[str, Any]) -> None:
    path = root / RESOURCE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    value["schema_version"] = "2.0.0"
    value["updated_at"] = _now()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _digest(path: str | Path | None) -> str | None:
    if not path:
        return None
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        return None
    return hashlib.sha256(candidate.read_bytes()).hexdigest()


def _library_match(category: str, item: dict[str, Any]) -> dict[str, Any] | None:
    library = list_library_items(RESOURCE_LIBRARIES[category])["items"]
    identifiers = {
        str(value).lower()
        for value in (
            item.get("library_item_id"), item.get("item_id"), item.get("library_icon_id"),
            item.get("resource_id"), item.get("asset_id"), item.get("reference_id"), item.get("component_id"),
        )
        if value
    }
    digest = _digest(item.get("path") or item.get("canonical_file") or item.get("manifest_path"))
    names = {
        Path(str(value)).stem.lower().replace("_", "-")
        for value in (item.get("path"), item.get("canonical_file"), item.get("manifest_path"), item.get("library_icon_id"))
        if value
    }
    for candidate in library:
        if candidate["item_id"].lower() in identifiers:
            return candidate
        if digest and _digest(candidate["path"]) == digest:
            return candidate
        candidate_names = {
            Path(candidate["path"]).stem.lower().replace("_", "-"),
            Path(candidate["filename"]).stem.lower().replace("_", "-"),
        }
        if names & candidate_names:
            return candidate
    return None


def _record(category: str, item: dict[str, Any], *, origin: str, source: str | None = None, slide_id: str | None = None) -> dict[str, Any]:
    matched = _library_match(category, item)
    if matched:
        resource_id = matched["item_id"]
        path = matched["path"]
        name = matched["name"]
        description = matched.get("description", "") or item.get("description", "")
        media_type = matched.get("media_type")
        library_item_id = matched["item_id"]
    else:
        resource_id = item.get("resource_id") or item.get("asset_id") or item.get("reference_id") or item.get("component_id")
        path = item.get("path") or item.get("canonical_file") or item.get("manifest_path")
        name = item.get("name") or item.get("library_icon_id") or resource_id
        description = item.get("description", "")
        media_type = item.get("media_type")
        library_item_id = item.get("library_item_id")
    if not resource_id:
        raise ValueError(f"Retrieved {category} resource has no stable identifier")
    common = {
        "resource_id": resource_id,
        "library_item_id": library_item_id,
        "name": name,
        "path": path,
        "description": description,
        "media_type": media_type,
        "category": category,
        "active": True,
        "assignment_origin": origin,
        "selection_mode": "user_selected" if origin == "user_selection" else "agent_retrieved",
        "provenance": item.get("provenance") or ("user_selected_from_library" if origin == "user_selection" else "agent_resource_retrieval"),
        "canonical_identity": _identity({**item, "path": path, "library_item_id": library_item_id, "resource_id": resource_id}),
        "source_records": [source] if source else [],
        "used_by_slide_ids": [slide_id] if slide_id else list(item.get("used_by_slide_ids", [])),
    }
    if category == "icons":
        return {
            **common,
            "kind": "canonical_icon",
            "library_icon_id": item.get("library_icon_id"),
            "requested_role": item.get("prompt_name") or item.get("requested_role"),
            "semantic_role": item.get("semantic_role"),
            "semantic_metadata_status": "ready" if item.get("semantic_role") else "needs_agent_description",
        }
    if category == "components":
        return {**common, "kind": "known_component", "manifest_path": path, "semantic_score": item.get("semantic_score")}
    return {
        **common,
        "kind": "visual_reference_page",
        "retrieval_reason": item.get("retrieval_reason", ""),
        "direct_use_allowed": False,
    }


def records_from_retrieval_payload(payload: dict[str, Any], *, source: str | None = None, slide_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
    result = {"visual_references": [], "icons": [], "components": []}
    selection = payload.get("agent_resource_selection", payload.get("resource_selection", {}))
    visual_items = selection.get("visual_references", payload.get("visual_references", payload.get("template_references", [])))
    for item in visual_items:
        result["visual_references"].append(_record("visual_references", item, origin="agent_retrieval", source=source, slide_id=slide_id))
    icon_items = selection.get("icons", payload.get("icon_retrieval", {}).get("assets", []))
    for item in icon_items:
        result["icons"].append(_record("icons", item, origin="agent_retrieval", source=source, slide_id=slide_id))
    component_items = selection.get("components", payload.get("known_component_retrieval", {}).get("selected", []))
    for item in component_items:
        result["components"].append(_record("components", item, origin="agent_retrieval", source=source, slide_id=slide_id))
    return result


def _upsert(ledger: dict[str, Any], record: dict[str, Any]) -> None:
    now = _now()
    existing = next((item for item in ledger["resources"] if item.get("canonical_identity") == record["canonical_identity"]), None)
    if existing:
        source_records = sorted({*existing.get("source_records", []), *record.get("source_records", [])})
        slide_ids = sorted({*existing.get("used_by_slide_ids", []), *record.get("used_by_slide_ids", [])})
        assigned_at = existing.get("assigned_at", now)
        existing.update({**record, "source_records": source_records, "used_by_slide_ids": slide_ids, "assigned_at": assigned_at, "updated_at": now})
    else:
        ledger["resources"].append({**record, "assigned_at": now, "updated_at": now})


def _is_excluded(ledger: dict[str, Any], record: dict[str, Any]) -> bool:
    return any(
        exclusion.get("canonical_identity") == record.get("canonical_identity")
        or exclusion.get("resource_id") == record.get("resource_id")
        for exclusion in ledger["exclusions"]
    )


def _ledger_counts(ledger: dict[str, Any]) -> dict[str, int]:
    return {
        category: sum(item.get("active", True) and item.get("category") == category for item in ledger["resources"])
        for category in RESOURCE_LIBRARIES
    }


def record_retrieved_project_resources(
    location: str | Path,
    payload_or_path: dict[str, Any] | str | Path,
    *,
    source: str | None = None,
    slide_id: str | None = None,
) -> dict[str, Any]:
    root = _root(location)
    if isinstance(payload_or_path, dict):
        payload = payload_or_path
    else:
        path = Path(payload_or_path).expanduser().resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = source or str(path)
    ledger = _read(root)
    records = records_from_retrieval_payload(payload, source=source, slide_id=slide_id)
    added = 0
    for category_records in records.values():
        for record in category_records:
            if _is_excluded(ledger, record):
                continue
            before = len(ledger["resources"])
            _upsert(ledger, record)
            added += len(ledger["resources"]) - before
    _write(root, ledger)
    return {"project_path": str(root), "added": added, "counts": _ledger_counts(ledger), "ledger_path": str(root / RESOURCE_FILE)}


def reconcile_project_resources(location: str | Path, *, include_legacy_outputs: bool = True) -> dict[str, Any]:
    root = _root(location)
    ledger = _read(root)
    sources: list[str] = []
    if include_legacy_outputs and not ledger["reconciliation"].get("legacy_scan_completed", False):
        candidates = sorted((root / "outputs").glob("**/reference_retrieval.json")) if (root / "outputs").is_dir() else []
        for path in candidates:
            payload = _read_json(path)
            if not payload:
                continue
            records = records_from_retrieval_payload(payload, source=str(path))
            for category_records in records.values():
                for record in category_records:
                    if not _is_excluded(ledger, record):
                        _upsert(ledger, record)
            sources.append(str(path))
        ledger["reconciliation"] = {
            "legacy_scan_completed": True,
            "completed_at": _now(),
            "sources": sorted({*ledger.get("reconciliation", {}).get("sources", []), *sources}),
        }
    _write(root, ledger)
    return {
        "status": "reconciled",
        "project_path": str(root),
        "ledger_path": str(root / RESOURCE_FILE),
        "counts": _ledger_counts(ledger),
        "legacy_sources_imported": len(sources),
    }


def ensure_project_resource_ledger(location: str | Path) -> dict[str, Any]:
    root = _root(location)
    if not (root / RESOURCE_FILE).exists():
        return reconcile_project_resources(root, include_legacy_outputs=True)
    return {"status": "ready", "project_path": str(root), "ledger_path": str(root / RESOURCE_FILE)}


def project_library_options(location: str | Path, category: str) -> dict[str, Any]:
    root = _root(location)
    ensure_project_resource_ledger(root)
    ledger = _read(root)
    selected = {
        item.get("library_item_id")
        for item in ledger["resources"]
        if item.get("active", True) and item.get("category") == category and item.get("library_item_id")
    }
    library = list_library_items(RESOURCE_LIBRARIES[category])
    return {
        "project_path": str(root),
        "category": category,
        "library": RESOURCE_LIBRARIES[category],
        "items": [{**item, "selected": item["item_id"] in selected} for item in library["items"]],
    }


def add_project_library_resource(
    location: str | Path,
    *,
    category: str,
    item_id: str,
    actor: str = "user_console",
) -> dict[str, Any]:
    root = _root(location)
    ensure_project_resource_ledger(root)
    item = resolve_library_item(RESOURCE_LIBRARIES[category], item_id)
    ledger = _read(root)
    record = _record(category, item, origin="user_selection", source="shared_library")
    ledger["exclusions"] = [
        value for value in ledger["exclusions"]
        if value.get("resource_id") != record["resource_id"] and value.get("canonical_identity") != record["canonical_identity"]
    ]
    _upsert(ledger, record)
    _write(root, ledger)
    record_project_event(
        root,
        event_type="project_resource_added",
        actor=actor,
        resource_id=record["resource_id"],
        changes={"category": category, "library": RESOURCE_LIBRARIES[category], "plan_changed": False},
    )
    return record


def remove_project_resource(
    location: str | Path,
    *,
    category: str,
    resource_id: str,
    actor: str = "user_console",
) -> dict[str, Any]:
    root = _root(location)
    if category not in RESOURCE_LIBRARIES:
        raise KeyError(category)
    ensure_project_resource_ledger(root)
    ledger = _read(root)
    record = next((item for item in ledger["resources"] if item.get("category") == category and item.get("resource_id") == resource_id), None)
    identity = record.get("canonical_identity") if record else f"id:{resource_id}"
    if record:
        record["active"] = False
        record["updated_at"] = _now()
    if not any(item.get("resource_id") == resource_id or item.get("canonical_identity") == identity for item in ledger["exclusions"]):
        ledger["exclusions"].append({
            "resource_id": resource_id,
            "canonical_identity": identity,
            "excluded_at": _now(),
            "actor": actor,
        })
    _write(root, ledger)
    record_project_event(
        root,
        event_type="project_resource_removed",
        actor=actor,
        resource_id=resource_id,
        changes={"category": category, "plan_changed": False},
    )
    return {"status": "removed", "category": category, "resource_id": resource_id}


def apply_project_resource_selections(
    location: str | Path,
    resources: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    root = _root(location)
    ensure_project_resource_ledger(root)
    ledger = _read(root)
    result = {category: [] for category in RESOURCE_LIBRARIES}
    for category, selected_resources in result.items():
        candidates: list[dict[str, Any]] = []
        for item in resources.get(category, []):
            candidates.append(_record(category, item, origin="agent_retrieval"))
        candidates.extend(
            item for item in ledger["resources"]
            if item.get("active", True) and item.get("category") == category
        )
        seen: set[str] = set()
        for item in candidates:
            identity = item.get("canonical_identity") or _identity(item)
            if identity in seen or _is_excluded(ledger, item):
                continue
            seen.add(identity)
            selected_resources.append(item)
    return result
