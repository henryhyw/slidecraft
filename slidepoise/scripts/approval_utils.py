#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable

VALID = {"pending", "approved", "changes_requested"}

def load_approvals(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"human approval artifact missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("human approval artifact must be a JSON object")
    return data

def require_approved(path: Path, gates: Iterable[str]) -> dict:
    data = load_approvals(path)
    missing = []
    for gate in gates:
        record = data.get(gate)
        status = record.get("status") if isinstance(record, dict) else None
        if status not in VALID:
            missing.append(f"{gate}: missing/invalid status")
        elif status != "approved":
            missing.append(f"{gate}: {status}")
    if missing:
        raise ValueError("required human approval not present: " + "; ".join(missing))
    return data
