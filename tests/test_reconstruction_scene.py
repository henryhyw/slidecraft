from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.reconstruction.conformance import ConstructorConformanceError
from slidecraft.reconstruction.scene import build_reconstruction_scene


class ReconstructionSceneTests(unittest.TestCase):
    def test_architecture_contract_compiles_connectors_and_canonical_assets(self) -> None:
        evidence_path = ROOT / "tests" / "fixtures" / "architecture" / "slide_entities.json"
        contract_path = ROOT / "tests" / "fixtures" / "architecture" / "reconstruction_contract.json"
        measured_scene = json.loads(evidence_path.read_text())
        contract = json.loads(contract_path.read_text())
        contract["reasoned_refinement_plan"] = json.loads(
            (ROOT / "tests" / "fixtures" / "architecture" / "normalization_plan.json").read_text()
        )
        fixture_root = ROOT / "tests" / "fixtures" / "architecture"
        starter_icons = ROOT / "src" / "slidecraft" / "starter_resources" / "icons"
        for mapping in contract["canonical_asset_mappings"]:
            filename = Path(mapping["selected_asset_path"]).name
            packaged = starter_icons / filename
            mapping["selected_asset_path"] = str(packaged if packaged.exists() else fixture_root / filename)
        design = json.loads((fixture_root / "design_config.json").read_text())
        scene = build_reconstruction_scene(measured_scene=measured_scene, contract=contract, design=design, slide_id="architecture")
        kinds = [item["kind"] for item in scene["objects"]]
        self.assertEqual(kinds.count("connector_graph"), 5)
        self.assertGreaterEqual(kinds.count("image"), 13)
        self.assertEqual(scene["compiler_report"]["evidence_objects_emitted"], 0)
        by_id = {item["id"]: item for item in scene["objects"]}
        self.assertEqual(by_id["S_stage1"]["bbox_px"], [38, 257, 290, 702])
        self.assertEqual(len([item for item in scene["objects"] if item.get("semantic_role") == "icon_slot_surface"]), 13)
        self.assertEqual(len([item for item in scene["objects"] if item.get("semantic_role") == "deck_chrome"]), 5)
        self.assertEqual(by_id["I_stage1"]["recolor"], "#D93900")
        self.assertIsNone(by_id["I_openai"]["recolor"])
        self.assertEqual(by_id["T_stage1_body"]["bullet_style"], "disc")
        self.assertGreaterEqual(by_id["T_title"]["style"]["font_size_px"], 48)
        for textbox in (item for item in scene["objects"] if item["kind"] == "textbox" and item["id"].startswith("T_")):
            self.assertAlmostEqual(textbox["style"]["font_size_pt"] * 2, round(textbox["style"]["font_size_pt"] * 2))
        self.assertTrue(scene["compiler_report"]["text_fitting"]["all_textboxes_passed"])
        self.assertEqual(scene["compiler_report"]["text_fitting"]["quantization_step_pt"], 0.5)
        self.assertEqual(by_id["S_output"]["shape"], "slanted_banner")
        output_surface = by_id["I_output.icon_slot_surface"]["bbox_px"]
        output_glyph = by_id["I_output"]["bbox_px"]
        self.assertGreater(output_glyph[0], output_surface[0])
        self.assertGreater(output_glyph[1], output_surface[1])
        self.assertLess(output_glyph[0] + output_glyph[2], output_surface[0] + output_surface[2])
        self.assertLess(output_glyph[1] + output_glyph[3], output_surface[1] + output_surface[3])
        self.assertGreaterEqual(scene["compiler_report"]["alignment_normalization"]["correction_count"], 2)
        self.assertEqual(
            scene["compiler_report"]["alignment_normalization"]["decisions"][0]["semantic_basis"],
            "The two objects are peer technology attribution badges placed at the bottom of adjacent stage containers.",
        )
        for connector in (item for item in scene["objects"] if item["kind"] == "connector_graph"):
            self.assertGreaterEqual(connector["style"]["width_px"], 4)
            self.assertEqual(connector["arrowhead"]["powerpoint_size"], "lg")

        connector_by_id = {item["id"]: item for item in scene["objects"] if item["kind"] == "connector_graph"}
        self.assertEqual(len(connector_by_id["C_stage2_stage3"]["sources_px"]), 4)
        self.assertEqual(len(connector_by_id["C_stage2_stage3"]["targets_px"]), 1)
        self.assertEqual(connector_by_id["C_stage2_stage3"]["route"], "elbow_shared_junction")
        self.assertEqual(len(connector_by_id["C_stage4_stage5"]["sources_px"]), 2)
        self.assertEqual(len(connector_by_id["C_stage4_stage5"]["targets_px"]), 2)
        self.assertEqual(connector_by_id["C_stage4_stage5"]["route"], "elbow_shared_junction")
        self.assertEqual(connector_by_id["C_stage4_stage5"]["junction_style"]["style"], "none")
        stage5_box = by_id["S_stage5"]["bbox_px"]
        stage5_output = connector_by_id["C_stage5_output"]
        self.assertAlmostEqual(stage5_output["sources_px"][0][0], stage5_box[0] + stage5_box[2] / 2, delta=0.6)
        self.assertAlmostEqual(stage5_output["sources_px"][0][1], stage5_box[1] + stage5_box[3], delta=0.6)

        broken = copy.deepcopy(contract)
        broken["canonical_asset_mappings"].append({"entity_id": "MISSING_REQUIRED_ASSET"})
        with self.assertRaises(ConstructorConformanceError):
            build_reconstruction_scene(measured_scene=measured_scene, contract=broken, design=design, slide_id="architecture")

    def test_portable_backend_contains_no_sample_entity_ids(self) -> None:
        source = (ROOT / "js" / "scene_to_pptx.mjs").read_text(encoding="utf-8")
        for identifier in ("S_output", "I_output", "G_stage1", "G_stage5", "C_stage4_stage5"):
            self.assertNotIn(identifier, source)


if __name__ == "__main__":
    unittest.main()
