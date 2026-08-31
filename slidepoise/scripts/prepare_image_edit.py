#!/usr/bin/env python3
"""Compile one targeted host-image edit prompt from an approved generation brief and explicit user-requested changes."""
from __future__ import annotations
import argparse
from pathlib import Path

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--generation-brief", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--request", type=Path, required=True, help="Plain-text summary of the user's requested changes")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not args.candidate.is_file():
        raise SystemExit(f"candidate image missing: {args.candidate}")
    request = args.request.read_text(encoding="utf-8").strip()
    if not request:
        raise SystemExit("user edit request is empty; do not spend an image call without requested changes")
    original = args.generation_brief.read_text(encoding="utf-8").strip()
    text = f"""# TARGETED IMAGE EDIT

Edit the supplied current candidate in place. The candidate image is the primary visual input and must remain the same design unless the user explicitly asks to change something.

## USER-REQUESTED CHANGES
{request}

## PRESERVATION RULE
- Preserve every unspecified element, wording, visual relationship, layout choice, approved asset choice, and overall style.
- Do not restart, restyle, or generate a different composition.
- Do not introduce new semantic visual assets beyond the already approved vocabulary unless the user explicitly requested that change.
- Keep the original generation contract below in force except where the user's requested changes explicitly override it.

## ORIGINAL APPROVED GENERATION BRIEF
{original}
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(args.output.resolve())

if __name__ == "__main__":
    main()
