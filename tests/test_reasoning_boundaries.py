from __future__ import annotations

import inspect
import json
import tempfile
from importlib.resources import files
from pathlib import Path

import pytest

from slidecraft.agent import list_capabilities, safe_call_capability
from slidecraft.orchestration.clarification import package_agent_questions
from slidecraft.orchestration.pipeline import run_pipeline
from slidecraft.orchestration.resource_selection import resolve_resource_selection
from slidecraft.reconstruction.contract import build_reconstruction_contract


def test_public_capability_discovery_is_workflow_oriented() -> None:
    public = list_capabilities()
    assert "workflows" in public
    assert "capabilities" not in public
    assert all("capabilities" not in workflow for workflow in public["workflows"])
    assert public["control_model"] == "agent_host"

    expanded = list_capabilities(workflow="resources_and_generation")
    assert expanded["workflow"]["name"] == "resources_and_generation"
    assert any(item["name"] == "search_resources" for item in expanded["workflow"]["capabilities"])


def test_packaged_semantic_design_contract_names_the_host_agent_as_owner() -> None:
    schema = json.loads(
        files("slidecraft.schemas").joinpath("semantic_design.schema.json").read_text(encoding="utf-8")
    )
    modes = schema["properties"]["planner"]["properties"]["provider_mode"]["enum"]
    assert modes == ["host_agent", "recorded_fixture"]


def test_generation_requires_the_recorded_agent_retrieval_decision() -> None:
    parameters = inspect.signature(run_pipeline).parameters
    assert parameters["resource_candidates"].default is inspect.Parameter.empty
    assert parameters["resource_selection"].default is inspect.Parameter.empty


def test_workflow_status_reports_facts_without_prescribing_actions() -> None:
    with tempfile.TemporaryDirectory() as directory:
        safe_call_capability("create_workspace", {"workspace": directory, "deck_id": "demo"})
        status = safe_call_capability("workflow_status", {"workspace": directory})["result"]
    assert "project_facts" in status
    assert "next_actions" not in status


def test_framework_accepts_the_agent_decision_to_ask_no_questions() -> None:
    package = package_agent_questions([])
    assert package["questions"] == []
    assert package["reasoning_ownership"]["question_selection"] == "host_agent"


def test_resource_search_evidence_cannot_become_a_selection_implicitly() -> None:
    with pytest.raises(ValueError, match="schema validation"):
        resolve_resource_selection(
            {"schema_version": "1.0.0", "authored_by": "agent_reasoning"},
            visual_search={"candidates": []},
            icon_search={"candidate_sets": []},
            component_search={"candidates": []},
        )


def test_reconstruction_route_must_be_agent_authored() -> None:
    measured = {
        "source": {"width_px": 100, "height_px": 100, "path": str(Path("slide.png"))},
        "entities": [
            {
                "id": "T1",
                "kind": "text",
                "role": "body",
                "measurement": {"layout_bbox": {"px": [1, 1, 40, 20]}},
            }
        ],
    }
    plan = {
        "schema_version": "1.0.0",
        "authored_by": "agent_reasoning",
        "coordinate_space": "generation_region_px",
        "decision_rationale": "The fixture needs no alignment adjustment.",
        "alignment_groups": [],
    }
    with pytest.raises(KeyError, match="reconstruction_route"):
        build_reconstruction_contract(measured, {}, plan)
