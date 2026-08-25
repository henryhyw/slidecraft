from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from slidecraft.agent import render_current_pptx, safe_call_capability
from slidecraft.deck.manager import DeckManager
from slidecraft.intake import normalize_deck_intake
from slidecraft.providers.file import RecordedDeckPlan
from slidecraft.runtime.artifacts import ArtifactWorkspace

ROOT = Path(__file__).resolve().parents[1]


def test_transport_errors_are_structured() -> None:
    result = safe_call_capability("missing_capability", {})
    assert result["status"] == "failed"
    assert result["error"]["code"] == "unknown_capability"
    assert result["permission_prompt_triggered"] is False


def test_workflow_status_is_derived_from_artifacts() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "request.json"
        source.write_text(json.dumps({"objective": "Explain"}), encoding="utf-8")
        created = safe_call_capability("create_workspace", {"workspace": str(root), "deck_id": "demo"})
        assert created["status"] == "ok"
        registered = safe_call_capability(
            "register_artifact",
            {
                "workspace": str(root),
                "logical_key": "slides/S1/request",
                "kind": "slide_request",
                "path": str(source),
                "producer": "test",
                "slide_id": "S1",
            },
        )
        assert registered["status"] == "ok"
        status = safe_call_capability("workflow_status", {"workspace": str(root)})
        assert status["status"] == "ok"
        assert status["result"]["status"] == "in_progress"
        assert status["result"]["project_facts"]["slides"][0]["available_artifacts"] == ["request"]
        assert "next_actions" not in status["result"]


def test_workflow_status_restores_completion_from_project_deliverables() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        safe_call_capability("create_workspace", {"workspace": str(root), "deck_id": "demo"})
        deliverable = root / "deliverables" / "deck.pptx"
        deliverable.parent.mkdir()
        deliverable.write_bytes(b"pptx")

        status = safe_call_capability("workflow_status", {"workspace": str(root)})

        assert status["status"] == "ok"
        assert status["result"]["status"] == "complete"
        assert Path(status["result"]["completed_output"]["path"]).samefile(deliverable)
        assert status["result"]["completed_output"]["provenance"]["source"] == "project_deliverables"


def test_current_deck_is_progress_without_claiming_final_completion() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        safe_call_capability("create_workspace", {"workspace": str(root), "deck_id": "demo"})
        current = root / "deliverables" / "current_deck.pptx"
        current.parent.mkdir()
        current.write_bytes(b"pptx")
        ArtifactWorkspace(root).register(
            logical_key="deck/current_pptx",
            kind="editable_deck_progress",
            path=current,
            producer="test",
        )

        status = safe_call_capability("workflow_status", {"workspace": str(root)})

        assert status["status"] == "ok"
        assert status["result"]["status"] == "in_progress"
        assert status["result"]["completed_output"] is None


def test_current_deck_uses_every_fresh_scene_in_planned_order() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = ArtifactWorkspace(root)
        workspace.initialize(deck_id="demo")
        plan_path = root / "plan.json"
        design_path = root / "design.json"
        first_scene = root / "first.json"
        second_scene = root / "second.json"
        plan = {
            "slides": [
                {"slide_id": "first", "ordinal": 1, "route": "image_generation"},
                {"slide_id": "second", "ordinal": 2, "route": "image_generation"},
            ]
        }
        design = {
            "config_id": "design-1",
            "full_slide_px": [1600, 900],
            "style": {"background": "#FFFFFF"},
        }
        scene_template = {
            "dimensions_px": [1600, 900],
            "background": "#FFFFFF",
            "design_config_id": "design-1",
            "objects": [],
        }
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        design_path.write_text(json.dumps(design), encoding="utf-8")
        first_scene.write_text(json.dumps({**scene_template, "slide_id": "first"}), encoding="utf-8")
        second_scene.write_text(json.dumps({**scene_template, "slide_id": "second"}), encoding="utf-8")
        workspace.register(logical_key="deck/plan", kind="deck_plan", path=plan_path, producer="test")
        workspace.register(logical_key="deck/design", kind="deck_design", path=design_path, producer="test")
        workspace.register(
            logical_key="slides/second/constructor_scene",
            kind="constructor_scene",
            path=second_scene,
            producer="test",
            slide_id="second",
        )
        workspace.register(
            logical_key="slides/first/constructor_scene",
            kind="constructor_scene",
            path=first_scene,
            producer="test",
            slide_id="first",
        )
        seen: list[list[str]] = []

        def fake_constructor(*, scene_paths: list[Path], output: Path, arguments: dict[str, object]) -> tuple[str, int]:
            seen.append([path.name for path in scene_paths])
            output.write_bytes(b"editable deck")
            return "ok", len(scene_paths)

        with patch("slidecraft.agent._run_powerpoint_constructor", side_effect=fake_constructor):
            result = render_current_pptx(
                workspace=str(root),
                output=str(root / "deliverables" / "current_deck.pptx"),
            )

        assert seen == [["first.json", "second.json"]]
        assert Path(result["display_path"]).read_bytes() == b"editable deck"
        assert result["validation"]["completed_slide_ids"] == ["first", "second"]
        assert result["validation"]["deck_complete"] is True


