from __future__ import annotations

import pytest

from slidecraft.orchestration.clarification import normalize_answers, package_agent_questions


def question(identifier: str = "clarify_decision") -> dict:
    return {
        "question_id": identifier,
        "impact_dimension": "decision context inferred by the Agent",
        "prompt": "Which decision should this presentation enable?",
        "why_it_matters": "The answer changes the governing message and evidence order.",
        "planning_decisions_affected": ["governing message", "storyline order"],
        "source_basis": ["The request names an audience but no decision."],
        "response_type": "single_choice_or_free_text",
        "options": ["Approve a recommendation", "Align on next steps"],
    }


def test_agent_questions_are_packaged_without_framework_selection() -> None:
    supplied = [question()]
    package = package_agent_questions(supplied)
    assert package["question_count"] == 1
    assert package["questions"][0]["prompt"] == supplied[0]["prompt"]
    assert package["questions"][0]["authored_by"] == "agent_reasoning"
    assert package["reasoning_ownership"]["question_selection"] == "host_agent"


def test_zero_questions_is_a_valid_agent_decision() -> None:
    package = package_agent_questions([])
    assert package["questions"] == []
    assert package["can_proceed_without_answers"]


def test_framework_rejects_excess_or_ungrounded_questions() -> None:
    with pytest.raises(ValueError, match="configured maximum"):
        package_agent_questions([question(f"q{index}") for index in range(4)])
    invalid = question()
    invalid["source_basis"] = []
    with pytest.raises(ValueError, match="evidence or uncertainty"):
        package_agent_questions([invalid])


def test_skip_all_records_agent_delegation_and_allows_planning() -> None:
    package = package_agent_questions([question()])
    result = normalize_answers(package, None, skipped_all=True)
    assert result["planning_may_proceed"]
    assert result["answers"][0]["resolution"] == "delegated_to_agent"
