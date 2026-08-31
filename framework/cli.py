from __future__ import annotations

import argparse
import json
import subprocess
import sys

from .installer import detect_host, setup
from .paths import data_home
from .profiles import active_profile_id, list_profiles, profile_record, set_active_profile
from . import sessions, run_versions
from . import profile_authoring
from . import library_sets, components, capabilities
from .panel import open_panel
from .storage import read, revision, write
from pathlib import Path


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def command_setup(args: argparse.Namespace) -> None:
    emit(setup(force_profiles=args.force_profiles, install_skill=not args.skip_skill,
               install_node=not args.skip_node, install_sam=not args.skip_sam))


def command_doctor(_args: argparse.Namespace) -> None:
    host = detect_host()
    host["framework_home"] = str(data_home())
    host["active_profile"] = active_profile_id()
    host["profiles"] = len(list_profiles())
    emit(host)


def command_profile(args: argparse.Namespace) -> None:
    if args.profile_command == "list":
        active = active_profile_id()
        emit([{**item, "active": item["id"] == active} for item in list_profiles()])
    elif args.profile_command == "show":
        emit(profile_authoring.profile_payload(args.profile_id or active_profile_id()))
    elif args.profile_command == "select":
        emit(set_active_profile(args.profile_id))
    elif args.profile_command == "create":
        emit(profile_authoring.create_profile(args.name, profile_id=args.profile_id, based_on=args.based_on, purpose=args.purpose))
    elif args.profile_command == "update":
        emit(profile_authoring.update_profile(args.profile_id, json.loads(args.json), args.expected))
    elif args.profile_command == "add-resource":
        emit(profile_authoring.add_resource(args.profile_id, args.kind, Path(args.file), name=args.name,
                                            description=args.description, tags=[tag.strip() for tag in args.tags.split(",") if tag.strip()],
                                            source_url=args.source_url, license_name=args.license))


def command_console(args: argparse.Namespace) -> None:
    command = [sys.executable, "-m", "webapp.server", "--host", args.host, "--port", str(args.port)]
    command.extend(["--view", args.view])
    if args.no_browser:
        command.append("--no-open")
    process = subprocess.Popen(command, cwd=data_home())
    try:
        code = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        code = process.wait()
    raise SystemExit(code)


def command_library(args: argparse.Namespace) -> None:
    if args.library_command == "list":
        emit(library_sets.payload())
    elif args.library_command == "create":
        emit(library_sets.create_set(args.name, args.kind, args.description))
    elif args.library_command == "add-resource":
        emit(library_sets.add_resource(args.set_id, Path(args.file), name=args.name, description=args.description,
                                       tags=[tag.strip() for tag in args.tags.split(",") if tag.strip()],
                                       source_url=args.source_url, license_name=args.license))
    elif args.library_command == "inspect":
        emit(components.inspect(args.set_id, args.component_id))
    elif args.library_command == "edit-object":
        emit(components.save_object(args.set_id, args.component_id, args.object_id, json.loads(args.json), args.expected, args.slide))
    elif args.library_command == "edit-component":
        emit(components.update_definition(args.set_id, args.component_id, json.loads(args.json), args.expected))


