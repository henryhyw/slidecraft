from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from slidecraft.library_manager import add_library_item
from slidecraft.project_resource_selections import (
    add_project_library_resource,
    project_library_options,
    reconcile_project_resources,
    record_retrieved_project_resources,
    remove_project_resource,
)
from slidecraft.project_resources import project_resource_catalog
from slidecraft.projects import create_project


class ProjectResourceLedgerTests(unittest.TestCase):
    def test_agent_retrieval_and_user_selection_share_one_durable_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            project = create_project(name="Deck", location=Path(directory) / "deck")
            icon = add_library_item(
                "icons",
                "planning.svg",
                base64.b64encode(b"<svg xmlns='http://www.w3.org/2000/svg'/>").decode(),
                {"name": "Planning", "description": "Planning icon", "semantic_roles": ["planning"]},
            )
            payload = {
                "icon_retrieval": {
                    "assets": [{
                        "asset_id": "ICON_PLANNING",
                        "library_icon_id": "planning",
                        "canonical_file": icon["path"],
                        "semantic_role": "planning",
                    }]
                }
            }

            result = record_retrieved_project_resources(project["workspace_path"], payload, source="test")
            catalog = project_resource_catalog(project["workspace_path"])
            options = project_library_options(project["workspace_path"], "icons")

            self.assertEqual(result["counts"]["icons"], 1)
            self.assertEqual(catalog["counts"]["icons"], 1)
            self.assertEqual(catalog["categories"]["icons"][0]["assignment_origin"], "agent_retrieval")
            self.assertTrue(next(item for item in options["items"] if item["item_id"] == icon["item_id"])["selected"])

            remove_project_resource(
                project["workspace_path"], category="icons", resource_id=icon["item_id"], actor="test"
            )
            record_retrieved_project_resources(project["workspace_path"], payload, source="second-pass")
            self.assertEqual(project_resource_catalog(project["workspace_path"])["counts"]["icons"], 0)

            add_project_library_resource(
                project["workspace_path"], category="icons", item_id=icon["item_id"], actor="test"
            )
            self.assertEqual(project_resource_catalog(project["workspace_path"])["counts"]["icons"], 1)

    def test_legacy_retrieval_output_is_reconciled_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            project = create_project(name="Deck", location=Path(directory) / "deck")
            reference = add_library_item(
                "visual_references",
                "reference.png",
                base64.b64encode(b"reference-image").decode(),
                {"name": "Reference", "description": "Visual reference"},
            )
            output = Path(project["workspace_path"]) / "outputs" / "slide-1"
            output.mkdir(parents=True)
            (output / "reference_retrieval.json").write_text(
                json.dumps({
                    "visual_references": [{
                        "reference_id": "REFERENCE_1",
                        "name": "Reference",
                        "path": reference["path"],
                    }]
                }),
                encoding="utf-8",
            )

            first = reconcile_project_resources(project["workspace_path"], include_legacy_outputs=True)
            second = reconcile_project_resources(project["workspace_path"], include_legacy_outputs=True)

            self.assertEqual(first["legacy_sources_imported"], 1)
            self.assertEqual(second["legacy_sources_imported"], 0)
            self.assertEqual(project_resource_catalog(project["workspace_path"])["counts"]["visual_references"], 1)


if __name__ == "__main__":
    unittest.main()
