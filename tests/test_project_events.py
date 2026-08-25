from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.project_assets import add_project_asset, update_project_asset
from slidecraft.project_events import acknowledge_project_events, list_project_events
from slidecraft.projects import create_project


class ProjectEventTests(unittest.TestCase):
    def test_asset_preference_changes_are_visible_to_agent_without_replanning(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "deck"
            create_project(name="Deck", location=root)
            source = Path(directory) / "logo.svg"
            source.write_text("<svg/>", encoding="utf-8")
            asset = add_project_asset(root, source)
            update_project_asset(root, asset["asset_id"], usage_policy="preferred", actor="user_console")
            inbox = list_project_events(root)
            acknowledged = acknowledge_project_events(root, [inbox["events"][0]["event_id"]])

            self.assertEqual(inbox["pending_count"], 1)
            self.assertEqual(inbox["events"][0]["changes"], {"usage_policy": "preferred"})
            self.assertEqual(len(acknowledged["acknowledged_event_ids"]), 1)
            self.assertEqual(list_project_events(root)["pending_count"], 0)


if __name__ == "__main__":
    unittest.main()
