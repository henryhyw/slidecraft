import json
import unittest
from pathlib import Path

from slidecraft.refinement.constrained_normalization import solve_plan

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "normalization_config.json").read_text())


class ConstrainedNormalizationTests(unittest.TestCase):
    def test_current_slide_peer_badges_align(self) -> None:
        plan = json.loads((ROOT / "tests" / "fixtures" / "architecture" / "normalization_plan.json").read_text())
        report = solve_plan(plan, CONFIG)
        decision = report["decisions"][0]
        self.assertEqual(decision["status"], "accepted")
        self.assertEqual(decision["target_anchor_value"], 13.5)
        self.assertEqual(decision["corrections"][0]["delta_px"], [0.0, 5.5])
        self.assertEqual(decision["corrections"][1]["delta_px"], [0.0, -5.5])

    def test_parent_overflow_rejects_complete_transaction(self) -> None:
        plan = {
            "alignment_groups": [{
                "id": "unsafe",
                "semantic_basis": "test",
                "anchor": "top",
                "confidence": 1.0,
                "target_value": 1,
                "members": [
                    {"id": "a", "bbox_px": [10, 10, 20, 20], "parent_bbox_px": [0, 0, 40, 40]},
                    {"id": "b", "bbox_px": [10, 20, 20, 20], "parent_bbox_px": [0, 0, 40, 40]},
                ],
            }]
        }
        decision = solve_plan(plan, CONFIG)["decisions"][0]
        self.assertEqual(decision["status"], "rejected")
        self.assertFalse(decision["checks"]["parent_containment"])

    def test_low_confidence_relationship_is_unchanged(self) -> None:
        plan = {
            "alignment_groups": [{
                "id": "uncertain",
                "semantic_basis": "weak visual similarity",
                "anchor": "bottom",
                "confidence": 0.4,
                "members": [
                    {"id": "a", "bbox_px": [10, 10, 20, 20], "parent_bbox_px": [0, 0, 100, 100]},
                    {"id": "b", "bbox_px": [50, 20, 20, 20], "parent_bbox_px": [0, 0, 100, 100]},
                ],
            }]
        }
        decision = solve_plan(plan, CONFIG)["decisions"][0]
        self.assertEqual(decision["status"], "rejected")
        self.assertIn("confidence", decision["reason"].lower())


if __name__ == "__main__":
    unittest.main()
