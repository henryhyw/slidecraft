"""Slidecraft command line interface."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import sysconfig
import tempfile
import traceback
from importlib.resources import files
from pathlib import Path
from typing import Any

from slidecraft.configuration import (
    apply_dotted_overrides,
    constructor_node_modules,
    data_root,
    flatten,
    initialize_user_environment,
    modify_config_value,
    parse_config_value,
    resolve_config,
    user_config_file,
)
from slidecraft.deck.manager import DeckManager
from slidecraft.intake import normalize_deck_intake
from slidecraft.providers.file import FileStructuredVisionProvider
from slidecraft.reconstruction.conformance import ConstructorConformanceError, validate_backend_capabilities
from slidecraft.reconstruction.scene import build_reconstruction_scene
from slidecraft.runtime.doctor import collect_diagnostics
from slidecraft.runtime.powerpoint import (
    CapabilityAuthorizationRequired,
    authorize_powerpoint,
    require_powerpoint_authorization,
)
from slidecraft.semantic_mapping.compiler import compile_semantic_map


def _agent_capabilities(args: argparse.Namespace) -> int:
    from slidecraft.agent import list_capabilities

    print(json.dumps(list_capabilities(), indent=2, ensure_ascii=False))
    return 0


def _agent_call(args: argparse.Namespace) -> int:
    from slidecraft.agent import call_from_json, safe_call_capability

    if args.request:
        result = call_from_json(Path(args.request).resolve())
    else:
        arguments = json.loads(args.arguments or "{}")
        if not isinstance(arguments, dict):
            raise TypeError("--arguments must decode to a JSON object")
        result = safe_call_capability(args.capability, arguments)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


def _workflow_status(args: argparse.Namespace) -> int:
    from slidecraft.agent import safe_call_capability

    result = safe_call_capability(
        "workflow_status",
        {"workspace": str(Path(args.workspace).expanduser().resolve()), "include_history": args.include_history},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


def _project(args: argparse.Namespace) -> int:
    from slidecraft.projects import list_projects, project_detail, resolve_project

    if args.project_command == "list":
        result: Any = {"projects": list_projects()}
    else:
        resolved = resolve_project(
            args.identifier,
            create_if_missing=bool(args.project_command == "create"),
            location=getattr(args, "location", None),
            description=getattr(args, "description", ""),
        )
        result = resolved
        if args.project_command == "show":
            result = {
                "resolution": resolved,
                "detail": project_detail(resolved["location"], include_internal=bool(args.include_internal)),
            }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _console(args: argparse.Namespace) -> int:
    from slidecraft.console import serve

    serve(host=args.host, port=args.port, open_browser=not args.no_open)
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_map(args: argparse.Namespace) -> int:
    provider = FileStructuredVisionProvider(Path(args.result))
    compiled = compile_semantic_map(
        provider=provider,
        image_path=Path(args.image),
        upstream_handoff=_read_json(Path(args.handoff)),
        segmentation_mode=args.segmentation,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(compiled, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "semantic_map": str(output), "entities": len(compiled["entities"]), "groups": len(compiled["groups"])}, indent=2))
    return 0


def _doctor(args: argparse.Namespace) -> int:
    checkpoint = Path(args.checkpoint) if args.checkpoint else None
    result = collect_diagnostics(checkpoint)
    print(json.dumps(result, indent=2))
    return 0 if result["ready_for_host_mode"] else 2


def _init(args: argparse.Namespace) -> int:
    result = initialize_user_environment(force=args.force, install_constructor=True)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 2


def _config(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve() if args.project else None
    if args.config_command == "path":
        print(json.dumps({"user_config": str(user_config_file()), "data_root": str(data_root())}, indent=2))
        return 0
    if args.config_command in {"set", "unset"}:
        if not args.key:
            raise ValueError("A dotted configuration key is required")
        if args.config_command == "set" and args.value is None:
            raise ValueError("A configuration value is required for set")
        path = modify_config_value(
            args.key,
            parse_config_value(args.value) if args.config_command == "set" else None,
            scope=args.scope,
            project_config=project,
            unset=args.config_command == "unset",
        )
        print(json.dumps({"status": "ok", "operation": args.config_command, "key": args.key, "scope": args.scope, "path": str(path)}, indent=2))
        return 0
    config, provenance = resolve_config(project)
    if args.config_command == "validate":
        print(json.dumps({"status": "ok", "schema_version": config["schema_version"], "project_config": str(project) if project else None}, indent=2))
        return 0
    if args.config_command == "explain":
        values = flatten(config)
        print(json.dumps({key: {"value": values[key], "source": provenance.get(key, "default")} for key in sorted(values)}, indent=2))
        return 0
    print(json.dumps(config, indent=2))
    return 0


def _prepare_generation(args: argparse.Namespace) -> int:
    from slidecraft.orchestration import run_pipeline

    result = run_pipeline(
        Path(args.design),
        Path(args.slide),
        Path(args.output_dir),
        overrides=args.set,
        resource_candidates=_read_json(Path(args.resource_candidates)),
        resource_selection=_read_json(Path(args.resource_selection)),
    )
    print(json.dumps({"status": "ok", **result}, indent=2))
    return 0


def _check_install(args: argparse.Namespace) -> int:
    config, _ = resolve_config(Path(args.project).resolve() if args.project else None)
    diagnostics = collect_diagnostics(Path(args.checkpoint).resolve() if args.checkpoint else None)
    required_resources = {
        "semantic_scene_schema": Path(__file__).resolve().parent / "schemas" / "semantic_scene_draft.schema.json",
        "connector_audit_schema": Path(__file__).resolve().parent / "schemas" / "connector_audit.schema.json",
    }
    resource_checks = {name: path.exists() for name, path in required_resources.items()}
    constructor = {"node": bool(diagnostics["construction"]["node"]), "pptxgenjs": False}
    if constructor["node"]:
        probe_env = dict(os.environ)
        managed_modules = constructor_node_modules()
        if managed_modules.exists():
            probe_env["NODE_PATH"] = str(managed_modules)
        probe = subprocess.run(
            [diagnostics["construction"]["node"], "--input-type=module", "-e", "import {createRequire} from 'node:module'; createRequire(import.meta.url)('pptxgenjs')"],
            env=probe_env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        constructor["pptxgenjs"] = probe.returncode == 0
    certified_backend = constructor["pptxgenjs"]
    requested_backend = config["reconstruction"]["backend"]
    constructor_ready = certified_backend
    checks = {
        "core_runtime": bool(diagnostics["ready_for_host_mode"]),
        "package_resources": all(resource_checks.values()),
        "configuration": True,
        "constructor_for_publish": constructor_ready,
    }
    report = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "resources": resource_checks,
        "constructor": {**constructor, "requested_backend": requested_backend},
        "diagnostics": diagnostics,
        "publish_policy": "No PPTX is accepted when a required capability or conformance gate fails.",
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 2


def _authorize_powerpoint(args: argparse.Namespace) -> int:
    result = authorize_powerpoint(timeout_seconds=args.timeout)
    print(json.dumps(result, indent=2))
    return 0 if result["authorized"] else 2


def _render_powerpoint(args: argparse.Namespace) -> int:
    require_powerpoint_authorization()
    repository_script = Path(__file__).resolve().parents[2] / "scripts" / "render_with_powerpoint_mac.py"
    if not repository_script.exists():
        repository_script = Path(sysconfig.get_path("data")) / "share" / "slidecraft" / "scripts" / "render_with_powerpoint_mac.py"
    if not repository_script.exists():
        raise FileNotFoundError("PowerPoint rendering is not ready. Run `slidecraft check-install` for setup guidance.")
    command = [sys.executable, str(repository_script), args.pptx, args.output_dir, "--dpi", str(args.dpi)]
    subprocess.run(command, check=True, timeout=args.timeout)
    return 0


def _plan_deck(args: argparse.Namespace) -> int:
    request_path = Path(args.request).resolve()
    request = _read_json(request_path)
    if args.slide_count is not None:
        if args.slide_count < 1:
            raise ValueError("--slide-count must be at least 1")
        request["preferred_slide_count"] = {
            "minimum": args.slide_count,
            "target": args.slide_count,
            "maximum": args.slide_count,
        }
    request = apply_dotted_overrides(request, args.set)
    intake = normalize_deck_intake(request, request_path.parent)
    design = _read_json(Path(args.design).resolve())
    from slidecraft.providers.file import FileStructuredReasoningProvider

    provider = FileStructuredReasoningProvider(Path(args.result))
    manifest = DeckManager(Path(args.run_dir), provider).initialize(
        request=request,
        intake=intake,
        design_system=design,
        system_layouts_path=Path(args.system_layouts).resolve() if args.system_layouts else None,
    )
    print(json.dumps(manifest, indent=2))
    return 0


def _compile_scene(args: argparse.Namespace) -> int:
    evidence_path = args.scene_evidence
    if not evidence_path:
        raise ValueError("--scene-evidence is required")
    scene = build_reconstruction_scene(
        measured_scene=_read_json(Path(evidence_path).resolve()),
        contract=_read_json(Path(args.contract).resolve()),
        design=_read_json(Path(args.design).resolve()),
        slide_id=args.slide_id,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "scene": str(output), "objects": len(scene["objects"]), "report": scene["compiler_report"]}, indent=2))
    return 0


def _constructor_script() -> Path:
    filename = "scene_to_pptx.mjs"
    repository_candidate = Path(__file__).resolve().parents[2] / "js" / filename
    if repository_candidate.exists():
        return repository_candidate
    installed = Path(sysconfig.get_path("data")) / "share" / "slidecraft" / "js" / filename
    if installed.exists():
        return installed
    raise FileNotFoundError("The PowerPoint constructor is not ready. Run `slidecraft init`, then try again.")


def _render_scenes(args: argparse.Namespace) -> int:
    scenes = [_read_json(Path(value).resolve()) for value in args.scene]
    for scene in scenes:
        validate_backend_capabilities(scene, {"textbox", "shape", "image", "connector_graph", "table", "chart", "freeform"})
    spec = {
        "title": args.title,
        "company": args.company,
        "language": args.language,
        "theme": {"display_font": args.display_font, "body_font": args.body_font},
        "slides": scenes,
    }
    with tempfile.TemporaryDirectory() as directory:
        spec_path = Path(directory) / "deck_scenes.json"
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        env = dict(os.environ)
        node_modules = Path(args.node_modules).resolve() if args.node_modules else constructor_node_modules()
        if node_modules.exists():
            env["NODE_PATH"] = str(node_modules)
        backend = "pptxgenjs"
        if args.backend == "auto":
            portable_script = _constructor_script()
            pptxgen_probe = subprocess.run(
                [args.node, "--input-type=module", "-e", "import {createRequire} from 'node:module'; createRequire(import.meta.url)('pptxgenjs')"],
                cwd=portable_script.parent,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if pptxgen_probe.returncode != 0:
                raise ConstructorConformanceError(
                    "The PowerPoint constructor is not ready. Run `slidecraft init`, then try again."
                )
        subprocess.run([args.node, str(_constructor_script()), "--input", str(spec_path), "--output", str(Path(args.output).resolve())], check=True, env=env)
    print(json.dumps({"status": "ok", "pptx": str(Path(args.output).resolve()), "slide_count": len(scenes), "backend": backend}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slidecraft", description="Create editable PowerPoint presentations with your agent app")
    parser.add_argument("--version", action="version", version="slidecraft 0.1.0a1")
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser("init", help="Create the user configuration and local library directories")
    initialize.add_argument("--force", action="store_true")
    initialize.set_defaults(handler=_init)

    config = commands.add_parser("config", help="View or change Slidecraft settings")
    config.add_argument("config_command", choices=["path", "show", "validate", "explain", "set", "unset"])
    config.add_argument("key", nargs="?")
    config.add_argument("value", nargs="?")
    config.add_argument("--scope", choices=["user", "project"], default="user")
    config.add_argument("--project", help="Optional project TOML or JSON overlay")
    config.set_defaults(handler=_config)

    check = commands.add_parser("check-install", help="Check that Slidecraft is ready to build presentations")
    check.add_argument("--project")
    check.add_argument("--checkpoint")
    check.set_defaults(handler=_check_install)

    doctor = commands.add_parser("doctor", help="Inspect local capabilities")
    doctor.add_argument("--checkpoint")
    doctor.set_defaults(handler=_doctor)

    agent_capabilities = commands.add_parser("agent-capabilities", help="List the presentation tools available to an agent app")
    agent_capabilities.set_defaults(handler=_agent_capabilities)

    agent_call = commands.add_parser("agent-call", help="Execute one JSON capability request from an agent host")
    agent_call_source = agent_call.add_mutually_exclusive_group(required=True)
    agent_call_source.add_argument("--request", help="JSON file containing capability and arguments")
    agent_call_source.add_argument("--capability", help="Capability name for a direct shell call")
    agent_call.add_argument("--arguments", help="JSON object used with --capability", default="{}")
    agent_call.set_defaults(handler=_agent_call)

    workflow = commands.add_parser("workflow-status", help="Show durable project facts for Agent interpretation")
    workflow.add_argument("--workspace", required=True)
    workflow.add_argument("--include-history", action="store_true")
    workflow.set_defaults(handler=_workflow_status)

    project = commands.add_parser("project", help="Find, create, or inspect a Slidecraft project")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_list = project_commands.add_parser("list", help="List registered projects")
    project_list.set_defaults(handler=_project)
    project_resolve = project_commands.add_parser("resolve", help="Resolve a project name, ID, or folder")
    project_resolve.add_argument("identifier")
    project_resolve.set_defaults(handler=_project)
    project_create = project_commands.add_parser("create", help="Create a project with the supplied human name")
    project_create.add_argument("identifier")
    project_create.add_argument("--location")
    project_create.add_argument("--description", default="")
    project_create.set_defaults(handler=_project)
    project_show = project_commands.add_parser("show", help="Show progress and user-facing artifacts for a project")
    project_show.add_argument("identifier")
    project_show.add_argument("--include-internal", action="store_true")
    project_show.set_defaults(handler=_project)

    console = commands.add_parser("console", help="Run the local project and configuration console")
    console.add_argument("--host", default="127.0.0.1")
    console.add_argument("--port", type=int, default=8765)
    console.add_argument("--no-open", action="store_true")
    console.set_defaults(handler=_console)

    authorize = commands.add_parser("authorize-powerpoint", help="Enable PowerPoint for Mac render checks")
    authorize.add_argument("--timeout", type=int, default=20)
    authorize.set_defaults(handler=_authorize_powerpoint)

    native_render = commands.add_parser("render-powerpoint", help="Render a presentation with PowerPoint for Mac")
    native_render.add_argument("--pptx", required=True)
    native_render.add_argument("--output-dir", required=True)
    native_render.add_argument("--dpi", type=int, default=144)
    native_render.add_argument("--timeout", type=int, default=120)
    native_render.set_defaults(handler=_render_powerpoint)

    semantic = commands.add_parser("semantic-map", help="Identify meaningful slide entities and relationships")
    semantic.add_argument("--image", required=True)
    semantic.add_argument("--handoff", required=True)
    semantic.add_argument("--output", required=True)
    semantic.add_argument("--result", required=True, help="Strict JSON result authored by the host Agent")
    semantic.add_argument("--segmentation", choices=["auto", "off"], default="auto")
    semantic.set_defaults(handler=_semantic_map)

    plan = commands.add_parser("plan-deck", help="Create the deck plan and typed per-slide jobs")
    plan.add_argument("--request", required=True)
    plan.add_argument("--design", required=True)
    plan.add_argument("--run-dir", required=True)
    plan.add_argument(
        "--system-layouts",
        default=str(files("slidecraft.defaults").joinpath("system_slide_layouts.json")),
    )
    plan.add_argument("--result", required=True, help="Strict deck-plan JSON authored by the host Agent")
    plan.add_argument("--slide-count", type=int, help="Exact total deck length for this run")
    plan.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Repeatable deck-request override for this run")
    plan.set_defaults(handler=_plan_deck)

    generation = commands.add_parser("prepare-generation", help="Assemble generation from Agent-authored semantics and resource choices")
    generation.add_argument("--design", required=True)
    generation.add_argument("--slide", required=True)
    generation.add_argument("--output-dir", required=True)
    generation.add_argument("--resource-candidates", required=True, help="Candidate set recorded by search-resources")
    generation.add_argument("--resource-selection", required=True, help="Agent-authored resource selection JSON")
    generation.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Repeatable deck-design override for this run")
    generation.set_defaults(handler=_prepare_generation)

    scene = commands.add_parser("compile-scene", help="Compile measured evidence and the reconstruction contract into a constructor scene")
    scene.add_argument("--scene-evidence", required=True, help="Measured and semantically mapped slide scene")
    scene.add_argument("--contract", required=True)
    scene.add_argument("--design", required=True)
    scene.add_argument("--slide-id", required=True)
    scene.add_argument("--output", required=True)
    scene.set_defaults(handler=_compile_scene)

    render = commands.add_parser("render-scenes", help="Render one or more constructor scenes into an editable PPTX")
    render.add_argument("--scene", action="append", required=True)
    render.add_argument("--output", required=True)
    render.add_argument("--title", default="Slidecraft presentation")
    render.add_argument("--company", default="")
    render.add_argument("--language", default="en-US")
    render.add_argument("--display-font", default="Georgia")
    render.add_argument("--body-font", default="Arial")
    render.add_argument("--node", default="node")
    render.add_argument("--node-modules")
    render.add_argument("--backend", choices=["auto", "pptxgenjs"], default="auto", help="Auto selects the certified portable PptxGenJS backend.")
    render.set_defaults(handler=_render_scenes)
    return parser


def main() -> int:
    parser = build_parser()
    parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        return int(args.handler(args))
    except (CapabilityAuthorizationRequired, ConstructorConformanceError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error), "permission_prompt_triggered": False}, indent=2), file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001, the CLI boundary must always return structured failure JSON
        if args.debug:
            traceback.print_exc()
        print(json.dumps({
            "status": "failed",
            "error_type": type(error).__name__,
            "reason": str(error),
            "permission_prompt_triggered": False,
            "action": "Run slidecraft doctor and slidecraft config validate. Re-run with --debug only during development.",
        }, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
