"""Cross-slide checks that protect a common visual and semantic system."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _style_signature(item: dict[str, Any]) -> tuple[Any, ...]:
    style = item.get("style", {})
    return (
        style.get("font_family"),
        style.get("font_weight"),
        style.get("color"),
        style.get("alignment"),
    )


def validate_constructor_deck(
    *, scenes: list[dict[str, Any]], planned_slides: list[dict[str, Any]], deck_design: dict[str, Any]
) -> dict[str, Any]:
    """Reject incomplete or internally inconsistent constructor decks before export."""
    issues: list[dict[str, Any]] = []
    expected = [item["slide_id"] for item in sorted(planned_slides, key=lambda item: item["ordinal"])]
    actual = [scene.get("slide_id") for scene in scenes]
    if actual != expected:
        issues.append({"category": "assembly", "severity": "high", "message": "Constructor scenes do not match deck-plan order", "expected": expected, "actual": actual})
    dimensions = {tuple(scene.get("dimensions_px", [])) for scene in scenes}
    if len(dimensions) != 1:
        issues.append({"category": "canvas", "severity": "high", "message": "Slides use inconsistent canvas dimensions", "values": sorted(dimensions)})
    expected_dimensions = tuple(deck_design.get("full_slide_px", []))
    if expected_dimensions and dimensions != {expected_dimensions}:
        issues.append({"category": "canvas", "severity": "high", "message": "Slide canvas differs from the frozen deck design", "expected": expected_dimensions, "actual": sorted(dimensions)})
    backgrounds = {scene.get("background") for scene in scenes}
    if len(backgrounds) > 1:
        issues.append({"category": "visual_language", "severity": "medium", "message": "Slides use multiple page backgrounds", "values": sorted(str(value) for value in backgrounds)})
    expected_background = deck_design.get("style", {}).get("background")
    if expected_background and backgrounds != {expected_background}:
        issues.append({"category": "visual_language", "severity": "high", "message": "Slide background differs from the frozen deck design", "expected": expected_background, "actual": sorted(str(value) for value in backgrounds)})
    expected_design_id = deck_design.get("config_id")
    design_ids = {scene.get("design_config_id") for scene in scenes}
    if expected_design_id and design_ids != {expected_design_id}:
        issues.append({"category": "visual_language", "severity": "high", "message": "Constructor scenes do not share the frozen design configuration", "expected": expected_design_id, "actual": sorted(str(value) for value in design_ids)})

    planned_by_id = {item["slide_id"]: item for item in planned_slides}
    for scene in scenes:
        planned = planned_by_id.get(scene.get("slide_id"), {})
        if planned.get("route") == "system_layout" and not scene.get("system_layout_id"):
            issues.append({"category": "routing", "severity": "high", "message": "A structural slide is missing its deterministic system layout", "slide_id": scene.get("slide_id")})
        if planned.get("route") == "image_generation" and scene.get("system_layout_id"):
            issues.append({"category": "routing", "severity": "high", "message": "An information-bearing slide was incorrectly replaced by a structural layout", "slide_id": scene.get("slide_id")})

    role_styles: dict[str, list[tuple[str, tuple[Any, ...]]]] = defaultdict(list)
    canonical_roles: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for scene in scenes:
        for item in scene.get("objects", []):
            role = item.get("semantic_role")
            if item.get("kind") == "textbox" and role and role != "deck_chrome":
                role_styles[role].append((scene.get("slide_id"), _style_signature(item)))
            if item.get("kind") == "image" and role and item.get("selected_asset_id"):
                canonical_roles[role].append((scene.get("slide_id"), item["selected_asset_id"]))
    for role, values in role_styles.items():
        if len({signature[:3] for _, signature in values}) > 1:
            issues.append({"category": "typography", "severity": "high", "message": "Repeated semantic text roles use inconsistent family, weight, or color", "role": role, "values": values})
    for role, values in canonical_roles.items():
        if len({asset_id for _, asset_id in values}) > 1:
            issues.append({"category": "canonical_assets", "severity": "medium", "message": "The same semantic icon role maps to multiple canonical assets", "role": role, "values": values})

    expected_connector = deck_design.get("connectors", {})
    expected_stroke = expected_connector.get("stroke", {})
    expected_arrow = expected_connector.get("arrowhead", {})
    for scene in scenes:
        for item in scene.get("objects", []):
            if item.get("kind") != "connector_graph":
                continue
            style = item.get("style", {})
            if expected_stroke.get("color") and style.get("color") != expected_stroke["color"]:
                issues.append({"category": "connectors", "severity": "high", "message": "Connector color differs from the frozen deck style", "slide_id": scene.get("slide_id"), "object_id": item.get("id")})
            if float(style.get("width_px", 0)) < float(expected_stroke.get("width_px", 0)):
                issues.append({"category": "connectors", "severity": "high", "message": "Connector stroke is below the configured minimum", "slide_id": scene.get("slide_id"), "object_id": item.get("id")})
            endpoint = item.get("arrowhead", {}).get("minimum_visible_endpoint_px", 0)
            if float(endpoint) < float(expected_arrow.get("minimum_visible_endpoint_px", 0)):
                issues.append({"category": "connectors", "severity": "high", "message": "Connector arrowhead is below the configured visibility minimum", "slide_id": scene.get("slide_id"), "object_id": item.get("id")})
    if deck_design.get("deck_chrome", {}).get("enabled"):
        missing_chrome = []
        chrome_signatures: dict[str, list[tuple[str, tuple[Any, ...], tuple[Any, ...]]]] = defaultdict(list)
        for scene in scenes:
            ids = {str(item.get("id", "")).lower() for item in scene.get("objects", [])}
            if not any(value.startswith("chrome_header") for value in ids) or not any(value.startswith("chrome_footer") for value in ids):
                missing_chrome.append(scene.get("slide_id"))
            for item in scene.get("objects", []):
                identifier = str(item.get("id", ""))
                if identifier.lower().startswith("chrome_"):
                    chrome_signatures[identifier].append((scene.get("slide_id"), tuple(item.get("bbox_px", [])), _style_signature(item)))
        if missing_chrome:
            issues.append({"category": "deck_chrome", "severity": "high", "message": "Slides are missing deterministic header or footer objects", "slides": missing_chrome})
        for identifier, values in chrome_signatures.items():
            if len(values) != len(scenes) or len({(box, style) for _, box, style in values}) > 1:
                issues.append({"category": "deck_chrome", "severity": "high", "message": "Header or footer geometry and styling is inconsistent across slides", "object_id": identifier, "values": values})
    return {
        "status": "passed" if not any(item["severity"] == "high" for item in issues) else "failed",
        "slide_count": len(scenes),
        "issues": issues,
        "passed": not any(item["severity"] == "high" for item in issues),
    }


def validate_cross_slide_artifacts(slides: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    style_ids = {slide.get("style_config_id") for slide in slides if slide.get("style_config_id")}
    if len(style_ids) > 1:
        issues.append({"category": "design_system", "severity": "high", "message": f"Multiple style snapshots are present: {sorted(style_ids)}"})
    role_values: dict[str, dict[str, list[tuple[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for slide in slides:
        for role, style in slide.get("typography_roles", {}).items():
            for property_name in ("font_family", "font_weight", "color"):
                if property_name in style:
                    role_values[role][property_name].append((slide["slide_id"], style[property_name]))
    for role, properties in role_values.items():
        for property_name, values in properties.items():
            distinct = {value for _, value in values}
            if len(distinct) > 1:
                issues.append({
                    "category": "typography",
                    "severity": "medium",
                    "role": role,
                    "property": property_name,
                    "values": values,
                    "message": f"Peer {role} text uses inconsistent {property_name}",
                })
    asset_roles: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for slide in slides:
        for mapping in slide.get("canonical_assets", []):
            asset_roles[mapping["semantic_role"]].append((slide["slide_id"], mapping["asset_id"]))
    for role, values in asset_roles.items():
        distinct = {asset for _, asset in values}
        if len(distinct) > 1 and not all(value.get("allow_variant", False) for slide in slides for value in slide.get("canonical_assets", []) if value["semantic_role"] == role):
            issues.append({"category": "canonical_assets", "severity": "medium", "role": role, "values": values, "message": "The same semantic icon role maps to multiple assets"})
    terminology = Counter(term for slide in slides for term in slide.get("terminology", []))
    statuses = {slide["slide_id"]: slide.get("status") for slide in slides}
    incomplete = sorted(slide_id for slide_id, status in statuses.items() if status not in {"validated", "ready_for_assembly"})
    if incomplete:
        issues.append({"category": "missing_constructor_scenes", "severity": "high", "message": f"Slides are incomplete: {incomplete}"})
    return {
        "slide_count": len(slides),
        "style_config_ids": sorted(style_ids),
        "shared_terminology": sorted(term for term, count in terminology.items() if count > 1),
        "issues": issues,
        "passed": not any(issue["severity"] == "high" for issue in issues),
    }
