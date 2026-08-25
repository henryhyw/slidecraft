#!/usr/bin/env python3
"""Render a fully configured preservation-first review prompt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from slidecraft.orchestration.review_prompt import build_review_prompt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Generated candidate image. It may be attached later when omitted.")
    parser.add_argument("--state", default="outputs/architecture_generation_orchestration/generation_context.json")
    parser.add_argument("--review-config", default="config/generation_review_config.json")
    parser.add_argument("--output-dir", default="outputs/architecture_generation_orchestration/review")
    args = parser.parse_args()

    state = json.loads(Path(args.state).resolve().read_text(encoding="utf-8"))
    config = json.loads(Path(args.review_config).resolve().read_text(encoding="utf-8"))
    image = str(Path(args.image).resolve()) if args.image else None
    prompt, manifest = build_review_prompt(state, config, image)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "configured_review_prompt.txt"
    manifest_path = output_dir / "review_input_manifest.json"
    prompt_path.write_text(prompt, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "prompt": str(prompt_path),
        "manifest": str(manifest_path),
        "generated_candidate": image,
        "status": "ready" if image else "ready_for_candidate_attachment",
    }, indent=2))


if __name__ == "__main__":
    main()
