"""Contracts for Agent-authored pre-planning clarifications."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_POLICY = {
    "maximum_questions": 3,
    "all_questions_optional": True,
    "allow_skip_all": True,
}


def clarification_prompt(request: dict[str, Any], intake: dict[str, Any] | None = None) -> str:
    """Give the host Agent a compact reasoning brief without deciding what to ask."""
    return f"""Decide whether any clarification is worth asking before planning this presentation.

Reason over the complete request, source material, objective, audience context, explicit constraints, and unresolved evidence. Ask only when an answer could materially change the storyline, governing message, evidence allocation, scope, decision logic, or another consequential planning choice.

Do not ask for information that is already available. Do not ask about visual preferences that the selected presentation style already resolves. Ask no questions when the Agent can make a sound documented judgment from the available context.

Return zero to three final questions in priority order. Each question must include a stable question_id, a concise prompt, why_it_matters, a free-form impact_dimension, the planning_decisions_affected, source_basis, response_type, and zero to four useful options. The user may answer freely or delegate the decision to the Agent.

REQUEST
{json.dumps(request, indent=2, ensure_ascii=False)}

NORMALIZED INTAKE
{json.dumps(intake or {}, indent=2, ensure_ascii=False)}
"""


def _validate_question(question: dict[str, Any], index: int) -> dict[str, Any]:
    required = {
        "question_id",
        "prompt",
        "why_it_matters",
        "impact_dimension",
        "planning_decisions_affected",
        "source_basis",
        "response_type",
        "options",
    }
    missing = sorted(required - set(question))
    if missing:
        raise ValueError(f"Agent-authored clarification {index} is missing fields {missing}")
    for field in ("question_id", "prompt", "why_it_matters", "impact_dimension", "response_type"):
        if not isinstance(question[field], str) or not question[field].strip():
            raise ValueError(f"Clarification {index} requires a non-empty {field}")
    for field in ("planning_decisions_affected", "source_basis", "options"):
        values = question[field]
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"Clarification {index} requires {field} to be a list of non-empty strings")
    if not question["planning_decisions_affected"]:
        raise ValueError(f"Clarification {index} must identify at least one planning decision it could change")
    if not question["source_basis"]:
        raise ValueError(f"Clarification {index} must identify the evidence or uncertainty that motivated it")
    if len(question["options"]) > 4:
        raise ValueError(f"Clarification {index} has more than four suggested options")
    return {
        **question,
        "question_id": question["question_id"].strip(),
        "prompt": question["prompt"].strip(),
        "authored_by": "agent_reasoning",
    }


def package_agent_questions(
    questions: list[dict[str, Any]],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and package final questions chosen by the host Agent."""
    resolved_policy = {**DEFAULT_POLICY, **(policy or {})}
    maximum = int(resolved_policy["maximum_questions"])
    if maximum < 0:
        raise ValueError("maximum_questions cannot be negative")
    if len(questions) > maximum:
        raise ValueError(f"The Agent supplied {len(questions)} clarifications, above the configured maximum of {maximum}")
    validated = [_validate_question(question, index) for index, question in enumerate(questions, start=1)]
    identifiers = [question["question_id"] for question in validated]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Agent-authored clarification IDs must be unique")
    normalized_prompts = [" ".join(question["prompt"].lower().split()) for question in validated]
    if len(normalized_prompts) != len(set(normalized_prompts)):
        raise ValueError("Agent-authored clarifications contain duplicate prompts")
    return {
        "schema_version": "1.1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "phase": "before_deck_planning",
        "questions": validated,
        "question_count": len(validated),
        "interaction": {
            "all_questions_optional": bool(resolved_policy["all_questions_optional"]),
            "allow_skip_all": bool(resolved_policy["allow_skip_all"]),
            "preferred_host_surface": "native_structured_input_when_available",
            "fallback_surface": "ordinary_agent_conversation",
        },
        "policy": resolved_policy,
        "reasoning_ownership": {
            "question_selection": "host_agent",
            "framework_role": "schema_validation_packaging_and_answer_provenance",
        },
        "can_proceed_without_answers": True,
    }


def normalize_answers(
    package: dict[str, Any],
    answers: dict[str, Any] | None,
    *,
    skipped_all: bool = False,
) -> dict[str, Any]:
    supplied = answers or {}
    resolved = []
    for question in package["questions"]:
        answer = supplied.get(question["question_id"])
        delegated = skipped_all or answer in (None, "")
        resolved.append({
            "question_id": question["question_id"],
            "impact_dimension": question["impact_dimension"],
            "answer": None if delegated else answer,
            "resolution": "delegated_to_agent" if delegated else "user_answered",
            "planning_decisions_affected": question["planning_decisions_affected"],
        })
    return {
        "schema_version": "1.1.0",
        "question_package_created_at": package["created_at"],
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "skipped_all": skipped_all,
        "answers": resolved,
        "planning_may_proceed": True,
    }


def load_questions(path: str | Path) -> list[dict[str, Any]]:
    value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("questions")
    if not isinstance(value, list):
        raise TypeError("Agent clarification result must contain a questions list")
    return value
