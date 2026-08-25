"""User-selected project workspaces and the local project registry."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from slidecraft.configuration import data_root
from slidecraft.runtime.artifacts import ArtifactWorkspace

PROJECT_FILE = ".slidecraft/project.json"
LEGACY_PROJECT_FILE = "slidecraft.project.json"
REGISTRY_FILE = "project_registry.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip()).strip("-").lower()
    return normalized or f"project-{uuid.uuid4().hex[:8]}"


def registry_path() -> Path:
    return data_root() / REGISTRY_FILE


def _read_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return {"schema_version": "1.0.0", "projects": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_registry(value: dict[str, Any]) -> None:
    value["updated_at"] = _now()
    _atomic_write(registry_path(), value)


def _existing_manifest(root: Path) -> Path | None:
    current = root / PROJECT_FILE
    if current.is_file():
        return current
    legacy = root / LEGACY_PROJECT_FILE
    return legacy if legacy.is_file() else None


def _unique_destination(path: Path, payload: bytes) -> Path:
    if not path.exists() or path.read_bytes() == payload:
        return path
    digest = hashlib.sha256(payload).hexdigest()[:8]
    return path.with_name(f"{path.stem}_{digest}{path.suffix}")


def _rewrite_internal_paths(root: Path, replacements: dict[str, str]) -> None:
    if not replacements:
        return

    def rewrite(value: object) -> object:
        if isinstance(value, str):
            return replacements.get(value, value)
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        return value

    for path in (root / ".slidecraft").rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        updated = rewrite(value)
        if updated != value:
            _atomic_write(path, updated)


def _ensure_visible_project_layout(root: Path) -> None:
    """Keep user files visible and engineering state under .slidecraft."""
    assets = root / "assets"
    materials = root / "materials"
    deliverables = root / "deliverables"
    for directory in (assets, materials, deliverables):
        directory.mkdir(parents=True, exist_ok=True)
    legacy_sources = root / "sources"
    replacements: dict[str, str] = {}
    if legacy_sources.is_dir():
        for source in sorted(legacy_sources.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(legacy_sources)
            destination = assets / Path(*relative.parts[1:]) if relative.parts[:1] == ("assets",) else materials / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload = source.read_bytes()
            destination = _unique_destination(destination, payload)
            if not destination.exists():
                shutil.move(str(source), str(destination))
            else:
                source.unlink()
            replacements[str(source)] = str(destination)
            replacements[str(Path("sources") / relative)] = str(destination.relative_to(root))
        for directory in sorted(legacy_sources.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        if not any(legacy_sources.iterdir()):
            legacy_sources.rmdir()
    _rewrite_internal_paths(root, replacements)


def create_project(
    *,
    name: str,
    location: str | Path | None = None,
    deck_id: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    project_id = f"project_{uuid.uuid4().hex[:12]}"
    root = (
        Path(location).expanduser().resolve()
        if location
        else (data_root() / "projects" / _slug(name)).resolve()
    )
    if _existing_manifest(root):
        return register_project(root)
    root.mkdir(parents=True, exist_ok=True)
    for relative in (
        "deliverables",
        "assets",
        "materials",
        ".slidecraft/artifacts",
        ".slidecraft/assets",
        ".slidecraft/cache",
        ".slidecraft/logs",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    now = _now()
    project = {
        "schema_version": "1.0.0",
        "project_id": project_id,
        "name": name,
        "description": description,
        "deck_id": deck_id,
        "created_at": now,
        "updated_at": now,
        "workspace_path": str(root),
        "visibility": {
            "primary_outputs": "deliverables",
            "project_assets": "assets",
            "working_materials": "materials",
            "internal_state": ".slidecraft",
            "internal_state_default_visibility": "hidden",
        },
    }
    _atomic_write(root / PROJECT_FILE, project)
    workspace = ArtifactWorkspace(root)
    workspace.initialize(deck_id=deck_id, metadata={"project_id": project_id, "project_name": name})
    design_path = root / ".slidecraft" / "deck_design.json"
    design_path.write_text(files("slidecraft.defaults").joinpath("deck_design.json").read_text(encoding="utf-8"), encoding="utf-8")
    workspace.register(
        logical_key="deck/design",
        kind="deck_design_configuration",
        path=design_path,
        producer="create_project",
        validation={"status": "passed", "source": "packaged_baseline"},
    )
    registry = _read_registry()
    registry["projects"] = [item for item in registry["projects"] if item.get("project_id") != project_id and item.get("path") != str(root)]
    registry["projects"].append({
        "project_id": project_id,
        "name": name,
        "path": str(root),
        "last_opened_at": now,
    })
    _write_registry(registry)
    return project


def register_project(location: str | Path) -> dict[str, Any]:
    root = Path(location).expanduser().resolve()
    manifest_path = _existing_manifest(root)
    if manifest_path is None:
        raise FileNotFoundError(f"No {PROJECT_FILE} exists at {root}")
    if manifest_path.name == LEGACY_PROJECT_FILE:
        target = root / PROJECT_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.replace(target)
        manifest_path = target
    _ensure_visible_project_layout(root)
    project = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_visibility = {
        "primary_outputs": "deliverables",
        "project_assets": "assets",
        "working_materials": "materials",
        "internal_state": ".slidecraft",
        "internal_state_default_visibility": "hidden",
    }
    if project.get("visibility") != expected_visibility:
        project["visibility"] = expected_visibility
        project["updated_at"] = _now()
        _atomic_write(manifest_path, project)
    design_path = root / ".slidecraft" / "deck_design.json"
    if not design_path.exists():
        design_path.parent.mkdir(parents=True, exist_ok=True)
        design_path.write_text(files("slidecraft.defaults").joinpath("deck_design.json").read_text(encoding="utf-8"), encoding="utf-8")
        workspace = ArtifactWorkspace(root)
        workspace.initialize(deck_id=project.get("deck_id"), metadata={"project_id": project.get("project_id"), "project_name": project.get("name")})
        workspace.register(
            logical_key="deck/design",
            kind="deck_design_configuration",
            path=design_path,
            producer="register_project",
            validation={"status": "passed", "source": "packaged_baseline"},
        )
    if project.get("workspace_path") != str(root):
        project["workspace_path"] = str(root)
        project["updated_at"] = _now()
        _atomic_write(manifest_path, project)
    registry = _read_registry()
    now = _now()
    registry["projects"] = [item for item in registry["projects"] if item.get("project_id") != project["project_id"]]
    registry["projects"].append({
        "project_id": project["project_id"],
        "name": project["name"],
        "path": str(root),
        "last_opened_at": now,
    })
    _write_registry(registry)
    from slidecraft.project_resource_selections import reconcile_project_resources

    reconcile_project_resources(root, include_legacy_outputs=True)
    return project


def list_projects() -> list[dict[str, Any]]:
    registry = _read_registry()
    result = []
    for entry in registry["projects"]:
        root = Path(entry["path"])
        manifest_path = _existing_manifest(root) if root.is_dir() else None
        available = manifest_path is not None
        item = {**entry, "available": available}
        if available:
            project = json.loads(manifest_path.read_text(encoding="utf-8"))
            item.update({
                "description": project.get("description", ""),
                "deck_id": project.get("deck_id"),
                "updated_at": project.get("updated_at"),
                "source_material_count": len([
                    path for path in (root / "materials").glob("**/*") if path.is_file()
                ]),
            })
            try:
                state = ArtifactWorkspace(root).inspect()
                item["artifact_summary"] = state["summary"]
                item["attention_count"] = len(state["attention"])
                item["progress"] = _project_progress(root, state)
            except FileNotFoundError:
                item["artifact_summary"] = {"active": 0, "fresh": 0, "stale": 0, "candidates_awaiting_decision": 0}
                item["attention_count"] = 0
        result.append(item)
    return sorted(result, key=lambda item: item.get("last_opened_at", ""), reverse=True)


def resolve_project(
    identifier: str | Path,
    *,
    create_if_missing: bool = False,
    location: str | Path | None = None,
    deck_id: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Resolve a project from the name, stable ID, or local folder an Agent received."""
    raw_identifier = str(identifier).strip()
    if not raw_identifier:
        raise ValueError("A project name, ID, or folder is required")

    candidate_path = Path(raw_identifier).expanduser()
    if candidate_path.name in {Path(PROJECT_FILE).name, LEGACY_PROJECT_FILE}:
        candidate_path = candidate_path.parent.parent if candidate_path.parent.name == ".slidecraft" else candidate_path.parent
    if candidate_path.exists() and candidate_path.is_dir() and _existing_manifest(candidate_path):
        project = register_project(candidate_path)
        return {
            "resolution": "found",
            "matched_by": "folder",
            "location": project["workspace_path"],
            "project": project,
        }

    available = [item for item in list_projects() if item.get("available")]
    exact_id = [item for item in available if item.get("project_id") == raw_identifier]
    exact_name = [item for item in available if str(item.get("name", "")).casefold() == raw_identifier.casefold()]
    normalized_name = [item for item in available if _slug(str(item.get("name", ""))) == _slug(raw_identifier)]
    matches = exact_id or exact_name or normalized_name
    matched_by = "project_id" if exact_id else "name" if exact_name else "normalized_name"

    if len(matches) > 1:
        choices = [{"project_id": item["project_id"], "name": item["name"], "path": item["path"]} for item in matches]
        raise ValueError(f"Project name is ambiguous. Use one of these project IDs or paths: {json.dumps(choices)}")
    if matches:
        project = register_project(matches[0]["path"])
        return {
            "resolution": "found",
            "matched_by": matched_by,
            "location": project["workspace_path"],
            "project": project,
        }

    if not create_if_missing:
        raise FileNotFoundError(
            f"No registered project matches {raw_identifier!r}. Set create_if_missing only when the user intends to start it."
        )
    project = create_project(
        name=raw_identifier,
        location=location,
        deck_id=deck_id,
        description=description,
    )
    return {
        "resolution": "created",
        "matched_by": "new_project_name",
        "location": project["workspace_path"],
        "project": project,
    }


