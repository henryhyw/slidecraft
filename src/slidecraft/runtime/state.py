"""Legacy approval snapshot retained for CLI compatibility.

Agent-host execution derives progress from the artifact ledger and does not use
this module as a session controller.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SLIDE_TRANSITIONS = {
    "ready_for_system_render": {"ready_for_assembly", "failed"},
    "ready_for_semantic_planning": {"awaiting_generation", "failed"},
    "awaiting_generation": {"awaiting_semantic_mapping", "failed"},
    "awaiting_semantic_mapping": {"awaiting_measurement", "failed"},
    "awaiting_measurement": {"awaiting_reconstruction", "failed"},
    "awaiting_reconstruction": {"awaiting_validation", "failed"},
    "awaiting_validation": {"ready_for_assembly", "failed"},
    "failed": {"ready_for_system_render", "ready_for_semantic_planning"},
    "ready_for_assembly": set(),
}


@dataclass
class RunStateStore:
    path: Path

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, value: dict[str, Any]) -> None:
        value["updated_at"] = datetime.now(timezone.utc).isoformat()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def transition_slide(self, slide_id: str, target: str, *, artifact: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
        state = self.read()
        slides = {slide["slide_id"]: slide for slide in state["slides"]}
        if slide_id not in slides:
            raise KeyError(slide_id)
        slide = slides[slide_id]
        current = slide["status"]
        if target not in SLIDE_TRANSITIONS.get(current, set()):
            raise ValueError(f"Invalid slide transition {current} -> {target}")
        slide["status"] = target
        slide.setdefault("events", []).append({
            "from": current,
            "to": target,
            "at": datetime.now(timezone.utc).isoformat(),
            "artifact": artifact,
            "error": error,
        })
        if artifact:
            slide.setdefault("artifacts", []).append(artifact)
        if error:
            slide["last_error"] = error
        state["status"] = "needs_attention" if any(item["status"] == "failed" for item in state["slides"]) else "running"
        if all(item["status"] == "ready_for_assembly" for item in state["slides"]):
            state["status"] = "ready_for_assembly"
        self.write(state)
        return slide

    def approve(self, fingerprint: str, *, approved_by: str = "user") -> dict[str, Any]:
        state = self.read()
        if state["status"] != "awaiting_preflight_approval":
            raise ValueError(f"Run is not awaiting approval: {state['status']}")
        if fingerprint != state["fingerprint"]:
            raise ValueError("Approval fingerprint does not match the current deck plan and design snapshot")
        state["status"] = "approved"
        state["approval"] = {"approved_by": approved_by, "approved_at": datetime.now(timezone.utc).isoformat(), "fingerprint": fingerprint}
        self.write(state)
        return state


def initialize_run_state(manifest: dict[str, Any], output_path: Path) -> dict[str, Any]:
    state = {
        "schema_version": "1.0.0",
        "run_id": manifest["run_id"],
        "deck_id": manifest["deck_id"],
        "fingerprint": manifest["fingerprint"],
        "status": "awaiting_preflight_approval",
        "slides": [
            {"slide_id": job["slide_id"], "status": job["status"], "events": [], "artifacts": []}
            for job in manifest["jobs"]
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    RunStateStore(output_path).write(state)
    return state
