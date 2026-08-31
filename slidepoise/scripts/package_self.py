#!/usr/bin/env python3
"""Package a writable SlidePoise Skill copy as skill.zip after objective preflight."""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 25 * 1024 * 1024
SKIP_PARTS = {"__pycache__", ".DS_Store", ".git", "work", "deliverables"}


def run(script: str, *args: str) -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], text=True, capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if not (ROOT / "SKILL.md").is_file() or not (ROOT / "agents/openai.yaml").is_file():
        raise SystemExit("Skill root is incomplete")
    run("audit_skill_boundaries.py")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "skill.zip"
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
                continue
            archive.write(path, Path(ROOT.name) / path.relative_to(ROOT))
    size = output.stat().st_size
    if size > MAX_BYTES:
        output.unlink(missing_ok=True)
        raise SystemExit(f"Packaged Skill exceeds 25 MB: {size} bytes")
    print(output)


if __name__ == "__main__":
    main()
