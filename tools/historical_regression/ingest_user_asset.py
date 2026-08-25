#!/usr/bin/env python3
"""Ingest a chat attachment or local user asset into the project asset store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from slidecraft.orchestration.asset_ingestion import ingest_user_asset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--asset-id")
    parser.add_argument("--semantic-role", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--usage", choices=["mandatory", "optional", "reference_only", "do_not_use"], required=True)
    parser.add_argument("--source-locator")
    parser.add_argument("--store", default="inputs/user_assets/ingested")
    parser.add_argument("--manifest", default="inputs/user_assets/ingested_assets.json")
    args = parser.parse_args()

    record = ingest_user_asset(
        Path(args.source),
        Path(args.store),
        {
            "asset_id": args.asset_id,
            "semantic_role": args.semantic_role,
            "description": args.description,
            "usage_class": args.usage,
            "source_locator": args.source_locator or args.source,
        },
    )
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1.0.0", "assets": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"] = [item for item in manifest["assets"] if item["asset_id"] != record["asset_id"]]
    manifest["assets"].append(record)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
