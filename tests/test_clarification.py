from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.orchestration.clarification import normalize_answers, select_questions


class ClarificationTests(unittest.TestCase):
    def test_questions_are_small_optional_and_storyline_relevant(self) -> None:
        package = select_questions({"deck_id": "D1", "objective": "Assess the market", "materials": []})
        dimensions = {item["impact_dimension"] for item in package["questions"]}
        self.assertLessEqual(package["question_count"], 3)
        self.assertTrue(package["interaction"]["allow_skip_all"])
        self.assertTrue(package["can_proceed_without_answers"])
        self.assertIn("audience_decision", dimensions)
        self.assertIn("governing_answer", dimensions)
        for question in package["questions"]:
            self.assertIn("请使用你的最佳判断", question["options"])

    def test_already_known_dimensions_are_not_asked_again(self) -> None:
        package = select_questions({
            "deck_id": "D1",
            "objective": "Recommend a path",
            "audience": {"description": "Board making an investment decision"},
            "desired_action": "Approve option A",
            "recommendation": "Choose option A",
            "materials": [],
        })
        dimensions = {item["impact_dimension"] for item in package["questions"]}
        self.assertNotIn("audience_decision", dimensions)
        self.assertNotIn("desired_action", dimensions)
        self.assertNotIn("governing_answer", dimensions)

    def test_skip_all_records_agent_delegation_and_allows_planning(self) -> None:
        package = select_questions({"deck_id": "D1", "objective": "Explain a change", "materials": []})
        result = normalize_answers(package, None, skipped_all=True)
        self.assertTrue(result["planning_may_proceed"])
        self.assertTrue(all(item["resolution"] == "delegated_to_agent" for item in result["answers"]))


if __name__ == "__main__":
    unittest.main()
