#!/usr/bin/env python3
"""Validate a reviewer delta and compose the configuration-constrained edit prompt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from slidecraft.orchestration.edit_prompt import build_edit_prompt, load_review_result, validate_review_result
from slidecraft.orchestration.naming import migrate_orchestration_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-result", required=True)
    parser.add_argument("--candidate", help="Generated candidate image. It may be attached later when omitted.")
    parser.add_argument("--state", default="outputs/architecture_generation_orchestration/orchestration_state.json")
    parser.add_argument("--review-config", default="config/generation_review_config.json")
    parser.add_argument("--output-dir", default="outputs/architecture_generation_orchestration/edit")
    args = parser.parse_args()

    state = json.loads(Path(args.state).resolve().read_text(encoding="utf-8"))
    state, naming_migration_notices = migrate_orchestration_state(state)
    config = json.loads(Path(args.review_config).resolve().read_text(encoding="utf-8"))
    result = load_review_result(Path(args.review_result).resolve())
    validate_review_result(result, config)
    candidate = str(Path(args.candidate).resolve()) if args.candidate else None
    if candidate and not Path(candidate).exists():
        raise FileNotFoundError(candidate)
    prompt, manifest = build_edit_prompt(state, result, candidate)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "edit_input_manifest.json"
    result_path = output_dir / "validated_review_result.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    prompt_path = None
    if prompt is not None:
        prompt_file = output_dir / "configured_edit_prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        prompt_path = str(prompt_file)
    print(json.dumps({
        "decision": result["decision"],
        "configured_edit_prompt": prompt_path,
        "input_manifest": str(manifest_path),
        "status": ("ready_for_image_edit" if candidate else "ready_for_candidate_attachment") if prompt else "no_edit_required",
        "naming_migration_notices": naming_migration_notices,
    }, indent=2))


if __name__ == "__main__":
    main()
