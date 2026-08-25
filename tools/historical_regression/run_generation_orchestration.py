#!/usr/bin/env python3
"""Run generation preparation and stop at the external image-generation boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from slidecraft.orchestration import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="workspace/projects/ai-slide-drafting-architecture/config/deck_design_config.json")
    parser.add_argument("--slide", default="inputs/architecture_generation_input.json")
    parser.add_argument("--output-dir", default="outputs/architecture_generation_orchestration")
    args = parser.parse_args()
    result = run_pipeline(Path(args.config).resolve(), Path(args.slide).resolve(), Path(args.output_dir).resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
