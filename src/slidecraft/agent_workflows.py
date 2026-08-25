"""Small, task-oriented workflows exposed to Agent applications."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from slidecraft import agent
from slidecraft.runtime.artifacts import ArtifactWorkspace


def _root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _active(workspace: Path) -> dict[str, dict[str, Any]]:
    return {
        item["logical_key"]: item
        for item in ArtifactWorkspace(workspace).inspect()["active_artifacts"]
    }


def _artifact_path(workspace: Path, logical_key: str) -> Path:
    record = _active(workspace).get(logical_key)
    if record is None:
        raise KeyError(f"Project work is missing {logical_key}")
    return Path(record["path"])


def _write_agent_result(workspace: Path, name: str, value: dict[str, Any]) -> Path:
    path = workspace / ".slidecraft" / "agent_inputs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _project_config(workspace: Path) -> str | None:
    path = workspace / ".slidecraft" / "config.toml"
    return str(path) if path.is_file() else None


def _prepared_slide(workspace: Path, slide_id: str, slide_dir: Path) -> dict[str, str]:
    active = _active(workspace)
    request = active.get(f"slides/{slide_id}/request")
    prompt = active.get(f"slides/{slide_id}/semantic_planning_prompt")
    if request and prompt and request["freshness"]["fresh"] and prompt["freshness"]["fresh"]:
        return {"slide_request": request["path"], "semantic_planning_prompt": prompt["path"]}
    return agent.prepare_slide(workspace=str(workspace), slide_id=slide_id, output_dir=str(slide_dir))


def open_project(
    *,
    identifier: str,
    create_if_missing: bool = False,
    location: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Open a named project and return everything an Agent needs to continue."""

    project_location = location
    if create_if_missing and project_location is None:
        project_location = str(Path.cwd())

    resolved = agent.resolve_project(
        identifier=identifier,
        create_if_missing=create_if_missing,
        location=project_location,
        description=description,
    )
    project = resolved["project"]
    workspace = resolved["location"]
    return {
        "resolution": resolved["resolution"],
        "project": project,
        "progress": agent.workflow_status(workspace=workspace),
        "contents": agent.project_detail(location=workspace, include_internal=False),
        "resources": agent.project_resource_catalog(location=workspace),
    }


