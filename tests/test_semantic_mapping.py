from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.providers.file import RecordedVisualAnalysis
from slidecraft.semantic_mapping.compiler import compile_semantic_map


class SemanticMappingTests(unittest.TestCase):
    def test_host_vlm_result_compiles_to_semantic_scene(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "slide.png"
            Image.new("RGB", (1000, 500), "white").save(image_path)
            handoff = {
                "exact_source_content": {"title": "Grounded title"},
                "selected_assets": [
                    {
                        "internal": {
                            "asset_id": "TABLER_EXAMPLE",
                            "semantic_role": "example_icon",
                            "canonical_file": "/tmp/example.svg"
                        }
                    }
                ],
            }
            analysis = RecordedVisualAnalysis(ROOT / "tests" / "fixtures" / "unit" / "semantic_scene_draft_fixture.json")
            result = compile_semantic_map(analysis=analysis, image_path=image_path, upstream_handoff=handoff)

        by_id = {entity["id"]: entity for entity in result["entities"]}
        self.assertEqual(by_id["T_title"]["authored_text"], "Grounded title")
        self.assertEqual(by_id["T_title"]["bbox_hint"], [70, 35, 600, 60])
        self.assertTrue(by_id["S_accent"]["sam_prompt"])
        self.assertFalse(by_id["I_example"]["sam_prompt"])
        self.assertEqual(by_id["I_example"]["asset_mapping_status"], "exact_agent_selected_asset")
        self.assertEqual(result["semantic_mapping_runtime"]["authored_by"], "agent_record")

    def test_agent_quality_assessment_is_recorded_for_review(self) -> None:
        fixture = json.loads((ROOT / "tests" / "fixtures" / "unit" / "semantic_scene_draft_fixture.json").read_text())
        fixture["quality"]["source_coverage"] = 0.4
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            result_path.write_text(json.dumps(fixture))
            image_path = Path(directory) / "slide.png"
            Image.new("RGB", (100, 100), "white").save(image_path)
            analysis = RecordedVisualAnalysis(result_path)
            result = compile_semantic_map(analysis=analysis, image_path=image_path, upstream_handoff={})

        self.assertEqual(result["semantic_mapping_runtime"]["quality"]["source_coverage"], 0.4)

    def test_agent_selected_project_image_maps_to_canonical_file(self) -> None:
        fixture = json.loads((ROOT / "tests" / "fixtures" / "unit" / "semantic_scene_draft_fixture.json").read_text())
        image_entity = dict(fixture["entities"][1])
        image_entity.update({
            "id": "P_product",
            "kind": "image",
            "role": "product screenshot",
            "bbox_norm": [100, 200, 400, 300],
            "reconstruction_route": "canonical_icon_or_image_asset",
            "upstream_asset_id": "PROJECT_IMAGE",
            "candidate_asset_ids": ["PROJECT_IMAGE"],
            "shape": None,
            "segmentation_role": "none",
        })
        fixture["entities"].append(image_entity)
        fixture["slide"]["reading_order"].append("P_product")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "result.json"
            result_path.write_text(json.dumps(fixture))
            image_path = root / "slide.png"
            canonical = root / "product.png"
            Image.new("RGB", (1000, 500), "white").save(image_path)
            Image.new("RGB", (800, 400), "white").save(canonical)
            analysis = RecordedVisualAnalysis(result_path)
            result = compile_semantic_map(
                analysis=analysis,
                image_path=image_path,
                upstream_handoff={
                    "selected_assets": [{
                        "internal": {
                            "asset_id": "PROJECT_IMAGE",
                            "source_kind": "project_visual",
                            "canonical_file": str(canonical),
                        }
                    }]
                },
            )

        mapped = next(item for item in result["entities"] if item["id"] == "P_product")
        self.assertEqual(mapped["asset_mapping_status"], "exact_agent_selected_project_visual")
        self.assertEqual(mapped["upstream_asset_mapping"]["canonical_file"], str(canonical))


if __name__ == "__main__":
    unittest.main()
