from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.library_manager import (
    add_library_item,
    delete_library_item,
    list_library_items,
    set_library_location,
    update_library_item_metadata,
)


class LibraryManagerTests(unittest.TestCase):
    def test_user_can_choose_collection_folder_add_and_remove_an_exact_item(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "SLIDECRAFT_DATA_DIR": str(Path(directory) / "data"),
                "SLIDECRAFT_CONFIG": str(Path(directory) / "config.toml"),
            },
        ):
            location = Path(directory) / "icons"
            set_library_location("icons", location)
            item = add_library_item("icons", "idea.svg", base64.b64encode(b"<svg/>").decode())
            listed = list_library_items("icons")
            deleted = delete_library_item("icons", item["item_id"])

            self.assertEqual(listed["item_count"], 1)
            self.assertEqual(deleted["status"], "deleted")
            self.assertEqual(list_library_items("icons")["item_count"], 0)

    def test_metadata_can_be_completed_after_upload(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "SLIDECRAFT_DATA_DIR": str(Path(directory) / "data"),
                "SLIDECRAFT_CONFIG": str(Path(directory) / "config.toml"),
            },
        ):
            set_library_location("icons", Path(directory) / "icons")
            item = add_library_item("icons", "idea.svg", base64.b64encode(b"<svg/>").decode())
            self.assertEqual(item["metadata_status"], "needs_description")

            updated = update_library_item_metadata(
                "icons",
                item["item_id"],
                {"name": "Idea", "description": "An idea or insight pictogram", "tags": ["idea", "insight"]},
            )

            self.assertEqual(updated["description"], "An idea or insight pictogram")
            self.assertEqual(updated["tags"], ["idea", "insight"])
            self.assertEqual(updated["metadata_status"], "ready")

    def test_component_preview_support_file_is_not_listed_as_a_component(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "SLIDECRAFT_DATA_DIR": str(Path(directory) / "data"),
                "SLIDECRAFT_CONFIG": str(Path(directory) / "config.toml"),
            },
        ):
            location = Path(directory) / "components"
            set_library_location("components", location)
            component = location / "map"
            component.mkdir()
            (component / "preview.svg").write_text("<svg/>", encoding="utf-8")
            (component / "map.component.json").write_text(
                json.dumps({"component_id": "map", "preview": {"image": "preview.png"}, "implementation": {"type": "pptx_fragment"}}),
                encoding="utf-8",
            )

            listed = list_library_items("components")

            self.assertEqual(listed["item_count"], 1)
            self.assertTrue(listed["items"][0]["preview_path"].endswith("preview.svg"))


if __name__ == "__main__":
    unittest.main()
