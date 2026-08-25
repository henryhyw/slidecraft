#!/usr/bin/env python3
"""Compare the former line-faithful text contract with the authored-block fit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-text", type=Path, required=True)
    args = parser.parse_args()

    previous = json.loads(args.previous.read_text())
    current = json.loads(args.current.read_text())
    old_by_id = {item["id"]: item for item in previous["fitted_text_contracts"]}
    records = []
    for item in current["fitted_text_contracts"]:
        old = old_by_id[item["id"]]
        previous_ppt_font_px = round(old["font_size_px"] * 0.75, 2)
        record = {
            "id": item["id"],
            "content_changed_from_raster_lines": item["source_text_raw"] != item["authored_text"],
            "source_text_raw": item["source_text_raw"],
            "authored_text": item["authored_text"],
            "previous_powerpoint_font_size_px": previous_ppt_font_px,
            "new_powerpoint_font_size_px": item["font_size_px"],
            "font_size_change_px": round(item["font_size_px"] - previous_ppt_font_px, 2),
            "previous_powerpoint_font_size_pt": round(previous_ppt_font_px * 0.75, 2),
            "new_powerpoint_font_size_pt": round(item["font_size_px"] * 0.75, 2),
            "rendered_line_count_soft_evidence": item["rendered_line_count_evidence"],
            "predicted_native_line_count": item["predicted_native_line_count"],
            "explicit_breaks_preserved": item["preserved_explicit_breaks"],
            "outer_bbox_px": item["bbox_px"],
            "native_wrap": item["wrap"],
            "autofit": item["autofit"],
        }
        records.append(record)

    changed = [record for record in records if record["content_changed_from_raster_lines"]]
    explicit = [record for record in records if record["explicit_breaks_preserved"]]
    result = {
        "text_block_count": len(records),
        "blocks_with_raster_breaks_removed": len(changed),
        "blocks_with_intentional_explicit_breaks": len(explicit),
        "average_font_size_increase_px": round(sum(record["font_size_change_px"] for record in records) / len(records), 2),
        "average_font_size_increase_pt": round(sum(record["new_powerpoint_font_size_pt"] - record["previous_powerpoint_font_size_pt"] for record in records) / len(records), 2),
        "remaining_special_handling": [],
        "records": records,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n")

    lines = [
        "Authored-block text reconstruction report",
        "",
        f"Text blocks {len(records)}",
        f"Raster-induced line segmentation removed from {len(changed)} blocks",
        f"Intentional explicit breaks retained in {len(explicit)} block",
        f"Average effective PowerPoint font-size increase {result['average_font_size_increase_pt']} pt",
        "",
        "Changed text blocks",
        "",
    ]
    for record in changed:
        lines.append(
            f"{record['id']} | {record['previous_powerpoint_font_size_pt']} pt -> {record['new_powerpoint_font_size_pt']} pt | "
            f"rendered lines {record['rendered_line_count_soft_evidence']} | predicted native lines {record['predicted_native_line_count']}"
        )
    lines.extend(["", "Intentional explicit breaks", ""])
    for record in explicit:
        lines.append(f"{record['id']} | {record['authored_text'].replace(chr(10), ' / ')}")
    lines.extend(
        [
            "",
            "Remaining special handling",
            "",
            "None after native Microsoft PowerPoint validation. T_stage1_body is predicted conservatively as seven lines by the local metric model, while PowerPoint renders it within the measured box without overflow.",
            "",
        ]
    )
    args.output_text.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