def _project_progress(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    active = {item["logical_key"]: item for item in state.get("active_artifacts", [])}
    kinds = {item["kind"] for item in active.values()}
    deliverables = [
        path for path in (root / "deliverables").glob("**/*")
        if path.is_file() and not path.name.startswith((".", "~$"))
    ]
    editable = [path for path in deliverables if path.suffix.lower() == ".pptx"]
    legacy_final = any(
        path.parent == root / "deliverables" and path.name != "current_deck.pptx"
        for path in editable
    )
    final_record = active.get("deck/editable_pptx")
    current_record = active.get("deck/current_pptx")
    final_editable = final_record if final_record and final_record["freshness"]["fresh"] else None
    current_editable = current_record if current_record and current_record["freshness"]["fresh"] else None
    if final_editable or legacy_final:
        status, label, index = "complete", "Editable presentation ready", 5
    elif current_editable:
        validation = current_editable.get("validation", {})
        completed = int(validation.get("slide_count", 0))
        planned = int(validation.get("planned_slide_count", 0))
        count = f"{completed} of {planned}" if planned else str(completed)
        status, label, index = "building", f"Current deck includes {count} planned slides", 4
    elif kinds & {"constructor_scene", "editable_presentation", "reconstruction_scene"}:
        status, label, index = "building", "Building the editable presentation", 4
    elif kinds & {"measurement_report", "visual_measurement", "semantic_map", "semantic_scene"}:
        status, label, index = "understanding", "Preparing editable slide objects", 3
    elif kinds & {"generated_image", "generation_package", "generation_prompt"}:
        status, label, index = "designing", "Designing slides", 2
    elif kinds & {"deck_plan", "semantic_design", "reference_retrieval", "intake_manifest"}:
        status, label, index = "planning", "Planning the presentation", 1
    else:
        status, label, index = "starting", "Ready to start", 0
    return {
        "status": status,
        "label": label,
        "milestone_index": index,
        "editable_presentation_count": len(editable),
        "deliverable_count": len(deliverables),
    }


def project_detail(location: str | Path, *, include_internal: bool = False) -> dict[str, Any]:
    root = Path(location).expanduser().resolve()
    manifest_path = _existing_manifest(root)
    if manifest_path is None:
        raise FileNotFoundError(f"No {PROJECT_FILE} exists at {root}")
    project = json.loads(manifest_path.read_text(encoding="utf-8"))
    state = ArtifactWorkspace(root).inspect(include_history=include_internal)
    deliverables = [
        str(path) for path in sorted((root / "deliverables").glob("**/*"))
        if path.is_file() and not path.name.startswith((".", "~$"))
    ]
    materials = [
        str(path)
        for path in sorted((root / "materials").glob("**/*"))
        if path.is_file()
    ]
    reviewable_kinds = {
        "clarification_package": "Planning questions",
        "clarification_answers": "Planning decisions",
        "deck_plan": "Deck plan",
        "semantic_design": "Communication plan",
        "generation_prompt": "Image generation brief",
        "generated_image": "Generated slide",
        "editable_deck_progress": "Current editable deck",
        "editable_powerpoint": "Editable presentation",
        "reconstruction_report": "Reconstruction report",
    }
    reviewable_artifacts = []
    for artifact in state.get("active_artifacts", []):
        label = reviewable_kinds.get(artifact.get("kind"))
        path = Path(artifact.get("path", ""))
        if label and path.is_file():
            reviewable_artifacts.append({
                "label": label,
                "kind": artifact["kind"],
                "path": str(path),
                "slide_id": artifact.get("slide_id"),
                "logical_key": artifact.get("logical_key"),
            })
    return {
        "project": project,
        "state": state,
        "deliverables": deliverables,
        "materials": materials,
        "reviewable_artifacts": reviewable_artifacts,
        "internal_visible": include_internal,
        "progress": _project_progress(root, state),
    }
