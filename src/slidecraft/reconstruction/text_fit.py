"""Office-safe fitting and joint normalization for native textboxes."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import ImageFont

FONT_PATHS = {
    ("Arial", False, False): (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
    ("Arial", True, False): (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    ("Arial", False, True): (
        "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
        "C:/Windows/Fonts/ariali.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    ),
    ("Arial", True, True): (
        "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
        "C:/Windows/Fonts/arialbi.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    ),
    ("Georgia", False, False): (
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ),
    ("Georgia", True, False): (
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "C:/Windows/Fonts/georgiab.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ),
    ("Georgia", False, True): (
        "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
        "C:/Windows/Fonts/georgiai.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    ),
    ("Georgia", True, True): (
        "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf",
        "C:/Windows/Fonts/georgiaz.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-BoldItalic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
    ),
}

def _authored_text(entity: dict[str, Any]) -> str:
    text = str(entity.get("authored_text") or entity.get("source_text") or entity.get("text") or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if (
        entity.get("preserve_explicit_breaks")
        or entity.get("text_structure", {}).get("preserve_explicit_breaks")
        or int(entity.get("paragraphs", 1) or 1) > 1
    ):
        return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")).strip()
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", text)]
    return "\n".join(part for part in paragraphs if part)


def _font_path(family: str, bold: bool, italic: bool) -> str | None:
    candidates = FONT_PATHS.get((family, bold, italic), ()) + FONT_PATHS[("Arial", bold, italic)]
    candidates += FONT_PATHS[("Arial", False, False)]
    return next((candidate for candidate in candidates if Path(candidate).exists()), None)


def _load_font(family: str, bold: bool, italic: bool, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = _font_path(family, bold, italic)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def _wrap(text: str, font: ImageFont.FreeTypeFont, width_px: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.getlength(candidate) <= width_px:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines or [""]


def _role_policy(entity: dict[str, Any], design: dict[str, Any]) -> dict[str, Any]:
    role = entity.get("role", "body")
    policies = design.get("text_reconstruction", {}).get("semantic_role_policies", {})
    return policies.get(role, policies.get("default", {}))


def _base_style(entity: dict[str, Any], design: dict[str, Any]) -> dict[str, Any]:
    hint = entity.get("style_hint", {})
    style = design.get("style", {})
    policy = _role_policy(entity, design)
    family = hint.get("font_family") or policy.get("font_family") or style.get("body_font", "Arial")
    weight = hint.get("font_weight", policy.get("font_weight", 400))
    return {
        "family": family or "Arial",
        "bold": weight == "bold" or (isinstance(weight, (int, float)) and weight >= 600),
        "italic": bool(hint.get("italic", False)),
        "color": hint.get("color", policy.get("color", "#111111")),
        "alignment": hint.get("alignment", policy.get("alignment", "left")),
        "vertical_alignment": hint.get("vertical_alignment", policy.get("vertical_alignment", "top")),
        "role_policy": policy,
    }


def _fits(entity: dict[str, Any], style: dict[str, Any], size_px: float) -> dict[str, Any] | None:
    _, _, width, height = entity["measurement"]["layout_bbox"]["px"]
    policy = style.get("role_policy", {})
    inset = float(policy.get("inset_px", 2))
    usable_width = max(1.0, width - 2 * inset)
    usable_height = max(1.0, height - 2 * inset)
    scaled = max(4, round(size_px * 4))
    font = _load_font(style["family"], style["bold"], style["italic"], scaled)
    office_width = usable_width * 4 * 0.90
    authored = _authored_text(entity)
    if entity.get("bullet_style"):
        authored = "\n".join(f"•  {paragraph}" if paragraph else "" for paragraph in authored.split("\n"))
    lines = _wrap(authored, font, office_width)
    widths = [font.getlength(line or " ") / 4 for line in lines]
    line_height = float(style.get("line_spacing", policy.get("line_spacing", 1.1)))
    block_height = len(lines) * size_px * line_height
    if max(widths, default=0) > usable_width * 0.91 or block_height > usable_height * 0.90:
        return None
    return {
        "lines": lines,
        "max_width_px": round(max(widths, default=0), 2),
        "block_height_px": round(block_height, 2),
        "inset_px": inset,
    }


def _floor_step(value: float, step: float) -> float:
    return int((value + 1e-9) / step) * step


def finalize_fitted_text_entities(
    entities: list[dict[str, Any]],
    design: dict[str, Any],
    fitted: dict[str, dict[str, Any]],
    *,
    points_per_px: float,
    quantization_step_pt: float = 0.5,
    absolute_minimum_pt: float = 5.0,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Revalidate every text contract and emit Office-safe half-point sizes."""
    text_entities = [entity for entity in entities if entity.get("kind") == "text"]
    styles = {entity["id"]: _base_style(entity, design) for entity in text_entities}
    role_policies = design.get("text_reconstruction", {}).get("semantic_role_policies", {})
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in text_entities:
        groups[entity.get("role", "body")].append(entity)

    finalized: dict[str, dict[str, Any]] = {}
    report_groups: list[dict[str, Any]] = []
    for role, members in groups.items():
        available = [fitted[member["id"]] for member in members if member["id"] in fitted]
        if len(available) != len(members):
            generated, _ = fit_text_entities(members, design)
            available = [fitted.get(member["id"], generated[member["id"]]) for member in members]
        for member, source in zip(members, available):
            styles[member["id"]]["line_spacing"] = float(
                source.get("line_spacing", role_policies.get(role, role_policies.get("default", {})).get("line_spacing", 1.1))
            )
        individual: list[dict[str, Any]] = []
        for member, source in zip(members, available):
            candidate_pt = _floor_step(float(source["font_size_px"]) * points_per_px, quantization_step_pt)
            while candidate_pt >= absolute_minimum_pt - 1e-9:
                fit = _fits(member, styles[member["id"]], candidate_pt / points_per_px)
                if fit is not None:
                    individual.append({"member": member, "source": source, "maximum_pt": candidate_pt})
                    break
                candidate_pt -= quantization_step_pt
            else:
                raise ValueError(
                    f"Textbox {member['id']} cannot fit its measured box at {absolute_minimum_pt:g} pt"
                )

        ordered = sorted(individual, key=lambda item: item["maximum_pt"])
        subgroups: list[list[dict[str, Any]]] = []
        for item in ordered:
            if not subgroups or item["maximum_pt"] - subgroups[-1][-1]["maximum_pt"] > 0.5:
                subgroups.append([item])
            else:
                subgroups[-1].append(item)
        assigned_pt = {
            item["member"]["id"]: min(record["maximum_pt"] for record in subgroup)
            for subgroup in subgroups
            for item in subgroup
        }
        evidence: dict[str, dict[str, Any]] = {}
        for item in individual:
            member = item["member"]
            fit = _fits(member, styles[member["id"]], assigned_pt[member["id"]] / points_per_px)
            if fit is None:
                raise ValueError(f"Textbox {member['id']} failed final overflow validation")
            evidence[member["id"]] = fit

        for member, source in zip(members, available):
            candidate_pt = assigned_pt[member["id"]]
            candidate_px = candidate_pt / points_per_px
            item = dict(source)
            item_fit = evidence[member["id"]]
            item.update({
                "font_size_px": candidate_px,
                "font_size_pt": candidate_pt,
                "predicted_native_wrap_lines": item_fit["lines"],
                "predicted_max_line_width_px": item_fit["max_width_px"],
                "predicted_block_height_px": item_fit["block_height_px"],
                "overflow_validation": "passed_after_configured_point_quantization",
            })
            finalized[member["id"]] = item
        report_groups.append({
            "semantic_role": role,
            "member_ids": [member["id"] for member in members],
            "subgroups": [
                {
                    "member_ids": [item["member"]["id"] for item in subgroup],
                    "shared_font_size_pt": min(item["maximum_pt"] for item in subgroup),
                }
                for subgroup in subgroups
            ],
            "split": len(subgroups) > 1,
            "quantization_step_pt": quantization_step_pt,
            "overflow_validation": "passed",
        })
    return finalized, {
        "source": "constructor_final_text_gate",
        "fitted_textbox_count": len(finalized),
        "quantization_step_pt": quantization_step_pt,
        "all_textboxes_passed": True,
        "text_groups": report_groups,
    }


