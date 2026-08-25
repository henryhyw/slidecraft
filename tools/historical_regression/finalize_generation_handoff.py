#!/usr/bin/env python3
"""Attach a user-generated image to the saved slide understanding handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--handoff", default="outputs/architecture_generation_orchestration/reconstruction_handoff.json")
    parser.add_argument("--allow-legacy-unapproved", action="store_true")
    args = parser.parse_args()
    image_path = Path(args.image).resolve()
    handoff_path = Path(args.handoff).resolve()
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    authorization = handoff.get("generation_authorization")
    if authorization is None and not args.allow_legacy_unapproved:
        raise ValueError("The handoff has no generation approval. Use the explicit legacy override only for a historical run.")
    if authorization is not None and not authorization.get("generation_released", False):
        raise ValueError("Generation is blocked until the current preflight fingerprint is approved")
    expected = handoff["generation_region"]["dimensions_px"]
    with Image.open(image_path) as image:
        actual = list(image.size)
    if actual != expected:
        raise ValueError(f"Generated region must be {expected}, image is {actual}")
    handoff["target_image"] = {
        "path": str(image_path),
        "status": "ready_for_step4",
        "scope": "generation_region",
    }
    handoff_path.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ready_for_step4", "image": str(image_path), "handoff": str(handoff_path)}, indent=2))


if __name__ == "__main__":
    main()
