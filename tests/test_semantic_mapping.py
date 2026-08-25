from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.providers.file import FileStructuredVisionProvider
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
            provider = FileStructuredVisionProvider(ROOT / "tests" / "fixtures" / "unit" / "semantic_scene_draft_fixture.json")
            result = compile_semantic_map(provider=provider, image_path=image_path, upstream_handoff=handoff)

        by_id = {entity["id"]: entity for entity in result["entities"]}
        self.assertEqual(by_id["T_title"]["authored_text"], "Grounded title")
        self.assertEqual(by_id["T_title"]["bbox_hint"], [70, 35, 600, 60])
        self.assertTrue(by_id["S_accent"]["sam_prompt"])
        self.assertFalse(by_id["I_example"]["sam_prompt"])
        self.assertEqual(by_id["I_example"]["asset_mapping_status"], "exact_upstream_candidate")
        self.assertTrue(result["semantic_mapping_runtime"]["automatic"])

    def test_low_quality_scene_is_rejected(self) -> None:
        fixture = json.loads((ROOT / "tests" / "fixtures" / "unit" / "semantic_scene_draft_fixture.json").read_text())
        fixture["quality"]["source_coverage"] = 0.4
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            result_path.write_text(json.dumps(fixture))
            image_path = Path(directory) / "slide.png"
            Image.new("RGB", (100, 100), "white").save(image_path)
            provider = FileStructuredVisionProvider(result_path)
            with self.assertRaisesRegex(ValueError, "quality floor"):
                compile_semantic_map(provider=provider, image_path=image_path, upstream_handoff={})


if __name__ == "__main__":
    unittest.main()
