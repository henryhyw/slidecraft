#!/usr/bin/env python3
"""Record a preflight decision and release the matching generation package."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/architecture_generation_orchestration")
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--decision", choices=["approved", "changes_requested", "rejected"], required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--comment", default="")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    preflight_path = output_dir / "generation_preflight.json"
    state_path = output_dir / "generation_context.json"
    handoff_path = output_dir / "reconstruction_handoff.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if args.fingerprint != preflight["approval"]["fingerprint"]:
        raise ValueError("Approval fingerprint does not match the current generation package")
    if args.decision == "approved" and not preflight["quality"]["ready_for_approval"]:
        raise ValueError("The preflight contains blocking issues and cannot be approved")

    record = {
        "schema_version": "1.0.0",
        "preflight_fingerprint": args.fingerprint,
        "decision": args.decision,
        "approved_by": args.approved_by,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "scope": "whole_run",
        "approved_slide_ids": [item["slide_id"] for item in preflight["slides"]] if args.decision == "approved" else [],
        "requested_changes": [],
        "comment": args.comment,
    }
    status = "approved" if args.decision == "approved" else args.decision
    preflight["approval"]["status"] = status
    preflight["approval"]["generation_released"] = args.decision == "approved"
    write_json(preflight_path, preflight)
    write_json(output_dir / "generation_approval.json", record)

    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["generation_preflight"] = preflight
        state["generation"]["execution"] = "external_user_action" if args.decision == "approved" else "blocked_until_preflight_approval"
        state["generation"]["prompt_status"] = "released" if args.decision == "approved" else "draft_pending_approval"
        write_json(state_path, state)
    if handoff_path.exists():
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        handoff["generation_authorization"] = preflight["approval"]
        write_json(handoff_path, handoff)

    print(json.dumps({
        "decision": args.decision,
        "generation_released": args.decision == "approved",
        "approval_record": str((output_dir / "generation_approval.json").resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
