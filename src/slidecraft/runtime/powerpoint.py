"""Explicit, non-interactive policy for permission-gated PowerPoint automation."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE_PATH = Path.home() / ".config" / "slidecraft" / "capabilities.json"


class CapabilityAuthorizationRequired(RuntimeError):
    """An optional permission-gated capability has not completed explicit setup."""


def read_capabilities(path: Path = DEFAULT_STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": "1.0.0", "powerpoint_automation": {"authorized": False}}
    return json.loads(path.read_text(encoding="utf-8"))


def powerpoint_is_authorized(path: Path = DEFAULT_STATE_PATH) -> bool:
    return bool(read_capabilities(path).get("powerpoint_automation", {}).get("authorized"))


def authorize_powerpoint(path: Path = DEFAULT_STATE_PATH, timeout_seconds: int = 20) -> dict[str, Any]:
    """Run the only command that may cause the macOS Automation consent dialog."""
    command = [
        "osascript",
        "-e",
        'tell application "Microsoft PowerPoint" to return name',
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
    authorized = completed.returncode == 0
    record = read_capabilities(path)
    record["powerpoint_automation"] = {
        "authorized": authorized,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "probe_returncode": completed.returncode,
        "message": "PowerPoint automation is available" if authorized else "PowerPoint automation was not authorized",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record["powerpoint_automation"]


def require_powerpoint_authorization(path: Path = DEFAULT_STATE_PATH) -> None:
    if powerpoint_is_authorized(path):
        return
    raise CapabilityAuthorizationRequired(
        "PowerPoint automation has not been enabled for Slidecraft. "
        "Run `slidecraft authorize-powerpoint` once if native Office validation is wanted. "
        "No permission-gated command was executed."
    )