def command_run(args):
    from . import run_events, run_activity, run_versions
    action = args.run_command
    if action == "list":
        emit(sessions.list_runs())
        return
    if action == "events":
        emit(run_events.pending(args.path))
        return
    if action == "ack-events":
        emit(run_events.acknowledge(args.path, args.ids, args.expected))
        return
    if action == "activity":
        if args.step:
            emit(run_activity.record(args.path, args.step, args.status, args.message or ""))
        else:
            emit(run_activity.snapshot(args.path))
        return
    if action == "sync":
        root = sessions.require_run(args.path)
        emit({"events": run_events.pending(root), "activity": run_activity.snapshot(root),
              "overrides": read(root / "session-overrides.json", {}),
              "session": read(root / "session.json", {}),
              "stage_selection": run_versions.selections(root),
              "selection_revision": revision(root / "work/stage-selections.json"),
              "overrides_revision": revision(root / "session-overrides.json"),
              "defaults_revision": revision(root / "work/session-defaults.json")})
        return
    if action == "archive":
        emit(run_versions.archive(args.path))
        return
    if action == "publish":
        emit(run_versions.publish(args.path, args.stage, args.expected))
        return
    if action == "create":
        root = sessions.create(args.name, args.location, args.profile)
    elif action == "attach":
        root = Path(sessions.register(args.path))
    else:
        root = sessions.require_run(args.path)
    if action == "set":
        sessions.save_overrides(root, json.loads(args.json), args.expected)
    elif action == "update":
        sessions.patchmetadata(root, json.loads(args.json), args.expected)
    elif action == "refresh-defaults":
        sessions.adopt_defaults(root, args.expected)
    elif action == "resolve":
        cfg = sessions.resolve(root)
        output = Path(args.output) if args.output else root / "work/resolved-config.json"
        write(output, cfg)
        emit({"output": str(output.resolve())})
        return
    emit({"path": str(root), "session": read(root / "session.json", {}),
          "overrides": read(root / "session-overrides.json", {}),
          "metadata_revision": revision(root / "session.json"),
          "overrides_revision": revision(root / "session-overrides.json"),
          "defaults_revision": revision(root / "work/session-defaults.json")})


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="slidepoise", description="Install and operate the SlidePoise presentation framework.")
    root.add_argument("--version", action="version", version="slidepoise 0.5.0")
    commands = root.add_subparsers(dest="command", required=True)

    setup_cmd = commands.add_parser("setup", help="Install profiles, dependencies, and the Codex skill.")
    setup_cmd.add_argument("--force-profiles", action="store_true")
    setup_cmd.add_argument("--skip-skill", action="store_true")
    setup_cmd.add_argument("--skip-node", action="store_true")
    setup_cmd.add_argument("--skip-sam", action="store_true", help="Skip the best-effort SAM installation.")
    setup_cmd.set_defaults(func=command_setup)

    doctor = commands.add_parser("doctor", help="Inspect framework dependencies and active configuration.")
    doctor.set_defaults(func=command_doctor)

    sam = commands.add_parser("sam", help="Install SAM or inspect installation progress.")
    sam.add_argument("action", choices=["install", "status"])
    sam.set_defaults(func=lambda args: emit(capabilities.install_and_wait() if args.action == "install" else capabilities.status()))

    panel = commands.add_parser("panel", help="Start a session-bound companion panel and return its URL.")
    panel.add_argument("--run", help="Presentation folder to bind after agreeing in conversation.")
    panel.add_argument("--id", help="Reuse this conversation's panel and preserve its selection unless --run is supplied.")
    panel.add_argument("--port", type=int, default=18765)
    panel.add_argument("--view", choices=["session", *run_versions.STAGES], default="session",
                       help="Open the current presentation at a specific review stage.")
    panel.set_defaults(func=lambda args: emit(open_panel(args.run, args.port, args.view, args.id)))

    profile = commands.add_parser("profile", help="List, inspect, or select isolated guidance profiles.")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_list = profile_commands.add_parser("list")
    profile_list.set_defaults(func=command_profile)
    profile_show = profile_commands.add_parser("show")
    profile_show.add_argument("profile_id", nargs="?")
    profile_show.set_defaults(func=command_profile)
    profile_select = profile_commands.add_parser("select")
    profile_select.add_argument("profile_id")
    profile_select.set_defaults(func=command_profile)
    profile_create = profile_commands.add_parser("create", help="Create a user-owned profile from an installed starting point.")
    profile_create.add_argument("name")
    profile_create.add_argument("--id", dest="profile_id")
    profile_create.add_argument("--based-on", help="Starting profile. The active profile is used when omitted.")
    profile_create.add_argument("--purpose", default="")
    profile_create.set_defaults(func=command_profile)
    profile_update = profile_commands.add_parser("update")
    profile_update.add_argument("profile_id")
    profile_update.add_argument("--json", required=True)
    profile_update.add_argument("--expected", required=True)
    profile_update.set_defaults(func=command_profile)
    profile_resource = profile_commands.add_parser("add-resource", help="Add a persistent visual reference to a profile.")
    profile_resource.add_argument("profile_id")
    profile_resource.add_argument("kind", choices=profile_authoring.KINDS)
    profile_resource.add_argument("file")
    profile_resource.add_argument("--name", required=True)
    profile_resource.add_argument("--description", default="")
    profile_resource.add_argument("--tags", default="")
    profile_resource.add_argument("--source-url", default="")
    profile_resource.add_argument("--license", default="")
    profile_resource.set_defaults(func=command_profile)

    library = commands.add_parser("library", help="Manage coherent icon and component sets shared by profiles.")
    library_commands = library.add_subparsers(dest="library_command", required=True)
    library_list = library_commands.add_parser("list")
    library_list.set_defaults(func=command_library)
    library_create = library_commands.add_parser("create")
    library_create.add_argument("kind", choices=sorted(library_sets.SET_KINDS))
    library_create.add_argument("name")
    library_create.add_argument("--description", default="")
    library_create.set_defaults(func=command_library)
    library_resource = library_commands.add_parser("add-resource")
    library_resource.add_argument("set_id")
    library_resource.add_argument("file")
    library_resource.add_argument("--name", required=True)
    library_resource.add_argument("--description", default="")
    library_resource.add_argument("--tags", default="")
    library_resource.add_argument("--source-url", default="")
    library_resource.add_argument("--license", default="")
    library_resource.set_defaults(func=command_library)
    for name in ("inspect", "edit-object", "edit-component"):
        command = library_commands.add_parser(name)
        command.add_argument("set_id")
        command.add_argument("component_id")
        if name != "inspect":
            command.add_argument("--json", required=True)
            command.add_argument("--expected", required=True)
        if name == "edit-object":
            command.add_argument("object_id")
            command.add_argument("--slide", type=int)
        command.set_defaults(func=command_library)

    console = commands.add_parser("console", help="Open the optional local management console.")
    console.add_argument("--host", default="127.0.0.1")
    console.add_argument("--port", type=int, default=8765)
    console.add_argument("--no-browser", action="store_true")
    console.add_argument("--view", choices=["overview", "runs", "style", "resources", "system"], default="overview")
    console.set_defaults(func=command_console)
    run = commands.add_parser("run", help="Manage the same local sessions used by Console.")
    actions = run.add_subparsers(dest="run_command", required=True)
    create = actions.add_parser("create")
    create.add_argument("name")
    create.add_argument("--location")
    create.add_argument("--profile")
    create.set_defaults(func=command_run)
    listing = actions.add_parser("list")
    listing.set_defaults(func=command_run)
    events = actions.add_parser("events", help="Read pending changes applied in the session panel.")
    events.add_argument("path")
    events.set_defaults(func=command_run)
    acknowledge = actions.add_parser("ack-events", help="Acknowledge panel changes after adopting them.")
    acknowledge.add_argument("path")
    acknowledge.add_argument("--ids", nargs="+", required=True)
    acknowledge.add_argument("--expected", required=True)
    acknowledge.set_defaults(func=command_run)
    activity = actions.add_parser("activity", help="Read or publish the Agent's current workflow activity.")
    activity.add_argument("path")
    activity.add_argument("--step", choices=sorted(__import__("framework.run_activity", fromlist=["STEPS"]).STEPS))
    activity.add_argument("--status", choices=["running", "waiting_for_user", "complete", "paused", "failed"], default="running")
    activity.add_argument("--message", default="")
    activity.set_defaults(func=command_run)
    sync = actions.add_parser("sync", help="Read Panel changes and current workflow activity together.")
    sync.add_argument("path")
    sync.set_defaults(func=command_run)
    archive = actions.add_parser("archive", help="Preserve current artifacts before revising a presentation.")
    archive.add_argument("path")
    archive.set_defaults(func=command_run)
    publish = actions.add_parser("publish", help="Display a newly written stage without changing approvals.")
    publish.add_argument("path")
    publish.add_argument("--stage", choices=("plan", "style", "design", "powerpoint"), required=True)
    publish.add_argument("--expected", required=True, help="selection_revision from run sync")
    publish.set_defaults(func=command_run)
    for action in ("show", "attach", "set", "update", "resolve", "refresh-defaults"):
        item = actions.add_parser(action)
        item.add_argument("path")
        if action in {"set", "update"}:
            item.add_argument("--json", required=True)
        if action in {"set", "update", "refresh-defaults"}:
            item.add_argument("--expected", required=True, help="Revision returned by run show.")
        if action == "resolve":
            item.add_argument("--output")
        item.set_defaults(func=command_run)
    return root


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
