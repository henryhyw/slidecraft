"""User-supplied source material ingestion for a Slidecraft project."""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path
from typing import Any

from slidecraft.project_events import record_project_event
from slidecraft.projects import project_manifest_path


def _root(location: str | Path) -> Path:
    root = Path(location).expanduser().resolve()
    project_manifest_path(root)
    return root


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", Path(value).name).strip("._") or "material"


def add_uploaded_material(
    location: str | Path,
    *,
    filename: str,
    content_base64: str,
    actor: str = "user_console",
) -> dict[str, Any]:
    """Add a user-facing source file without changing the active deck plan."""
    root = _root(location)
    payload = base64.b64decode(content_base64, validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    source_root = root / "materials"
    source_root.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_name(filename)
    destination = source_root / safe_name
    if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
        destination = source_root / f"{Path(safe_name).stem}_{digest[:8]}{Path(safe_name).suffix}"
    if not destination.exists():
        destination.write_bytes(payload)
    event = record_project_event(
        root,
        event_type="source_material_added",
        actor=actor,
        resource_id=f"SOURCE_{digest[:12].upper()}",
        changes={"path": str(destination), "filename": filename, "plan_changed": False},
    )
    return {
        "resource_id": f"SOURCE_{digest[:12].upper()}",
        "name": destination.name,
        "path": str(destination),
        "sha256": digest,
        "event_id": event["event_id"],
    }


def add_project_material(
    location: str | Path,
    source: str | Path,
    *,
    actor: str = "agent_host",
) -> dict[str, Any]:
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    return add_uploaded_material(
        location,
        filename=source_path.name,
        content_base64=base64.b64encode(source_path.read_bytes()).decode("ascii"),
        actor=actor,
    )
