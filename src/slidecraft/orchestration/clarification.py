"""High-value pre-planning clarification selection for Agent-hosted workflows."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_POLICY = {
    "maximum_questions": 3,
    "minimum_value_score": 0.34,
    "allowed_dimensions": [
        "audience_decision",
        "desired_action",
        "governing_answer",
        "situation_complication",
        "scope_boundary",
        "time_horizon_or_baseline",
        "proof_requirement",
        "stakeholder_sensitivity",
        "success_criterion",
    ],
}


def _known(request: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = request.get(key)
        if value not in (None, "", [], {}):
            return True
    return False


def _dimension_answered(request: dict[str, Any], dimension: str) -> bool:
    mapping = {
        "audience_decision": ("audience", "audience_decision"),
        "desired_action": ("desired_outcome", "desired_action", "call_to_action"),
        "governing_answer": ("recommendation", "main_message", "governing_answer", "hypothesis"),
        "situation_complication": ("situation", "complication", "context"),
        "scope_boundary": ("scope", "scope_boundaries", "priorities"),
        "time_horizon_or_baseline": ("time_horizon", "comparison_baseline", "baseline"),
        "proof_requirement": ("proof_requirement", "evidence_standard"),
        "stakeholder_sensitivity": ("stakeholder_sensitivity", "sensitivities"),
        "success_criterion": ("success_criterion", "success_metrics"),
    }
    return _known(request, *mapping.get(dimension, ()))


def fallback_candidates(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Create conservative candidates when the host Agent supplies no model result."""
    candidates = []

    def add(
        question_id: str,
        dimension: str,
        prompt: str,
        why: str,
        options: list[str],
        impact: float,
        uncertainty: float,
    ) -> None:
        candidates.append({
            "question_id": question_id,
            "impact_dimension": dimension,
            "prompt": prompt,
            "why_it_matters": why,
            "response_type": "single_choice_or_free_text",
            "options": options + ["请使用你的最佳判断"],
            "impact_score": impact,
            "uncertainty_score": uncertainty,
            "answerability_score": 0.95,
            "already_answered": False,
            "changes": [],
        })

    audience = request.get("audience")
    audience_known = bool(audience and (not isinstance(audience, dict) or audience.get("description")))
    if not audience_known:
        add(
            "clarify_audience_decision",
            "audience_decision",
            "这份材料主要给谁看，他们需要据此作出什么决定？",
            "受众和决策决定答案先行程度、证据深度和故事线顺序。",
            ["高管作出方向性决策", "项目团队对齐执行方案", "客户理解分析结论", "用于汇报进展并争取支持"],
            0.98,
            0.95,
        )
    if not _known(request, "desired_outcome", "desired_action", "call_to_action"):
        add(
            "clarify_desired_action",
            "desired_action",
            "看完这套材料后，你最希望受众做什么？",
            "明确行动目标可以区分说明型、决策型和说服型 storyline。",
            ["批准一个建议", "选择一个方案", "形成共同理解", "启动下一步行动"],
            0.96,
            0.88,
        )
    if not _known(request, "recommendation", "main_message", "governing_answer", "hypothesis"):
        add(
            "clarify_governing_answer",
            "governing_answer",
            "你已经有希望传达的结论，还是希望 Agent 根据材料形成结论？",
            "这会决定 deck 使用建议先行、假设验证或探索式结构。",
            ["已有明确结论，请围绕它组织证据", "有初步假设，可以调整", "请根据材料形成最佳结论", "只客观呈现，不提出建议"],
            0.94,
            0.90,
        )
    objective = str(request.get("objective", "")).lower()
    comparative = any(token in objective for token in ("compare", "comparison", "versus", "vs", "benchmark", "对比", "比较", "基准"))
    if comparative and not _known(request, "comparison_baseline", "baseline", "time_horizon"):
        add(
            "clarify_baseline",
            "time_horizon_or_baseline",
            "这次比较最重要的基准或时间范围是什么？",
            "基准决定数据选择、图表口径和结论有效范围。",
            ["与当前状态比较", "与主要竞争者比较", "与目标状态比较", "按最近一个完整年度比较"],
            0.86,
            0.82,
        )
    materials = request.get("materials", [])
    if len(materials) >= 4 and not _known(request, "scope", "scope_boundaries", "priorities"):
        add(
            "clarify_scope",
            "scope_boundary",
            "如果材料之间存在取舍，哪些主题必须进入主线？",
            "范围优先级决定主 deck、附录和可省略内容之间的分配。",
            ["优先支持最终建议的内容", "优先量化证据", "所有材料都需要覆盖", "由 Agent 根据受众价值取舍"],
            0.78,
            0.76,
        )
    return candidates


