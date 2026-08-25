from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from slidecraft.orchestration.component_retrieval import retrieve_known_components


class ComponentRetrievalTests(unittest.TestCase):
    def test_uncertified_component_stays_retrieval_evidence(self) -> None:
        semantic_design = {
            "main_message": "Show global distribution on a world map",
            "communication_archetype": "geographic distribution",
            "semantic_units": [{"meaning": "world regions", "role": "world_map"}],
            "semantic_relationships": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "component_id": "example.world-map",
                "version": "1.0.0",
                "name": "World map",
                "description": "Editable regional map",
                "semantic": {
                    "roles": ["world_map"],
                    "concepts": ["world", "map", "distribution"],
                    "aliases": ["global map"],
                    "required_parts": ["regions"],
                    "relationship_types": ["distribution"],
                },
                "recognition": {"minimum_confidence": 0.2},
                "implementation": {"type": "pptx_fragment", "source": "missing.pptx"},
            }
            (root / "world.component.json").write_text(json.dumps(manifest), encoding="utf-8")

            result = retrieve_known_components(root, semantic_design)

            self.assertEqual(result["selected"], [])
            self.assertTrue(result["candidates"][0]["confidence_met"])
            self.assertFalse(result["candidates"][0]["implementation_available"])
            self.assertEqual(result["candidates"][0]["fallback_route"], "standard_reconstruction")


if __name__ == "__main__":
    unittest.main()