def test_workflow_status_reports_an_unplanned_deck_without_choosing_an_action() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        request = root / "request.json"
        request.write_text(json.dumps({"deck_id": "demo", "objective": "Explain the decision"}), encoding="utf-8")
        safe_call_capability("create_workspace", {"workspace": str(root), "deck_id": "demo"})
        safe_call_capability(
            "register_artifact",
            {
                "workspace": str(root),
                "logical_key": "deck/request",
                "kind": "deck_request",
                "path": str(request),
                "producer": "test",
            },
        )

        status = safe_call_capability("workflow_status", {"workspace": str(root)})

        assert status["status"] == "ok"
        assert status["result"]["project_facts"]["brief_recorded"] is True
        assert status["result"]["project_facts"]["clarifications_recorded"] is False
        assert status["result"]["project_facts"]["deck_plan_recorded"] is False
        assert "next_actions" not in status["result"]


def test_agent_resolves_named_project_before_workflow_actions() -> None:
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
        created = safe_call_capability("create_project", {"name": "Market Review"})
        resolved = safe_call_capability("resolve_project", {"identifier": "market review"})

    assert created["status"] == "ok"
    assert resolved["status"] == "ok"
    assert resolved["result"]["project"]["project_id"] == created["result"]["project_id"]


def test_new_project_status_reports_an_empty_project() -> None:
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
        project = safe_call_capability("create_project", {"name": "New Deck", "location": str(Path(directory) / "project")})["result"]
        status = safe_call_capability("workflow_status", {"workspace": project["workspace_path"]})

    assert status["result"]["status"] == "in_progress"
    assert status["result"]["project_facts"]["brief_recorded"] is False


def test_agent_can_start_a_deck_without_direct_filesystem_authoring() -> None:
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
        project = safe_call_capability("create_project", {"name": "Shared Workflow", "location": str(Path(directory) / "project")})["result"]
        started = safe_call_capability(
            "set_deck_brief",
            {
                "workspace": project["workspace_path"],
                "brief": {
                    "objective": "Recommend a market entry",
                    "materials": [{"modality": "text", "content": "The market grew by 12%.", "authority": "authoritative"}],
                    "delegated_execution": True,
                },
            },
        )
        status = safe_call_capability("workflow_status", {"workspace": project["workspace_path"]})

    assert started["status"] == "ok"
    assert started["result"]["brief"]["project_name"] == "Shared Workflow"
    assert started["result"]["brief"]["materials"][0]["material_id"] == "MATERIAL_001"
    assert status["result"]["project_facts"]["brief_recorded"] is True
    assert status["result"]["project_facts"]["clarifications_recorded"] is False


def test_planned_deck_status_reports_slide_artifacts_without_orchestrating() -> None:
    request = {
        "schema_version": "1.0.0",
        "deck_id": "demo_deck",
        "objective": "Explain one answer",
        "audience": {"description": "Executives"},
        "materials": [{"material_id": "M1", "modality": "text", "content": "Authoritative evidence", "authority": "authoritative"}],
    }
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}):
        project = safe_call_capability("create_project", {"name": "Demo", "location": str(Path(directory) / "project")})["result"]
        root = Path(project["workspace_path"])
        authored_plan = RecordedDeckPlan(ROOT / "tests" / "fixtures" / "unit" / "deck_plan_fixture.json").read()
        DeckManager(root, authored_plan).initialize(
            request=request,
            intake=normalize_deck_intake(request, root),
            design_system=json.loads((root / ".slidecraft" / "deck_design.json").read_text()),
        )

        status = safe_call_capability("workflow_status", {"workspace": str(root)})
        slide_facts = {item["slide_id"]: item for item in status["result"]["project_facts"]["slides"]}
        assert "job" in slide_facts["content_1"]["available_artifacts"]
        assert "request" not in slide_facts["content_1"]["available_artifacts"]
        assert "next_actions" not in status["result"]

        prepared = safe_call_capability(
            "prepare_slide",
            {"workspace": str(root), "slide_id": "content_1", "output_dir": str(root / ".slidecraft" / "slides" / "content_1")},
        )
        assert prepared["status"] == "ok"
        slide_request = json.loads(Path(prepared["result"]["slide_request"]).read_text())
        assert slide_request["exact_content"]["content"] == ["Authoritative evidence"]