def clarification_prompt(request: dict[str, Any], intake: dict[str, Any] | None = None) -> str:
    return f"""Identify a very small set of high-value questions before planning this presentation.

The questions must resolve uncertainty that can materially change the storyline, governing message, evidence allocation, scope, or decision logic. Do not ask about visual style, colors, exact layouts, or information already present. Prefer questions a user can answer immediately from intent. Every question must allow the user to delegate the decision to the Agent.

Candidate dimensions are audience decision, desired action, governing answer, situation or complication, scope boundary, time horizon or comparison baseline, proof requirement, stakeholder sensitivity, and success criterion.

Return at most five candidates. For each candidate provide question_id, impact_dimension, prompt, why_it_matters, response_type, two to four concise options, impact_score, uncertainty_score, answerability_score, already_answered, and the planning decisions that could change.

REQUEST
{json.dumps(request, indent=2, ensure_ascii=False)}

NORMALIZED INTAKE
{json.dumps(intake or {}, indent=2, ensure_ascii=False)}
"""


def select_questions(
    request: dict[str, Any],
    candidates: list[dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_policy = {**DEFAULT_POLICY, **(policy or {})}
    source = candidates if candidates is not None else fallback_candidates(request)
    selected = []
    seen_dimensions = set()
    for candidate in source:
        if candidate.get("already_answered"):
            continue
        dimension = candidate.get("impact_dimension")
        if dimension and _dimension_answered(request, dimension):
            continue
        if dimension not in resolved_policy["allowed_dimensions"] or dimension in seen_dimensions:
            continue
        impact = float(candidate.get("impact_score", 0.0))
        uncertainty = float(candidate.get("uncertainty_score", 0.0))
        answerability = float(candidate.get("answerability_score", 0.0))
        value_score = round(impact * uncertainty * answerability, 4)
        if value_score < float(resolved_policy["minimum_value_score"]):
            continue
        record = {**candidate, "value_score": value_score}
        options = list(record.get("options", []))
        if not any("最佳判断" in option or "best judgment" in option.lower() for option in options):
            options.append("请使用你的最佳判断")
        record["options"] = options
        selected.append(record)
        seen_dimensions.add(dimension)
    selected.sort(key=lambda item: item["value_score"], reverse=True)
    selected = selected[: int(resolved_policy["maximum_questions"])]
    return {
        "schema_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "phase": "before_deck_planning",
        "questions": selected,
        "question_count": len(selected),
        "interaction": {
            "all_questions_optional": True,
            "allow_skip_all": True,
            "skip_label": "跳过，由 Agent 使用最佳判断",
            "preferred_host_surface": "native_structured_input_when_available",
            "fallback_surface": "ordinary_agent_conversation",
        },
        "policy": resolved_policy,
        "can_proceed_without_answers": True,
    }


def normalize_answers(package: dict[str, Any], answers: dict[str, Any] | None, *, skipped_all: bool = False) -> dict[str, Any]:
    supplied = answers or {}
    resolved = []
    for question in package["questions"]:
        answer = supplied.get(question["question_id"])
        delegated = skipped_all or answer in (None, "", "请使用你的最佳判断")
        resolved.append({
            "question_id": question["question_id"],
            "impact_dimension": question["impact_dimension"],
            "answer": None if delegated else answer,
            "resolution": "delegated_to_agent" if delegated else "user_answered",
        })
    return {
        "schema_version": "1.0.0",
        "question_package_created_at": package["created_at"],
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "skipped_all": skipped_all,
        "answers": resolved,
        "planning_may_proceed": True,
    }


def load_candidates(path: str | Path | None) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return value.get("questions", value.get("candidates", value)) if isinstance(value, dict) else value
