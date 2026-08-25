import unittest

from slidecraft.orchestration.naming import (
    migrate_deck_and_slide,
    migrate_orchestration_state,
    migrate_reconstruction_handoff,
)


class NamingMigrationTests(unittest.TestCase):
    def test_deck_and_slide_legacy_fields_migrate(self) -> None:
        deck, slide, notices = migrate_deck_and_slide(
            {"local_libraries": {"template_manifest": "inputs/template_references/library_manifest.json", "template_max_results_per_slide": 3}},
            {"fixed_template_references": [{"reference_id": "OLD", "path": "inputs/template_references/old.png"}]},
        )
        self.assertEqual(deck["local_libraries"]["visual_reference_manifest"], "inputs/visual_references/library_manifest.json")
        self.assertEqual(slide["fixed_visual_references"][0]["reference_id"], "OLD")
        self.assertEqual(slide["fixed_visual_references"][0]["path"], "inputs/visual_references/old.png")
        self.assertEqual(len(notices), 5)

    def test_state_legacy_fields_migrate(self) -> None:
        state, notices = migrate_orchestration_state({
            "deck_configuration": {"id": "legacy"},
            "reference_retrieval": {"template_references": [1], "template_retrieval": {"selected": [1]}},
        })
        self.assertEqual(state["deck_design_configuration"]["id"], "legacy")
        self.assertEqual(state["reference_retrieval"]["visual_references"], [1])
        self.assertEqual(len(notices), 3)

    def test_handoff_legacy_fields_migrate(self) -> None:
        handoff, notices = migrate_reconstruction_handoff({"template_references": [1], "template_retrieval": {}})
        self.assertEqual(handoff["visual_references"], [1])
        self.assertEqual(len(notices), 2)


if __name__ == "__main__":
    unittest.main()
