#!/usr/bin/env python3
"""Apply bounded system-level alignment and joint typography refinement."""

from __future__ import annotations

import argparse
import copy
import json
import statistics
from pathlib import Path
from typing import Any

from fit_reconstruction_contract import ROLE_LINE_HEIGHT, ROLE_SIZE_LIMITS_PX, measure_line, wrap_authored_text
from slidecraft.refinement.constrained_normalization import solve_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step4", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--report-text", type=Path, required=True)
    parser.add_argument("--normalization-plan", type=Path)
    parser.add_argument("--normalization-config", type=Path, default=Path("config/normalization_config.json"))
    return parser.parse_args()


def apply_constrained_decisions(contract: dict[str, Any], decisions: dict[str, Any]) -> None:
    """Apply accepted rigid translations to known contract geometry stores."""
    text_fits = {item["id"]: item for item in contract.get("fitted_text_contracts", [])}
    icon_maps = {item["entity_id"]: item for item in contract.get("canonical_asset_mappings", [])}
    units = contract.get("reconstruction_units", [])
    overrides = contract.setdefault("alignment_bbox_overrides", {})

    for decision in decisions["decisions"]:
        if decision["status"] != "accepted":
            continue
        for correction in decision["corrections"]:
            dx, dy = correction["delta_px"]
            moved_unit_ids: set[str] = set()
            for entity_id in correction["member_entity_ids"]:
                if entity_id in text_fits:
                    box = list(text_fits[entity_id]["bbox_px"])
                    box[0] += dx
                    box[1] += dy
                    text_fits[entity_id]["bbox_px"] = box
                    overrides[entity_id] = box
                if entity_id in icon_maps:
                    icon = icon_maps[entity_id]
                    for key in ("final_svg_bbox_px", "target_bbox_source_px"):
                        if key in icon:
                            box = list(icon[key])
                            box[0] += dx
                            box[1] += dy
                            icon[key] = box
                    if "slot_center_px" in icon:
                        icon["slot_center_px"] = [icon["slot_center_px"][0] + dx, icon["slot_center_px"][1] + dy]
                for unit in units:
                    if entity_id not in unit.get("entity_ids", []):
                        continue
                    if unit.get("id") in moved_unit_ids:
                        continue
                    box = list(unit.get("bbox_source_px", []))
                    if len(box) == 4:
                        box[0] += dx
                        box[1] += dy
                        unit["bbox_source_px"] = box
                        moved_unit_ids.add(unit.get("id"))


def fits(item: dict[str, Any], size: float, inset: float, line_spacing: float, role: str) -> bool:
    _, _, width, height = item["bbox_px"]
    usable_width = max(1, width - 2 * inset)
    usable_height = max(1, height - 2 * inset)
    lines, paragraph_breaks = wrap_authored_text(
        item["authored_text"], item["font_family"], item["bold"], item["italic"], size, usable_width * 0.94
    )
    widths = [measure_line(line, item["font_family"], item["bold"], item["italic"], 400)[0] * size / 400 for line in lines]
    block_height = len(lines) * size * ROLE_LINE_HEIGHT.get(role, 1.08) * line_spacing + paragraph_breaks * size * 0.25
    return max(widths, default=0) <= usable_width * 0.96 and block_height <= usable_height * 0.96


