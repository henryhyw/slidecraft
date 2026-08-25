"""Canonical framework naming and temporary migration aliases."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def migrate_deck_and_slide(deck: dict[str, Any], slide: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    deck = deepcopy(deck)
    slide = deepcopy(slide)
    notices: list[str] = []
    libraries = deck.get("local_libraries", {})
    aliases = {
        "template_manifest": "visual_reference_manifest",
        "template_max_results_per_slide": "visual_reference_max_results_per_slide",
    }
    for legacy, canonical in aliases.items():
        if legacy in libraries and canonical not in libraries:
            libraries[canonical] = libraries.pop(legacy)
            notices.append(f"Migrated legacy local_libraries.{legacy} to {canonical}.")
    manifest = libraries.get("visual_reference_manifest")
    if isinstance(manifest, str) and "inputs/template_references/" in manifest:
        libraries["visual_reference_manifest"] = manifest.replace("inputs/template_references/", "inputs/visual_references/")
        notices.append("Migrated the legacy visual-reference directory path.")
    if "fixed_template_references" in slide and "fixed_visual_references" not in slide:
        slide["fixed_visual_references"] = slide.pop("fixed_template_references")
        notices.append("Migrated legacy fixed_template_references to fixed_visual_references.")
    for reference in slide.get("fixed_visual_references", []):
        path = reference.get("path")
        if isinstance(path, str) and "inputs/template_references/" in path:
            reference["path"] = path.replace("inputs/template_references/", "inputs/visual_references/")
            notices.append(f"Migrated the legacy path for {reference.get('reference_id', 'visual reference')}.")
    return deck, slide, notices


def migrate_orchestration_state(state: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    state = deepcopy(state)
    notices: list[str] = []
    if "deck_configuration" in state and "deck_design_configuration" not in state:
        state["deck_design_configuration"] = state.pop("deck_configuration")
        notices.append("Migrated legacy deck_configuration to deck_design_configuration.")
    retrieval = state.get("reference_retrieval", {})
    if "template_references" in retrieval and "visual_references" not in retrieval:
        retrieval["visual_references"] = retrieval.pop("template_references")
        notices.append("Migrated legacy template_references to visual_references.")
    if "template_retrieval" in retrieval and "visual_reference_retrieval" not in retrieval:
        retrieval["visual_reference_retrieval"] = retrieval.pop("template_retrieval")
        notices.append("Migrated legacy template_retrieval to visual_reference_retrieval.")
    return state, notices


def migrate_reconstruction_handoff(handoff: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    handoff = deepcopy(handoff)
    notices: list[str] = []
    if "template_references" in handoff and "visual_references" not in handoff:
        handoff["visual_references"] = handoff.pop("template_references")
        notices.append("Migrated legacy template_references to visual_references.")
    if "template_retrieval" in handoff and "visual_reference_retrieval" not in handoff:
        handoff["visual_reference_retrieval"] = handoff.pop("template_retrieval")
        notices.append("Migrated legacy template_retrieval to visual_reference_retrieval.")
    return handoff, notices
