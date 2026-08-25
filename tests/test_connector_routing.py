from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.historical_regression.build_generated_contract import semantic_owner_anchors


class ConnectorRoutingTests(unittest.TestCase):
    def test_merge_terminal_projects_junction_onto_target_boundary(self) -> None:
        boxes = {
            "source_a": [100, 100, 180, 80],
            "source_b": [100, 220, 180, 80],
            "source_c": [100, 340, 180, 80],
            "target_stage": [500, 80, 300, 420],
        }
        starts, ends, _ = semantic_owner_anchors(
            intent={
                "source_entities": ["source_a", "source_b", "source_c"],
                "target_entities": ["target_stage"],
            },
            starts=[[280, 140], [280, 260], [280, 380]],
            ends=[[500, 300]],
            orientation="horizontal_inputs_to_vertical_bus_then_horizontal_output",
            boxes=boxes,
            junctions=[[400, 260]],
        )
        self.assertEqual(starts, [[280, 140.0], [280, 260.0], [280, 380.0]])
        self.assertEqual(ends, [[500, 260]])

    def test_horizontal_peer_flow_has_one_shared_axis(self) -> None:
        starts, ends, _ = semantic_owner_anchors(
            intent={"source_entities": ["left"], "target_entities": ["right"]},
            starts=[[300, 200]],
            ends=[[500, 204]],
            orientation="horizontal",
            boxes={"left": [100, 100, 200, 300], "right": [500, 80, 220, 360]},
        )
        self.assertEqual(starts[0][1], ends[0][1])
        self.assertEqual(starts[0][0], 300)
        self.assertEqual(ends[0][0], 500)


if __name__ == "__main__":
    unittest.main()
