from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.project_assets import add_project_asset, list_project_assets, update_project_asset
from slidecraft.projects import create_project


class ProjectAssetTests(unittest.TestCase):
    def test_chat_console_and_folder_assets_share_one_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "deck"
            create_project(name="Deck", location=root)
            chat_asset = Path(directory) / "client-logo.svg"
            chat_asset.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
            first = add_project_asset(
                root,
                chat_asset,
                semantic_role="client logo",
                description="The client's canonical identity mark.",
            )
            direct_asset = root / "assets/product.png"
            direct_asset.write_bytes(b"placeholder-image")
            catalog = list_project_assets(root)
            updated = update_project_asset(root, first["asset_id"], usage_policy="required_somewhere")

        self.assertEqual(len(catalog["assets"]), 2)
        self.assertEqual(updated["usage_policy"], "required_somewhere")
        self.assertEqual(updated["semantic_metadata_status"], "ready")
        self.assertEqual(catalog["default_usage_policy"], "available")
        self.assertTrue(all("workflow_effect" not in item for item in catalog["assets"]))

    def test_duplicate_asset_is_deduplicated_by_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "deck"
            create_project(name="Deck", location=root)
            first_path = Path(directory) / "a.svg"
            second_path = Path(directory) / "b.svg"
            first_path.write_text("<svg/>", encoding="utf-8")
            second_path.write_text("<svg/>", encoding="utf-8")
            first = add_project_asset(root, first_path)
            second = add_project_asset(root, second_path)

        self.assertEqual(first["asset_id"], second["asset_id"])

    def test_project_image_records_intrinsic_geometry_and_exact_content_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "deck"
            create_project(name="Deck", location=root)
            source = Path(directory) / "screenshot.png"
            Image.new("RGB", (1200, 600), "white").save(source)
            record = add_project_asset(root, source, semantic_role="product screenshot")

        self.assertEqual(record["visual_kind"], "raster_image")
        self.assertEqual(record["intrinsic_width"], 1200)
        self.assertEqual(record["intrinsic_height"], 600)
        self.assertEqual(record["intrinsic_aspect_ratio"], 2.0)
        self.assertTrue(record["preserve_exact_content"])
        self.assertTrue(record["preserve_aspect_ratio"])

    def test_folder_scan_repairs_a_stale_canonical_asset_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "deck"
            create_project(name="Deck", location=root)
            source = Path(directory) / "logo.svg"
            source.write_text("<svg/>", encoding="utf-8")
            record = add_project_asset(root, source)
            manifest_path = root / ".slidecraft/assets/asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["assets"][0]["stored_path"] = str(Path(directory) / "missing" / "logo.svg")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            catalog = list_project_assets(root)

        repaired = next(item for item in catalog["assets"] if item["asset_id"] == record["asset_id"])
        self.assertEqual(
            Path(repaired["stored_path"]),
            (root / "assets" / Path(record["stored_path"]).name).resolve(),
        )


if __name__ == "__main__":
    unittest.main()
