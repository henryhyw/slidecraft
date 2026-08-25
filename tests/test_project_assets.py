from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
            first = add_project_asset(root, chat_asset, semantic_role="client logo")
            direct_asset = root / "sources/assets/product.png"
            direct_asset.write_bytes(b"placeholder-image")
            catalog = list_project_assets(root)
            updated = update_project_asset(root, first["asset_id"], usage_policy="required_somewhere")

        self.assertEqual(len(catalog["assets"]), 2)
        self.assertEqual(updated["usage_policy"], "required_somewhere")
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


if __name__ == "__main__":
    unittest.main()
