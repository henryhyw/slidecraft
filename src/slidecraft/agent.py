"""Presentation capabilities exposed to Agent applications."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import sysconfig
import uuid
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from slidecraft.runtime.artifacts import ArtifactWorkspace

CAPABILITIES = {
    "create_workspace": {
        "description": "Create or open the working folder for a presentation.",
        "required": ["workspace"],
        "optional": ["deck_id", "metadata"],
        "mutates": True,
    },
    "create_project": {
        "description": "Create a presentation project with source and deliverable folders, then add it to the local project list.",
        "required": ["name"],
        "optional": ["location", "deck_id", "description"],
        "mutates": True,
    },
    "list_projects": {
        "description": "List locally registered projects and whether their selected folders remain available.",
        "required": [],
        "optional": [],
        "mutates": False,
    },
    "resolve_project": {
        "description": "Find a project by its name, stable ID, or folder, and create it when the user starts new work.",
        "required": ["identifier"],
        "optional": ["create_if_missing", "location", "deck_id", "description"],
        "mutates": True,
    },
    "project_detail": {
        "description": "Show project progress, user-facing outputs, and technical evidence when requested.",
        "required": ["location"],
        "optional": ["include_internal"],
        "mutates": False,
    },
    "set_deck_brief": {
        "description": "Create or revise the authoritative deck brief from the conversation, materials, constraints, audience, and desired output.",
        "required": ["workspace", "brief"],
        "optional": [],
        "mutates": True,
    },
    "add_project_asset": {
        "description": "Add a user asset from chat or a local path to the shared project asset catalog.",
        "required": ["location", "source"],
        "optional": ["semantic_role", "description", "usage_policy", "slide_ids", "provenance"],
        "mutates": True,
    },
    "add_project_material": {
        "description": "Add a source document or data file to a project without changing its current plan.",
        "required": ["location", "source"],
        "optional": [],
        "mutates": True,
    },
    "list_project_assets": {
        "description": "List project assets and discover files added directly to the asset folder.",
        "required": ["location"],
        "optional": ["sync_folder"],
        "mutates": True,
    },
    "update_project_asset": {
        "description": "Update the semantic role or deck usage policy for one project asset.",
        "required": ["location", "asset_id"],
        "optional": ["semantic_role", "description", "usage_policy", "slide_ids"],
        "mutates": True,
    },
    "remove_project_asset": {
        "description": "Remove a visual asset from the active project catalog while preserving its source file.",
        "required": ["location", "asset_id"],
        "optional": [],
        "mutates": True,
    },
    "add_project_library_resource": {
        "description": "Select an icon, component, or visual reference from a reusable collection for one project.",
        "required": ["location", "category", "item_id"],
        "optional": [],
        "mutates": True,
    },
    "remove_project_resource": {
        "description": "Hide a retrieved or user-selected reusable resource from one project without deleting it from the shared collection.",
        "required": ["location", "category", "resource_id"],
        "optional": [],
        "mutates": True,
    },
    "list_project_events": {
        "description": "Read user changes made in the project console since the Agent last reviewed them.",
        "required": ["location"],
        "optional": ["pending_only"],
        "mutates": False,
    },
    "acknowledge_project_events": {
        "description": "Mark reviewed project-console changes as acknowledged without triggering a plan automatically.",
        "required": ["location", "event_ids"],
        "optional": [],
        "mutates": True,
    },
    "project_resource_catalog": {
        "description": "Inspect project materials, direct-use visuals, retrieved references, icons, and reusable components.",
        "required": ["location"],
        "optional": [],
        "mutates": True,
    },
    "reconcile_project_resources": {
        "description": "Reconcile durable project resource assignments with legacy and current retrieval records.",
        "required": ["location"],
        "optional": ["include_legacy_outputs"],
        "mutates": True,
    },
    "list_library_resources": {
        "description": "Inspect one reusable resource collection and its retrieval metadata.",
        "required": ["name"],
        "optional": [],
        "mutates": False,
    },
    "add_library_resource": {
        "description": "Add a local file to a reusable collection with optional semantic metadata.",
        "required": ["name", "source"],
        "optional": ["metadata"],
        "mutates": True,
    },
    "update_library_resource": {
        "description": "Complete or revise the name, description, tags, and semantic roles of a reusable resource.",
        "required": ["name", "item_id"],
        "optional": ["metadata"],
        "mutates": True,
    },
    "resolve_image_generation_route": {
        "description": "Choose the Agent image tool or the configured API connection using the workspace policy.",
        "required": ["host_supports_image_generation"],
        "optional": ["project_config"],
        "mutates": False,
    },
    "generate_slide_image": {
        "description": "Generate a slide image through the image service selected in Slidecraft settings.",
        "required": ["workspace", "slide_id", "handoff_key", "prompt", "output", "canvas_px", "host_supports_image_generation"],
        "optional": ["reference_images", "project_config", "activate"],
        "mutates": True,
    },
    "inspect_workspace": {
        "description": "Inspect active artifacts, candidates, freshness, and history.",
        "required": ["workspace"],
        "optional": ["include_history"],
        "mutates": False,
    },
    "workflow_status": {
        "description": "Show durable project facts, artifacts, validation attention, and deliverables for Agent interpretation.",
        "required": ["workspace"],
        "optional": ["include_history"],
        "mutates": False,
    },
    "register_artifact": {
        "description": "Register one immutable output revision and its logical dependencies.",
        "required": ["workspace", "logical_key", "kind", "path", "producer"],
        "optional": ["dependencies", "slide_id", "config_sha256", "provenance", "activate", "validation"],
        "mutates": True,
    },
    "accept_artifact": {
        "description": "Make a candidate or earlier revision active.",
        "required": ["workspace", "artifact_id"],
        "optional": [],
        "mutates": True,
    },
    "reject_artifact": {
        "description": "Reject a non-active candidate while retaining its audit record.",
        "required": ["workspace", "artifact_id"],
        "optional": ["reason"],
        "mutates": True,
    },
    "prepare_generation": {
        "description": "Assemble the visual-generation brief from Agent-authored semantic design and resource selections.",
        "required": ["workspace", "design", "slide", "output_dir", "slide_id", "resource_selection"],
        "optional": ["overrides", "semantic_design"],
        "mutates": True,
    },
    "search_resources": {
        "description": "Search reusable collections and return candidates for the Agent to inspect and select.",
        "required": ["workspace", "design", "slide", "semantic_design", "output"],
        "optional": ["slide_id"],
        "mutates": True,
    },
    "prepare_clarifications": {
        "description": "Validate and store zero to three final planning questions chosen by the Agent after reasoning over the request and materials.",
        "required": ["workspace", "request", "output", "questions"],
        "optional": ["policy"],
        "mutates": True,
    },
    "record_clarification_answers": {
        "description": "Record user answers or delegation and make them available to deck planning.",
        "required": ["workspace", "question_package", "output"],
        "optional": ["answers", "answers_file", "skipped_all"],
        "mutates": True,
    },
    "plan_deck": {
        "description": "Validate and register the deck plan authored by the host Agent from the agreed brief and source material.",
        "required": ["workspace", "request", "design", "result"],
        "optional": ["system_layouts"],
        "mutates": True,
    },
    "prepare_slide": {
        "description": "Compile one planned content-slide job into an authoritative slide request and semantic-planning prompt for the host Agent.",
        "required": ["workspace", "slide_id", "output_dir"],
        "optional": [],
        "mutates": True,
    },
    "register_generated_image": {
        "description": "Register a generated image candidate against its generation handoff.",
        "required": ["workspace", "image", "handoff_key", "slide_id"],
        "optional": ["activate", "provenance"],
        "mutates": True,
    },
    "semantic_map": {
        "description": "Validate and compile the semantic scene authored by the host Agent from the generated slide and handoff.",
        "required": ["workspace", "image", "handoff", "output", "slide_id", "result"],
        "optional": ["segmentation"],
        "mutates": True,
    },
    "measure_slide": {
        "description": "Measure slide geometry with OpenCV and add SAM boundary evidence for eligible irregular regions.",
        "required": ["workspace", "image", "semantic_map", "handoff", "output_dir", "slide_id"],
        "optional": ["checkpoint", "sam_config", "device", "no_sam"],
        "mutates": True,
    },
    "compile_reconstruction_scene": {
        "description": "Compile measured scene evidence and the audited reconstruction contract into a constructor scene.",
        "required": ["workspace", "contract", "design", "slide_id", "output"],
        "optional": ["scene_evidence", "dependencies"],
        "mutates": True,
    },
    "build_reconstruction_contract": {
        "description": "Compile Agent-authored reconstruction and refinement decisions with measured scene evidence.",
        "required": ["workspace", "scene_evidence", "design", "slide_id", "output", "refinement_plan"],
        "optional": [],
        "mutates": True,
    },
    "render_pptx": {
        "description": "Render one or more active constructor scenes into an editable PowerPoint file.",
        "required": ["workspace", "output"],
        "optional": ["scene_keys", "title", "company", "language", "display_font", "body_font", "backend", "node_modules"],
        "mutates": True,
    },
}


WORKFLOWS = [
    {
        "name": "project",
        "description": "Create, find, inspect, and continue presentation projects.",
        "capabilities": ["resolve_project", "project_detail", "workflow_status"],
    },
    {
        "name": "brief_and_sources",
        "description": "Capture the agreed brief and add source materials or direct-use visual assets.",
        "capabilities": ["set_deck_brief", "add_project_material", "add_project_asset", "update_project_asset"],
    },
    {
        "name": "plan",
        "description": "Record useful clarifications and author the deck storyline, slide jobs, routes, and chrome.",
        "capabilities": ["prepare_clarifications", "record_clarification_answers", "plan_deck", "prepare_slide"],
    },
    {
        "name": "resources_and_generation",
        "description": "Search reusable collections, record Agent selections, assemble prompts, and generate slide images.",
        "capabilities": ["search_resources", "prepare_generation", "generate_slide_image", "register_generated_image"],
    },
    {
        "name": "understand_and_reconstruct",
        "description": "Map slide meaning, measure pixels, author refinement decisions, and construct editable objects.",
        "capabilities": [
            "semantic_map",
            "measure_slide",
            "build_reconstruction_contract",
            "compile_reconstruction_scene",
        ],
    },
    {
        "name": "deliver",
        "description": "Assemble validated constructor scenes into the editable PowerPoint deliverable.",
        "capabilities": ["render_pptx", "project_detail"],
    },
]


def list_capabilities(
    *, capability: str | None = None, workflow: str | None = None, include_internal: bool = False
) -> dict[str, Any]:
    workflow_summaries = [
        {"name": item["name"], "description": item["description"]}
        for item in WORKFLOWS
    ]
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "control_model": "agent_host",
        "workflows": workflow_summaries,
        "interaction": "The agent app chooses the tools that match the conversation. After a new session begins, inspect the project and continue from its current progress.",
        "recommended_entrypoint": {
            "existing_or_named_project": "resolve_project",
            "after_project_resolution": "workflow_status",
            "user_facing_project_view": "project_detail",
        },
        "artifact_policy": "Return deliverables, reviewable artifacts, and decisions that answer the user's request. Keep low-level evidence hidden unless requested.",
    }
    if capability:
        if capability not in CAPABILITIES:
            raise KeyError(f"Unknown capability {capability}")
        result["capability"] = {"name": capability, **CAPABILITIES[capability]}
    elif workflow:
        selected = next((item for item in WORKFLOWS if item["name"] == workflow), None)
        if selected is None:
            raise KeyError(f"Unknown workflow {workflow}")
        result["workflow"] = {
            **selected,
            "capabilities": [
                {"name": name, "description": CAPABILITIES[name]["description"]}
                for name in selected["capabilities"]
            ],
        }
    elif include_internal:
        result["capabilities"] = [{"name": name, **spec} for name, spec in CAPABILITIES.items()]
    else:
        result["capability_discovery"] = (
            "Inspect project facts, choose a workflow through your own reasoning, then expand only that workflow or capability."
        )
    return result


def _workspace(value: str | Path) -> ArtifactWorkspace:
    return ArtifactWorkspace(Path(value).expanduser().resolve())


def create_workspace(**arguments: Any) -> dict[str, Any]:
    return _workspace(arguments["workspace"]).initialize(deck_id=arguments.get("deck_id"), metadata=arguments.get("metadata"))


def create_project(**arguments: Any) -> dict[str, Any]:
    from slidecraft.projects import create_project as create

    return create(
        name=arguments["name"],
        location=arguments.get("location"),
        deck_id=arguments.get("deck_id"),
        description=arguments.get("description", ""),
    )


def list_projects(**arguments: Any) -> dict[str, Any]:
    from slidecraft.projects import list_projects as list_registered

    return {"projects": list_registered()}


def resolve_project(**arguments: Any) -> dict[str, Any]:
    from slidecraft.projects import resolve_project as resolve

    return resolve(
        arguments["identifier"],
        create_if_missing=bool(arguments.get("create_if_missing", False)),
        location=arguments.get("location"),
        deck_id=arguments.get("deck_id"),
        description=arguments.get("description", ""),
    )


def project_detail(**arguments: Any) -> dict[str, Any]:
    from slidecraft.projects import project_detail as inspect_project

    return inspect_project(arguments["location"], include_internal=bool(arguments.get("include_internal", False)))


def set_deck_brief(**arguments: Any) -> dict[str, Any]:
    """Persist an Agent-authored deck brief without requiring direct file access."""
    from importlib.resources import files

    workspace_path = Path(arguments["workspace"]).expanduser().resolve()
    brief = dict(arguments["brief"])
    if not str(brief.get("objective", "")).strip():
        raise ValueError("The deck brief requires an objective")
    materials = brief.get("materials", [])
    if not isinstance(materials, list):
        raise TypeError("Deck brief materials must be a list")
    for index, material in enumerate(materials, start=1):
        if not isinstance(material, dict):
            raise TypeError(f"Material {index} must be an object")
        material.setdefault("material_id", f"MATERIAL_{index:03d}")
        material.setdefault("modality", "text")
        if "content" not in material and "path" not in material:
            raise ValueError(f"Material {material['material_id']} requires content or a local path")
    from slidecraft.projects import PROJECT_FILE

    manifest_path = workspace_path / PROJECT_FILE
    project = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    brief.setdefault("schema_version", "1.0.0")
    brief.setdefault("deck_id", project.get("deck_id") or f"deck_{uuid.uuid4().hex[:12]}")
    brief.setdefault("project_name", project.get("name", brief.get("objective", "Presentation")))
    output = workspace_path / ".slidecraft" / "requests" / f"deck_request_{uuid.uuid4().hex[:12]}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    workspace = _workspace(workspace_path)
    workspace.initialize(deck_id=brief["deck_id"], metadata={"project_name": brief["project_name"]})
    active = {item["logical_key"] for item in workspace.inspect()["active_artifacts"]}
    if "deck/design" not in active:
        design_path = workspace_path / ".slidecraft" / "deck_design.json"
        design_path.parent.mkdir(parents=True, exist_ok=True)
        design_path.write_text(
            files("slidecraft.defaults").joinpath("deck_design.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        workspace.register(
            logical_key="deck/design",
            kind="deck_design_configuration",
            path=design_path,
            producer="set_deck_brief",
            validation={"status": "passed", "source": "packaged_baseline"},
        )
    record = workspace.register(
        logical_key="deck/request",
        kind="deck_request",
        path=output,
        producer="set_deck_brief",
        validation={"status": "passed", "material_count": len(materials)},
    )
    return {"artifact": record, "request": str(output), "brief": brief}


def add_project_asset(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_assets import add_project_asset as add

    return add(
        arguments["location"],
        arguments["source"],
        semantic_role=arguments.get("semantic_role"),
        description=arguments.get("description"),
        usage_policy=arguments.get("usage_policy", "available"),
        slide_ids=arguments.get("slide_ids"),
        provenance=arguments.get("provenance", "agent_host_attachment"),
    )


def add_project_material(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_materials import add_project_material as add

    return add(arguments["location"], arguments["source"], actor="agent_host")


def list_project_assets(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_assets import list_project_assets as list_assets

    return list_assets(arguments["location"], sync_folder=bool(arguments.get("sync_folder", True)))


def update_project_asset(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_assets import update_project_asset as update

    return update(
        arguments["location"],
        arguments["asset_id"],
        semantic_role=arguments.get("semantic_role"),
        description=arguments.get("description"),
        usage_policy=arguments.get("usage_policy"),
        slide_ids=arguments.get("slide_ids"),
        actor="agent_host",
    )


def remove_project_asset(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_assets import deactivate_project_asset

    return deactivate_project_asset(arguments["location"], arguments["asset_id"], actor="agent_host")


def add_project_library_resource(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_resource_selections import add_project_library_resource as add

    return add(
        arguments["location"],
        category=arguments["category"],
        item_id=arguments["item_id"],
        actor="agent_host",
    )


def remove_project_resource(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_resource_selections import remove_project_resource as remove

    return remove(
        arguments["location"],
        category=arguments["category"],
        resource_id=arguments["resource_id"],
        actor="agent_host",
    )


def list_project_events(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_events import list_project_events as list_events

    return list_events(arguments["location"], pending_only=bool(arguments.get("pending_only", True)))


def acknowledge_project_events(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_events import acknowledge_project_events as acknowledge

    return acknowledge(arguments["location"], arguments["event_ids"])


def project_resource_catalog(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_resources import project_resource_catalog as catalog

    return catalog(arguments["location"])


def reconcile_project_resources(**arguments: Any) -> dict[str, Any]:
    from slidecraft.project_resource_selections import reconcile_project_resources as reconcile

    return reconcile(
        arguments["location"],
        include_legacy_outputs=bool(arguments.get("include_legacy_outputs", True)),
    )


def list_library_resources(**arguments: Any) -> dict[str, Any]:
    from slidecraft.library_manager import list_library_items

    return list_library_items(arguments["name"])


def add_library_resource(**arguments: Any) -> dict[str, Any]:
    from slidecraft.library_manager import add_library_path

    return add_library_path(arguments["name"], arguments["source"], arguments.get("metadata"))


def update_library_resource(**arguments: Any) -> dict[str, Any]:
    from slidecraft.library_manager import update_library_item_metadata

    return update_library_item_metadata(arguments["name"], arguments["item_id"], arguments.get("metadata", {}))


def resolve_image_generation_route(**arguments: Any) -> dict[str, Any]:
    from slidecraft.configuration import resolve_config
    from slidecraft.providers.resolution import resolve_image_generation_route as resolve_route

    project_config = Path(arguments["project_config"]).expanduser().resolve() if arguments.get("project_config") else None
    config, _ = resolve_config(project_config)
    return resolve_route(
        config["providers"]["image_generation"],
        host_supports_image_generation=bool(arguments["host_supports_image_generation"]),
    )


def generate_slide_image(**arguments: Any) -> dict[str, Any]:
    from slidecraft.configuration import resolve_config
    from slidecraft.credentials import resolve_provider_credential
    from slidecraft.providers.openai import OpenAIImageGenerationProvider
    from slidecraft.providers.resolution import resolve_image_generation_route as resolve_route

    project_config = Path(arguments["project_config"]).expanduser().resolve() if arguments.get("project_config") else None
    config, _ = resolve_config(project_config)
    provider_config = config["providers"]["image_generation"]
    credential = resolve_provider_credential(provider_config)
    route = resolve_route(
        provider_config,
        host_supports_image_generation=bool(arguments["host_supports_image_generation"]),
    )
    if route["route"] == "host":
        return {**route, "action": "generate_with_agent_then_call_register_generated_image"}
    if route["status"] != "ready":
        return route

    provider = OpenAIImageGenerationProvider(
        model=route["model"],
        api_key=credential["secret"],
        base_url=route.get("base_url") or None,
    )
    canvas = arguments["canvas_px"]
    result = provider.generate(
        prompt=arguments["prompt"],
        output_path=Path(arguments["output"]),
        reference_images=[Path(value) for value in arguments.get("reference_images", [])],
        canvas_px=(int(canvas[0]), int(canvas[1])),
    )
    artifact = register_generated_image(
        workspace=arguments["workspace"],
        slide_id=arguments["slide_id"],
        handoff_key=arguments["handoff_key"],
        image=result["output_path"],
        provenance={"provider": result["provider"], "model": result["model"], "selection": route["reason"]},
        activate=bool(arguments.get("activate", False)),
    )
    return {**result, "route": route, "artifact": artifact}


def inspect_workspace(**arguments: Any) -> dict[str, Any]:
    return _workspace(arguments["workspace"]).inspect(include_history=bool(arguments.get("include_history", False)))


def workflow_status(**arguments: Any) -> dict[str, Any]:
    """Report durable project facts without choosing the Agent's next action."""
    inspection = inspect_workspace(**arguments)
    active = {item["logical_key"]: item for item in inspection["active_artifacts"]}
    workspace_root = Path(arguments["workspace"]).expanduser().resolve()
    existing_deliverables = sorted(
        (
            path for path in (workspace_root / "deliverables").glob("**/*.pptx")
            if path.is_file() and not path.name.startswith((".", "~$"))
            and path.parent == workspace_root / "deliverables"
            and path.name != "current_deck.pptx"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if (workspace_root / "deliverables").is_dir() else []
    final_record = active.get("deck/editable_pptx")
    current_record = active.get("deck/current_pptx")
    completed_output = final_record if final_record and final_record["freshness"]["fresh"] else None
    current_output = current_record if current_record and current_record["freshness"]["fresh"] else None
    if final_record is None and existing_deliverables:
        completed_output = {
            "logical_key": "deck/editable_pptx",
            "kind": "editable_powerpoint",
            "path": str(existing_deliverables[0]),
            "provenance": {"source": "project_deliverables"},
            "validation": {"status": "restored_from_project"},
        }
    planned_slides: list[dict[str, Any]] = []
    if "deck/plan" in active:
        planned_slides = json.loads(Path(active["deck/plan"]["path"]).read_text(encoding="utf-8")).get("slides", [])
    slide_ids = [item["slide_id"] for item in sorted(planned_slides, key=lambda item: item["ordinal"])] or sorted({
        item["slide_id"] for item in inspection["active_artifacts"] if item.get("slide_id")
    })
    artifact_suffixes = (
        "job",
        "request",
        "semantic_design",
        "resource_candidates",
        "reconstruction_handoff",
        "generated_image",
        "semantic_scene",
        "measured_scene",
        "reconstruction_contract",
        "constructor_scene",
        "editable_pptx",
    )
    slides = []
    for slide_id in slide_ids:
        prefix = f"slides/{slide_id}"
        available = [suffix for suffix in artifact_suffixes if f"{prefix}/{suffix}" in active]
        slides.append({"slide_id": slide_id, "available_artifacts": available})

    if completed_output:
        status = "complete"
    elif inspection["attention"]:
        status = "attention_available"
    elif active:
        status = "in_progress"
    else:
        status = "empty"
    return {
        "schema_version": "1.0.0",
        "status": status,
        "workspace_id": inspection["workspace_id"],
        "completed_output": completed_output,
        "current_output": current_output,
        "project_facts": {
            "brief_recorded": "deck/request" in active,
            "clarifications_recorded": "deck/clarification_questions" in active,
            "clarification_answers_recorded": "deck/clarification_answers" in active,
            "deck_plan_recorded": "deck/plan" in active,
            "planned_slide_count": len(planned_slides),
            "slides": slides,
        },
        "attention": inspection["attention"],
        "inspection": inspection,
        "ownership": "The host Agent interprets these facts and chooses the next action from the user's request.",
    }


def register_artifact(**arguments: Any) -> dict[str, Any]:
    workspace = _workspace(arguments["workspace"])
    return workspace.register(
        logical_key=arguments["logical_key"],
        kind=arguments["kind"],
        path=Path(arguments["path"]),
        dependencies=arguments.get("dependencies", []),
        producer=arguments["producer"],
        slide_id=arguments.get("slide_id"),
        config_sha256=arguments.get("config_sha256"),
        provenance=arguments.get("provenance"),
        activate=bool(arguments.get("activate", True)),
        validation=arguments.get("validation"),
    )


def accept_artifact(**arguments: Any) -> dict[str, Any]:
    return _workspace(arguments["workspace"]).activate(arguments["artifact_id"])


def reject_artifact(**arguments: Any) -> dict[str, Any]:
    return _workspace(arguments["workspace"]).reject(arguments["artifact_id"], reason=arguments.get("reason"))


def prepare_generation(**arguments: Any) -> dict[str, Any]:
    from slidecraft.orchestration import run_pipeline

    workspace = _workspace(arguments["workspace"])
    workspace.initialize()
    slide_id = arguments["slide_id"]
    active = {item["logical_key"]: item for item in workspace.inspect()["active_artifacts"]}
    candidates_key = f"slides/{slide_id}/resource_candidates"
    candidates_record = active.get(candidates_key)
    if candidates_record is None:
        raise ValueError(f"No recorded resource candidates exist for {slide_id}. Call search_resources first.")
    if not candidates_record["freshness"]["fresh"]:
        raise ValueError(f"Recorded resource candidates for {slide_id} are stale. Call search_resources again.")
    resource_candidates = json.loads(Path(candidates_record["path"]).read_text(encoding="utf-8"))
    output_dir = Path(arguments["output_dir"]).expanduser().resolve()
    slide_path = Path(arguments["slide"]).expanduser().resolve()
    if arguments.get("semantic_design") or arguments.get("resource_selection"):
        slide_value = json.loads(slide_path.read_text(encoding="utf-8"))
        if arguments.get("semantic_design"):
            slide_value["semantic_design_path"] = str(Path(arguments["semantic_design"]).expanduser().resolve())
        selection = arguments["resource_selection"]
        if isinstance(selection, dict):
            slide_value["resource_selection"] = selection
        else:
            slide_value["resource_selection_path"] = str(Path(selection).expanduser().resolve())
        output_dir.mkdir(parents=True, exist_ok=True)
        slide_path = output_dir / "slide_request.json"
        slide_path.write_text(json.dumps(slide_value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result = run_pipeline(
        Path(arguments["design"]).expanduser().resolve(),
        slide_path,
        output_dir,
        overrides=arguments.get("overrides"),
        resource_candidates=resource_candidates,
        resource_selection=selection if isinstance(selection, dict) else json.loads(Path(selection).expanduser().read_text(encoding="utf-8")),
    )
    prefix = f"slides/{slide_id}"
    registered = []
    design_record = workspace.register(
        logical_key="deck/design",
        kind="deck_design_configuration",
        path=Path(arguments["design"]),
        producer="prepare_generation",
    )
    slide_record = workspace.register(
        logical_key=f"{prefix}/request",
        kind="slide_request",
        path=slide_path,
        producer="prepare_generation",
    )
    registered.extend([design_record, slide_record])
    outputs = [
        ("intake", "intake_manifest", "intake_manifest.json", [f"{prefix}/request"]),
        ("semantic_design", "semantic_design", "semantic_design.json", [f"{prefix}/intake", "deck/design"]),
        ("retrieval", "reference_retrieval", "reference_retrieval.json", [candidates_key, f"{prefix}/semantic_design", "deck/design"]),
        ("assets", "normalized_assets", "normalized_assets.json", [f"{prefix}/retrieval"]),
        ("generation_package", "generation_package", "generation_package.json", [f"{prefix}/semantic_design", f"{prefix}/assets", "deck/design"]),
        ("generation_prompt", "generation_prompt", "imagegen_prompt.txt", [f"{prefix}/generation_package"]),
        ("reconstruction_handoff", "generation_to_reconstruction_handoff", "reconstruction_handoff.json", [f"{prefix}/generation_package"]),
    ]
    for suffix, kind, filename, dependencies in outputs:
        path = output_dir / filename
        if path.exists():
            registered.append(workspace.register(
                logical_key=f"{prefix}/{suffix}",
                kind=kind,
                path=path,
                dependencies=dependencies,
                producer="prepare_generation",
                slide_id=slide_id,
            ))
    project_resources = None
    from slidecraft.projects import PROJECT_FILE

    if (Path(arguments["workspace"]).expanduser().resolve() / PROJECT_FILE).is_file():
        from slidecraft.project_resource_selections import record_retrieved_project_resources

        project_resources = record_retrieved_project_resources(
            arguments["workspace"],
            output_dir / "reference_retrieval.json",
            source=str(output_dir / "reference_retrieval.json"),
            slide_id=slide_id,
        )
    return {"pipeline_result": result, "registered_artifacts": registered, "project_resources": project_resources, "workspace": workspace.inspect()}


def search_resources(**arguments: Any) -> dict[str, Any]:
    from slidecraft.orchestration.component_retrieval import search_known_components
    from slidecraft.orchestration.icon_retrieval import search_icons
    from slidecraft.orchestration.pipeline import _apply_user_defaults, _resolve_from
    from slidecraft.orchestration.semantic_planning import resolve_semantic_design
    from slidecraft.orchestration.visual_reference_retrieval import search_visual_references

    workspace_path = Path(arguments["workspace"]).expanduser().resolve()
    design_path = Path(arguments["design"]).expanduser().resolve()
    slide_path = Path(arguments["slide"]).expanduser().resolve()
    slide = json.loads(slide_path.read_text(encoding="utf-8"))
    semantic_path = Path(arguments["semantic_design"]).expanduser().resolve()
    slide["semantic_design_path"] = str(semantic_path)
    plan = resolve_semantic_design(slide, slide_path.parent)
    deck = _apply_user_defaults(json.loads(design_path.read_text(encoding="utf-8")), design_path.parent)
    libraries = deck["local_libraries"]
    exact_roles = {
        asset.get("semantic_role")
        for asset in slide.get("user_provided_assets", [])
        if asset.get("required_usage") and asset.get("canonical_file") and asset.get("semantic_role")
    }
    result = {
        "schema_version": "1.0.0",
        "decision_owner": "host_agent",
        "selection_instruction": (
            "Inspect candidates in context, then author a resource_selection object with explicit rationales. "
            "Candidate scores aid discovery and never make the final decision."
        ),
        "visual_references": search_visual_references(
            _resolve_from(design_path.parent, libraries["visual_reference_manifest"]),
            plan,
            deck,
            max_results=max(12, int(libraries["visual_reference_max_results_per_slide"]) * 4),
        ),
        "icons": search_icons(
            _resolve_from(design_path.parent, libraries["icon_root"]),
            plan.get("asset_needs"),
            excluded_semantic_roles=exact_roles,
            online_policy=deck.get("resource_policy", {}).get("icons"),
        ),
        "components": search_known_components(
            _resolve_from(design_path.parent, libraries["known_component_root"]), plan
        ),
    }
    output = Path(arguments["output"]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    slide_id = arguments.get("slide_id", "slide_01")
    workspace = _workspace(workspace_path)
    semantic_record = workspace.register(
        logical_key=f"slides/{slide_id}/semantic_design",
        kind="semantic_design",
        path=semantic_path,
        dependencies=[f"slides/{slide_id}/request", "deck/design"],
        producer="host_agent_reasoning",
        slide_id=slide_id,
        validation={"status": "passed", "decision_owner": "host_agent"},
    )
    record = workspace.register(
        logical_key=f"slides/{slide_id}/resource_candidates",
        kind="resource_candidates",
        path=output,
        dependencies=[f"slides/{slide_id}/semantic_design", "deck/design"],
        producer="search_resources",
        slide_id=slide_id,
        validation={"status": "passed", "decision_owner": "host_agent"},
    )
    return {
        "artifacts": [semantic_record, record],
        "resource_candidates": str(output),
        "result": result,
    }


def prepare_slide(**arguments: Any) -> dict[str, Any]:
    from slidecraft.deck.slide_jobs import build_slide_request
    from slidecraft.orchestration.semantic_planning import build_semantic_planning_prompt
    from slidecraft.project_assets import list_project_assets

    workspace = _workspace(arguments["workspace"])
    active = {item["logical_key"]: item for item in workspace.inspect()["active_artifacts"]}
    slide_id = arguments["slide_id"]
    job_key = f"slides/{slide_id}/job"
    for required in (job_key, "deck/request", "deck/design"):
        if required not in active:
            raise KeyError(f"Active deck artifact is missing: {required}")
    job = json.loads(Path(active[job_key]["path"]).read_text(encoding="utf-8"))
    if job["route"] != "image_generation":
        raise ValueError(f"Slide {slide_id} uses the deterministic system-layout route")
    deck_request = json.loads(Path(active["deck/request"]["path"]).read_text(encoding="utf-8"))
    slide_request = build_slide_request(
        job=job,
        deck_request=deck_request,
        project_assets=list_project_assets(arguments["workspace"], sync_folder=True)["assets"],
    )
    output_dir = Path(arguments["output_dir"]).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    request_path = output_dir / "slide_request.json"
    prompt_path = output_dir / "semantic_planning_prompt.txt"
    request_path.write_text(json.dumps(slide_request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    prompt_path.write_text(build_semantic_planning_prompt(slide_request), encoding="utf-8")
    request_record = workspace.register(
        logical_key=f"slides/{slide_id}/request",
        kind="slide_request",
        path=request_path,
        dependencies=[job_key, "deck/request"],
        producer="prepare_slide",
        slide_id=slide_id,
        validation={"status": "passed", "route": "image_generation"},
    )
    prompt_record = workspace.register(
        logical_key=f"slides/{slide_id}/semantic_planning_prompt",
        kind="semantic_planning_prompt",
        path=prompt_path,
        dependencies=[f"slides/{slide_id}/request", "deck/design"],
        producer="prepare_slide",
        slide_id=slide_id,
    )
    return {
        "slide_request": str(request_path),
        "semantic_planning_prompt": str(prompt_path),
        "artifacts": [request_record, prompt_record],
    }


def prepare_clarifications(**arguments: Any) -> dict[str, Any]:
    from slidecraft.orchestration.clarification import package_agent_questions

    request_path = Path(arguments["request"]).expanduser().resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    package = package_agent_questions(arguments["questions"], policy=arguments.get("policy"))
    output = Path(arguments["output"]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    workspace = _workspace(arguments["workspace"])
    workspace.initialize(deck_id=request.get("deck_id"))
    workspace.register(logical_key="deck/request", kind="deck_request", path=request_path, producer="prepare_clarifications")
    record = workspace.register(
        logical_key="deck/clarification_questions",
        kind="clarification_package",
        path=output,
        dependencies=["deck/request"],
        producer="prepare_clarifications",
        validation={"status": "passed", "question_count": package["question_count"]},
    )
    return {"artifact": record, "question_package": package}


def record_clarification_answers(**arguments: Any) -> dict[str, Any]:
    from slidecraft.orchestration.clarification import normalize_answers

    package_path = Path(arguments["question_package"]).expanduser().resolve()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    answers = arguments.get("answers")
    if arguments.get("answers_file"):
        answers = json.loads(Path(arguments["answers_file"]).expanduser().read_text(encoding="utf-8"))
    result = normalize_answers(package, answers, skipped_all=bool(arguments.get("skipped_all", False)))
    output = Path(arguments["output"]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    workspace = _workspace(arguments["workspace"])
    record = workspace.register(
        logical_key="deck/clarification_answers",
        kind="clarification_answers",
        path=output,
        dependencies=["deck/clarification_questions"],
        producer="record_clarification_answers",
        validation={"status": "passed", "planning_may_proceed": True},
    )
    return {"artifact": record, "answers": result}


def plan_deck(**arguments: Any) -> dict[str, Any]:
    from slidecraft.deck.manager import DeckManager
    from slidecraft.intake import normalize_deck_intake
    from slidecraft.providers.file import RecordedDeckPlan

    workspace_path = Path(arguments["workspace"]).expanduser().resolve()
    request_path = Path(arguments["request"]).expanduser().resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    workspace = _workspace(workspace_path)
    workspace.initialize(deck_id=request.get("deck_id"))
    active = {item["logical_key"]: item for item in workspace.inspect()["active_artifacts"]}
    clarification = active.get("deck/clarification_answers")
    if clarification and clarification["freshness"]["fresh"]:
        request["clarification_answers"] = json.loads(Path(clarification["path"]).read_text(encoding="utf-8"))
    from slidecraft.projects import PROJECT_FILE

    if (workspace_path / PROJECT_FILE).is_file():
        from slidecraft.project_assets import list_project_assets as project_assets

        request["project_assets"] = project_assets(workspace_path, sync_folder=True)["assets"]
    else:
        request.setdefault("project_assets", [])
    intake_base = workspace_path if (workspace_path / PROJECT_FILE).is_file() else request_path.parent
    intake = normalize_deck_intake(request, intake_base)
    design = json.loads(Path(arguments["design"]).expanduser().read_text(encoding="utf-8"))
    authored_plan = RecordedDeckPlan(Path(arguments["result"]).expanduser().resolve()).read()
    manifest = DeckManager(workspace_path, authored_plan).initialize(
        request=request,
        intake=intake,
        design_system=design,
        system_layouts_path=Path(arguments["system_layouts"]).expanduser().resolve() if arguments.get("system_layouts") else None,
    )
    return {"manifest": manifest, "workspace": workspace.inspect()}


def register_generated_image(**arguments: Any) -> dict[str, Any]:
    workspace = _workspace(arguments["workspace"])
    slide_id = arguments["slide_id"]
    return workspace.register(
        logical_key=f"slides/{slide_id}/generated_image",
        kind="generated_slide_image",
        path=Path(arguments["image"]),
        dependencies=[arguments["handoff_key"]],
        producer="image_generation_adapter",
        slide_id=slide_id,
        provenance=arguments.get("provenance", {}),
        activate=bool(arguments.get("activate", False)),
    )


def semantic_map(**arguments: Any) -> dict[str, Any]:
    from slidecraft.providers.file import RecordedVisualAnalysis
    from slidecraft.semantic_mapping.compiler import compile_semantic_map

    analysis = RecordedVisualAnalysis(Path(arguments["result"]).expanduser().resolve())
    handoff_path = Path(arguments["handoff"]).expanduser().resolve()
    compiled = compile_semantic_map(
        analysis=analysis,
        image_path=Path(arguments["image"]).expanduser().resolve(),
        upstream_handoff=json.loads(handoff_path.read_text(encoding="utf-8")),
        segmentation_mode=arguments.get("segmentation", "auto"),
    )
    output = Path(arguments["output"]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(compiled, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    workspace = _workspace(arguments["workspace"])
    slide_id = arguments["slide_id"]
    record = workspace.register(
        logical_key=f"slides/{slide_id}/semantic_scene",
        kind="semantic_scene",
        path=output,
        dependencies=[f"slides/{slide_id}/generated_image", f"slides/{slide_id}/reconstruction_handoff"],
        producer="semantic_map:host_agent",
        slide_id=slide_id,
        provenance={"provider": "host_agent"},
    )
    return {"artifact": record, "entities": len(compiled["entities"]), "groups": len(compiled["groups"])}


def _installed_script(filename: str) -> Path:
    repository = Path(__file__).resolve().parents[2] / "scripts" / filename
    if repository.exists():
        return repository
    installed = Path(sysconfig.get_path("data")) / "share" / "slidecraft" / "scripts" / filename
    if installed.exists():
        return installed
    raise FileNotFoundError(f"Required Slidecraft worker script is unavailable: {filename}")


def measure_slide(**arguments: Any) -> dict[str, Any]:
    output_dir = Path(arguments["output_dir"]).expanduser().resolve()
    command = [
        sys.executable,
        str(_installed_script("measure_visual_scene.py")),
        str(Path(arguments["image"]).expanduser().resolve()),
        "--semantic-map", str(Path(arguments["semantic_map"]).expanduser().resolve()),
        "--upstream-handoff", str(Path(arguments["handoff"]).expanduser().resolve()),
        "--output-dir", str(output_dir),
        "--device", arguments.get("device", "auto"),
    ]
    if arguments.get("checkpoint"):
        command.extend(["--checkpoint", str(Path(arguments["checkpoint"]).expanduser().resolve())])
    if arguments.get("sam_config"):
        command.extend(["--sam-config", arguments["sam_config"]])
    if arguments.get("no_sam"):
        command.append("--no-sam")
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "Slide measurement failed")
    entities = output_dir / "slide_entities.json"
    workspace = _workspace(arguments["workspace"])
    slide_id = arguments["slide_id"]
    dependencies = [f"slides/{slide_id}/generated_image", f"slides/{slide_id}/semantic_scene"]
    registered = [workspace.register(
        logical_key=f"slides/{slide_id}/measured_scene",
        kind="measured_reconstruction_scene",
        path=entities,
        dependencies=dependencies,
        producer="measure_slide",
        slide_id=slide_id,
        provenance={"device": arguments.get("device", "auto"), "sam_disabled": bool(arguments.get("no_sam"))},
    )]
    for suffix, kind, filename in (
        ("measurement_debug", "debug_visualization", "debug_overlay.png"),
        ("measurement_report", "measurement_report", "report.md"),
    ):
        path = output_dir / filename
        if path.exists():
            registered.append(workspace.register(
                logical_key=f"slides/{slide_id}/{suffix}",
                kind=kind,
                path=path,
                dependencies=[f"slides/{slide_id}/measured_scene"],
                producer="measure_slide",
                slide_id=slide_id,
            ))
    return {"artifacts": registered, "worker_output": process.stdout.strip()}


def build_reconstruction_contract_capability(**arguments: Any) -> dict[str, Any]:
    from slidecraft.reconstruction.contract import build_reconstruction_contract

    scene_path = Path(arguments["scene_evidence"]).expanduser().resolve()
    design_path = Path(arguments["design"]).expanduser().resolve()
    plan_value = arguments["refinement_plan"]
    refinement_plan = (
        plan_value
        if isinstance(plan_value, dict)
        else json.loads(Path(plan_value).expanduser().resolve().read_text(encoding="utf-8"))
    )
    contract = build_reconstruction_contract(
        json.loads(scene_path.read_text(encoding="utf-8")),
        json.loads(design_path.read_text(encoding="utf-8")),
        refinement_plan,
    )
    output = Path(arguments["output"]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    workspace = _workspace(arguments["workspace"])
    slide_id = arguments["slide_id"]
    record = workspace.register(
        logical_key=f"slides/{slide_id}/reconstruction_contract",
        kind="reconstruction_contract",
        path=output,
        dependencies=[f"slides/{slide_id}/measured_scene", "deck/design"],
        producer="build_reconstruction_contract",
        slide_id=slide_id,
        validation={"status": "passed", "unit_count": len(contract["reconstruction_units"])},
    )
    return {"artifact": record, "contract": contract}


def compile_reconstruction_scene(**arguments: Any) -> dict[str, Any]:
    from slidecraft.reconstruction.scene import build_reconstruction_scene

    def read(path: str) -> dict[str, Any]:
        return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))

    evidence_path = arguments.get("scene_evidence")
    if not evidence_path:
        raise ValueError("scene_evidence is required")
    scene = build_reconstruction_scene(
        measured_scene=read(evidence_path),
        contract=read(arguments["contract"]),
        design=read(arguments["design"]),
        slide_id=arguments["slide_id"],
    )
    output = Path(arguments["output"]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    workspace = _workspace(arguments["workspace"])
    dependencies = arguments.get("dependencies") or [
        f"slides/{arguments['slide_id']}/measured_scene",
        f"slides/{arguments['slide_id']}/reconstruction_contract",
        "deck/design",
    ]
    record = workspace.register(
        logical_key=f"slides/{arguments['slide_id']}/constructor_scene",
        kind="constructor_scene_ir",
        path=output,
        dependencies=dependencies,
        producer="compile_reconstruction_scene",
        slide_id=arguments["slide_id"],
        validation={"status": "passed", "compiler_report": scene.get("compiler_report", {})},
    )
    return {"artifact": record, "objects": len(scene["objects"]), "compiler_report": scene.get("compiler_report", {})}


def _run_powerpoint_constructor(
    *, scene_paths: list[Path], output: Path, arguments: dict[str, Any]
) -> tuple[str, int]:
    from slidecraft.configuration import constructor_node_modules

    command = [sys.executable, "-m", "slidecraft.cli", "render-scenes"]
    for path in scene_paths:
        command.extend(["--scene", str(path)])
    command.extend([
        "--output", str(output),
        "--title", arguments.get("title", "Slidecraft presentation"),
        "--company", arguments.get("company", ""),
        "--language", arguments.get("language", "en-US"),
        "--display-font", arguments.get("display_font", "Georgia"),
        "--body-font", arguments.get("body_font", "Arial"),
        "--backend", arguments.get("backend", "auto"),
    ])
    node_modules = Path(arguments["node_modules"]).expanduser().resolve() if arguments.get("node_modules") else constructor_node_modules()
    if node_modules.exists():
        command.extend(["--node-modules", str(node_modules)])
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "PowerPoint construction failed")
    with zipfile.ZipFile(output) as archive:
        damaged = archive.testzip()
        names = set(archive.namelist())
        if damaged:
            raise RuntimeError(f"PowerPoint package contains a damaged entry: {damaged}")
        required = {"[Content_Types].xml", "ppt/presentation.xml"}
        missing_package_parts = sorted(required - names)
        slides = sorted(name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        if missing_package_parts or not slides:
            raise RuntimeError(f"PowerPoint package validation failed. Missing parts: {missing_package_parts}")
    return process.stdout.strip(), len(slides)


def render_slide_pptx(**arguments: Any) -> dict[str, Any]:
    """Render the active constructor scene for one slide as an editable intermediate file."""
    workspace = _workspace(arguments["workspace"])
    slide_id = arguments["slide_id"]
    key = f"slides/{slide_id}/constructor_scene"
    active = {item["logical_key"]: item for item in workspace.inspect()["active_artifacts"]}
    if key not in active:
        raise KeyError(f"Active constructor scene is missing for {slide_id}")
    if not active[key]["freshness"]["fresh"]:
        raise ValueError(f"Refusing to render a stale constructor scene for {slide_id}")
    output = Path(arguments["output"]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    constructor_output, slide_count = _run_powerpoint_constructor(
        scene_paths=[Path(active[key]["path"])], output=output, arguments=arguments
    )
    if slide_count != 1:
        raise RuntimeError(f"Single-slide construction produced {slide_count} slides")
    validation = {"status": "passed", "package_integrity": "passed", "slide_count": 1}
    record = workspace.register(
        logical_key=f"slides/{slide_id}/editable_pptx",
        kind="editable_slide_powerpoint",
        path=output,
        dependencies=[key],
        producer="render_slide_pptx",
        slide_id=slide_id,
        validation=validation,
    )
    return {"artifact": record, "constructor_output": constructor_output, "validation": validation}


def render_current_pptx(**arguments: Any) -> dict[str, Any]:
    """Refresh the editable deck snapshot from every fresh completed slide."""
    from slidecraft.deck.coherence import validate_constructor_deck

    workspace = _workspace(arguments["workspace"])
    inspection = workspace.inspect(include_history=True)
    active = {item["logical_key"]: item for item in inspection["active_artifacts"]}
    planned_slides: list[dict[str, Any]] = []
    if "deck/plan" in active:
        planned_slides = json.loads(Path(active["deck/plan"]["path"]).read_text(encoding="utf-8"))["slides"]
    ordered_plan = sorted(planned_slides, key=lambda item: item["ordinal"])
    completed_plan = []
    scene_keys = []
    for item in ordered_plan:
        key = f"slides/{item['slide_id']}/constructor_scene"
        if key in active and active[key]["freshness"]["fresh"]:
            completed_plan.append(item)
            scene_keys.append(key)
    if not scene_keys:
        raise ValueError("No fresh reconstructed slides are available for the current deck")

    scenes = [json.loads(Path(active[key]["path"]).read_text(encoding="utf-8")) for key in scene_keys]
    design = json.loads(Path(active["deck/design"]["path"]).read_text(encoding="utf-8")) if "deck/design" in active else {}
    coherence = validate_constructor_deck(
        scenes=scenes,
        planned_slides=completed_plan,
        deck_design=design,
    )
    display_output = Path(arguments["output"]).expanduser().resolve()
    display_output.parent.mkdir(parents=True, exist_ok=True)
    revision_output = (
        workspace.root
        / ".slidecraft"
        / "deck"
        / "current_revisions"
        / f"current_deck_{uuid.uuid4().hex[:12]}.pptx"
    )
    revision_output.parent.mkdir(parents=True, exist_ok=True)
    constructor_output, slide_count = _run_powerpoint_constructor(
        scene_paths=[Path(active[key]["path"]) for key in scene_keys],
        output=revision_output,
        arguments=arguments,
    )
    temporary_display = display_output.with_suffix(display_output.suffix + ".tmp")
    shutil.copy2(revision_output, temporary_display)
    temporary_display.replace(display_output)
    validation = {
        "status": "passed" if coherence["passed"] else "needs_review",
        "package_integrity": "passed",
        "slide_count": slide_count,
        "completed_slide_ids": [item["slide_id"] for item in completed_plan],
        "planned_slide_count": len(ordered_plan),
        "deck_complete": len(completed_plan) == len(ordered_plan),
        "cross_slide_coherence": coherence,
    }
    record = workspace.register(
        logical_key="deck/current_pptx",
        kind="editable_deck_progress",
        path=revision_output,
        dependencies=scene_keys,
        producer="render_current_pptx",
        provenance={"display_path": str(display_output), "backend": arguments.get("backend", "auto")},
        validation=validation,
    )
    return {
        "artifact": record,
        "display_path": str(display_output),
        "constructor_output": constructor_output,
        "validation": validation,
    }


def render_pptx(**arguments: Any) -> dict[str, Any]:
    from slidecraft.deck.coherence import validate_constructor_deck

    workspace = _workspace(arguments["workspace"])
    inspection = workspace.inspect(include_history=True)
    active = {item["logical_key"]: item for item in inspection["active_artifacts"]}
    planned_slides: list[dict[str, Any]] = []
    if "deck/plan" in active:
        planned_slides = json.loads(Path(active["deck/plan"]["path"]).read_text(encoding="utf-8"))["slides"]
    expected_keys = [f"slides/{item['slide_id']}/constructor_scene" for item in sorted(planned_slides, key=lambda item: item["ordinal"])]
    scene_keys = list(arguments.get("scene_keys") or expected_keys)
    if expected_keys and scene_keys != expected_keys:
        raise ValueError("PowerPoint assembly must include every planned slide in deck-plan order")
    missing = [key for key in scene_keys if key not in active]
    if missing:
        raise KeyError(f"Active constructor scenes are missing: {', '.join(missing)}")
    stale = [key for key in scene_keys if not active[key]["freshness"]["fresh"]]
    if stale:
        raise ValueError(f"Refusing to render stale constructor scenes: {', '.join(stale)}")
    scenes = [json.loads(Path(active[key]["path"]).read_text(encoding="utf-8")) for key in scene_keys]
    design = json.loads(Path(active["deck/design"]["path"]).read_text(encoding="utf-8")) if "deck/design" in active else {}
    coherence = validate_constructor_deck(scenes=scenes, planned_slides=planned_slides, deck_design=design)
    if not coherence["passed"]:
        raise ValueError(f"Deck coherence validation failed: {coherence['issues']}")
    output = Path(arguments["output"]).expanduser().resolve()
    constructor_output, slide_count = _run_powerpoint_constructor(
        scene_paths=[Path(active[key]["path"]) for key in scene_keys], output=output, arguments=arguments
    )
    validation = {
        "status": "passed",
        "package_integrity": "passed",
        "slide_count": slide_count,
        "constructor_conformance": "passed",
        "native_powerpoint_render": "optional_not_run",
        "cross_slide_coherence": coherence,
    }
    record = workspace.register(
        logical_key="deck/editable_pptx",
        kind="editable_powerpoint",
        path=output,
        dependencies=scene_keys,
        producer="render_pptx",
        provenance={"backend": arguments.get("backend", "auto")},
        validation=validation,
    )
    return {"artifact": record, "constructor_output": constructor_output, "validation": validation}


_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "create_workspace": create_workspace,
    "create_project": create_project,
    "list_projects": list_projects,
    "resolve_project": resolve_project,
    "project_detail": project_detail,
    "set_deck_brief": set_deck_brief,
    "add_project_asset": add_project_asset,
    "add_project_material": add_project_material,
    "list_project_assets": list_project_assets,
    "update_project_asset": update_project_asset,
    "remove_project_asset": remove_project_asset,
    "add_project_library_resource": add_project_library_resource,
    "remove_project_resource": remove_project_resource,
    "reconcile_project_resources": reconcile_project_resources,
    "list_project_events": list_project_events,
    "acknowledge_project_events": acknowledge_project_events,
    "project_resource_catalog": project_resource_catalog,
    "list_library_resources": list_library_resources,
    "add_library_resource": add_library_resource,
    "update_library_resource": update_library_resource,
    "resolve_image_generation_route": resolve_image_generation_route,
    "generate_slide_image": generate_slide_image,
    "inspect_workspace": inspect_workspace,
    "workflow_status": workflow_status,
    "register_artifact": register_artifact,
    "accept_artifact": accept_artifact,
    "reject_artifact": reject_artifact,
    "prepare_generation": prepare_generation,
    "search_resources": search_resources,
    "prepare_clarifications": prepare_clarifications,
    "record_clarification_answers": record_clarification_answers,
    "plan_deck": plan_deck,
    "prepare_slide": prepare_slide,
    "register_generated_image": register_generated_image,
    "semantic_map": semantic_map,
    "measure_slide": measure_slide,
    "build_reconstruction_contract": build_reconstruction_contract_capability,
    "compile_reconstruction_scene": compile_reconstruction_scene,
    "render_pptx": render_pptx,
}


def call_capability(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in _HANDLERS:
        raise KeyError(f"Unknown capability {name}. Call list_capabilities first.")
    missing = [key for key in CAPABILITIES[name]["required"] if key not in arguments]
    if missing:
        raise ValueError(f"Missing required arguments for {name}: {', '.join(missing)}")
    result = _HANDLERS[name](**arguments)
    return {"status": "ok", "capability": name, "result": result}


def safe_call_capability(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call a capability through a non-throwing Agent transport boundary."""
    try:
        return call_capability(name, arguments)
    except Exception as error:  # noqa: BLE001, transport boundaries return structured failures
        if name not in CAPABILITIES:
            code = "unknown_capability"
            recovery = {"capability": "list_capabilities", "arguments": {}}
        else:
            missing = [key for key in CAPABILITIES[name]["required"] if key not in arguments]
            code = "missing_arguments" if missing else "capability_failed"
            recovery = {
                "capability": "workflow_status" if arguments.get("workspace") else "list_capabilities",
                "arguments": {"workspace": arguments["workspace"]} if arguments.get("workspace") else {},
            }
        return {
            "status": "failed",
            "capability": name,
            "error": {"code": code, "type": type(error).__name__, "message": str(error)},
            "retryable": code != "unknown_capability",
            "recovery": recovery,
            "permission_prompt_triggered": False,
        }


def call_from_json(request: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, (str, Path)):
        value = json.loads(Path(request).expanduser().read_text(encoding="utf-8"))
    else:
        value = request
    return safe_call_capability(value.get("capability", ""), value.get("arguments", {}))