def prepare_deck(
    *,
    project: str,
    brief: dict[str, Any] | None = None,
    deck_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a brief, prepare the planning brief, or validate an Agent-authored deck plan."""

    workspace = _root(project)
    if brief is not None:
        brief = json.loads(json.dumps(brief))
        for material in brief.get("materials", []):
            source = material.get("path")
            if not source:
                continue
            original = str(_root(source))
            stored = agent.add_project_material(location=str(workspace), source=original)
            material["path"] = stored["path"]
            material.setdefault("source_locator", original)
        for asset in brief.pop("visual_assets", []):
            asset_id = asset.get("asset_id")
            if asset_id:
                agent.update_project_asset(
                    location=str(workspace),
                    asset_id=asset_id,
                    semantic_role=asset.get("semantic_role"),
                    description=asset.get("description"),
                    usage_policy=asset.get("usage_policy"),
                    slide_ids=asset.get("slide_ids"),
                )
                continue
            source = asset.get("source") or asset.get("path")
            if not source:
                raise ValueError("Each visual asset requires an asset_id or source file")
            record = agent.add_project_asset(
                location=str(workspace),
                source=str(_root(source)),
                semantic_role=asset.get("semantic_role"),
                description=asset.get("description"),
                usage_policy=asset.get("usage_policy", "available"),
                slide_ids=asset.get("slide_ids"),
                provenance="agent_conversation_upload",
            )
            if any(key in asset for key in ("semantic_role", "description", "usage_policy", "slide_ids")):
                agent.update_project_asset(
                    location=str(workspace),
                    asset_id=record["asset_id"],
                    semantic_role=asset.get("semantic_role"),
                    description=asset.get("description"),
                    usage_policy=asset.get("usage_policy"),
                    slide_ids=asset.get("slide_ids"),
                )
        agent.set_deck_brief(workspace=str(workspace), brief=brief)
    request_path = _artifact_path(workspace, "deck/request")
    design_path = _artifact_path(workspace, "deck/design")
    request = json.loads(request_path.read_text(encoding="utf-8"))

    if deck_plan is None:
        from slidecraft.deck.planning import build_deck_prompt, load_deck_plan_schema
        from slidecraft.intake import normalize_deck_intake

        intake = normalize_deck_intake(request, workspace)
        design = json.loads(design_path.read_text(encoding="utf-8"))
        return {
            "status": "ready_for_deck_plan",
            "planning_brief": build_deck_prompt(request, intake, design),
            "result_schema": load_deck_plan_schema(),
            "project_progress": agent.workflow_status(workspace=str(workspace)),
        }

    plan_path = _write_agent_result(workspace, "deck_plan.json", deck_plan)
    result = agent.plan_deck(
        workspace=str(workspace),
        request=str(request_path),
        design=str(design_path),
        result=str(plan_path),
    )
    return {
        "status": "deck_prepared",
        "deck": result["manifest"],
        "project_progress": agent.workflow_status(workspace=str(workspace)),
    }


def generate_slide(
    *,
    project: str,
    slide_id: str,
    semantic_design: dict[str, Any] | None = None,
    resource_selection: dict[str, Any] | None = None,
    generated_image: str | None = None,
    host_supports_image_generation: bool = True,
) -> dict[str, Any]:
    """Prepare, generate, or register one information-bearing slide image."""

    workspace = _root(project)
    slide_dir = workspace / ".slidecraft" / "slides" / slide_id
    slide_dir.mkdir(parents=True, exist_ok=True)
    handoff_key = f"slides/{slide_id}/reconstruction_handoff"

    if generated_image:
        record = agent.register_generated_image(
            workspace=str(workspace),
            image=str(_root(generated_image)),
            handoff_key=handoff_key,
            slide_id=slide_id,
            activate=True,
            provenance={"source": "agent_image_tool"},
        )
        return {"status": "image_registered", "artifact": record}

    prepared = _prepared_slide(workspace, slide_id, slide_dir)
    if semantic_design is None:
        return {
            "status": "ready_for_semantic_design",
            "slide_request": json.loads(Path(prepared["slide_request"]).read_text(encoding="utf-8")),
            "planning_brief": Path(prepared["semantic_planning_prompt"]).read_text(encoding="utf-8"),
        }

    semantic_path = _write_agent_result(workspace, f"{slide_id}_semantic_design.json", semantic_design)
    candidates_path = slide_dir / "resource_candidates.json"
    candidates = agent.search_resources(
        workspace=str(workspace),
        design=str(_artifact_path(workspace, "deck/design")),
        slide=prepared["slide_request"],
        semantic_design=str(semantic_path),
        output=str(candidates_path),
        slide_id=slide_id,
    )
    if resource_selection is None:
        return {
            "status": "ready_for_resource_selection",
            "candidates": candidates["result"],
            "instruction": "Choose useful resources in context and return their stable IDs with concise rationales.",
        }

    generation = agent.prepare_generation(
        workspace=str(workspace),
        design=str(_artifact_path(workspace, "deck/design")),
        slide=prepared["slide_request"],
        output_dir=str(slide_dir),
        slide_id=slide_id,
        semantic_design=str(semantic_path),
        resource_selection=resource_selection,
    )
    package = generation["pipeline_result"]
    prompt = Path(package["prompt"]).read_text(encoding="utf-8")
    route = agent.resolve_image_generation_route(
        host_supports_image_generation=host_supports_image_generation,
        project_config=_project_config(workspace),
    )
    if route["route"] == "host":
        image_inputs = _generation_image_inputs(slide_dir / "generation_context.json")
        return {
            "status": "ready_for_agent_image_generation",
            "prompt": prompt,
            "reference_images": [item["path"] for item in image_inputs],
            "image_inputs": image_inputs,
            "canvas_px": package["generation_canvas_px"],
            "registration": {"project": str(workspace), "slide_id": slide_id},
        }
    if route["status"] != "ready":
        return {"status": "image_service_unavailable", "connection": route, "prompt": prompt}
    image_path = slide_dir / "generated_slide.png"
    result = agent.generate_slide_image(
        workspace=str(workspace),
        slide_id=slide_id,
        handoff_key=handoff_key,
        prompt=prompt,
        output=str(image_path),
        canvas_px=package["generation_canvas_px"],
        reference_images=[item["path"] for item in _generation_image_inputs(slide_dir / "generation_context.json")],
        host_supports_image_generation=host_supports_image_generation,
        project_config=_project_config(workspace),
        activate=True,
    )
    return {"status": "image_generated", "result": result}


def _selected_reference_paths(path: Path) -> list[str]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("visual_references", {}).get("selected", [])
    return [str(item["path"]) for item in records if item.get("path")]


def _generation_image_inputs(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [item for item in payload.get("generation", {}).get("image_inputs", []) if item.get("path")]


def measure_slide(
    *,
    project: str,
    slide_id: str,
    visual_analysis: dict[str, Any] | None = None,
    segmentation: str = "auto",
    checkpoint: str | None = None,
    device: str = "auto",
) -> dict[str, Any]:
    """Prepare visual-analysis guidance or measure an Agent-understood slide."""

    workspace = _root(project)
    image = _artifact_path(workspace, f"slides/{slide_id}/generated_image")
    handoff = _artifact_path(workspace, f"slides/{slide_id}/reconstruction_handoff")
    output_dir = workspace / ".slidecraft" / "slides" / slide_id / "measurement"
    output_dir.mkdir(parents=True, exist_ok=True)

    if visual_analysis is None:
        from PIL import Image

        from slidecraft.semantic_mapping.compiler import load_connector_audit_schema, load_schema
        from slidecraft.semantic_mapping.prompt import build_semantic_mapping_prompt

        with Image.open(image) as raster:
            canvas = raster.size
        handoff_value = json.loads(handoff.read_text(encoding="utf-8"))
        return {
            "status": "ready_for_visual_analysis",
            "analysis_brief": build_semantic_mapping_prompt(canvas_px=canvas, upstream_handoff=handoff_value),
            "result_schema": load_schema(),
            "connector_audit_brief_builder": "After identifying connectors, audit their source, target, direction, topology, and feasible native routing.",
            "connector_audit_schema": load_connector_audit_schema(),
        }

    analysis_path = _write_agent_result(workspace, f"{slide_id}_visual_analysis.json", visual_analysis)
    semantic_path = output_dir / "semantic_scene.json"
    agent.semantic_map(
        workspace=str(workspace),
        image=str(image),
        handoff=str(handoff),
        output=str(semantic_path),
        slide_id=slide_id,
        result=str(analysis_path),
        segmentation=segmentation,
    )
    result = agent.measure_slide(
        workspace=str(workspace),
        image=str(image),
        semantic_map=str(semantic_path),
        handoff=str(handoff),
        output_dir=str(output_dir),
        slide_id=slide_id,
        checkpoint=checkpoint,
        device=device,
        no_sam=segmentation == "never",
    )
    return {"status": "slide_measured", **result}


def reconstruct_slide(
    *,
    project: str,
    slide_id: str,
    refinement_plan: dict[str, Any],
) -> dict[str, Any]:
    """Build one editable slide from measured evidence and Agent-authored refinement intent."""

    workspace = _root(project)
    slide_dir = workspace / ".slidecraft" / "slides" / slide_id / "reconstruction"
    slide_dir.mkdir(parents=True, exist_ok=True)
    measured = _artifact_path(workspace, f"slides/{slide_id}/measured_scene")
    design = _artifact_path(workspace, "deck/design")
    contract_path = slide_dir / "reconstruction_contract.json"
    scene_path = slide_dir / "constructor_scene.json"
    contract = agent.build_reconstruction_contract_capability(
        workspace=str(workspace),
        scene_evidence=str(measured),
        design=str(design),
        slide_id=slide_id,
        output=str(contract_path),
        refinement_plan=refinement_plan,
    )
    scene = agent.compile_reconstruction_scene(
        workspace=str(workspace),
        contract=str(contract_path),
        design=str(design),
        slide_id=slide_id,
        output=str(scene_path),
        scene_evidence=str(measured),
    )
    active = _active(workspace)
    plan_record = active.get("deck/plan")
    ordinal = 1
    if plan_record:
        plan = json.loads(Path(plan_record["path"]).read_text(encoding="utf-8"))
        planned = next((item for item in plan.get("slides", []) if item["slide_id"] == slide_id), None)
        if planned:
            ordinal = int(planned["ordinal"])
    slide_output = workspace / "deliverables" / "slides" / f"{ordinal:02d}_{slide_id}.pptx"
    editable = agent.render_slide_pptx(
        workspace=str(workspace),
        slide_id=slide_id,
        output=str(slide_output),
    )
    current_deck = agent.render_current_pptx(
        workspace=str(workspace),
        output=str(workspace / "deliverables" / "current_deck.pptx"),
    )
    return {
        "status": "slide_reconstructed",
        "contract": contract,
        "scene": scene,
        "editable_slide": editable,
        "current_deck": current_deck,
    }


def render_deck(
    *,
    project: str,
    output: str | None = None,
    title: str = "Slidecraft presentation",
    company: str = "",
    language: str = "en-US",
) -> dict[str, Any]:
    """Validate all planned slides and export the editable PowerPoint deck."""

    workspace = _root(project)
    destination = _root(output) if output else workspace / "deliverables" / "presentation.pptx"
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = agent.render_pptx(
        workspace=str(workspace),
        output=str(destination),
        title=title,
        company=company,
        language=language,
    )
    return {
        "status": "deck_rendered",
        "powerpoint": str(destination),
        "validation": result["validation"],
        "project": agent.project_detail(location=str(workspace), include_internal=False),
    }
