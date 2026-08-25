from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from slidecraft.agent_workflows import generate_slide, open_project, prepare_deck
from slidecraft.mcp_server import build_server


def test_mcp_exposes_only_six_complete_workflow_tools() -> None:
    server = build_server()
    assert set(server._tool_manager._tools) == {
        "slidecraft_open_project",
        "slidecraft_prepare_deck",
        "slidecraft_generate_slide",
        "slidecraft_measure_slide",
        "slidecraft_reconstruct_slide",
        "slidecraft_render_deck",
    }


def test_open_project_returns_context_and_prepare_deck_returns_planning_brief() -> None:
    with tempfile.TemporaryDirectory() as directory, patch.dict(
        os.environ,
        {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")},
    ):
        project = open_project(
            identifier="Market Review",
            create_if_missing=True,
            location=str(Path(directory) / "market-review"),
        )
        prepared = prepare_deck(
            project=project["project"]["workspace_path"],
            brief={
                "objective": "Recommend a market entry strategy",
                "materials": [
                    {
                        "modality": "text",
                        "content": "The market grew by 12 percent last year.",
                        "authority": "authoritative",
                    }
                ],
            },
        )

    assert project["project"]["name"] == "Market Review"
    assert "progress" in project
    assert prepared["status"] == "ready_for_deck_plan"
    assert "PLANNING METHOD" in prepared["planning_brief"]
    assert prepared["result_schema"]["type"] == "object"


def test_prepare_deck_accepts_agent_authored_evidence_without_parsing_source_files() -> None:
    with tempfile.TemporaryDirectory() as directory, patch.dict(
        os.environ,
        {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")},
    ):
        root = Path(directory)
        source = root / "legacy-deck.pptx"
        source.write_bytes(b"opaque source owned by the host Agent")
        project = open_project(
            identifier="Grounded Planning",
            create_if_missing=True,
            location=str(root / "grounded-planning"),
        )
        prepared = prepare_deck(
            project=project["project"]["workspace_path"],
            brief={
                "objective": "Explain the operating model",
                "materials": [{
                    "material_id": "SOURCE_DECK",
                    "modality": "presentation",
                    "path": str(source),
                }],
                "source_atoms": [{
                    "atom_id": "FACT_001",
                    "material_id": "SOURCE_DECK",
                    "locator": "slide:4",
                    "modality": "structured_text",
                    "value": {"claim": "The workflow has five connected capabilities."},
                    "authority": "authoritative",
                    "required_usage": True,
                    "provenance": "agent_source_analysis",
                }],
            },
        )

    assert prepared["status"] == "ready_for_deck_plan"
    assert "The workflow has five connected capabilities" in prepared["planning_brief"]


def test_new_project_defaults_to_the_agent_current_workspace() -> None:
    with tempfile.TemporaryDirectory() as directory, patch.dict(
        os.environ,
        {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")},
    ), patch("slidecraft.agent_workflows.Path.cwd", return_value=Path(directory) / "workspace"):
        opened = open_project(identifier="Current Workspace Deck", create_if_missing=True)

    assert opened["resolution"] == "created"
    assert opened["project"]["workspace_path"] == str((Path(directory) / "workspace").resolve())


def test_prepared_deck_exposes_semantic_design_guidance_for_a_content_slide() -> None:
    fixture = Path(__file__).parent / "fixtures" / "unit" / "deck_plan_fixture.json"
    with tempfile.TemporaryDirectory() as directory, patch.dict(
        os.environ,
        {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")},
    ):
        opened = open_project(
            identifier="Workflow Test",
            create_if_missing=True,
            location=str(Path(directory) / "workflow-test"),
        )
        project = opened["project"]["workspace_path"]
        brief = {
            "schema_version": "1.0.0",
            "deck_id": "demo_deck",
            "objective": "Explain one answer",
            "audience": {"description": "Executives"},
            "materials": [
                {
                    "material_id": "M1",
                    "modality": "text",
                    "content": "Authoritative evidence",
                    "authority": "authoritative",
                }
            ],
        }
        prepare_deck(project=project, brief=brief)
        prepare_deck(project=project, deck_plan=json.loads(fixture.read_text(encoding="utf-8")))
        generated = generate_slide(project=project, slide_id="content_1")

    assert generated["status"] == "ready_for_semantic_design"
    assert generated["slide_request"]["slide_id"] == "content_1"
    assert "Design the semantic communication structure" in generated["planning_brief"]
