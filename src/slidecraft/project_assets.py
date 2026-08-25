"""Project asset catalog shared by chat, the local console, and direct folder edits."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slidecraft.projects import PROJECT_FILE

ASSET_DIRECTORY = Path("sources/assets")
ASSET_MANIFEST = Path(".slidecraft/assets/asset_manifest.json")
USAGE_POLICIES = {"available", "preferred", "required_somewhere", "required_on_slides", "required_each_slide"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", Path(value).name).strip("._") or "asset"


def _root(location: str | Path) -> Path:
    root = Path(location).expanduser().resolve()
    if not (root / PROJECT_FILE).is_file():
        raise FileNotFoundError(f"No {PROJECT_FILE} exists at {root}")
    return root


def _read(root: Path) -> dict[str, Any]:
    path = root / ASSET_MANIFEST
    if not path.exists():
        return {"schema_version": "1.0.0", "updated_at": _now(), "assets": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(root: Path, manifest: dict[str, Any]) -> None:
    path = root / ASSET_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = _now()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _semantic_role(filename: str) -> str:
    value = Path(filename).stem.lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", value).strip() or "user supplied asset"


def add_project_asset(
    location: str | Path,
    source: str | Path,
    *,
    semantic_role: str | None = None,
    usage_policy: str = "available",
    slide_ids: list[str] | None = None,
    provenance: str = "user_local_file",
) -> dict[str, Any]:
    root = _root(location)
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if usage_policy not in USAGE_POLICIES:
        raise ValueError(f"Unsupported asset usage policy {usage_policy}")
    if usage_policy == "required_on_slides" and not slide_ids:
        raise ValueError("required_on_slides needs at least one slide_id")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    asset_dir = root / ASSET_DIRECTORY
    asset_dir.mkdir(parents=True, exist_ok=True)
    destination = source_path if source_path.parent == asset_dir.resolve() else asset_dir / f"{digest[:12]}_{_safe_name(source_path.name)}"
    if source_path != destination and not destination.exists():
        shutil.copy2(source_path, destination)
    manifest = _read(root)
    existing = next((item for item in manifest["assets"] if item["sha256"] == digest), None)
    if existing:
        return existing
    record = {
        "asset_id": f"PROJECT_{digest[:12].upper()}",
        "name": source_path.name,
        "stored_path": str(destination),
        "sha256": digest,
        "media_type": mimetypes.guess_type(source_path.name)[0] or "application/octet-stream",
        "semantic_role": semantic_role or _semantic_role(source_path.name),
        "usage_policy": usage_policy,
        "slide_ids": slide_ids or [],
        "preserve_aspect_ratio": True,
        "provenance": provenance,
        "created_at": _now(),
        "status": "active",
    }
    manifest["assets"].append(record)
    _write(root, manifest)
    return record


def add_uploaded_asset(
    location: str | Path,
    *,
    filename: str,
    content_base64: str,
    semantic_role: str | None = None,
    usage_policy: str = "available",
) -> dict[str, Any]:
    root = _root(location)
    incoming = root / ".slidecraft/assets/incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    temporary = incoming / f"{uuid.uuid4().hex}_{_safe_name(filename)}"
    temporary.write_bytes(base64.b64decode(content_base64, validate=True))
    return add_project_asset(
        root,
        temporary,
        semantic_role=semantic_role,
        usage_policy=usage_policy,
        provenance="local_console_upload",
    )


def scan_project_assets(location: str | Path) -> dict[str, Any]:
    root = _root(location)
    asset_dir = root / ASSET_DIRECTORY
    asset_dir.mkdir(parents=True, exist_ok=True)
    manifest = _read(root)
    known = {item["sha256"] for item in manifest["assets"]}
    added = []
    for path in sorted(asset_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in known:
            continue
        record = add_project_asset(root, path, provenance="direct_project_folder")
        added.append(record)
        known.add(digest)
    return {"added": added, "asset_count": len(_read(root)["assets"])}


def list_project_assets(location: str | Path, *, sync_folder: bool = True) -> dict[str, Any]:
    root = _root(location)
    if sync_folder:
        scan_project_assets(root)
    manifest = _read(root)
    return {
        "project_path": str(root),
        "asset_folder": str(root / ASSET_DIRECTORY),
        "assets": [item for item in manifest["assets"] if item.get("status") == "active"],
        "default_usage_policy": "available",
    }


def update_project_asset(
    location: str | Path,
    asset_id: str,
    *,
    semantic_role: str | None = None,
    usage_policy: str | None = None,
    slide_ids: list[str] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    root = _root(location)
    manifest = _read(root)
    record = next((item for item in manifest["assets"] if item["asset_id"] == asset_id), None)
    if record is None:
        raise KeyError(asset_id)
    changes: dict[str, Any] = {}
    if usage_policy is not None:
        if usage_policy not in USAGE_POLICIES:
            raise ValueError(f"Unsupported asset usage policy {usage_policy}")
        record["usage_policy"] = usage_policy
        changes["usage_policy"] = usage_policy
    if semantic_role is not None:
        record["semantic_role"] = semantic_role
        changes["semantic_role"] = semantic_role
    if slide_ids is not None:
        record["slide_ids"] = slide_ids
        changes["slide_ids"] = slide_ids
    _write(root, manifest)
    if actor and changes:
        from slidecraft.project_events import record_project_event

        record_project_event(
            root,
            event_type="resource_preference_changed",
            actor=actor,
            resource_id=asset_id,
            changes=changes,
        )
    return record


def deactivate_project_asset(
    location: str | Path,
    asset_id: str,
    *,
    actor: str = "user_console",
) -> dict[str, Any]:
    """Hide an asset from the project catalog while preserving its source file."""
    root = _root(location)
    manifest = _read(root)
    record = next((item for item in manifest["assets"] if item["asset_id"] == asset_id), None)
    if record is None:
        raise KeyError(asset_id)
    record["status"] = "inactive"
    _write(root, manifest)
    from slidecraft.project_events import record_project_event

    record_project_event(
        root,
        event_type="project_asset_removed",
        actor=actor,
        resource_id=asset_id,
        changes={"status": "inactive", "source_file_preserved": True, "plan_changed": False},
    )
    return record
