from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.deck.manager import DeckManager
from slidecraft.intake import normalize_deck_intake
from slidecraft.providers.file import FileStructuredReasoningProvider


class DeckManagerTests(unittest.TestCase):
    def test_manager_routes_and_emits_jobs(self) -> None:
        request = {
            "schema_version": "1.0.0",
            "deck_id": "demo_deck",
            "objective": "Explain one answer",
            "audience": {"description": "Executives"},
            "materials": [{"material_id": "M1", "modality": "text", "content": "Authoritative evidence", "authority": "authoritative"}],
        }
        intake = normalize_deck_intake(request, ROOT)
        provider = FileStructuredReasoningProvider(ROOT / "tests" / "fixtures" / "unit" / "deck_plan_fixture.json")
        with tempfile.TemporaryDirectory() as directory:
            manifest = DeckManager(Path(directory), provider).initialize(
                request=request,
                intake=intake,
                design_system={"config_id": "test", "full_slide_px": [1000, 562], "style": {}, "deck_chrome": {"enabled": False}},
            )
            plan = json.loads((Path(directory) / "deck_plan.json").read_text())
            content_job = json.loads((Path(directory) / "slides" / "content_1" / "job.json").read_text())
            cover_scene = json.loads((Path(directory) / "slides" / "cover" / "system_scene.json").read_text())
            artifact_manifest = json.loads((Path(directory) / ".slidecraft" / "artifact_manifest.json").read_text())

        self.assertEqual(plan["slides"][0]["route"], "system_layout")
        self.assertEqual(plan["slides"][1]["route"], "image_generation")
        self.assertEqual(content_job["status"], "ready_for_semantic_planning")
        self.assertEqual(cover_scene["system_layout_id"], "title_slide_minimal_v1")
        self.assertEqual(manifest["next_gate"], "agent_slide_execution")
        self.assertEqual(manifest["interaction_policy"]["workflow_state_source"], "artifact_ledger")
        self.assertEqual(artifact_manifest["control_model"], "agent_host")
        self.assertIn("deck/plan", artifact_manifest["active"])
        self.assertIn("slides/cover/constructor_scene", artifact_manifest["active"])

    def test_requested_slide_count_is_enforced(self) -> None:
        request = {
            "schema_version": "1.0.0",
            "deck_id": "demo_deck",
            "objective": "Explain one answer",
            "audience": {"description": "Executives"},
            "preferred_slide_count": {"minimum": 3, "target": 3, "maximum": 3},
            "materials": [{"material_id": "M1", "modality": "text", "content": "Evidence", "authority": "authoritative"}],
        }
        intake = normalize_deck_intake(request, ROOT)
        provider = FileStructuredReasoningProvider(ROOT / "tests" / "fixtures" / "unit" / "deck_plan_fixture.json")
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            ValueError, "outside the requested range"
        ):
            DeckManager(Path(directory), provider).initialize(
                request=request,
                intake=intake,
                design_system={"config_id": "test", "full_slide_px": [1000, 562], "style": {}, "deck_chrome": {"enabled": False}},
                system_layouts_path=ROOT / "src" / "slidecraft" / "defaults" / "system_slide_layouts.json",
            )


if __name__ == "__main__":
    unittest.main()
