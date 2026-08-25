#!/usr/bin/env python3
"""Validate the reconstruction-oriented slide understanding output and its referenced masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", nargs="?", default="outputs/sample_slide/slide_entities.json")
    args = parser.parse_args()
    json_path = Path(args.json_path).resolve()
    data = json.loads(json_path.read_text())
    width = data["source"]["width_px"]
    height = data["source"]["height_px"]
    ids = [entity["id"] for entity in data["entities"]]
    assert len(ids) == len(set(ids)), "Entity IDs must be unique"
    assert data["coordinate_system"]["units"] == ["px", "normalized", "inches", "pptx_emu"]

    missing_masks = []
    invalid_boxes = []
    for entity in data["entities"]:
        measurement = entity["measurement"]
        x, y, w, h = measurement["layout_bbox"]["px"]
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
            invalid_boxes.append(entity["id"])
        mask_path = json_path.parent / measurement["selected_mask"]
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.shape != (height, width):
            missing_masks.append(entity["id"])
    assert not invalid_boxes, f"Invalid boxes {invalid_boxes}"
    assert not missing_masks, f"Missing or invalid masks {missing_masks}"

    known = set(ids) | {group["id"] for group in data["groups"]}
    dangling = []
    for group in data["groups"]:
        dangling.extend(child for child in group["children"] if child not in known)
    assert not dangling, f"Dangling group members {dangling}"
    assert data["runtime"]["mps_available"] is True
    assert data["runtime"]["sam_device"] == "mps"
    assert data["quality_summary"]["sam_prompted_entity_count"] == 5
    print(f"Validated {len(ids)} entities, {len(data['groups'])} groups, and all referenced masks")


if __name__ == "__main__":
    main()
