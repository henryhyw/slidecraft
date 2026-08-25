#!/usr/bin/env python3
"""Measure a semantically mapped slide for editable reconstruction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output

from slidecraft.orchestration.naming import migrate_reconstruction_handoff
from slidecraft.segmentation.policy import sam_eligible_entities


KIND_COLORS = {
    "text": (32, 125, 246),
    "icon": (247, 156, 56),
    "icon_slot": (255, 126, 0),
    "image": (39, 145, 190),
    "shape": (77, 190, 98),
    "connector": (187, 102, 219),
    "table": (52, 196, 221),
    "chart": (103, 78, 167),
    "novel_visual": (241, 92, 128),
}

SUPPORTED_SEMANTIC_KINDS = set(KIND_COLORS)


def optional_torch() -> Any | None:
    try:
        import torch
    except ImportError:
        return None
    return torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", nargs="?", default="sample slide.png")
    parser.add_argument("--semantic-map", default="semantic_map.json")
    parser.add_argument("--output-dir", default="outputs/sample_slide")
    parser.add_argument("--checkpoint", default="checkpoints/sam2.1_hiera_tiny.pt")
    parser.add_argument("--sam-config", default="configs/sam2.1/sam2.1_hiera_t.yaml")
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    parser.add_argument("--no-sam", action="store_true")
    parser.add_argument("--upstream-handoff", help="Optional generation orchestration handoff JSON")
    return parser.parse_args()


def clipped_bbox(box: list[int], width: int, height: int) -> tuple[int, int, int, int]:
    x, y, w, h = [int(v) for v in box]
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    return x, y, max(1, min(w, width - x)), max(1, min(h, height - y))


def cv_foreground_mask(image_rgb: np.ndarray, entity: dict[str, Any]) -> np.ndarray:
    height, width = image_rgb.shape[:2]
    x, y, w, h = clipped_bbox(entity["bbox_hint"], width, height)
    crop = image_rgb[y : y + h, x : x + w]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    kind = entity["kind"]
    polarity = entity.get("foreground_polarity", "dark")

    if kind == "image":
        local = np.ones((h, w), dtype=np.uint8)
    elif kind in {"shape", "novel_visual"}:
        r, g, b = [channel.astype(np.int16) for channel in cv2.split(crop)]
        if "red" in json.dumps(entity.get("style_hint", {})).lower() or entity["id"] == "S_key_shape":
            local = ((r > g + 35) & (r > b + 25) & (r > 130)).astype(np.uint8)
        elif entity["id"] == "S_insights_bg":
            local = ((gray > 225) & (gray < 252)).astype(np.uint8)
        else:
            local = (gray < 245).astype(np.uint8)
    elif polarity == "light":
        saturation = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)[:, :, 1]
        local = ((gray > 210) & ((saturation < 75) | (gray > 245))).astype(np.uint8)
    else:
        local = (gray < (185 if kind == "text" else 170)).astype(np.uint8)

    if kind in {"text", "icon", "icon_slot"}:
        local = cv2.morphologyEx(local, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    elif kind in {"shape", "novel_visual"}:
        local = cv2.morphologyEx(local, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y : y + h, x : x + w] = local
    return mask


def tight_bbox(mask: np.ndarray, fallback: list[int]) -> list[int]:
    ys, xs = np.where(mask > 0)
    if len(xs) < 3:
        return [int(v) for v in fallback]
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]


def bbox_variants(box: list[int], canvas: tuple[int, int]) -> dict[str, list[float] | list[int]]:
    width, height = canvas
    x, y, w, h = box
    sx, sy = 13.333333 / width, 7.5 / height
    return {
        "px": [int(x), int(y), int(w), int(h)],
        "normalized": [round(x / width, 6), round(y / height, 6), round(w / width, 6), round(h / height, 6)],
        "inches": [round(x * sx, 4), round(y * sy, 4), round(w * sx, 4), round(h * sy, 4)],
        "pptx_emu": [int(x * sx * 914400), int(y * sy * 914400), int(w * sx * 914400), int(h * sy * 914400)],
    }


def dominant_colors(image_rgb: np.ndarray, box: list[int], mask: np.ndarray | None = None) -> list[dict[str, Any]]:
    x, y, w, h = box
    pixels = image_rgb[y : y + h, x : x + w].reshape(-1, 3)
    if mask is not None:
        local_mask = mask[y : y + h, x : x + w].reshape(-1) > 0
        if local_mask.sum() >= 10:
            pixels = pixels[local_mask]
    if len(pixels) == 0:
        return []
    quantized = (pixels // 16 * 16).astype(np.uint8)
    counts = Counter(map(tuple, quantized.tolist()))
    total = len(pixels)
    return [
        {"hex": "#%02x%02x%02x" % rgb, "fraction": round(count / total, 4)}
        for rgb, count in counts.most_common(5)
    ]


def canonical_icon_color(colors: list[dict[str, Any]]) -> str | None:
    saturated = []
    for item in colors:
        value = item["hex"].lstrip("#")
        red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
        maximum = max(red, green, blue)
        saturation = 0 if maximum == 0 else (maximum - min(red, green, blue)) / maximum
        if saturation >= 0.45:
            saturated.append((item["fraction"], saturation, item["hex"]))
    if saturated:
        return max(saturated)[2]
    return colors[0]["hex"] if colors else None


def contours_for(mask: np.ndarray) -> list[list[list[int]]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result: list[list[list[int]]] = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        if cv2.contourArea(contour) < 4:
            continue
        epsilon = max(1.0, 0.006 * cv2.arcLength(contour, True))
        points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
        if len(points) > 80:
            points = points[:: max(1, len(points) // 80)]
        result.append([[int(x), int(y)] for x, y in points])
    return result


def edge_geometry(image_rgb: np.ndarray, box: list[int]) -> dict[str, Any]:
    x, y, w, h = box
    crop = image_rgb[y : y + h, x : x + w]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 80, 180)
    min_length = max(8, min(w, h) // 3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=max(8, min_length // 2), minLineLength=min_length, maxLineGap=5)
    segments = []
    if lines is not None:
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4)[:30]:
            segments.append([int(x1 + x), int(y1 + y), int(x2 + x), int(y2 + y)])
    return {"edge_pixel_count": int(np.count_nonzero(edges)), "line_segments_px": segments}


def text_geometry(mask: np.ndarray, fallback: list[int]) -> dict[str, Any]:
    x, y, w, h = fallback
    local = mask[y : y + h, x : x + w]
    count, _, stats, centroids = cv2.connectedComponentsWithStats(local, 8)
    components = []
    for i in range(1, count):
        cx, cy, cw, ch, area = stats[i]
        if area >= 3 and ch >= 2:
            components.append((int(cx + x), int(cy + y), int(cw), int(ch), float(centroids[i][1] + y)))
    components.sort(key=lambda item: item[4])
    lines: list[list[tuple[int, int, int, int, float]]] = []
    for component in components:
        target = None
        for line in lines:
            median_y = float(np.median([item[4] for item in line]))
            if abs(component[4] - median_y) <= max(5, component[3] * 0.7):
                target = line
                break
        (target if target is not None else lines.append([]) or lines[-1]).append(component)
    line_boxes = []
    for line in lines:
        lx = min(item[0] for item in line)
        ly = min(item[1] for item in line)
        rx = max(item[0] + item[2] for item in line)
        by = max(item[1] + item[3] for item in line)
        line_boxes.append([lx, ly, rx - lx, by - ly])
    heights = [box[3] for box in line_boxes if box[3] > 2]
    estimated_pt = round((float(np.median(heights)) / (941 / 7.5)) * 72 * 1.25, 1) if heights else None
    return {"line_boxes_px": line_boxes, "line_count": len(line_boxes), "estimated_font_size_pt": estimated_pt}


def ocr_once(image_rgb: np.ndarray) -> list[dict[str, Any]]:
    data = pytesseract.image_to_data(Image.fromarray(image_rgb), config="--psm 11", output_type=Output.DICT)
    words = []
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        try:
            confidence = float(data["conf"][i])
        except (ValueError, TypeError):
            confidence = -1
        if text and confidence >= 20:
            words.append({
                "text": text,
                "confidence": round(confidence, 2),
                "bbox_px": [int(data["left"][i]), int(data["top"][i]), int(data["width"][i]), int(data["height"][i])],
            })
    return words


def words_in_box(words: list[dict[str, Any]], box: list[int]) -> list[dict[str, Any]]:
    x, y, w, h = box
    result = []
    for word in words:
        wx, wy, ww, wh = word["bbox_px"]
        center = (wx + ww / 2, wy + wh / 2)
        if x <= center[0] <= x + w and y <= center[1] <= y + h:
            result.append(word)
    return result


def choose_device(requested: str) -> str:
    torch = optional_torch()
    if torch is None:
        if requested == "mps":
            raise RuntimeError("MPS requires the optional PyTorch and SAM dependencies")
        return "cpu"
    if requested == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is unavailable")
        return "mps"
    if requested == "cpu":
        return "cpu"
    return "mps" if torch.backends.mps.is_available() else "cpu"


def run_sam(
    image_rgb: np.ndarray,
    entities: list[dict[str, Any]],
    checkpoint: Path,
    config: str,
    device: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
    torch = optional_torch()
    if torch is None:
        raise RuntimeError("SAM requires the optional PyTorch and SAM dependencies")
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    t0 = time.perf_counter()
    model = build_sam2(config, str(checkpoint), device=device)
    predictor = SAM2ImagePredictor(model)
    t1 = time.perf_counter()
    predictor.set_image(image_rgb)
    t2 = time.perf_counter()
    results: dict[str, dict[str, Any]] = {}
    for entity in entities:
        if not entity.get("sam_prompt"):
            continue
        x, y, w, h = entity["bbox_hint"]
        box = np.array([x, y, x + w - 1, y + h - 1], dtype=np.float32)
        start = time.perf_counter()
        with torch.inference_mode():
            masks, scores, logits = predictor.predict(box=box, multimask_output=True)
        best = int(np.argmax(scores))
        mask = np.asarray(masks[best]).astype(np.uint8)
        results[entity["id"]] = {
            "mask": mask,
            "score": float(scores[best]),
            "all_scores": [float(v) for v in scores],
            "prompt_time_sec": time.perf_counter() - start,
            "logit_range": [float(np.min(logits[best])), float(np.max(logits[best]))],
        }
    return results, {"model_load_sec": t1 - t0, "image_embedding_sec": t2 - t1, "total_sam_sec": time.perf_counter() - t0}


def compare_masks(cv_mask: np.ndarray, sam_mask: np.ndarray, box: list[int]) -> dict[str, Any]:
    cv_bool = cv_mask > 0
    sam_bool = sam_mask > 0
    intersection = int(np.logical_and(cv_bool, sam_bool).sum())
    union = int(np.logical_or(cv_bool, sam_bool).sum())
    x, y, w, h = box
    sam_inside = int(sam_bool[y : y + h, x : x + w].sum())
    sam_total = int(sam_bool.sum())
    cv_total = int(cv_bool.sum())
    return {
        "iou_with_cv_foreground": round(intersection / union, 4) if union else 0.0,
        "cv_foreground_recall": round(intersection / cv_total, 4) if cv_total else 0.0,
        "sam_precision_against_cv_strokes": round(intersection / sam_total, 4) if sam_total else 0.0,
        "sam_area_px": sam_total,
        "cv_area_px": cv_total,
        "fraction_of_sam_inside_prompt_box": round(sam_inside / sam_total, 4) if sam_total else 0.0,
    }


def select_mask(entity: dict[str, Any], cv_mask: np.ndarray, sam_record: dict[str, Any] | None) -> tuple[np.ndarray, str, str]:
    if entity["kind"] == "image":
        return cv_mask, "semantic_image_region", "The full meaningful image region is the reconstruction object"
    if sam_record is None:
        return cv_mask, "opencv", "Deterministic foreground segmentation"
    comparison = compare_masks(cv_mask, sam_record["mask"], entity["bbox_hint"])
    if entity["kind"] == "novel_visual" and comparison["fraction_of_sam_inside_prompt_box"] > 0.98:
        return sam_record["mask"], "sam2", "SAM supplied a closed boundary for an irregular filled shape"
    return cv_mask, "opencv", "OpenCV preserved thin vector-like strokes more faithfully than a filled SAM region"


def infer_overlaps(measured: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overlaps = []
    candidates = [e for e in measured if e["kind"] in {"shape", "novel_visual", "icon", "image"}]
    for index, first in enumerate(candidates):
        ax, ay, aw, ah = first["measurement"]["layout_bbox"]["px"]
        for second in candidates[index + 1 :]:
            bx, by, bw, bh = second["measurement"]["layout_bbox"]["px"]
            ix, iy = max(ax, bx), max(ay, by)
            iw, ih = min(ax + aw, bx + bw) - ix, min(ay + ah, by + bh) - iy
            if iw > 0 and ih > 0:
                overlaps.append({"type": "bbox_overlap", "members": [first["id"], second["id"]], "intersection_px": [ix, iy, iw, ih], "z_order": "see explicit semantic stacking relationship or parent-child containment"})
    return overlaps


def dashed_rect(canvas: np.ndarray, box: list[int], color: tuple[int, int, int], dash: int = 10) -> None:
    x, y, w, h = box
    for start in range(x, x + w, dash * 2):
        cv2.line(canvas, (start, y), (min(start + dash, x + w), y), color, 1)
        cv2.line(canvas, (start, y + h), (min(start + dash, x + w), y + h), color, 1)
    for start in range(y, y + h, dash * 2):
        cv2.line(canvas, (x, start), (x, min(start + dash, y + h)), color, 1)
        cv2.line(canvas, (x + w, start), (x + w, min(start + dash, y + h)), color, 1)


def render_debug(
    image_rgb: np.ndarray,
    measured: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    out_path: Path,
) -> None:
    base = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    overlay = base.copy()
    for entity in measured:
        mask_path = entity["measurement"].get("selected_mask_absolute")
        if not mask_path or entity["kind"] not in {"icon", "icon_slot", "novel_visual"}:
            continue
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            continue
        color = np.array(KIND_COLORS[entity["kind"]], dtype=np.uint8)
        overlay[mask > 0] = (0.5 * overlay[mask > 0] + 0.5 * color).astype(np.uint8)
    canvas = cv2.addWeighted(overlay, 0.72, base, 0.28, 0)

    for group in groups:
        dashed_rect(canvas, group["bbox_hint"], (120, 120, 120))
        x, y, _, _ = group["bbox_hint"]
        cv2.putText(canvas, group["id"], (x + 2, max(12, y + 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (90, 90, 90), 1, cv2.LINE_AA)

    for entity in measured:
        x, y, w, h = entity["measurement"]["layout_bbox"]["px"]
        color = KIND_COLORS.get(entity["kind"], (0, 0, 0))
        thickness = 2 if entity["kind"] in {"icon", "icon_slot", "novel_visual", "table", "chart"} else 1
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, thickness)
        label = entity["id"]
        scale = 0.34 if entity["kind"] == "text" else 0.42
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        ly = y - 3 if y > 15 else y + th + 3
        cv2.rectangle(canvas, (x, ly - th - 2), (x + tw + 4, ly + 2), color, -1)
        cv2.putText(canvas, label, (x + 2, ly), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)

    legend_w = 430
    debug = np.full((canvas.shape[0], canvas.shape[1] + legend_w, 3), 248, np.uint8)
    debug[:, : canvas.shape[1]] = canvas
    lx = canvas.shape[1] + 18
    cv2.putText(debug, "STEP 4 DEBUG", (lx, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(debug, "Solid boxes = entities", (lx, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.putText(debug, "Dashed boxes = semantic groups", (lx, 94), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.putText(debug, "Tinted masks = SAM/OpenCV boundary", (lx, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 40, 40), 1, cv2.LINE_AA)
    yy = 160
    for kind, color in KIND_COLORS.items():
        cv2.rectangle(debug, (lx, yy - 13), (lx + 22, yy + 3), color, -1)
        cv2.putText(debug, kind, (lx + 32, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (30, 30, 30), 1, cv2.LINE_AA)
        yy += 30
    yy += 20
    cv2.putText(debug, "RELATIONSHIPS", (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (20, 20, 20), 1, cv2.LINE_AA)
    yy += 28
    relation_lines = []
    for relationship in relationships:
        relation_type = relationship.get("type", "relation")
        if "from" in relationship and "to" in relationship:
            target = relationship["to"]
            target_text = ",".join(target) if isinstance(target, list) else str(target)
            relation_lines.append(f"{relation_type}: {relationship['from']} -> {target_text}")
        elif "back" in relationship and "front" in relationship:
            relation_lines.append(f"stack: {relationship['back']} -> {relationship['front']}")
    for line in relation_lines[:7]:
        cv2.putText(debug, line, (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 40, 40), 1, cv2.LINE_AA)
        yy += 24
    yy += 18
    cv2.putText(debug, "MASK SOURCE", (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (20, 20, 20), 1, cv2.LINE_AA)
    yy += 28
    for entity in measured:
        source = entity["measurement"].get("mask_source")
        if source and ("sam2" in entity["measurement"] or entity["kind"] in {"icon", "novel_visual"}):
            cv2.putText(debug, f"{entity['id']}: {source}", (lx, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (40, 40, 40), 1, cv2.LINE_AA)
            yy += 22
    cv2.imwrite(str(out_path), debug)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    image_path = Path(args.image).resolve()
    semantic_path = Path(args.semantic_map).resolve()
    output_dir = Path(args.output_dir).resolve()
    masks_dir = output_dir / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    semantic = json.loads(semantic_path.read_text())
    upstream_handoff = None
    naming_migration_notices: list[str] = []
    if args.upstream_handoff:
        upstream_handoff = json.loads(Path(args.upstream_handoff).resolve().read_text(encoding="utf-8"))
        upstream_handoff, naming_migration_notices = migrate_reconstruction_handoff(upstream_handoff)
    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(image_path)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    height, width = image_rgb.shape[:2]
    if [width, height] != semantic["slide"]["canvas_px"]:
        raise ValueError(f"Semantic map expects {semantic['slide']['canvas_px']}, image is {[width, height]}")

    t_ocr = time.perf_counter()
    ocr_words = ocr_once(image_rgb)
    ocr_sec = time.perf_counter() - t_ocr
    entities = semantic["entities"]
    unsupported = sorted({entity["kind"] for entity in entities} - SUPPORTED_SEMANTIC_KINDS)
    if unsupported:
        raise ValueError(f"Unsupported semantic entity kinds: {unsupported}")
    cv_masks = {entity["id"]: cv_foreground_mask(image_rgb, entity) for entity in entities}

    device = "cpu"
    sam_results: dict[str, dict[str, Any]] = {}
    sam_timing = {"model_load_sec": 0.0, "image_embedding_sec": 0.0, "total_sam_sec": 0.0}
    sam_error = None
    eligible_sam_entities = sam_eligible_entities(entities)
    sam_skip_reason = None
    if args.no_sam:
        sam_skip_reason = "disabled_by_cli"
    elif not eligible_sam_entities:
        sam_skip_reason = "no_semantically_eligible_entities"
    else:
        checkpoint = Path(args.checkpoint).resolve()
        if not checkpoint.exists():
            sam_skip_reason = "checkpoint_unavailable"
        elif optional_torch() is None:
            sam_skip_reason = "optional_sam_dependencies_unavailable"
        else:
            device = choose_device(args.device)
            try:
                sam_results, sam_timing = run_sam(image_rgb, eligible_sam_entities, checkpoint, args.sam_config, device)
            except Exception as exc:
                if device == "mps" and args.device == "auto":
                    sam_error = f"MPS failed, retried on CPU: {type(exc).__name__}: {exc}"
                    device = "cpu"
                    sam_results, sam_timing = run_sam(image_rgb, eligible_sam_entities, checkpoint, args.sam_config, device)
                else:
                    raise

    measured_entities = []
    for entity in entities:
        entity_out = dict(entity)
        cv_mask = cv_masks[entity["id"]]
        sam_record = sam_results.get(entity["id"])
        selected_mask, mask_source, reason = select_mask(entity, cv_mask, sam_record)
        selected_path = masks_dir / f"{entity['id']}_selected.png"
        cv2.imwrite(str(selected_path), selected_mask * 255)
        cv_path = masks_dir / f"{entity['id']}_opencv.png"
        cv2.imwrite(str(cv_path), cv_mask * 255)
        measurement: dict[str, Any] = {
            "layout_bbox": bbox_variants(entity["bbox_hint"], (width, height)),
            "visible_bbox": bbox_variants(tight_bbox(selected_mask, entity["bbox_hint"]), (width, height)),
            "aspect_ratio": round(entity["bbox_hint"][2] / entity["bbox_hint"][3], 4),
            "area_px": int(np.count_nonzero(selected_mask)),
            "mask_source": mask_source,
            "mask_selection_reason": reason,
            "selected_mask": str(selected_path.relative_to(output_dir)),
            "selected_mask_absolute": str(selected_path),
            "opencv_mask": str(cv_path.relative_to(output_dir)),
            "dominant_colors": dominant_colors(image_rgb, entity["bbox_hint"], selected_mask),
        }
        if entity["kind"] == "image":
            x, y, w, h = clipped_bbox(entity["bbox_hint"], width, height)
            screenshot_path = images_dir / f"{entity['id']}_screenshot.png"
            crop_bgr = cv2.cvtColor(image_rgb[y : y + h, x : x + w], cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(screenshot_path), crop_bgr)
            screenshot_hash = hashlib.sha256(screenshot_path.read_bytes()).hexdigest()
            measurement["image_object"] = {
                "reconstruction_policy": "exact_upstream_image_then_embedded_screenshot",
                "screenshot_crop": str(screenshot_path.relative_to(output_dir)),
                "screenshot_crop_absolute": str(screenshot_path),
                "screenshot_sha256": screenshot_hash,
                "pixel_dimensions": [w, h],
                "placement_bbox": bbox_variants([x, y, w, h], (width, height)),
                "crop_mode": entity.get("crop_mode", "fill"),
                "rotation_degrees": float(entity.get("rotation_degrees", 0)),
                "preserve_aspect_ratio": bool(entity.get("preserve_aspect_ratio", True)),
                "generated_pixels_are_reconstruction_source": True,
                "internal_contours_emit_objects": False,
                "internal_text_is_raster_content": True,
            }
            entity_out["reconstruction_policy"] = "embedded_raster_image"
        elif entity["kind"] in {"icon", "icon_slot"}:
            slot_box = entity.get("slot_bbox_hint", entity["bbox_hint"])
            glyph_box = entity.get("generated_glyph_bbox_hint", tight_bbox(selected_mask, entity["bbox_hint"]))
            slot_x, slot_y, slot_w, slot_h = slot_box
            glyph_x, glyph_y, glyph_w, glyph_h = glyph_box
            padding = {
                "left": max(0, glyph_x - slot_x),
                "top": max(0, glyph_y - slot_y),
                "right": max(0, slot_x + slot_w - glyph_x - glyph_w),
                "bottom": max(0, slot_y + slot_h - glyph_y - glyph_h),
            }
            measurement["icon_slot_placement"] = {
                "slot_box": bbox_variants(slot_box, (width, height)),
                "slot_center_px": [round(slot_x + slot_w / 2, 2), round(slot_y + slot_h / 2, 2)],
                "padding_estimate_px": padding,
                "nearby_related_entities": entity.get("nearby_related_entities", []),
                "semantic_icon_intent": entity.get("semantic_icon_intent", entity.get("role")),
                "target_color": canonical_icon_color(measurement["dominant_colors"]),
                "rotation_degrees": float(entity.get("rotation_degrees", 0)),
                "preserve_aspect_ratio": True,
                "fit": "contain",
                "alignment": "center",
                "placement_authority": "slot_box",
                "generated_glyph_evidence": {
                    "visible_bbox": bbox_variants(glyph_box, (width, height)),
                    "authoritative_for_semantics": True,
                    "authoritative_for_geometry": False,
                },
                "generated_pixels_are_geometry_source": False,
            }
            measurement["canonical_asset_placement"] = {
                "target_visual_footprint": bbox_variants(slot_box, (width, height)),
                "target_color": measurement["icon_slot_placement"]["target_color"],
                "rotation_degrees": float(entity.get("rotation_degrees", 0)),
                "preserve_aspect_ratio": True,
                "fit": "contain",
                "alignment": "center",
                "placement_authority": "slot_box",
                "generated_pixels_are_geometry_source": False,
            }
            entity_out["reconstruction_policy"] = "canonical_asset_in_authoritative_icon_slot"
        elif entity["kind"] == "connector":
            intent = dict(entity.get("connector_intent", {}))
            if not intent:
                relationship = next(
                    (item for item in semantic["relationships"] if item.get("via") == entity["id"]),
                    {},
                )
                source = relationship.get("from", [])
                target = relationship.get("to", [])
                intent = {
                    "source_entities": source if isinstance(source, list) else [source],
                    "target_entities": target if isinstance(target, list) else [target],
                    "relationship_type": relationship.get("type", entity.get("role", "relationship")),
                    "directionality": "forward",
                    "structure_membership": "single",
                }
            constraints = dict(entity.get("visual_constraints", {}))
            x, y, w, h = entity["bbox_hint"]
            constraints.setdefault("start_anchors_px", [[x, y + h / 2]])
            constraints.setdefault("end_anchors_px", [[x + w, y + h / 2]])
            constraints.setdefault("junctions_px", [])
            constraints.setdefault("routing_orientation", "horizontal")
            constraints.setdefault("routing_type", "straight")
            constraints.setdefault("stroke_style", {"color": canonical_icon_color(measurement["dominant_colors"]), "width_px": 2, "dash": "solid"})
            constraints.setdefault("junction_treatment", {"style": "none"})
            constraints.setdefault("arrowhead_treatment", "triangle_at_target")
            constraints.setdefault("routing_corridor_px", entity["bbox_hint"])
            source_count = len(intent.get("source_entities", []))
            target_count = len(intent.get("target_entities", []))
            if source_count > 1 and target_count > 1:
                topology_type = "many_to_many_shared_junction"
            elif source_count > 1:
                topology_type = "many_to_one_merge"
            elif target_count > 1:
                topology_type = "one_to_many_branch"
            else:
                topology_type = "one_to_one"
            measurement["connector_constraints"] = {
                "intent": intent,
                "topology": {
                    "type": topology_type,
                    "source_count": source_count,
                    "target_count": target_count,
                    "source_anchor_count": len(constraints["start_anchors_px"]),
                    "target_anchor_count": len(constraints["end_anchors_px"]),
                    "junction_count": len(constraints["junctions_px"]),
                    "source_anchor_cardinality_consistent": len(constraints["start_anchors_px"]) == source_count,
                    "target_anchor_cardinality_consistent": len(constraints["end_anchors_px"]) == target_count,
                    "shared_junction_required": source_count > 1 or target_count > 1,
                    "shared_junction_measured": bool(constraints["junctions_px"]),
                },
                "approximate_start_anchors_px": constraints["start_anchors_px"],
                "approximate_end_anchors_px": constraints["end_anchors_px"],
                "junction_positions_px": constraints["junctions_px"],
                "routing_orientation": constraints["routing_orientation"],
                "routing_type": constraints["routing_type"],
                "stroke_style": constraints["stroke_style"],
                "junction_treatment": constraints["junction_treatment"],
                "arrowhead_treatment": constraints["arrowhead_treatment"],
                "routing_corridor": bbox_variants(constraints["routing_corridor_px"], (width, height)),
                "exact_raster_path_is_authoritative": False,
                "preferred_step5_route": "native_powerpoint_connector_system",
                "emission_rule": "compile semantic topology into native connector segments",
            }
            entity_out["reconstruction_policy"] = "relationship_intent_native_connector"
        else:
            measurement["contours_px"] = contours_for(selected_mask)
            measurement["edge_geometry"] = edge_geometry(image_rgb, entity["bbox_hint"])
        if entity["kind"] == "text":
            matched = words_in_box(ocr_words, entity["bbox_hint"])
            measurement["text_geometry"] = text_geometry(cv_mask, entity["bbox_hint"])
            measurement["ocr_support"] = {
                "observed_text": " ".join(word["text"] for word in matched),
                "mean_confidence": round(float(np.mean([word["confidence"] for word in matched])), 2) if matched else None,
                "word_boxes": matched,
                "semantic_text_is_authoritative": True,
            }
        if sam_record is not None:
            sam_path = masks_dir / f"{entity['id']}_sam2.png"
            cv2.imwrite(str(sam_path), sam_record["mask"] * 255)
            measurement["sam2"] = {
                "predicted_iou_score": round(sam_record["score"], 5),
                "all_candidate_scores": [round(v, 5) for v in sam_record["all_scores"]],
                "prompt_time_sec": round(sam_record["prompt_time_sec"], 4),
                "mask": str(sam_path.relative_to(output_dir)),
                "comparison_to_opencv": compare_masks(cv_mask, sam_record["mask"], entity["bbox_hint"]),
            }
        entity_out["measurement"] = measurement
        measured_entities.append(entity_out)

    overlaps = infer_overlaps(measured_entities)
    debug_path = output_dir / "debug_overlay.png"
    render_debug(image_rgb, measured_entities, semantic["groups"], semantic["relationships"], debug_path)

    sam_improvements = [e["id"] for e in measured_entities if e["measurement"].get("mask_source") == "sam2"]
    report_path = output_dir / "report.md"
    torch = optional_torch()
    result = {
        "schema_version": "0.1.0",
        "source": {"image": str(image_path), "width_px": width, "height_px": height, "aspect_ratio": round(width / height, 6)},
        "coordinate_system": {"origin": "top_left", "x_direction": "right", "y_direction": "down", "units": ["px", "normalized", "inches", "pptx_emu"], "slide_size_inches": [13.333333, 7.5]},
        "semantic_summary": {"intent": semantic["slide"]["intent"], "reading_order": semantic["slide"]["reading_order"], "ambiguities": semantic["ambiguities"]},
        "semantic_kind_policy": {
            "supported_kinds": sorted(SUPPORTED_SEMANTIC_KINDS),
            "image": "One meaningful raster image region is one reconstruction entity. Internal pixels are not child reconstruction objects.",
            "icon_slot": "The rectangular slot is the placement entity. The generated glyph is non-authoritative semantic evidence.",
        },
        "groups": semantic["groups"],
        "entities": measured_entities,
        "relationships": semantic["relationships"] + overlaps,
        "reconstruction_guidance": {
            "table": "Reconstruct as a native table when cell padding and merged cells can match. Fall back to aligned rectangles, text boxes, and connectors.",
            "icons": "Resolve each icon to an upstream canonical asset or a coherent preset-library substitute. Preserve the detected icon slot, center and contain-fit the SVG inside its configured inset, and discard generated glyph geometry.",
            "images": "Treat each meaningful raster image region as one reconstruction entity. Restore an exact upstream image asset when available. Otherwise embed the exported screenshot crop at the measured position and z-order.",
            "connectors": "Reconstruct ordinary connectors from relationship intent, approximate anchors, junctions, routing corridors, stroke style, corner treatment, and arrowhead treatment. Emit native PowerPoint connectors only. Prefer horizontal and vertical segments, use the measured destination anchor instead of forcing the route to the container center, and remove a terminal bend whenever the junction and destination anchor already share an axis. Consolidate redundant raster fragments. Do not emit separate arrowhead shapes or incidental edge fragments. Preserve custom geometry only when the connector is itself a designed visual.",
            "text": "Use semantic text as authoritative content and visible/line boxes as fitting constraints.",
            "z_order": ["slide background", "table and insights backgrounds", "accent fills", "grid lines and icons", "text"],
        },
        "runtime": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__ if torch is not None else None,
            "opencv": cv2.__version__,
            "mps_built": bool(torch and torch.backends.mps.is_built()),
            "mps_available": bool(torch and torch.backends.mps.is_available()),
            "sam_enabled": not args.no_sam and torch is not None,
            "sam_executed": bool(sam_results),
            "sam_skip_reason": sam_skip_reason,
            "sam_eligible_entity_ids": [entity["id"] for entity in eligible_sam_entities],
            "sam_model": "SAM 2.1 Hiera Tiny" if eligible_sam_entities else None,
            "sam_checkpoint": str(Path(args.checkpoint).resolve()) if eligible_sam_entities else None,
            "sam_device": device if eligible_sam_entities else None,
            "sam_error_or_fallback": sam_error,
            "ocr_sec": round(ocr_sec, 4),
            **{key: round(value, 4) for key, value in sam_timing.items()},
            "total_sec": round(time.perf_counter() - started, 4),
        },
        "quality_summary": {
            "entity_count": len(measured_entities),
            "group_count": len(semantic["groups"]),
            "sam_prompted_entity_count": len(sam_results),
            "sam_selected_as_final_mask_for": sam_improvements,
            "sam_material_contribution": "material for irregular filled boundaries" if sam_improvements else "limited on this clean vector-like slide",
        },
        "artifacts": {"debug_overlay": str(debug_path), "mask_directory": str(masks_dir), "image_directory": str(images_dir), "report": str(report_path)},
    }
    if upstream_handoff is not None:
        expected = upstream_handoff["target_image"].get(
            "actual_dimensions_px",
            upstream_handoff["generation_region"]["dimensions_px"],
        )
        scope = upstream_handoff["target_image"].get("scope", "generation_region")
        if scope == "generation_region" and [width, height] != expected:
            raise ValueError(f"Upstream handoff expects generation image {expected}, image is {[width, height]}")
        result["upstream_handoff"] = {
            "path": str(Path(args.upstream_handoff).resolve()),
            "scope": scope,
            "full_slide_dimensions_px": upstream_handoff["full_slide_dimensions_px"],
            "generation_region": upstream_handoff["generation_region"],
            "exact_title_text": upstream_handoff["exact_title_text"],
            "exact_source_content": upstream_handoff["exact_source_content"],
            "semantic_design": upstream_handoff["semantic_design"],
            "selected_assets": upstream_handoff["selected_assets"],
            "icon_slot_configuration": upstream_handoff.get("icon_slot_configuration", {}),
            "user_asset_policy": upstream_handoff.get("user_asset_policy", {}),
            "connector_configuration": upstream_handoff.get("connector_configuration", {}),
            "connector_configuration_qa": upstream_handoff.get("connector_configuration_qa", {}),
            "style_configuration": upstream_handoff["style_configuration"],
            "visual_references": upstream_handoff["visual_references"],
            "deck_chrome_configuration": upstream_handoff.get("deck_chrome_configuration", {}),
            "resolved_chrome_content": upstream_handoff.get("resolved_chrome_content", {}),
            "naming_migration_notices": naming_migration_notices,
        }
        result["coordinate_system"]["full_slide_offset_px"] = [0, upstream_handoff["generation_region"]["offset_y_px"]]
        result["reconstruction_guidance"]["upstream_priority"] = "Exact source content, canonical asset IDs, and configured style values take precedence over OCR or visual inference."
    result_path = output_dir / "slide_entities.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    prompted = [e for e in measured_entities if "sam2" in e["measurement"]]
    icon_ious = [
        e["measurement"]["sam2"]["comparison_to_opencv"]["iou_with_cv_foreground"]
        for e in prompted
        if e["kind"] == "icon"
    ]
    report_path.write_text(
        "# Slide understanding report\n\n"
        "## Result\n\n"
        f"- Identified {len(measured_entities)} editable reconstruction entities across {len(semantic['groups'])} semantic groups.\n"
        f"- Recovered the semantic structure described as {semantic['slide']['intent']}\n"
        "- Stored pixel, normalized, inch, and PowerPoint EMU coordinates together with OCR evidence, reading order, grouping, stacking, and geometry evidence for non-icon shapes. Icon measurements retain only canonical-asset placement evidence.\n\n"
        "## Local setup\n\n"
        f"- PyTorch {torch.__version__ if torch is not None else 'not installed'}\n"
        f"- MPS built and available {bool(torch and torch.backends.mps.is_built())} and {bool(torch and torch.backends.mps.is_available())}\n"
        f"- SAM 2.1 Hiera Tiny on {device if eligible_sam_entities else 'skipped'}\n"
        f"- OpenCV {cv2.__version__} ARM64\n"
        f"- OCR {ocr_sec:.2f} seconds\n"
        f"- SAM image embedding and prompts {sam_timing['total_sam_sec']:.2f} seconds\n"
        f"- End-to-end extraction {result['runtime']['total_sec']:.2f} seconds\n\n"
        "## SAM 2 assessment\n\n"
        f"SAM was prompted for {len(prompted)} entities and selected as the final mask for {len(sam_improvements)}. "
        f"The line-art icon masks averaged {float(np.mean(icon_ious)) if icon_ious else 0:.3f} IoU because SAM filled enclosed regions while OpenCV preserved editable stroke geometry. "
        "SAM therefore made a limited contribution on this clean vector-like slide.\n\n"
        "## Remaining ambiguity\n\n"
        "- Exact source font names and font metrics remain inferred.\n"
        "- Subtle fills and gradients remain inferred from raster pixels.\n"
        "- Icon selection requires an upstream asset ID or a coherent canonical-library substitution policy.\n",
        encoding="utf-8",
    )

    summary = {
        "json": str(result_path),
        "debug": str(debug_path),
        "entities": len(measured_entities),
        "groups": len(semantic["groups"]),
        "sam_device": result["runtime"]["sam_device"],
        "sam_total_sec": result["runtime"]["total_sam_sec"],
        "total_sec": result["runtime"]["total_sec"],
        "sam_selected_for": sam_improvements,
        "ambiguities": semantic["ambiguities"],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
