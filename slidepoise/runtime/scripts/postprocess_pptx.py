#!/usr/bin/env python3
"""Post-process SlidePoise PPTX packages without Node-side JSZip.

Normalizes text-body autofit settings and converts connector placeholders emitted
by PptxGenJS into native PowerPoint connector shapes.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


SLIDE_RE = re.compile(r"^ppt/slides/slide\d+\.xml$")
CONNECTOR_SP_RE = re.compile(r"<p:sp>(?:(?!</p:sp>)[\s\S])*?</p:sp>")
CONNECTOR_NAME_RE = re.compile(r'<p:cNvPr[^>]*name="SC_CONNECTOR__[^"]*"')
INVALID_CONNECTOR_RE = re.compile(r'<p:cxnSp>(?:(?!</p:cxnSp>)[\s\S])*?<p:cNvPr[^>]*name="(?!SC_CONNECTOR__)[^"]*"')
UNCONVERTED_CONNECTOR_RE = re.compile(r'<p:sp>(?:(?!</p:sp>)[\s\S])*?<p:cNvPr[^>]*name="SC_CONNECTOR__[^"]*"')


def convert_connector_block(block: str) -> tuple[str, bool]:
    if not CONNECTOR_NAME_RE.search(block):
        return block, False
    converted = block
    converted = converted.replace("<p:sp>", "<p:cxnSp>")
    converted = converted.replace("</p:sp>", "</p:cxnSp>")
    converted = converted.replace("<p:nvSpPr>", "<p:nvCxnSpPr>")
    converted = converted.replace("</p:nvSpPr>", "</p:nvCxnSpPr>")
    converted = converted.replace("<p:cNvSpPr/>", "<p:cNvCxnSpPr/>")
    converted = re.sub(r'<a:tailEnd type="triangle"/>', '<a:tailEnd type="triangle" w="lg" len="lg"/>', converted)
    converted = re.sub(r'<a:headEnd type="triangle"/>', '<a:headEnd type="triangle" w="lg" len="lg"/>', converted)
    if "__CURVED" in block:
        converted = converted.replace('prst="line"', 'prst="curvedConnector3"')
    if "<a:round/>" not in converted:
        converted = re.sub(r"(<a:prstDash[^>]*/>)", r"\1<a:round/>", converted, count=1)
    return converted, True


def apply_round_rect_adjustments(xml: str, adjustments: dict[str, int]) -> tuple[str, int]:
    """Apply exact editable roundRect corner adjustments by object name."""
    changed = 0
    for object_name, raw_adjustment in adjustments.items():
        adjustment = max(0, min(50000, int(raw_adjustment)))
        escaped_name = re.escape(escape(str(object_name), {'"': '&quot;'}))
        block_re = re.compile(
            rf'<p:sp>(?:(?!</p:sp>)[\s\S])*?<p:cNvPr[^>]*name="{escaped_name}"[^>]*>(?:(?!</p:sp>)[\s\S])*?</p:sp>'
        )
        def replace_block(match: re.Match[str]) -> str:
            nonlocal changed
            block = match.group(0)
            geom_re = re.compile(r'<a:prstGeom prst="roundRect"><a:avLst>(?:(?!</a:avLst>)[\s\S])*?</a:avLst></a:prstGeom>')
            if not geom_re.search(block):
                return block
            replacement = f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {adjustment}"/></a:avLst></a:prstGeom>'
            updated = geom_re.sub(replacement, block, count=1)
            if updated != block:
                changed += 1
            return updated
        xml = block_re.sub(replace_block, xml, count=1)
    return xml, changed


def process_xml(xml: str, round_rect_adjustments: dict[str, int] | None = None) -> tuple[str, int, int, int]:
    text_bodies = 0

    def normalize_self_closing(match: re.Match[str]) -> str:
        nonlocal text_bodies
        text_bodies += 1
        return f"<a:bodyPr{match.group(1)}><a:noAutofit/></a:bodyPr>"

    xml = re.sub(r"<a:bodyPr([^>]*)/>", normalize_self_closing, xml)
    xml = re.sub(r"<a:bodyPr([^>]*)></a:bodyPr>", normalize_self_closing, xml)

    converted_count = 0

    def replace_block(match: re.Match[str]) -> str:
        nonlocal converted_count
        block, converted = convert_connector_block(match.group(0))
        if converted:
            converted_count += 1
        return block

    xml = CONNECTOR_SP_RE.sub(replace_block, xml)
    rounding_count = 0
    if round_rect_adjustments:
        xml, rounding_count = apply_round_rect_adjustments(xml, round_rect_adjustments)
    if INVALID_CONNECTOR_RE.search(xml) or UNCONVERTED_CONNECTOR_RE.search(xml):
        raise RuntimeError("Native connector conversion failed structural validation")
    return xml, converted_count, text_bodies, rounding_count


def postprocess(pptx_path: Path, metadata: dict | None = None) -> dict[str, int | str]:
    pptx_path = pptx_path.resolve()
    if not pptx_path.is_file():
        raise FileNotFoundError(pptx_path)
    converted = 0
    text_bodies = 0
    rounded_rectangles_adjusted = 0
    metadata = metadata or {}
    round_rect_adjustments = metadata.get("round_rect_adjustments", {}) or {}
    with zipfile.ZipFile(pptx_path, "r") as source:
        names = source.namelist()
        replacements: dict[str, bytes] = {}
        for name in names:
            if not SLIDE_RE.match(name):
                continue
            xml = source.read(name).decode("utf-8")
            updated, local_converted, local_text, local_rounding = process_xml(xml, round_rect_adjustments)
            converted += local_converted
            text_bodies += local_text
            rounded_rectangles_adjusted += local_rounding
            replacements[name] = updated.encode("utf-8")
        if not replacements:
            return {"converted": 0, "textBodiesNormalized": 0, "roundedRectanglesAdjusted": 0, "status": "ok"}
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as handle:
            tmp = Path(handle.name)
        try:
            with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for info in source.infolist():
                    data = replacements.get(info.filename)
                    if data is None:
                        data = source.read(info.filename)
                    target.writestr(info, data)
            pptx_path.write_bytes(tmp.read_bytes())
        finally:
            tmp.unlink(missing_ok=True)
    return {"converted": converted, "textBodiesNormalized": text_bodies, "roundedRectanglesAdjusted": rounded_rectangles_adjusted, "status": "ok"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pptx")
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8")) if args.metadata and args.metadata.exists() else {}
    print(json.dumps(postprocess(Path(args.pptx), metadata), indent=2))


if __name__ == "__main__":
    main()