def solve_group(role: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    minimum, maximum = ROLE_SIZE_LIMITS_PX.get(role, (12.0, 20.0))
    base_spacing = min(float(member["line_spacing"]) for member in members)
    configurations = [
        (2.0, base_spacing),
        (1.0, base_spacing),
        (0.0, base_spacing),
        (1.0, max(0.9, base_spacing - 0.02)),
        (0.0, max(0.9, base_spacing - 0.02)),
        (0.0, max(0.88, base_spacing - 0.04)),
    ]
    size = maximum
    while size >= max(6.0, minimum - 2) - 0.001:
        for inset, spacing in configurations:
            if all(fits(member, size, inset, spacing, role) for member in members):
                return {"font_size_px": round(size, 2), "inset_px": inset, "line_spacing": round(spacing, 3)}
        size -= 0.25
    return {"font_size_px": round(max(6.0, minimum - 2), 2), "inset_px": 0.0, "line_spacing": round(max(0.88, base_spacing - 0.04), 3)}


def joint_typography(contract: dict[str, Any], entities: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fits_by_id = {item["id"]: item for item in contract["fitted_text_contracts"]}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in fits_by_id.values():
        role = entities[item["id"]]["role"]
        grouped.setdefault(role, []).append(item)

    decisions = []
    splits = []
    for role, members in grouped.items():
        if len(members) == 1:
            decision = {
                "group": role,
                "semantic_role": role,
                "members": [members[0]["id"]],
                "shared_font_size_px": members[0]["font_size_px"],
                "shared_font_size_pt": round(members[0]["font_size_px"] * 0.75, 2),
                "inset_px": members[0]["insets_px"]["left"],
                "line_spacing": members[0]["line_spacing"],
                "singleton": True,
            }
            members[0]["typography_group"] = role
            decisions.append(decision)
            continue

        solution = solve_group(role, members)
        median_individual = statistics.median(float(member["font_size_px"]) for member in members)
        limiting = [member for member in members if float(member["font_size_px"]) <= solution["font_size_px"] + 0.25]
        subsets = [(role, members)]
        if len(members) >= 3 and solution["font_size_px"] < median_individual * 0.88 and 0 < len(limiting) < len(members):
            regular = [member for member in members if member not in limiting]
            subsets = [(f"{role}_compact", limiting), (f"{role}_standard", regular)]
            splits.append({
                "semantic_role": role,
                "reason": "One or more members would reduce the shared size below 88 percent of the group median.",
                "compact_members": [member["id"] for member in limiting],
                "standard_members": [member["id"] for member in regular],
            })

        for group_name, subset in subsets:
            group_solution = solve_group(role, subset)
            for member in subset:
                member["individual_font_size_before_refinement_px"] = member["font_size_px"]
                member["font_size_px"] = group_solution["font_size_px"]
                member["line_spacing"] = group_solution["line_spacing"]
                inset = group_solution["inset_px"]
                member["insets_px"] = {"left": inset, "top": inset, "right": inset, "bottom": inset}
                member["typography_group"] = group_name
            decisions.append({
                "group": group_name,
                "semantic_role": role,
                "members": [member["id"] for member in subset],
                "shared_font_size_px": group_solution["font_size_px"],
                "shared_font_size_pt": round(group_solution["font_size_px"] * 0.75, 2),
                "inset_px": group_solution["inset_px"],
                "line_spacing": group_solution["line_spacing"],
                "singleton": len(subset) == 1,
            })
    return decisions, splits


def apply_alignment(contract: dict[str, Any], step4: dict[str, Any]) -> list[dict[str, Any]]:
    entities = {item["id"]: item for item in step4["entities"]}
    text_fits = {item["id"]: item for item in contract["fitted_text_contracts"]}
    icons = {item["entity_id"]: item for item in contract["canonical_asset_mappings"]}
    overrides: dict[str, list[float]] = {}
    corrections = []

    stage_groups = [group for group in step4["groups"] if group["role"].startswith("architecture_stage")]
    badge_records = []
    for group in stage_groups:
        container = next((entities[child] for child in group["children"] if entities.get(child, {}).get("role") in {"stage_container", "stage_container_emphasis"}), None)
        badge = next((entities[child] for child in group["children"] if entities.get(child, {}).get("role") == "stage_badge"), None)
        number = next((entities[child] for child in group["children"] if entities.get(child, {}).get("role") == "stage_number"), None)
        if container and badge and number:
            badge_records.append((container, badge, number, badge["measurement"]["layout_bbox"]["px"][0] - container["measurement"]["layout_bbox"]["px"][0]))
    if badge_records:
        shared_inset = round(statistics.median(record[3] for record in badge_records))
        for container, badge, number, old_inset in badge_records:
            delta = shared_inset - old_inset
            if abs(delta) <= 4 and delta:
                for entity in (badge, number):
                    box = list(entity["measurement"]["layout_bbox"]["px"])
                    box[0] += delta
                    overrides[entity["id"]] = box
                    if entity["id"] in text_fits:
                        text_fits[entity["id"]]["bbox_px"] = box
                corrections.append({"relationship": "shared_stage_badge_inset", "entities": [badge["id"], number["id"]], "delta_px": [delta, 0], "shared_inset_px": shared_inset})

    module_groups = [group for group in step4["groups"] if group["role"] in {"understanding_module", "reconstruction_module"}]
    title_insets = []
    module_records = []
    for group in module_groups:
        background = next(entities[child] for child in group["children"] if entities[child]["kind"] == "shape")
        title = next(entities[child] for child in group["children"] if entities[child]["role"] == "module_title")
        icon = next(
            (
                entities[child]
                for child in group["children"]
                if entities.get(child, {}).get("kind") in {"icon", "icon_slot"}
            ),
            None,
        )
        if icon is None:
            continue
        bg_box = background["measurement"]["layout_bbox"]["px"]
        title_box = title["measurement"]["layout_bbox"]["px"]
        title_insets.append(title_box[1] - bg_box[1])
        module_records.append((background, title, icon))
    shared_title_inset = statistics.median(title_insets) if title_insets else 0
    for background, title, icon in module_records:
        bg_box = background["measurement"]["layout_bbox"]["px"]
        title_box = list(text_fits[title["id"]]["bbox_px"])
        target_y = bg_box[1] + shared_title_inset
        delta_y = round(target_y - title_box[1], 2)
        if abs(delta_y) <= 2 and delta_y:
            title_box[1] = target_y
            text_fits[title["id"]]["bbox_px"] = title_box
            overrides[title["id"]] = title_box
            corrections.append({"relationship": "shared_module_title_top_inset", "entities": [title["id"]], "delta_px": [0, delta_y], "shared_inset_px": shared_title_inset})
        icon_map = icons.get(icon["id"])
        if not icon_map or "final_svg_bbox_px" not in icon_map:
            continue
        icon_box = list(icon_map["final_svg_bbox_px"])
        target_center = bg_box[0] + bg_box[2] / 2
        delta_x = round(target_center - (icon_box[0] + icon_box[2] / 2), 2)
        if abs(delta_x) <= 3 and delta_x:
            icon_box[0] += delta_x
            icon_map["final_svg_bbox_px"] = icon_box
            corrections.append({"relationship": "center_module_icon", "entities": [icon["id"]], "delta_px": [delta_x, 0]})

    reference_groups = [group for group in step4["groups"] if group["role"] == "reference_card"]
    for group in reference_groups:
        background = next(entities[child] for child in group["children"] if entities[child]["kind"] == "shape")
        icon = next((entities[child] for child in group["children"] if entities[child]["kind"] in {"icon", "icon_slot"}), None)
        if icon is None:
            continue
        bg_box = background["measurement"]["layout_bbox"]["px"]
        icon_map = icons.get(icon["id"])
        if not icon_map or "final_svg_bbox_px" not in icon_map:
            continue
        icon_box = list(icon_map["final_svg_bbox_px"])
        target_center = bg_box[1] + bg_box[3] / 2
        delta_y = round(target_center - (icon_box[1] + icon_box[3] / 2), 2)
        if abs(delta_y) <= 3 and delta_y:
            icon_box[1] += delta_y
            icon_map["final_svg_bbox_px"] = icon_box
            corrections.append({"relationship": "center_reference_icon", "entities": [icon["id"]], "delta_px": [0, delta_y]})

    output_group = next((group for group in step4["groups"] if group["role"] == "editable_output"), None)
    if output_group:
        icon = next((entities[child] for child in output_group["children"] if entities[child]["kind"] in {"icon", "icon_slot"}), None)
        label = next((entities[child] for child in output_group["children"] if entities[child]["kind"] == "text"), None)
        icon_map = icons.get(icon["id"]) if icon else None
        if icon is None or label is None or not icon_map or "final_svg_bbox_px" not in icon_map:
            contract["alignment_bbox_overrides"] = overrides
            return corrections
        icon_box = list(icon_map["final_svg_bbox_px"])
        label_box = text_fits[label["id"]]["bbox_px"]
        delta_x = round(label_box[0] + label_box[2] / 2 - (icon_box[0] + icon_box[2] / 2), 2)
        if abs(delta_x) <= 2 and delta_x:
            icon_box[0] += delta_x
            icon_map["final_svg_bbox_px"] = icon_box
            corrections.append({"relationship": "center_output_icon_and_label", "entities": [icon["id"], label["id"]], "delta_px": [delta_x, 0]})

    contract["alignment_bbox_overrides"] = overrides
    return corrections


def main() -> None:
    args = parse_args()
    step4 = json.loads(args.step4.read_text())
    contract = copy.deepcopy(json.loads(args.contract.read_text()))
    entities = {item["id"]: item for item in step4["entities"]}
    typography, splits = joint_typography(contract, entities)
    alignment = apply_alignment(contract, step4)
    constrained = None
    if args.normalization_plan:
        constrained = solve_plan(
            json.loads(args.normalization_plan.read_text()),
            json.loads(args.normalization_config.read_text()),
        )
        apply_constrained_decisions(contract, constrained)
        for decision in constrained["decisions"]:
            if decision["status"] == "accepted":
                alignment.extend({
                    "relationship": decision["group_id"],
                    "entities": correction["member_entity_ids"],
                    "delta_px": correction["delta_px"],
                    "constraint_checks": decision["checks"],
                } for correction in decision["corrections"])
    contract["refinement_pass"] = {
        "policy": "Bounded semantic-system normalization after initial reconstruction fit.",
        "typography_groups": typography,
        "group_splits": splits,
        "alignment_corrections": alignment,
        "constrained_normalization": constrained,
        "maximum_alignment_correction_px": max((max(abs(value) for value in item["delta_px"]) for item in alignment), default=0),
    }
    args.output.write_text(json.dumps(contract, indent=2) + "\n")
    report = contract["refinement_pass"]
    args.report_json.write_text(json.dumps(report, indent=2) + "\n")
    lines = ["Reasoning-guided reconstruction refinement report", "", "Alignment corrections", ""]
    for item in alignment:
        lines.append(f"{item['relationship']} | {', '.join(item['entities'])} | delta {item['delta_px']} px")
    lines.extend(["", "Joint typography groups", ""])
    for item in typography:
        lines.append(f"{item['group']} | {item['shared_font_size_pt']} pt | inset {item['inset_px']} px | line spacing {item['line_spacing']} | {', '.join(item['members'])}")
    lines.extend(["", "Group splits", ""])
    if splits:
        for item in splits:
            lines.append(f"{item['semantic_role']} | compact {', '.join(item['compact_members'])} | standard {', '.join(item['standard_members'])} | {item['reason']}")
    else:
        lines.append("None")
    lines.append("")
    args.report_text.write_text("\n".join(lines))
    print(json.dumps({"typography_groups": len(typography), "group_splits": len(splits), "alignment_corrections": len(alignment), "max_correction_px": contract["refinement_pass"]["maximum_alignment_correction_px"]}, indent=2))


if __name__ == "__main__":
    main()
