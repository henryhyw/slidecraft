from __future__ import annotations

import unittest

from slidecraft.segmentation.policy import sam_eligible_entities


class SegmentationPolicyTests(unittest.TestCase):
    def test_empty_prompt_set_skips_model(self) -> None:
        self.assertEqual(sam_eligible_entities([{"id": "T1", "kind": "text", "sam_prompt": False}]), [])

    def test_legacy_icon_prompt_is_filtered(self) -> None:
        self.assertEqual(sam_eligible_entities([{"id": "I1", "kind": "icon", "sam_prompt": True}]), [])

    def test_irregular_visual_remains_eligible(self) -> None:
        entities = [{"id": "S1", "kind": "novel_visual", "sam_prompt": True}]
        self.assertEqual([item["id"] for item in sam_eligible_entities(entities)], ["S1"])


if __name__ == "__main__":
    unittest.main()
