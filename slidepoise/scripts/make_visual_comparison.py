#!/usr/bin/env python3
"""Arrange images for host-Agent visual comparison without judging them.

For reconstruction review, pass --config to compare the generated target against the
substantive region of the full-slide PPTX render. The full render should still be
inspected separately for Slide Master frame quality.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def crop_generation_region(image: Image.Image, config_path: Path) -> Image.Image:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    design = config["design"]
    full_width, full_height = map(float, design["full_slide_px"])
    frame = design["frame"]
    header = frame["header"]
    footer = frame["footer"]
    header_height = float(header.get("height_px", 0)) if header.get("enabled", True) else 0.0
    footer_height = float(footer.get("height_px", 0)) if footer.get("enabled", True) else 0.0
    top = round(image.height * header_height / full_height)
    bottom = round(image.height * (full_height - footer_height) / full_height)
    return image.crop((0, top, image.width, bottom))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    parser.add_argument("--left-label", default="Target")
    parser.add_argument("--right-label", default="Render")
    parser.add_argument("--config", type=Path, help="Crop the right full-slide render to the configured substantive generation region.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    left = Image.open(args.left).convert("RGB")
    right = Image.open(args.right).convert("RGB")
    if args.config:
        right = crop_generation_region(right, args.config)
    if right.size != left.size:
        right = right.resize(left.size, Image.Resampling.LANCZOS)

    top_margin = 52
    gap = 28
    canvas_width = left.width + right.width + gap
    canvas_height = max(left.height, right.height) + top_margin
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    canvas.paste(left, (0, top_margin))
    canvas.paste(right, (left.width + gap, top_margin))

    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    draw.text((8, 14), args.left_label, fill="black", font=font)
    draw.text((left.width + gap + 8, 14), args.right_label, fill="black", font=font)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    print(output)


if __name__ == "__main__":
    main()
