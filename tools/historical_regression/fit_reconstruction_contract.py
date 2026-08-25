#!/usr/bin/env python3
"""Fit native text and editable line-art geometry from a slide understanding contract."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import ImageFont

from text_authoring import authored_text, logical_paragraphs


FONT_PATHS = {
    ("Arial", False, False): "/System/Library/Fonts/Supplemental/Arial.ttf",
    ("Arial", True, False): "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ("Arial", False, True): "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
    ("Arial", True, True): "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
    ("Georgia", False, False): "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ("Georgia", True, False): "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ("Georgia", False, True): "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    ("Georgia", True, True): "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf",
}

ROLE_SIZE_LIMITS_PX = {
    "slide_title": (42.0, 58.0),
    "subtitle": (18.0, 24.0),
    "stage_number": (20.0, 30.0),
    "stage_title": (17.0, 23.0),
    "stage_body": (15.0, 19.0),
    "card_title": (15.0, 20.0),
    "card_body": (13.0, 17.0),
    "module_title": (15.0, 20.0),
    "module_body": (14.0, 18.0),
    "model_label": (20.0, 27.0),
    "output_label": (22.0, 31.0),
    "page_number": (10.0, 15.0),
}

ROLE_LINE_HEIGHT = {
    "slide_title": 1.02,
    "subtitle": 1.06,
    "stage_number": 1.0,
    "stage_title": 1.04,
    "stage_body": 1.12,
    "card_title": 1.05,
    "card_body": 1.1,
    "module_title": 1.05,
    "module_body": 1.1,
    "model_label": 1.03,
    "output_label": 1.04,
    "page_number": 1.05,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step4", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def text_style(entity: dict[str, Any]) -> dict[str, Any]:
    role = entity["role"]
    hint = entity.get("style_hint", {})
    bold_roles = {"slide_title", "stage_title", "card_title", "module_title", "model_label", "output_label"}
    family = hint.get("font_family") or ("Georgia" if role == "slide_title" else "Arial")
    color = "#E84912" if role in {"model_label", "output_label"} else "#111111"
    if role == "stage_number":
        color = "#FFFFFF"
    color = hint.get("color", color)
    alignment = hint.get("alignment", "center" if role in {"stage_number", "module_title", "model_label", "output_label"} else "left")
    vertical = hint.get("vertical_alignment", "middle" if role == "stage_number" else "top")
    weight = hint.get("font_weight")
    return {
        "family": family,
        "bold": bool(weight >= 600) if isinstance(weight, (int, float)) else role in bold_roles,
        "italic": hint.get("font_style") == "italic",
        "color": color,
        "alignment": alignment,
        "vertical_alignment": vertical,
    }


def semantic_line_boxes(mask: np.ndarray, box: list[int], line_count: int) -> list[list[int]]:
    x, y, w, h = box
    local = mask[y : y + h, x : x + w]
    projection = np.count_nonzero(local, axis=1)
    active = projection > 0
    runs: list[tuple[int, int]] = []
    start = None
    for index, value in enumerate(active):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(active) - 1):
            end = index if not value else index + 1
            if end - start >= 2:
                runs.append((start, end))
            start = None
    if len(runs) > line_count:
        runs = sorted(runs, key=lambda run: int(projection[run[0] : run[1]].sum()), reverse=True)[:line_count]
        runs.sort()
    if len(runs) != line_count:
        runs = [(round(i * h / line_count), round((i + 1) * h / line_count)) for i in range(line_count)]
    results = []
    for top, bottom in runs:
        region = local[top:bottom]
        ys, xs = np.where(region > 0)
        if len(xs):
            results.append([x + int(xs.min()), y + top + int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)])
        else:
            results.append([x, y + top, w, max(1, bottom - top)])
    return results


def measure_line(text: str, family: str, bold: bool, italic: bool, size: int) -> tuple[float, float]:
    font = ImageFont.truetype(FONT_PATHS[(family, bold, italic)], size=size)
    left, top, right, bottom = font.getbbox(text or " ")
    return float(right - left), float(bottom - top)


def wrap_authored_text(text: str, family: str, bold: bool, italic: bool, size: float, width: float) -> tuple[list[str], int]:
    font = ImageFont.truetype(FONT_PATHS[(family, bold, italic)], size=max(1, round(size * 4)))

    def line_width(value: str) -> float:
        return float(font.getlength(value)) / 4

    lines: list[str] = []
    paragraph_breaks = 0
    paragraphs = logical_paragraphs(text)
    for paragraph_index, paragraph in enumerate(paragraphs):
        if paragraph_index:
            paragraph_breaks += 1
        hard_lines = paragraph.split("\n")
        for hard_line in hard_lines:
            words = hard_line.split()
            if not words:
                lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if line_width(candidate) <= width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
    return lines or [""], paragraph_breaks


def fit_text(entity: dict[str, Any], mask: np.ndarray) -> dict[str, Any]:
    style = text_style(entity)
    logical_text, preserved_breaks = authored_text(entity)
    box = entity["measurement"]["layout_bbox"]["px"]
    rendered_line_count = entity["text"].count("\n") + 1
    line_boxes = semantic_line_boxes(mask, box, rendered_line_count)
    x, y, w, h = box
    inset = 0 if entity["role"] in {"slide_title", "stage_number"} else 2
    insets = {"left": inset, "top": inset, "right": inset, "bottom": inset}
    usable_w = max(1, w - insets["left"] - insets["right"])
    usable_h = max(1, h - insets["top"] - insets["bottom"])
    minimum, maximum = ROLE_SIZE_LIMITS_PX.get(entity["role"], (12.0, 20.0))
    line_height_factor = ROLE_LINE_HEIGHT.get(entity["role"], 1.08)
    line_spacing = 0.96 if entity["role"] in {"slide_title", "stage_title", "card_title", "module_title", "model_label", "output_label"} else 1.0
    candidates = []
    size = maximum
    while size >= max(6.0, minimum) - 0.001:
        wrapped_lines, paragraph_breaks = wrap_authored_text(logical_text, style["family"], style["bold"], style["italic"], size, usable_w * 0.94)
        widths = [measure_line(line, style["family"], style["bold"], style["italic"], 400)[0] * size / 400 for line in wrapped_lines]
        block_height = len(wrapped_lines) * size * line_height_factor * line_spacing + paragraph_breaks * size * 0.25
        if max(widths, default=0) <= usable_w * 0.96 and block_height <= usable_h * 0.96:
            score = size - 0.08 * abs(len(wrapped_lines) - rendered_line_count)
            candidates.append((score, size, wrapped_lines, widths, block_height))
        size -= 0.25
    if candidates:
        _, font_size, wrapped_lines, widths, predicted_block_height = max(candidates, key=lambda item: (item[0], item[1]))
    else:
        font_size = max(6.0, minimum - 2)
        wrapped_lines, _ = wrap_authored_text(logical_text, style["family"], style["bold"], style["italic"], font_size, usable_w * 0.94)
        widths = [measure_line(line, style["family"], style["bold"], style["italic"], 400)[0] * font_size / 400 for line in wrapped_lines]
        predicted_block_height = len(wrapped_lines) * font_size * line_height_factor * line_spacing
    predicted_max_width = max(widths, default=0)
    return {
        "id": entity["id"],
        "bbox_px": box,
        "source_text_raw": entity["text"],
        "authored_text": logical_text,
        "logical_paragraphs": logical_paragraphs(logical_text),
        "preserved_explicit_breaks": preserved_breaks,
        "rendered_line_count_evidence": rendered_line_count,
        "predicted_native_wrap_lines": wrapped_lines,
        "predicted_native_line_count": len(wrapped_lines),
        "measured_line_boxes_soft_evidence_px": line_boxes,
        "font_family": style["family"],
        "font_size_px": round(font_size, 2),
        "bold": style["bold"],
        "italic": style["italic"],
        "color": style["color"],
        "alignment": style["alignment"],
        "vertical_alignment": style["vertical_alignment"],
        "line_spacing": round(line_spacing, 3),
        "paragraph_space_before_px": 0,
        "paragraph_space_after_px": 0,
        "insets_px": insets,
        "wrap": "square",
        "autofit": "none",
        "fit_safety_factor": 0.94,
        "predicted_max_line_width_px": round(predicted_max_width, 2),
        "predicted_block_height_px": round(predicted_block_height, 2),
        "usable_width_px": usable_w,
        "usable_height_px": usable_h,
        "predicted_width_ratio": round(predicted_max_width / usable_w, 4),
        "predicted_height_ratio": round(predicted_block_height / usable_h, 4),
    }


def skeletonize(mask: np.ndarray) -> np.ndarray:
    image = (mask > 0).astype(np.uint8) * 255
    skeleton = np.zeros_like(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while cv2.countNonZero(image):
        eroded = cv2.erode(image, kernel)
        opened = cv2.dilate(eroded, kernel)
        skeleton = cv2.bitwise_or(skeleton, cv2.subtract(image, opened))
        image = eroded
    return (skeleton > 0).astype(np.uint8)


NEIGHBORS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def neighbors(pixel: tuple[int, int], pixels: set[tuple[int, int]]) -> list[tuple[int, int]]:
    y, x = pixel
    return [(y + dy, x + dx) for dy, dx in NEIGHBORS if (y + dy, x + dx) in pixels]


def trace_skeleton(skeleton: np.ndarray) -> list[list[tuple[int, int]]]:
    ys, xs = np.where(skeleton > 0)
    pixels = set(zip(ys.tolist(), xs.tolist()))
    if not pixels:
        return []
    degree = {pixel: len(neighbors(pixel, pixels)) for pixel in pixels}
    nodes = {pixel for pixel, value in degree.items() if value != 2}
    visited_edges: set[frozenset[tuple[int, int]]] = set()
    paths: list[list[tuple[int, int]]] = []

    def trace(start: tuple[int, int], nxt: tuple[int, int]) -> list[tuple[int, int]]:
        path = [start, nxt]
        previous, current = start, nxt
        visited_edges.add(frozenset((previous, current)))
        while current not in nodes:
            options = [candidate for candidate in neighbors(current, pixels) if candidate != previous]
            if not options:
                break
            candidate = options[0]
            edge = frozenset((current, candidate))
            if edge in visited_edges:
                break
            path.append(candidate)
            visited_edges.add(edge)
            previous, current = current, candidate
        return path

    for node in nodes:
        for nxt in neighbors(node, pixels):
            if frozenset((node, nxt)) not in visited_edges:
                path = trace(node, nxt)
                if len(path) >= 3:
                    paths.append(path)

    for pixel in pixels:
        for nxt in neighbors(pixel, pixels):
            if frozenset((pixel, nxt)) in visited_edges:
                continue
            path = trace(pixel, nxt)
            if len(path) >= 4:
                paths.append(path)
    return paths


def simplify_path(path: list[tuple[int, int]]) -> list[list[int]]:
    points = np.array([[x, y] for y, x in path], dtype=np.float32).reshape(-1, 1, 2)
    closed = np.linalg.norm(points[0, 0] - points[-1, 0]) <= 2.0
    epsilon = max(0.8, 0.012 * cv2.arcLength(points, closed))
    simplified = cv2.approxPolyDP(points, epsilon, closed).reshape(-1, 2)
    return [[int(round(x)), int(round(y))] for x, y in simplified]


def point_line_distance(point: list[int], start: list[int], end: list[int]) -> float:
    p = np.array(point, dtype=float)
    a = np.array(start, dtype=float)
    b = np.array(end, dtype=float)
    if np.allclose(a, b):
        return float(np.linalg.norm(p - a))
    delta = b - a
    return float(abs(delta[0] * (a - p)[1] - delta[1] * (a - p)[0]) / np.linalg.norm(delta))


def classify_path(points: list[list[int]]) -> tuple[str, dict[str, Any]]:
    if len(points) < 2:
        return "discard", {}
    closed = math.dist(points[0], points[-1]) <= 3
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    bbox = [min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1]
    max_deviation = max(point_line_distance(point, points[0], points[-1]) for point in points)
    if not closed and max_deviation <= 1.5 and math.dist(points[0], points[-1]) >= 5:
        return "line", {"points_px": [points[0], points[-1]]}
    if closed and bbox[2] >= 5 and bbox[3] >= 5:
        center = np.array([bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2])
        radii = [np.linalg.norm(np.array(point) - center) for point in points]
        ratio = bbox[2] / bbox[3]
        if 0.7 <= ratio <= 1.3 and np.std(radii) / max(np.mean(radii), 1) < 0.22:
            return "ellipse", {"bbox_px": bbox}
        if len(points) in {4, 5}:
            return "rect", {"bbox_px": bbox}
    return "custom_path", {"points_px": points, "closed": closed}


def sampled_color(image_rgb: np.ndarray, mask: np.ndarray, box: list[int]) -> str:
    x, y, w, h = box
    pixels = image_rgb[y : y + h, x : x + w][mask[y : y + h, x : x + w] > 0]
    if len(pixels) == 0:
        return "#E84912"
    hsv = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    saturated = pixels[hsv[:, 1] > 100]
    sample = saturated if len(saturated) else pixels
    rgb = np.median(sample, axis=0).astype(int)
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def fit_geometry(entity: dict[str, Any], image_rgb: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    box = entity["measurement"]["layout_bbox"]["px"]
    x, y, w, h = box
    local_mask = mask[y : y + h, x : x + w]
    skeleton_source = local_mask.copy()
    filled_primitives = []
    component_count, component_labels, component_stats, _ = cv2.connectedComponentsWithStats((local_mask > 0).astype(np.uint8), 8)
    for component_index in range(1, component_count):
        area = int(component_stats[component_index, cv2.CC_STAT_AREA])
        component = (component_labels == component_index).astype(np.uint8) * 255
        component_distance = cv2.distanceTransform((component > 0).astype(np.uint8), cv2.DIST_L2, 5)
        if area < 24 or float(component_distance.max()) < 3.2:
            continue
        contours, hierarchy = cv2.findContours(component, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            continue
        for contour_index, contour in enumerate(contours):
            points = contour.reshape(-1, 2)
            if len(points) < 3:
                continue
            epsilon = max(0.8, 0.006 * cv2.arcLength(contour, True))
            points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
            global_points = [[int(point[0] + x), int(point[1] + y)] for point in points]
            parent = int(hierarchy[0][contour_index][3])
            filled_primitives.append({
                "type": "knockout_path" if parent >= 0 else "filled_path",
                "points_px": global_points,
                "closed": True,
            })
        skeleton_source[component > 0] = 0
    skeleton = skeletonize(skeleton_source)
    distance = cv2.distanceTransform((local_mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
    stroke_samples = distance[skeleton > 0]
    stroke_width = float(np.median(stroke_samples) * 2) if len(stroke_samples) else 1.6
    stroke_width = max(1.1, min(2.4, stroke_width))
    primitives = list(filled_primitives)
    for raw_path in trace_skeleton(skeleton):
        if len(raw_path) < 4:
            continue
        points = simplify_path(raw_path)
        if len(points) < 2:
            continue
        points = [[point[0] + x, point[1] + y] for point in points]
        kind, payload = classify_path(points)
        if kind != "discard":
            primitives.append({"type": kind, **payload})
    return {
        "id": entity["id"],
        "semantic_role": entity["role"],
        "bbox_px": box,
        "visible_bbox_px": entity["measurement"]["visible_bbox"]["px"],
        "source": "opencv_selected_mask_skeleton",
        "color": sampled_color(image_rgb, mask, box),
        "stroke_width_px": round(stroke_width, 2),
        "primitives": primitives,
        "primitive_counts": {kind: sum(1 for item in primitives if item["type"] == kind) for kind in ("line", "ellipse", "rect", "custom_path", "filled_path", "knockout_path")},
        "sam_used": False,
    }


def main() -> None:
    args = parse_args()
    step4 = json.loads(args.step4.read_text())
    contract = json.loads(args.contract.read_text())
    image_bgr = cv2.imread(step4["source"]["image"])
    if image_bgr is None:
        raise FileNotFoundError(step4["source"]["image"])
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    entities = {entity["id"]: entity for entity in step4["entities"]}
    text_fits = []
    geometry_fits = []
    for entity in entities.values():
        mask = cv2.imread(entity["measurement"]["selected_mask_absolute"], cv2.IMREAD_GRAYSCALE)
        if mask is None:
            continue
        if entity["kind"] == "text":
            text_fits.append(fit_text(entity, mask))
        if entity["kind"] in {"novel_visual"}:
            geometry_fits.append(fit_geometry(entity, image_rgb, mask))
    contract["fitted_text_contracts"] = text_fits
    contract["fitted_geometry_contracts"] = geometry_fits
    contract["fit_policy"] = {
        "text": "Measured outer geometry is immutable. Font metrics, line spacing, paragraph spacing, and insets are fitted inside it.",
        "line_art": "OpenCV masks are skeletonized and decomposed into lines, ellipses, rectangles, and residual custom paths.",
        "sam": "SAM remains reserved for irregular filled regions and is disabled for thin line art.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "text_fits": len(text_fits),
        "geometry_fits": len(geometry_fits),
        "geometry_primitives": sum(len(item["primitives"]) for item in geometry_fits),
    }, indent=2))


if __name__ == "__main__":
    main()
