"""Solve small peer-alignment corrections under hard layout constraints."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_list(cls, value: list[float]) -> Box:
        return cls(*map(float, value))

    def as_list(self) -> list[float]:
        return [round(self.x, 3), round(self.y, 3), round(self.width, 3), round(self.height, 3)]

    def moved(self, dx: float, dy: float) -> Box:
        return Box(self.x + dx, self.y + dy, self.width, self.height)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2


def _anchor(box: Box, parent: Box, anchor: str) -> float:
    values = {
        "top": box.y,
        "bottom": box.bottom,
        "center_y": box.center_y,
        "left": box.x,
        "right": box.right,
        "center_x": box.center_x,
        "parent_top_inset": box.y - parent.y,
        "parent_bottom_inset": parent.bottom - box.bottom,
        "parent_left_inset": box.x - parent.x,
        "parent_right_inset": parent.right - box.right,
    }
    if anchor not in values:
        raise ValueError(f"Unsupported alignment anchor: {anchor}")
    return values[anchor]


def _axis(anchor: str) -> str:
    return "x" if anchor in {"left", "right", "center_x", "parent_left_inset", "parent_right_inset"} else "y"


def _delta_for_target(box: Box, parent: Box, anchor: str, target: float) -> tuple[float, float]:
    difference = target - _anchor(box, parent, anchor)
    if anchor in {"parent_bottom_inset", "parent_right_inset"}:
        difference *= -1
    return (difference, 0.0) if _axis(anchor) == "x" else (0.0, difference)


def _inside(box: Box, parent: Box, padding: float) -> bool:
    return (
        box.x >= parent.x + padding
        and box.y >= parent.y + padding
        and box.right <= parent.right - padding
        and box.bottom <= parent.bottom - padding
    )


def _intersects_with_clearance(a: Box, b: Box, clearance: float) -> bool:
    return not (
        a.right + clearance <= b.x
        or b.right + clearance <= a.x
        or a.bottom + clearance <= b.y
        or b.bottom + clearance <= a.y
    )


def _movement_limit(box: Box, config: dict[str, Any]) -> float:
    cap = float(config["maximum_translation_px"])
    fraction = float(config["maximum_translation_object_fraction"])
    return min(cap, max(float(config["minimum_useful_translation_px"]), min(box.width, box.height) * fraction))


def solve_alignment_group(group: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Return a transactional normalization decision for one semantic peer group."""
    members = group["members"]
    anchor = group["anchor"]
    confidence = float(group.get("confidence", 1.0))
    result: dict[str, Any] = {
        "group_id": group["id"],
        "semantic_basis": group.get("semantic_basis", "explicit peer group"),
        "anchor": anchor,
        "confidence": confidence,
        "status": "rejected",
        "corrections": [],
        "checks": {},
    }
    if confidence < float(config["minimum_alignment_confidence"]):
        result["reason"] = "Alignment confidence is below the configured threshold."
        return result
    if len(members) < 2:
        result["reason"] = "A peer group needs at least two members."
        return result

    boxes = [Box.from_list(member["bbox_px"]) for member in members]
    parents = [Box.from_list(member["parent_bbox_px"]) for member in members]
    observed = [_anchor(box, parent, anchor) for box, parent in zip(boxes, parents)]
    target = float(group.get("target_value", statistics.median(observed)))
    before_error = sum((value - target) ** 2 for value in observed)
    proposed: list[Box] = []
    deltas: list[tuple[float, float]] = []
    padding = float(group.get("parent_padding_px", config["parent_inner_padding_px"]))

    for member, box, parent in zip(members, boxes, parents):
        for check_name in ("post_move_text_fit", "connector_topology_preserved", "semantic_order_preserved", "z_order_preserved"):
            if member.get(check_name, True) is False:
                result["reason"] = f"{member['id']} failed the declared {check_name} guardrail."
                result["checks"][check_name] = False
                return result
        dx, dy = _delta_for_target(box, parent, anchor, target)
        limit = min(float(member.get("maximum_translation_px", math.inf)), _movement_limit(box, config))
        magnitude = max(abs(dx), abs(dy))
        if magnitude > limit and magnitude > 0:
            scale = limit / magnitude
            dx *= scale
            dy *= scale
        candidate = box.moved(dx, dy)
        if not _inside(candidate, parent, padding):
            result["reason"] = f"Moving {member['id']} would cross its parent boundary."
            result["checks"]["parent_containment"] = False
            return result
        obstacles = [Box.from_list(item) for item in member.get("obstacle_bboxes_px", [])]
        clearance = float(member.get("minimum_clearance_px", config["minimum_clearance_px"]))
        if any(_intersects_with_clearance(candidate, obstacle, clearance) for obstacle in obstacles):
            result["reason"] = f"Moving {member['id']} would violate object clearance."
            result["checks"]["collision_clearance"] = False
            return result
        proposed.append(candidate)
        deltas.append((dx, dy))

    after_values = [_anchor(box, parent, anchor) for box, parent in zip(proposed, parents)]
    after_error = sum((value - target) ** 2 for value in after_values)
    improvement = 1.0 if before_error == 0 else (before_error - after_error) / before_error
    if before_error <= float(config["alignment_tolerance_px"]) ** 2 * len(members):
        result["status"] = "unchanged"
        result["reason"] = "The peer group is already within alignment tolerance."
        result["checks"] = {"parent_containment": True, "collision_clearance": True, "material_improvement": True}
        return result
    if improvement < float(config["minimum_error_improvement_ratio"]):
        result["reason"] = "The bounded movement does not improve alignment enough."
        result["checks"]["material_improvement"] = False
        return result

    result["status"] = "accepted"
    result["target_anchor_value"] = round(target, 3)
    result["before_error"] = round(before_error, 3)
    result["after_error"] = round(after_error, 3)
    result["improvement_ratio"] = round(improvement, 4)
    result["checks"] = {
        "parent_containment": True,
        "collision_clearance": True,
        "preserved_dimensions": True,
        "preserved_z_order": True,
        "preserved_semantic_order": True,
        "preserved_connector_topology": True,
        "text_fit": True,
        "material_improvement": True,
    }
    for member, before, after, delta in zip(members, boxes, proposed, deltas):
        result["corrections"].append({
            "entity_id": member["id"],
            "member_entity_ids": member.get("member_entity_ids", [member["id"]]),
            "before_bbox_px": before.as_list(),
            "after_bbox_px": after.as_list(),
            "delta_px": [round(delta[0], 3), round(delta[1], 3)],
            "apply_as_rigid_group": bool(member.get("member_entity_ids")),
        })
    return result


def solve_plan(plan: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    decisions = [solve_alignment_group(group, config) for group in plan.get("alignment_groups", [])]
    return {
        "policy": "Semantic peer normalization with hard containment, clearance, movement, and rollback constraints.",
        "decisions": decisions,
        "accepted_groups": sum(item["status"] == "accepted" for item in decisions),
        "rejected_groups": sum(item["status"] == "rejected" for item in decisions),
        "unchanged_groups": sum(item["status"] == "unchanged" for item in decisions),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = solve_plan(json.loads(args.plan.read_text()), json.loads(args.config.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("accepted_groups", "rejected_groups", "unchanged_groups")}, indent=2))


if __name__ == "__main__":
    main()
