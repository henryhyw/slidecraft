from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.deck.manager import DeckManager
from slidecraft.deck.planning import build_deck_prompt
from slidecraft.intake import normalize_deck_intake
from slidecraft.providers.file import RecordedDeckPlan


class DeckManagerTests(unittest.TestCase):
    def test_planning_prompt_resolves_selected_guidance_and_density(self) -> None:
        design = json.loads((ROOT / "src" / "slidecraft" / "defaults" / "deck_design.json").read_text())
        prompt = build_deck_prompt(
            {"deck_id": "demo", "objective": "Make a decision"},
            {"source_atoms": [], "materials": [], "constraint_register": [], "quality": {}},
            design,
        )
        self.assertIn("A reader should be able to recover the core argument from slide messages alone.", prompt)
        self.assertIn("target_semantic_units_per_content_slide", prompt)
        self.assertIn("Avoid a product tour or internal component inventory", prompt)

    def test_manager_routes_and_emits_jobs(self) -> None:
        request = {
            "schema_version": "1.0.0",
            "deck_id": "demo_deck",
            "objective": "Explain one answer",
            "audience": {"description": "Executives"},
            "materials": [{"material_id": "M1", "modality": "text", "content": "Authoritative evidence", "authority": "authoritative"}],
        }
        intake = normalize_deck_intake(request, ROOT)
        authored_plan = RecordedDeckPlan(ROOT / "tests" / "fixtures" / "unit" / "deck_plan_fixture.json").read()
        with tempfile.TemporaryDirectory() as directory:
            manifest = DeckManager(Path(directory), authored_plan).initialize(
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
        self.assertEqual(cover_scene["system_layout_id"], "title_slide_minimal_v1")
        self.assertNotIn("next_gate", manifest)
        self.assertNotIn("status", content_job)
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
        authored_plan = RecordedDeckPlan(ROOT / "tests" / "fixtures" / "unit" / "deck_plan_fixture.json").read()
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            ValueError, "outside the requested range"
        ):
            DeckManager(Path(directory), authored_plan).initialize(
                request=request,
                intake=intake,
                design_system={"config_id": "test", "full_slide_px": [1000, 562], "style": {}, "deck_chrome": {"enabled": False}},
                system_layouts_path=ROOT / "src" / "slidecraft" / "defaults" / "system_slide_layouts.json",
            )

    def test_source_coverage_enforces_agent_authored_required_usage(self) -> None:
        request = {
            "schema_version": "1.0.0",
            "deck_id": "demo_deck",
            "objective": "Explain one answer",
            "audience": {"description": "Executives"},
            "materials": [{
                "material_id": "M1",
                "modality": "text",
                "content": "Authoritative context",
                "authority": "authoritative",
                "required_usage": False,
            }],
        }
        plan = RecordedDeckPlan(ROOT / "tests" / "fixtures" / "unit" / "deck_plan_fixture.json").read()
        plan["slides"][1]["source_atom_ids"] = []
        intake = normalize_deck_intake(request, ROOT)
        with tempfile.TemporaryDirectory() as directory:
            manifest = DeckManager(Path(directory), plan).initialize(
                request=request,
                intake=intake,
                design_system={"config_id": "test", "full_slide_px": [1000, 562], "style": {}, "deck_chrome": {"enabled": False}},
            )
        self.assertEqual(manifest["validation"]["missing_required_source_atoms"], [])

        request["materials"][0]["required_usage"] = True
        required_intake = normalize_deck_intake(request, ROOT)
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "Required source atoms"):
            DeckManager(Path(directory), plan).initialize(
                request=request,
                intake=required_intake,
                design_system={"config_id": "test", "full_slide_px": [1000, 562], "style": {}, "deck_chrome": {"enabled": False}},
            )


if __name__ == "__main__":
    unittest.main()
