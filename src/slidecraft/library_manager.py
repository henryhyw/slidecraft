"""User-manageable reusable resource collections."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any

from slidecraft.configuration import data_root, modify_config_value, resolve_config

USER_LIBRARIES = {"visual_references", "icons", "components"}
METADATA_FILE = ".slidecraft-library.json"
SUPPORT_FILES = {METADATA_FILE, "semantic_manifest.json", "LICENSE.txt", "LICENSE", "README.md"}


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", Path(value).name).strip("._") or "resource"


def library_root(name: str) -> Path:
    if name not in USER_LIBRARIES:
        raise KeyError(name)
    config, _ = resolve_config()
    path = Path(config["libraries"][name]).expanduser()
    if not path.is_absolute():
        path = data_root() / path
    return path.resolve()


def _read_metadata(root: Path) -> dict[str, Any]:
    path = root / METADATA_FILE
    if not path.exists():
        return {"schema_version": "1.0.0", "items": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"schema_version": "1.0.0", "items": {}}
    value.setdefault("items", {})
    return value


def _write_metadata(root: Path, value: dict[str, Any]) -> None:
    path = root / METADATA_FILE
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _record(path: Path, root: Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    relative_path = str(path.relative_to(root))
    details = (metadata or {}).get(relative_path, {})
    record = {
        "item_id": f"LIB_{digest[:16].upper()}",
        "name": details.get("name") or path.stem.replace("_", " ").replace("-", " ").title(),
        "filename": path.name,
        "description": details.get("description", ""),
        "tags": details.get("tags", []),
        "semantic_roles": details.get("semantic_roles", []),
        "metadata_status": "ready" if details.get("description") else "needs_description",
        "relative_path": relative_path,
        "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "size_bytes": path.stat().st_size,
        "path": str(path),
    }
    if path.name.endswith(".component.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            manifest = {}
        preview = manifest.get("preview", {}).get("image")
        preview_path = (path.parent / preview).resolve() if preview else None
        if preview_path and not preview_path.is_file():
            preview_path = next((candidate.resolve() for candidate in sorted(path.parent.glob("preview.*")) if candidate.is_file()), None)
        record.update({
            "component_id": manifest.get("component_id"),
            "implementation_type": manifest.get("implementation", {}).get("type"),
            "preview_path": str(preview_path) if preview_path and preview_path.is_file() else None,
        })
    return record


def list_library_items(name: str) -> dict[str, Any]:
    root = library_root(name)
    root.mkdir(parents=True, exist_ok=True)
    metadata = _read_metadata(root)["items"]
    component_support: set[Path] = set()
    if name == "components":
        for manifest_path in root.rglob("*.component.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            for value in (manifest.get("preview", {}).get("image"), manifest.get("implementation", {}).get("source")):
                if value:
                    component_support.add((manifest_path.parent / value).resolve())
            component_support.update(candidate.resolve() for candidate in manifest_path.parent.glob("preview.*") if candidate.is_file())
    items = [
        _record(path, root, metadata)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.name.startswith(".") and path.name not in SUPPORT_FILES and path.resolve() not in component_support
    ]
    return {"name": name, "path": str(root), "items": items, "item_count": len(items)}


def resolve_library_item(name: str, item_id: str) -> dict[str, Any]:
    library = list_library_items(name)
    item = next((item for item in library["items"] if item["item_id"] == item_id), None)
    if item is None:
        raise KeyError(item_id)
    return item


def set_library_location(name: str, location: str | Path) -> dict[str, Any]:
    if name not in USER_LIBRARIES:
        raise KeyError(name)
    path = Path(location).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    modify_config_value(f"libraries.{name}", str(path), scope="user")
    return list_library_items(name)


def add_library_item(
    name: str,
    filename: str,
    content_base64: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = library_root(name)
    root.mkdir(parents=True, exist_ok=True)
    payload = base64.b64decode(content_base64, validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    destination = root / f"{digest[:12]}_{_safe_name(filename)}"
    if not destination.exists():
        destination.write_bytes(payload)
    if metadata:
        update_library_item_metadata(name, _record(destination, root)["item_id"], metadata)
    return resolve_library_item(name, _record(destination, root)["item_id"])


def add_library_path(name: str, source: str | Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    root = library_root(name)
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    destination = root / f"{digest[:12]}_{_safe_name(source_path.name)}"
    if not destination.exists():
        shutil.copyfile(source_path, destination)
    item = _record(destination, root)
    if metadata:
        return update_library_item_metadata(name, item["item_id"], metadata)
    return resolve_library_item(name, item["item_id"])


def update_library_item_metadata(name: str, item_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    item = resolve_library_item(name, item_id)
    root = library_root(name)
    metadata = _read_metadata(root)
    current = metadata["items"].get(item["relative_path"], {})
    allowed = {key: updates[key] for key in ("name", "description", "tags", "semantic_roles") if key in updates}
    metadata["items"][item["relative_path"]] = {**current, **allowed}
    _write_metadata(root, metadata)
    return resolve_library_item(name, item_id)


def delete_library_item(name: str, item_id: str) -> dict[str, Any]:
    item = resolve_library_item(name, item_id)
    target = Path(item["path"]).resolve()
    root = library_root(name)
    if root not in target.parents:
        raise ValueError("Resource is outside the configured collection")
    metadata = _read_metadata(root)
    metadata["items"].pop(item["relative_path"], None)
    _write_metadata(root, metadata)
    target.unlink()
    return {"status": "deleted", "item_id": item_id, "name": item["name"]}
