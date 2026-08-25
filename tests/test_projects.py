from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.project_resources import project_resource_catalog
from slidecraft.projects import (
    LEGACY_PROJECT_FILE,
    PROJECT_FILE,
    create_project,
    list_projects,
    project_detail,
    register_project,
    resolve_project,
)


class ProjectWorkspaceTests(unittest.TestCase):
    def test_user_selected_project_keeps_internal_state_hidden(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
            root = Path(directory) / "client-deck"
            project = create_project(name="Client deck", location=root, deck_id="D1")
            projects = list_projects()
            detail = project_detail(root)
            project_file_exists = (root / PROJECT_FILE).exists()
            deliverables_exists = (root / "deliverables").is_dir()
            materials_exists = (root / "materials").is_dir()
            assets_exists = (root / "assets").is_dir()
            artifact_manifest_exists = (root / ".slidecraft" / "artifact_manifest.json").exists()
            deck_design_exists = (root / ".slidecraft" / "deck_design.json").exists()

        self.assertEqual(project["workspace_path"], str(root.resolve()))
        self.assertTrue(project_file_exists)
        self.assertTrue(deliverables_exists)
        self.assertTrue(materials_exists)
        self.assertTrue(assets_exists)
        self.assertTrue(artifact_manifest_exists)
        self.assertTrue(deck_design_exists)
        self.assertNotIn("history", detail["state"])
        self.assertEqual(projects[0]["project_id"], project["project_id"])

    def test_deleted_project_is_retained_as_unavailable_registry_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
            root = Path(directory) / "temporary-project"
            create_project(name="Temporary", location=root)
            (root / PROJECT_FILE).unlink()
            projects = list_projects()
        self.assertFalse(projects[0]["available"])

    def test_agent_can_resolve_a_project_from_its_human_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
            root = Path(directory) / "client-deck"
            created = create_project(name="Client Growth Review", location=root)
            resolved = resolve_project("client growth review")

        self.assertEqual(resolved["resolution"], "found")
        self.assertEqual(resolved["matched_by"], "name")
        self.assertEqual(resolved["project"]["project_id"], created["project_id"])

    def test_agent_can_create_an_explicitly_new_named_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
            resolved = resolve_project("New Strategy Deck", create_if_missing=True)

        self.assertEqual(resolved["resolution"], "created")
        self.assertEqual(resolved["project"]["name"], "New Strategy Deck")

    def test_existing_sources_are_migrated_into_visible_materials_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "legacy"
            created = create_project(name="Legacy", location=root)
            current_manifest = root / PROJECT_FILE
            legacy_manifest = root / LEGACY_PROJECT_FILE
            current_manifest.replace(legacy_manifest)
            (root / "sources/assets").mkdir(parents=True)
            (root / "sources/brief.txt").write_text("Brief", encoding="utf-8")
            (root / "sources/assets/logo.svg").write_text("<svg/>", encoding="utf-8")

            registered = register_project(root)
            legacy_sources_exists = (root / "sources").exists()
            material_exists = (root / "materials/brief.txt").is_file()
            asset_exists = (root / "assets/logo.svg").is_file()
            manifest_exists = (root / PROJECT_FILE).is_file()
            legacy_manifest_exists = (root / LEGACY_PROJECT_FILE).exists()

        self.assertEqual(registered["project_id"], created["project_id"])
        self.assertFalse(legacy_sources_exists)
        self.assertTrue(material_exists)
        self.assertTrue(asset_exists)
        self.assertTrue(manifest_exists)
        self.assertFalse(legacy_manifest_exists)

    def test_legacy_project_can_be_opened_before_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "legacy"
            create_project(name="Legacy", location=root)
            (root / PROJECT_FILE).replace(root / LEGACY_PROJECT_FILE)

            projects = list_projects()
            detail = project_detail(root)
            resources = project_resource_catalog(root)

        self.assertTrue(projects[0]["available"])
        self.assertEqual(detail["project"]["name"], "Legacy")
        self.assertEqual(resources["project_path"], str(root.resolve()))


if __name__ == "__main__":
    unittest.main()
