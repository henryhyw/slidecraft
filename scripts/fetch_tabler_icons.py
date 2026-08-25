#!/usr/bin/env python3
"""Vendor the configured Tabler outline icon subset with provenance hashes."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path


VERSION = "v3.46.0"
BASE_URL = f"https://raw.githubusercontent.com/tabler/tabler-icons/{VERSION}"
ICON_NAMES = (
    "hierarchy-3",
    "template",
    "icons",
    "cloud-upload",
    "palette",
    "photo-spark",
    "affiliate",
    "ruler-measure",
    "layout-dashboard",
    "vector-bezier-2",
    "file-type-ppt",
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Slidecraft"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "vendor" / "tabler-icons"
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for name in ICON_NAMES:
        url = f"{BASE_URL}/icons/outline/{name}.svg"
        data = fetch(url)
        path = output_dir / f"{name}.svg"
        path.write_bytes(data)
        records.append({
            "icon_id": name,
            "style": "outline",
            "version": VERSION,
            "source_url": url,
            "canonical_file": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    license_url = f"{BASE_URL}/LICENSE"
    license_data = fetch(license_url)
    (output_dir / "LICENSE.txt").write_bytes(license_data)
    manifest = {
        "provider": "Tabler Icons",
        "version": VERSION,
        "style": "outline",
        "license": "MIT",
        "license_url": "https://tabler.io/license",
        "source_repository": "https://github.com/tabler/tabler-icons",
        "assets": records,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
