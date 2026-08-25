"""Small durable event inbox shared by the local console and Agent hosts."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slidecraft.projects import project_manifest_path

EVENT_FILE = Path(".slidecraft/events/project_events.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root(location: str | Path) -> Path:
    root = Path(location).expanduser().resolve()
    project_manifest_path(root)
    return root


def _read(root: Path) -> dict[str, Any]:
    path = root / EVENT_FILE
    if not path.exists():
        return {"schema_version": "1.0.0", "events": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(root: Path, value: dict[str, Any]) -> None:
    path = root / EVENT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def record_project_event(
    location: str | Path,
    *,
    event_type: str,
    actor: str,
    resource_id: str | None = None,
    changes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = _root(location)
    inbox = _read(root)
    event = {
        "event_id": f"EVENT_{uuid.uuid4().hex[:12].upper()}",
        "event_type": event_type,
        "actor": actor,
        "resource_id": resource_id,
        "changes": changes or {},
        "created_at": _now(),
        "acknowledged_at": None,
    }
    inbox["events"].append(event)
    _write(root, inbox)
    return event


def list_project_events(location: str | Path, *, pending_only: bool = True) -> dict[str, Any]:
    root = _root(location)
    events = _read(root)["events"]
    if pending_only:
        events = [event for event in events if not event.get("acknowledged_at")]
    return {"project_path": str(root), "events": events, "pending_count": len(events)}


def acknowledge_project_events(location: str | Path, event_ids: list[str]) -> dict[str, Any]:
    root = _root(location)
    inbox = _read(root)
    wanted = set(event_ids)
    acknowledged = []
    for event in inbox["events"]:
        if event["event_id"] in wanted and not event.get("acknowledged_at"):
            event["acknowledged_at"] = _now()
            acknowledged.append(event["event_id"])
    _write(root, inbox)
    return {"project_path": str(root), "acknowledged_event_ids": acknowledged}
