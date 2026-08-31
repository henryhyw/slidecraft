#!/usr/bin/env python3
"""Collect objective reconstruction-contract and config consistency facts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measured-scene", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measured = json.loads(args.measured_scene.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    errors: list[dict] = []

    if not measured.get("runtime", {}).get("opencv"):
        errors.append({"reason": "fresh_OpenCV_measurement_missing"})
    local_norm = measured.get("runtime", {}).get("local_geometry_normalization", {}) or {}
    if local_norm.get("enabled") is not True:
        errors.append({"reason": "mandatory_local_geometry_normalization_missing"})
    if "fixture://" in args.measured_scene.read_text(encoding="utf-8").lower():
        errors.append({"reason": "fixture_measurement_forbidden"})

    design = config["design"]
    full = list(design["full_slide_px"])
    header = design["frame"]["header"]
    footer = design["frame"]["footer"]
    hh = int(header.get("height_px", 0)) if header.get("enabled", True) else 0
    fh = int(footer.get("height_px", 0)) if footer.get("enabled", True) else 0
    expected_region = [int(full[0]), int(full[1]) - hh - fh]
    if list(contract.get("full_slide_dimensions_px", [])) != full:
        errors.append({"reason": "full_slide_dimensions_do_not_match_resolved_config"})
    region = contract.get("generation_region", {})
    if list(region.get("dimensions_px", [])) != expected_region or int(region.get("offset_y_px", -1)) != hh:
        errors.append({"reason": "generation_region_does_not_match_frame_heights", "expected_dimensions": expected_region, "expected_offset_y": hh})
    frame = contract.get("frame_configuration", {})
    for area, expected in (("header", header), ("footer", footer)):
        actual = frame.get(area, {})
        for key in ("enabled", "height_px", "implementation"):
            if actual.get(key) != expected.get(key):
                errors.append({"reason": "frame_configuration_mismatch", "area": area, "field": key, "expected": expected.get(key), "actual": actual.get(key)})

    allowed = set(design.get("connectors", {}).get("allowed_families", []))
    for plan in contract.get("connector_reconstruction_plans", []):
        if plan.get("connector_family") not in allowed:
            errors.append({"reason": "unsupported_connector_family", "connector": plan.get("entity_id")})
    for mapping in contract.get("canonical_asset_mappings", []):
        if not Path(mapping.get("selected_asset_path", "")).is_file():
            errors.append({"reason": "missing_canonical_asset", "entity": mapping.get("entity_id"), "path": mapping.get("selected_asset_path")})

    report = {
        "evidence_type": "objective_reconstruction_contract_facts",
        "blocking_facts": errors,
        "agent_reasoning_gate_required": True,
        "note": "No reconstruction verdict is produced. The host Agent interprets these facts together with the accepted target and render.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if not errors else 2)


if __name__ == "__main__":
    main()
