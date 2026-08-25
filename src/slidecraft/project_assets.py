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

from PIL import Image

from slidecraft.projects import project_manifest_path

ASSET_DIRECTORY = Path("assets")
ASSET_MANIFEST = Path(".slidecraft/assets/asset_manifest.json")
USAGE_POLICIES = {"available", "preferred", "required_somewhere", "required_on_slides", "required_each_slide"}


def _visual_metadata(path: Path, media_type: str) -> dict[str, Any]:
    """Measure file facts without assigning a semantic meaning to the asset."""
    width: float | None = None
    height: float | None = None
    visual_kind = "other"
    if path.suffix.lower() == ".svg" or media_type == "image/svg+xml":
        visual_kind = "vector_image"
        text = path.read_text(encoding="utf-8", errors="ignore")[:8000]
        view_box = re.search(r"viewBox=[\"']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)", text)
        if view_box:
            width, height = float(view_box.group(1)), float(view_box.group(2))
        else:
            width_match = re.search(r"\bwidth=[\"']([\d.]+)", text)
            height_match = re.search(r"\bheight=[\"']([\d.]+)", text)
            if width_match and height_match:
                width, height = float(width_match.group(1)), float(height_match.group(1))
    elif media_type.startswith("image/"):
        visual_kind = "raster_image"
        try:
            with Image.open(path) as image:
                width, height = float(image.width), float(image.height)
        except OSError:
            pass
    return {
        "visual_kind": visual_kind,
        "intrinsic_width": width,
        "intrinsic_height": height,
        "intrinsic_aspect_ratio": round(width / height, 6) if width and height else None,
        "preserve_exact_content": visual_kind in {"vector_image", "raster_image"},
        "preserve_aspect_ratio": visual_kind in {"vector_image", "raster_image"},
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", Path(value).name).strip("._") or "asset"


def _root(location: str | Path) -> Path:
    root = Path(location).expanduser().resolve()
    project_manifest_path(root)
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


def add_project_asset(
    location: str | Path,
    source: str | Path,
    *,
    semantic_role: str | None = None,
    description: str | None = None,
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
    media_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
    record = {
        "asset_id": f"PROJECT_{digest[:12].upper()}",
        "name": source_path.name,
        "stored_path": str(destination),
        "sha256": digest,
        "media_type": media_type,
        "semantic_role": semantic_role,
        "description": description,
        "semantic_metadata_status": "ready" if semantic_role and description else "needs_agent_description",
        "usage_policy": usage_policy,
        "slide_ids": slide_ids or [],
        **_visual_metadata(destination, media_type),
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
    manifest = _read(root)
    project_files = {
        hashlib.sha256(path.read_bytes()).hexdigest(): path.resolve()
        for path in asset_dir.iterdir()
        if path.is_file() and not path.name.startswith(".")
    }
    enriched = False
    for item in manifest["assets"]:
        canonical_path = project_files.get(item["sha256"])
        if canonical_path and item.get("stored_path") != str(canonical_path):
            item["stored_path"] = str(canonical_path)
            enriched = True
        stored = Path(item["stored_path"])
        if stored.is_file() and "visual_kind" not in item:
            item.update(_visual_metadata(stored, item.get("media_type", "application/octet-stream")))
            enriched = True
        metadata_status = (
            "ready" if item.get("semantic_role") and item.get("description") else "needs_agent_description"
        )
        if item.get("semantic_metadata_status") != metadata_status:
            item["semantic_metadata_status"] = metadata_status
            enriched = True
    if enriched:
        _write(root, manifest)
    return {"added": added, "asset_count": len(manifest["assets"])}


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
    description: str | None = None,
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
    if description is not None:
        record["description"] = description
        changes["description"] = description
    record["semantic_metadata_status"] = (
        "ready" if record.get("semantic_role") and record.get("description") else "needs_agent_description"
    )
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
