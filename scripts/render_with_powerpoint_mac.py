#!/usr/bin/env python3
"""Render a PPTX through Microsoft PowerPoint for Mac.

PowerPoint exports the deck to PDF. Poppler then rasterizes each PDF page.
The temporary PPTX copy avoids path caching and leaves existing presentations open.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path


APPLESCRIPT = r'''
on run argv
  set srcPath to item 1 of argv
  set dstPath to item 2 of argv
  set presentationName to item 3 of argv
  tell application "Microsoft PowerPoint"
    activate
    open POSIX file srcPath
    delay 1
    set targetPresentation to presentation presentationName
    save targetPresentation in (POSIX file dstPath) as save as PDF
    close targetPresentation saving no
  end tell
end run
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("pptx", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=144)
    parser.add_argument("--pdf-name", default=None)
    return parser.parse_args()


def run_applescript(src: Path, dst: Path, presentation_name: str) -> None:
    command = ["osascript"]
    for line in APPLESCRIPT.strip().splitlines():
        command.extend(["-e", line])
    command.extend([str(src), str(dst), presentation_name])
    subprocess.run(command, check=True, timeout=90)


def main() -> None:
    args = parse_args()
    source = args.pptx.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_name = args.pdf_name or f"{source.stem}.powerpoint.pdf"
    pdf_path = output_dir / pdf_name

    with tempfile.TemporaryDirectory(prefix="pptx-powerpoint-render-") as temp_dir:
        temp_name = f"codex-{uuid.uuid4().hex}.pptx"
        temp_pptx = Path(temp_dir) / temp_name
        shutil.copy2(source, temp_pptx)
        run_applescript(temp_pptx, pdf_path, temp_name)

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise RuntimeError("pdftoppm was not found. The native PowerPoint PDF is still available.")

    page_prefix = output_dir / "slide"
    subprocess.run(
        [pdftoppm, "-png", "-r", str(args.dpi), str(pdf_path), str(page_prefix)],
        check=True,
        timeout=90,
    )
    pngs = sorted(output_dir.glob("slide-*.png"))
    print(f"PowerPoint PDF {pdf_path}")
    print(f"Rendered pages {len(pngs)}")
    for png in pngs:
        print(png)


if __name__ == "__main__":
    main()
