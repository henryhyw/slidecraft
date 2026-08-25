#!/usr/bin/env python3
"""Bind a user-generated candidate image to the preserved generation handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-handoff", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-legacy-unapproved", action="store_true")
    args = parser.parse_args()

    base_path = Path(args.base_handoff).resolve()
    image_path = Path(args.image).resolve()
    output_path = Path(args.output).resolve()
    handoff = json.loads(base_path.read_text(encoding="utf-8"))
    authorization = handoff.get("generation_authorization")
    if authorization is None and not args.allow_legacy_unapproved:
        raise ValueError("The handoff has no generation approval. Use the explicit legacy override only for a historical run.")
    if authorization is not None and not authorization.get("generation_released", False):
        raise ValueError("Generation is blocked until the current preflight fingerprint is approved")

    with Image.open(image_path) as image:
        actual = [int(image.width), int(image.height)]

    configured = list(handoff["generation_region"]["dimensions_px"])
    offset_y = int(handoff["generation_region"]["offset_y_px"])
    scale = [configured[0] / actual[0], configured[1] / actual[1]]

    handoff["target_image"] = {
        "path": str(image_path),
        "status": "accepted_for_reconstruction",
        "scope": "generation_region",
        "actual_dimensions_px": actual,
    }
    handoff["generation_region"]["configured_dimensions_px"] = configured
    handoff["generation_region"]["source_dimensions_px"] = actual
    handoff["coordinate_transform_to_full_slide"] = {
        "source_origin_px": [0, 0],
        "full_slide_offset_px": [0, offset_y],
        "scale_xy": scale,
        "mapping": "full_x = source_x * scale_x; full_y = offset_y + source_y * scale_y",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
