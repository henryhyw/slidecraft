from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.project_resources import project_resource_catalog
from slidecraft.projects import create_project
from slidecraft.runtime.artifacts import ArtifactWorkspace


class ProjectResourceTests(unittest.TestCase):
    def test_catalog_separates_sources_visuals_and_retrieved_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "deck"
            create_project(name="Deck", location=root)
            (root / "sources/brief.txt").write_text("Authoritative brief", encoding="utf-8")
            (root / "sources/assets/logo.svg").write_text("<svg/>", encoding="utf-8")
            intake = root / ".slidecraft/intake.json"
            intake.write_text(json.dumps({"source_atoms": [{
                "atom_id": "ATOM_1", "locator": "user_message:1", "modality": "structured_text",
                "value": "Focus on growth", "authority": "authoritative", "provenance": "user_message",
            }]}), encoding="utf-8")
            retrieval = root / ".slidecraft/retrieval.json"
            retrieval.write_text(json.dumps({
                "visual_references": [{"reference_id": "REF_1", "name": "Timeline", "path": "/ref.png"}],
                "icon_retrieval": {"assets": [{"asset_id": "ICON_1", "prompt_name": "Growth", "semantic_role": "growth"}]},
                "known_component_retrieval": {"selected": [{"component_id": "MAP_1", "manifest_path": "/map.json", "semantic_score": 0.9}]},
            }), encoding="utf-8")
            workspace = ArtifactWorkspace(root)
            workspace.register(logical_key="deck/intake", kind="intake_manifest", path=intake, producer="test")
            workspace.register(logical_key="deck/retrieval", kind="reference_retrieval", path=retrieval, producer="test")
            catalog = project_resource_catalog(root)

        self.assertEqual(catalog["counts"], {
            "deliverables": 0,
            "materials": 1,
            "visual_assets": 1,
            "visual_references": 1,
            "icons": 1,
            "components": 1,
        })
        self.assertEqual(catalog["categories"]["materials"][0]["provenance"], "project_sources_folder")
        self.assertEqual(catalog["internal_evidence"]["normalized_source_item_count"], 1)
        self.assertFalse(catalog["internal_evidence"]["user_visible"])


if __name__ == "__main__":
    unittest.main()
