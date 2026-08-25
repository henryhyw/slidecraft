"""Decide whether an entity merits an expensive segmentation prompt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ELIGIBLE_ROLES = {"irregular_filled_boundary", "photo_subject", "overlapping_filled_object"}


@dataclass(frozen=True)
class SegmentationDecision:
    use_segmentation: bool
    reason: str


def decide_segmentation(entity: dict[str, Any], *, mode: str = "auto") -> SegmentationDecision:
    if mode == "off":
        return SegmentationDecision(False, "segmentation_disabled")
    kind = entity.get("kind")
    role = entity.get("segmentation_role", "none")
    if kind in {"text", "table", "chart", "connector", "icon", "icon_slot", "shape"}:
        return SegmentationDecision(False, f"{kind}_uses_deterministic_or_canonical_reconstruction")
    if role in ELIGIBLE_ROLES:
        return SegmentationDecision(True, f"eligible_role:{role}")
    return SegmentationDecision(False, "no_irregular_filled_boundary_requirement")


def sam_eligible_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter prompts before importing or loading the segmentation runtime."""
    eligible = []
    for entity in entities:
        if not entity.get("sam_prompt"):
            continue
        role = entity.get("segmentation_role")
        if role in ELIGIBLE_ROLES or entity.get("kind") == "novel_visual":
            eligible.append(entity)
    return eligible