def _largest_size(entities: list[dict[str, Any]], styles: dict[str, dict[str, Any]], maximum: float, minimum: float) -> tuple[float, dict[str, dict[str, Any]]]:
    size = maximum
    while size >= max(6.0, minimum) - 0.001:
        evidence: dict[str, dict[str, Any]] = {}
        for entity in entities:
            fit = _fits(entity, styles[entity["id"]], size)
            if fit is None:
                break
            evidence[entity["id"]] = fit
        else:
            return round(size, 2), evidence
        size -= 0.25
    fallback = max(6.0, minimum - 2)
    return fallback, {entity["id"]: (_fits(entity, styles[entity["id"]], fallback) or {}) for entity in entities}


def fit_text_entities(entities: list[dict[str, Any]], design: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Fit authored text jointly by semantic role with Office-safe metrics."""
    text_entities = [entity for entity in entities if entity.get("kind") == "text"]
    styles = {entity["id"]: _base_style(entity, design) for entity in text_entities}
    role_policies = design.get("text_reconstruction", {}).get("semantic_role_policies", {})
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in text_entities:
        groups[entity.get("role", "body")].append(entity)
    fitted: dict[str, dict[str, Any]] = {}
    report_groups: list[dict[str, Any]] = []
    for role, members in groups.items():
        policy = role_policies.get(role, role_policies.get("default", {}))
        minimum, maximum = policy.get("font_size_range_px", [10.0, 20.0])
        estimated = []
        for member in members:
            value = member.get("measurement", {}).get("text_geometry", {}).get("estimated_font_size_pt")
            if value:
                estimated.append(float(value) * 96 / 72)
        if estimated:
            maximum = min(maximum, max(estimated))
        size, evidence = _largest_size(members, styles, maximum, minimum)
        for member in members:
            style = styles[member["id"]]
            item_evidence = evidence.get(member["id"], {})
            fitted[member["id"]] = {
                "id": member["id"],
                "authored_text": _authored_text(member),
                "font_family": style["family"],
                "font_size_px": size,
                "bold": style["bold"],
                "italic": style["italic"],
                "color": style["color"],
                "alignment": style["alignment"],
                "vertical_alignment": style["vertical_alignment"],
                "line_spacing": policy.get("line_spacing", 1.1),
                "paragraph_space_after_px": 0,
                "insets_px": {side: item_evidence.get("inset_px", 0) for side in ("left", "top", "right", "bottom")},
                "predicted_native_wrap_lines": item_evidence.get("lines", []),
                "predicted_max_line_width_px": item_evidence.get("max_width_px"),
                "predicted_block_height_px": item_evidence.get("block_height_px"),
                "autofit": "none",
                "bullet_style": member.get("bullet_style"),
                "office_width_safety_factor": 0.90,
                "office_height_safety_factor": 0.90,
            }
        report_groups.append({
            "semantic_role": role,
            "member_ids": [member["id"] for member in members],
            "shared_font_size_px": size,
            "font_family": styles[members[0]["id"]]["family"],
            "split": False,
        })
    return fitted, {"text_groups": report_groups, "group_count": len(report_groups), "fitted_textbox_count": len(fitted)}
