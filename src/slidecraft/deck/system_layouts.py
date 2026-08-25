"""Deterministic structural-slide scene generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _box(normalized: list[float], dimensions: list[int]) -> list[int]:
    width, height = dimensions
    return [round(normalized[0] * width), round(normalized[1] * height), round(normalized[2] * width), round(normalized[3] * height)]


def load_layouts(path: Path) -> dict[str, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {layout["system_layout_id"]: layout for layout in raw["layouts"]}


def _style(design: dict[str, Any], role: str) -> dict[str, Any]:
    style = design.get("style", {})
    title = design.get("title", {})
    roles = {
        "deck_title": {"font_family": style.get("display_font", "Georgia"), "font_size_px": 80, "font_weight": "regular", "color": "#111111"},
        "deck_subtitle": {"font_family": style.get("body_font", "Arial"), "font_size_px": 30, "font_weight": "regular", "color": "#4A4A4A"},
        "slide_title": {"font_family": title.get("font_family", style.get("display_font", "Georgia")), "font_size_px": title.get("nominal_size_px", 64), "font_weight": title.get("weight", "regular"), "color": title.get("color", "#111111")},
        "section_number": {"font_family": style.get("body_font", "Arial"), "font_size_px": 92, "font_weight": "bold", "color": "#FFFFFF"},
        "section_title": {"font_family": style.get("display_font", "Georgia"), "font_size_px": 64, "font_weight": "regular", "color": "#111111"},
        "section_subtitle": {"font_family": style.get("body_font", "Arial"), "font_size_px": 28, "font_weight": "regular", "color": "#4A4A4A"},
        "statement": {"font_family": style.get("display_font", "Georgia"), "font_size_px": 58, "font_weight": "regular", "color": "#111111"},
        "metadata": {"font_family": style.get("body_font", "Arial"), "font_size_px": 18, "font_weight": "regular", "color": "#4A4A4A"},
        "body": {"font_family": style.get("body_font", "Arial"), "font_size_px": 24, "font_weight": "regular", "color": "#111111"},
    }
    return {**roles.get(role, roles["body"]), "alignment": "left", "vertical_alignment": "middle"}


def _slot_content(job: dict[str, Any], slot: str, deck_context: dict[str, Any]) -> str:
    section = deck_context.get("section", {})
    values = {
        "title": job["message_title"],
        "subtitle": job["communication_job"],
        "metadata": deck_context.get("metadata", ""),
        "section_number": str(section.get("number", job.get("ordinal", ""))).zfill(2),
        "section_title": section.get("title", job["message_title"]),
        "section_promise": section.get("promise") or job["communication_job"],
        "statement": job["message_title"],
        "attribution": deck_context.get("attribution", ""),
        "closing_message": job["message_title"],
        "next_steps": job["communication_job"],
        "contact": deck_context.get("contact", ""),
    }
    return str(values.get(slot, ""))


def _chrome_objects(job: dict[str, Any], design: dict[str, Any], dimensions: list[int], deck_context: dict[str, Any]) -> list[dict[str, Any]]:
    chrome = design.get("deck_chrome", {})
    exclusions = design.get("exclusions_px", {"header": 0, "footer": 0})
    if not chrome.get("enabled", False):
        return []
    width, height = dimensions
    padding = chrome.get("outer_padding_px", 40)
    header_height, footer_height = exclusions["header"], exclusions["footer"]
    resolved = deck_context.get("resolved_chrome", {})
    variant = resolved.get("variant", {}).get("value") or (
        "content_slide" if job["route"] == "image_generation" else job.get("role", "content_slide")
    )
    header = chrome.get("header", {})
    footer = chrome.get("footer", {})
    header_left = resolved.get("header", {}).get("left_text", {}).get("value", "")
    header_right = resolved.get("header", {}).get("right_text", {}).get("value", "")
    footer_left = resolved.get("footer", {}).get("left_text", {}).get("value", "")
    footer_center = resolved.get("footer", {}).get("center_text", {}).get("value", "")
    footer_right = resolved.get("footer", {}).get("right_text_format", {}).get("value", "")
    family = chrome.get("font_family", design.get("style", {}).get("body_font", "Arial"))
    header_text_height = max(18, header_height - 12)
    header_text_top = max(2, round((header_height - header_text_height) / 2 - 1))
    footer_text_height = max(18, footer_height - 12)
    footer_text_top = height - footer_height + max(3, round((footer_height - footer_text_height) / 2 + 1))

    def chrome_text_style(config: dict[str, Any], *, alignment: str, weight_key: str = "font_weight", secondary: bool = False) -> dict[str, Any]:
        return {
            "font_family": family,
            "font_size_px": config.get("font_size_px", 12),
            "font_weight": "bold" if config.get(weight_key) == "bold" else "regular",
            "color": config.get("secondary_text_color" if secondary else "text_color", "#4A4A4A"),
            "alignment": alignment,
            "vertical_alignment": "middle",
            "margins_px": [0, 0, 0, 0],
            "line_spacing_multiple": 1,
            "paragraph_spacing_px": 0,
            "autofit": "none",
        }
    objects = []
    if header_height > 0:
        objects.extend([
            {"id": "CHROME_HEADER.left", "kind": "textbox", "bbox_px": [padding, header_text_top, round(width * 0.48), header_text_height], "text": header_left, "style": chrome_text_style(header, alignment="left"), "semantic_role": "deck_chrome", "z": 9000},
            {"id": "CHROME_HEADER.right", "kind": "textbox", "bbox_px": [round(width * 0.52), header_text_top, round(width * 0.48) - padding, header_text_height], "text": header_right, "style": chrome_text_style(header, alignment="right", secondary=True), "semantic_role": "deck_chrome", "z": 9000},
            {"id": "CHROME_HEADER.rule", "kind": "shape", "shape": "line", "bbox_px": [padding, max(0, header_height - 1), width - 2 * padding, 0], "style": {"fill": "none", "stroke": header.get("rule_color", "#DED7CF"), "stroke_width_px": header.get("rule_width_px", 1)}, "z": 8999},
            {"id": "CHROME_HEADER.accent", "kind": "shape", "shape": "line", "bbox_px": [padding, max(0, header_height - 1), header.get("accent_rule_width_px", 120), 0], "style": {"fill": "none", "stroke": header.get("accent_color", "#D93900"), "stroke_width_px": 2}, "z": 9000},
        ])
    if footer_height > 0:
        objects.extend([
            {"id": "CHROME_FOOTER.rule", "kind": "shape", "shape": "line", "bbox_px": [padding, height - footer_height, width - 2 * padding, 0], "style": {"fill": "none", "stroke": footer.get("rule_color", "#DED7CF"), "stroke_width_px": footer.get("rule_width_px", 1)}, "z": 9000},
            {"id": "CHROME_FOOTER.left", "kind": "textbox", "bbox_px": [padding, footer_text_top, 420, footer_text_height], "text": footer_left, "style": chrome_text_style(footer, alignment="left", weight_key="left_font_weight"), "semantic_role": "deck_chrome", "z": 9001},
            {"id": "CHROME_FOOTER.center", "kind": "textbox", "bbox_px": [round((width - 600) / 2), footer_text_top, 600, footer_text_height], "text": footer_center, "style": chrome_text_style(footer, alignment="center", secondary=True), "semantic_role": "deck_chrome", "z": 9001},
            {"id": "CHROME_FOOTER.right", "kind": "textbox", "bbox_px": [width - padding - 460, footer_text_top, 460, footer_text_height], "text": footer_right, "style": chrome_text_style(footer, alignment="right", secondary=True), "semantic_role": "deck_chrome", "z": 9001},
        ])
    for item in objects:
        item["chrome_variant"] = variant
    return objects


def build_system_scene(
    *,
    job: dict[str, Any],
    layout: dict[str, Any],
    design: dict[str, Any],
    deck_context: dict[str, Any],
) -> dict[str, Any]:
    dimensions = list(design.get("full_slide_px", [1920, 1080]))
    objects: list[dict[str, Any]] = []
    color_roles = design.get("style", {}).get("brand_inspiration", {}).get("color_roles", {})
    fills = {
        "accent_primary": color_roles.get("signature_orange", "#D93900"),
        "accent_secondary": color_roles.get("bright_orange", "#EB8C00"),
    }
    for index, recipe in enumerate(layout.get("decorative_recipe", []), start=1):
        objects.append({
            "id": f"DECOR_{index:02d}",
            "kind": "shape",
            "shape": recipe["kind"],
            "bbox_px": _box(recipe["box"], dimensions),
            "style": {"fill": fills.get(recipe.get("fill_role"), "#D93900"), "stroke": "none"},
            "z": index,
        })
    for index, slot in enumerate(layout["slots"], start=1):
        if slot["kind"] == "repeating_group":
            sections = deck_context.get("sections", [])
            x, y, w, h = _box(slot["box"], dimensions)
            row_height = h / max(1, len(sections))
            for row, section in enumerate(sections):
                objects.append({
                    "id": f"AGENDA_{row + 1:02d}",
                    "kind": "textbox",
                    "bbox_px": [x, round(y + row * row_height), w, round(row_height)],
                    "text": f"{section['number']:02d}  {section['title']}",
                    "style": {**_style(design, "body"), "font_weight": "bold"},
                    "z": 100 + row,
                })
            continue
        objects.append({
            "id": f"SLOT_{slot['name']}",
            "kind": "textbox",
            "bbox_px": _box(slot["box"], dimensions),
            "text": _slot_content(job, slot["name"], deck_context),
            "style": _style(design, slot["style_role"]),
            "semantic_role": slot["style_role"],
            "z": 100 + index,
        })
    objects.extend(_chrome_objects(job, design, dimensions, deck_context))
    from slidecraft.reconstruction.text_fit import finalize_fitted_text_entities, fit_text_entities

    text_entities = [
        {
            "id": item["id"],
            "kind": "text",
            "role": item.get("semantic_role", "metadata" if item["id"].lower().startswith("chrome_") else "body"),
            "authored_text": item.get("text", ""),
            "measurement": {"layout_bbox": {"px": item["bbox_px"]}},
            "style_hint": {
                "font_family": item["style"].get("font_family"),
                "font_weight": item["style"].get("font_weight"),
                "color": item["style"].get("color"),
                "alignment": item["style"].get("alignment"),
                "vertical_alignment": item["style"].get("vertical_alignment"),
            },
        }
        for item in objects
        if item.get("kind") == "textbox" and item.get("text") and not item["id"].lower().startswith("chrome_")
    ]
    fitted, _ = fit_text_entities(text_entities, design)
    slide_width_inches = float(design.get("slide_width_inches", 13.333333))
    points_per_px = slide_width_inches * 72 / dimensions[0]
    fitted, text_report = finalize_fitted_text_entities(
        text_entities,
        design,
        fitted,
        points_per_px=points_per_px,
        quantization_step_pt=float(design.get("text_reconstruction", {}).get("font_size_quantization_pt", 0.5)),
        absolute_minimum_pt=float(design.get("text_reconstruction", {}).get("absolute_minimum_font_size_pt", 5.0)),
    )
    for item in objects:
        if item["id"] in fitted:
            item["style"].update({
                "font_family": fitted[item["id"]]["font_family"],
                "font_size_px": fitted[item["id"]]["font_size_px"],
                "font_size_pt": fitted[item["id"]]["font_size_pt"],
                "line_spacing_multiple": fitted[item["id"]]["line_spacing"],
                "autofit": "none",
            })
    return {
        "schema_version": "1.0.0",
        "slide_id": job["slide_id"],
        "dimensions_px": dimensions,
        "background": design.get("style", {}).get("background", "#FFFFFF"),
        "design_config_id": design.get("config_id"),
        "system_layout_id": layout["system_layout_id"],
        "objects": sorted(objects, key=lambda item: item["z"]),
        "compiler_report": {"text_fitting": text_report, "route": "deterministic_system_layout"},
    }
