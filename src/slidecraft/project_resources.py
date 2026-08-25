"""Derived project resource view over authoritative project artifacts and folders."""

from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any

from slidecraft.library_manager import list_library_items
from slidecraft.project_assets import list_project_assets
from slidecraft.project_resource_selections import apply_project_resource_selections
from slidecraft.projects import project_manifest_path
from slidecraft.runtime.artifacts import ArtifactWorkspace


def _read_json(path: str | Path) -> dict[str, Any] | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _file_resource(path: Path, root: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "resource_id": f"FILE_{digest[:12].upper()}",
        "name": path.name,
        "kind": "source_file",
        "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "path": str(path),
        "project_relative_path": str(path.relative_to(root)),
        "sha256": digest,
        "provenance": "project_materials_folder",
    }


def _active_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    try:
        inspection = ArtifactWorkspace(root).inspect()
    except FileNotFoundError:
        return {}
    return {item["logical_key"]: item for item in inspection["active_artifacts"] if item["freshness"]["fresh"]}


def _source_materials(root: Path, active: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    source_root = root / "materials"
    if source_root.is_dir():
        for path in sorted(source_root.rglob("*")):
            if path.is_file():
                records.append(_file_resource(path, root))
    clarification_artifact = active.get("deck/clarification_answers")
    clarifications = _read_json(clarification_artifact["path"]) if clarification_artifact else None
    if clarifications:
        known = {item["resource_id"] for item in records}
        for answer in clarifications.get("answers", []):
            if answer.get("resolution") != "user_answered":
                continue
            resource_id = f"USER_{answer['question_id']}"
            if resource_id not in known:
                records.append({
                    "resource_id": resource_id,
                    "name": answer.get("impact_dimension", "User decision").replace("_", " "),
                    "kind": "user_statement",
                    "value": answer.get("answer"),
                    "authority": "authoritative",
                    "provenance": "user_clarification",
                    "locator": answer["question_id"],
                })
    return records


def _deliverables(root: Path, active: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    deliverables_root = root / "deliverables"
    final_path = Path(active["deck/editable_pptx"]["path"]).resolve() if "deck/editable_pptx" in active else None
    if deliverables_root.is_dir():
        for path in sorted(deliverables_root.rglob("*")):
            if path.is_file() and not path.name.startswith((".", "~$")):
                record = _file_resource(path, root)
                record.update(kind="deliverable", provenance="project_deliverables")
                if path.suffix.lower() == ".pptx":
                    if final_path and path.resolve() == final_path:
                        record["presentation_role"] = "final"
                    elif path.parent == deliverables_root and path.name == "current_deck.pptx":
                        record["presentation_role"] = "current_progress"
                    elif path.parent == deliverables_root / "slides":
                        record["presentation_role"] = "individual_slide"
                    else:
                        record["presentation_role"] = "archived_output"
                records.append(record)
    return records


def _internal_evidence_summary(active: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Summarize normalized evidence without exposing engineering records in the user catalog."""
    intake_artifact = active.get("deck/intake")
    intake = _read_json(intake_artifact["path"]) if intake_artifact else None
    atoms = intake.get("source_atoms", []) if intake else []
    return {
        "normalized_source_item_count": len(atoms),
        "available_to_agent": bool(atoms),
        "user_visible": False,
    }


def _retrieved_resources(active: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result = {"visual_references": [], "icons": [], "components": []}
    retrieval_artifacts = [item for item in active.values() if item["kind"] == "reference_retrieval"]
    seen = {key: set() for key in result}
    for artifact in retrieval_artifacts:
        value = _read_json(artifact["path"])
        if not value:
            continue
        selection = value.get("agent_resource_selection", value.get("resource_selection", {}))
        visual_items = selection.get("visual_references", value.get("visual_references", value.get("template_references", [])))
        for item in visual_items:
            resource_id = item.get("reference_id")
            if resource_id and resource_id not in seen["visual_references"]:
                result["visual_references"].append({
                    "resource_id": resource_id,
                    "name": item.get("name", resource_id),
                    "kind": "visual_reference_page",
                    "path": item.get("path"),
                    "description": item.get("description", ""),
                    "retrieval_reason": item.get("retrieval_reason", ""),
                    "direct_use_allowed": False,
                    "provenance": "visual_reference_library_retrieval",
                })
                seen["visual_references"].add(resource_id)
        icon_items = selection.get("icons", value.get("icon_retrieval", {}).get("assets", []))
        for item in icon_items:
            resource_id = item.get("asset_id")
            if resource_id and resource_id not in seen["icons"]:
                result["icons"].append({
                    "resource_id": resource_id,
                    "name": item.get("library_icon_id", resource_id).replace("-", " ").replace("_", " ").title(),
                    "kind": "canonical_icon",
                    "library_icon_id": item.get("library_icon_id"),
                    "requested_role": item.get("prompt_name"),
                    "semantic_role": item.get("semantic_role"),
                    "path": item.get("canonical_file"),
                    "selection_mode": item.get("selection_mode"),
                    "provenance": item.get("library", "icon_library_retrieval"),
                })
                seen["icons"].add(resource_id)
        component_items = selection.get("components", value.get("known_component_retrieval", {}).get("selected", []))
        for item in component_items:
            resource_id = item.get("component_id")
            if resource_id and resource_id not in seen["components"]:
                result["components"].append({
                    "resource_id": resource_id,
                    "name": resource_id,
                    "kind": "known_component",
                    "path": item.get("manifest_path"),
                    "semantic_score": item.get("semantic_score"),
                    "provenance": "known_component_library_retrieval",
                })
                seen["components"].add(resource_id)
    return result


def project_resource_catalog(location: str | Path) -> dict[str, Any]:
    root = Path(location).expanduser().resolve()
    project_manifest_path(root)
    active = _active_artifacts(root)
    retrieved = apply_project_resource_selections(root, _retrieved_resources(active))
    categories = {
        "deliverables": _deliverables(root, active),
        "materials": _source_materials(root, active),
        "visual_assets": list_project_assets(root, sync_folder=True)["assets"],
        **retrieved,
    }
    usage: dict[str, list[str]] = {}
    plan_artifact = active.get("deck/plan")
    plan = _read_json(plan_artifact["path"]) if plan_artifact else None
    if plan:
        for slide in plan.get("slides", []):
            for resource_id in [
                *slide.get("source_atom_ids", []),
                *(item["asset_id"] for item in slide.get("asset_allocations", [])),
            ]:
                usage.setdefault(resource_id, []).append(slide["slide_id"])
    for records in categories.values():
        for record in records:
            record["used_by_slide_ids"] = sorted(set(usage.get(record.get("resource_id"), [])))
    return {
        "schema_version": "1.0.0",
        "project_path": str(root),
        "categories": categories,
        "counts": {key: len(value) for key, value in categories.items()},
        "shared_availability": {
            category: list_library_items(category)["item_count"]
            for category in ("visual_references", "icons", "components")
        },
        "internal_evidence": _internal_evidence_summary(active),
        "traceability": "Slides cite source atoms and selected canonical resource IDs. Retrieved resources retain library provenance.",
    }


def resolve_project_resource(location: str | Path, resource_id: str) -> dict[str, Any]:
    """Resolve a previewable resource by catalog ID without accepting an arbitrary file path."""
    catalog = project_resource_catalog(location)
    for category, records in catalog["categories"].items():
        for record in records:
            identifier = record.get("resource_id") or record.get("asset_id")
            if identifier == resource_id:
                path = record.get("path") or record.get("stored_path")
                if not path:
                    raise FileNotFoundError(f"{resource_id} has no previewable file")
                resolved = Path(path).expanduser().resolve()
                if not resolved.is_file():
                    raise FileNotFoundError(resolved)
                return {**record, "category": category, "resolved_path": str(resolved)}
    raise KeyError(resource_id)
