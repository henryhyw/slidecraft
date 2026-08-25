#!/usr/bin/env python3
"""Guided, dependency-light installer for Slidecraft."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

RELEASE = "v0.1.0-alpha.1"
REPOSITORY = "https://github.com/henryhyw/slidecraft"
DEFAULT_SOURCE = f"{REPOSITORY}/archive/refs/tags/{RELEASE}.zip"
EXTRAS = "cv,documents,agent,openai"


class InstallError(RuntimeError):
    """A friendly installation failure."""


def default_install_root(system: str | None = None, home: Path | None = None) -> Path:
    system = system or platform.system()
    home = home or Path.home()
    if system == "Darwin":
        return home / "Library" / "Application Support" / "Slidecraft" / "app"
    if system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return local / "Slidecraft" / "app"
    data_home = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
    return data_home / "slidecraft" / "app"


def executable(venv: Path, name: str, system: str | None = None) -> Path:
    if (system or platform.system()) == "Windows":
        suffix = ".exe" if name in {"python", "slidecraft", "slidecraft-mcp", "slidecraft-console"} else ""
        return venv / "Scripts" / f"{name}{suffix}"
    return venv / "bin" / name


def package_requirement(source: str) -> str:
    path = Path(source).expanduser()
    if path.exists():
        return f"{path.resolve()}[{EXTRAS}]"
    return f"slidecraft-ai[{EXTRAS}] @ {source}"


def prompt(question: str, default: bool = True) -> bool:
    if not sys.stdin.isatty():
        return default
    marker = "Y/n" if default else "y/N"
    answer = input(f"{question} [{marker}] ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


class Runner:
    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def run(
        self,
        command: Iterable[str | Path],
        *,
        capture: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        argv = [str(item) for item in command]
        if self.dry_run:
            print("    $ " + " ".join(_quote(item) for item in argv))
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.run(
            argv,
            check=check,
            text=True,
            capture_output=capture,
        )


def _quote(value: str) -> str:
    if not value or any(character.isspace() for character in value):
        return json.dumps(value)
    return value


def _version(command: str) -> str | None:
    path = shutil.which(command)
    if not path:
        return None
    result = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    return (result.stdout or result.stderr).strip() or "installed"


def check_prerequisites() -> dict[str, str]:
    if sys.version_info[:2] < (3, 10):  # noqa: UP036 - the bootstrap may be launched by an unsupported Python
        raise InstallError("Slidecraft needs Python 3.10 or newer. Download Python from https://python.org/downloads/ and run this installer again.")
    node = _version("node")
    npm = _version("npm")
    if not node or not npm:
        raise InstallError(
            "Slidecraft needs Node.js for editable PowerPoint construction. Install the current LTS release from https://nodejs.org/ and run this installer again."
        )
    return {"python": platform.python_version(), "node": node, "npm": npm}


def create_launchers(install_root: Path, venv: Path, dry_run: bool = False) -> dict[str, str]:
    target = install_root / "bin"
    commands = ("slidecraft", "slidecraft-mcp", "slidecraft-console")
    launchers: dict[str, str] = {}
    if dry_run:
        for command in commands:
            launchers[command] = str(target / (f"{command}.cmd" if platform.system() == "Windows" else command))
        print(f"    create launchers in {_quote(str(target))}")
        return launchers
    target.mkdir(parents=True, exist_ok=True)
    for command in commands:
        source = executable(venv, command)
        if platform.system() == "Windows":
            launcher = target / f"{command}.cmd"
            launcher.write_text(f'@echo off\r\n"{source}" %*\r\n', encoding="utf-8")
        else:
            launcher = target / command
            launcher.write_text(f'#!/bin/sh\nexec "{source}" "$@"\n', encoding="utf-8")
            launcher.chmod(0o755)
        launchers[command] = str(launcher)
    return launchers


def _configured(command: str, name: str, runner: Runner) -> bool:
    result = runner.run([command, "mcp", "get", name], capture=True, check=False)
    return result.returncode == 0


def connect_cli_agent(
    command: str,
    mcp_path: Path,
    runner: Runner,
    assume_yes: bool,
    refresh: bool,
) -> dict[str, Any]:
    label = "Codex" if command == "codex" else "Claude Code"
    if not shutil.which(command) and not runner.dry_run:
        return {"host": label, "status": "not_detected"}
    exists = _configured(command, "slidecraft", runner)
    if exists and not refresh:
        return {"host": label, "status": "already_connected"}
    action = "Refresh" if exists else "Connect"
    if not assume_yes and not prompt(f"{action} Slidecraft in {label}?"):
        return {"host": label, "status": "skipped"}
    if exists:
        remove = [command, "mcp", "remove", "slidecraft"]
        if command == "claude":
            remove.extend(["--scope", "user"])
        runner.run(remove, capture=True)
    add = [command, "mcp", "add", "slidecraft"]
    if command == "claude":
        add.extend(["--scope", "user"])
    add.extend(["--", mcp_path])
    runner.run(add, capture=True)
    return {"host": label, "status": "connected", "command": str(mcp_path)}


def connect_copilot(workspace: Path | None, mcp_path: Path, dry_run: bool = False) -> dict[str, Any]:
    config_path = (
        workspace.expanduser().resolve() / ".mcp.json"
        if workspace
        else Path.home() / ".copilot" / "mcp-config.json"
    )
    if dry_run:
        print(f"    update {_quote(str(config_path))}")
        return {"host": "GitHub Copilot", "status": "connected", "config": str(config_path)}
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InstallError(f"Cannot update {config_path} because it is not plain JSON. Add Slidecraft to that file manually.") from exc
    else:
        payload = {}
    payload.setdefault("servers", {})["slidecraft"] = {"command": str(mcp_path), "args": []}
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"host": "GitHub Copilot", "status": "connected", "config": str(config_path)}


def choose_agents(requested: list[str], copilot_workspace: Path | None) -> list[str]:
    if "none" in requested:
        return []
    explicit = [item for item in requested if item != "auto"]
    if explicit:
        return list(dict.fromkeys(explicit))
    detected = [name for name in ("codex", "claude") if shutil.which(name)]
    if copilot_workspace:
        detected.append("copilot")
    return detected


def install(args: argparse.Namespace) -> dict[str, Any]:
    print("\nSlidecraft guided installation\n")
    print("1 of 5  Checking this computer")
    prerequisites = check_prerequisites()
    print(f"    Python {prerequisites['python']}")
    print(f"    Node.js {prerequisites['node']}")

    install_root = Path(args.install_dir).expanduser().resolve() if args.install_dir else default_install_root()
    venv = install_root / "runtime"
    runner = Runner(args.dry_run)

    print("2 of 5  Preparing an isolated runtime")
    if not executable(venv, "python").exists() or args.dry_run:
        install_root.mkdir(parents=True, exist_ok=True) if not args.dry_run else None
        runner.run([sys.executable, "-m", "venv", venv])
    python = executable(venv, "python")
    runner.run([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip", "setuptools", "wheel"])

    print("3 of 5  Installing Slidecraft")
    source = args.source or os.environ.get("SLIDECRAFT_INSTALL_SOURCE") or DEFAULT_SOURCE
    runner.run([python, "-m", "pip", "install", "--quiet", "--upgrade", package_requirement(source)])
    cli = executable(venv, "slidecraft")
    mcp = executable(venv, "slidecraft-mcp")
    launchers = create_launchers(install_root, venv, args.dry_run)

    print("4 of 5  Preparing presentation tools")
    runner.run([cli, "init"], capture=True)
    runner.run([cli, "check-install"], capture=True)

    print("5 of 5  Connecting agent apps")
    connections: list[dict[str, Any]] = []
    agents = choose_agents(args.agent, Path(args.copilot_workspace) if args.copilot_workspace else None)
    for agent in agents:
        if agent in {"codex", "claude"}:
            connections.append(connect_cli_agent(agent, mcp, runner, args.yes, args.refresh_agent_connections))
        elif agent == "copilot":
            workspace = Path(args.copilot_workspace) if args.copilot_workspace else None
            connections.append(connect_copilot(workspace, mcp, args.dry_run))
    if not connections:
        print("    No supported agent app was selected. The MCP command is available for manual connection.")
    for connection in connections:
        status = connection["status"].replace("_", " ")
        print(f"    {connection['host']}  {status}")

    receipt = {
        "status": "ready" if not args.dry_run else "dry_run",
        "release": RELEASE,
        "install_root": str(install_root),
        "commands": launchers,
        "mcp_command": str(mcp),
        "connections": connections,
        "source": source,
    }
    if not args.dry_run:
        receipt_path = install_root / "install.json"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipt["receipt"] = str(receipt_path)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install Slidecraft and connect it to your agent app")
    parser.add_argument("--yes", "-y", action="store_true", help="accept recommended agent connections")
    parser.add_argument("--install-dir", help="choose the managed installation folder")
    parser.add_argument("--source", help="install from a local checkout or another package URL")
    parser.add_argument(
        "--agent",
        action="append",
        choices=("auto", "codex", "claude", "copilot", "none"),
        default=[],
        help="choose an agent app, repeat to select more than one",
    )
    parser.add_argument("--copilot-workspace", help="workspace where .mcp.json should be updated")
    parser.add_argument(
        "--refresh-agent-connections",
        action="store_true",
        help="replace an existing Slidecraft agent connection with this managed runtime",
    )
    parser.add_argument("--dry-run", action="store_true", help="show the installation plan without changing files")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.agent:
        args.agent = ["auto"]
    try:
        result = install(args)
    except InstallError as exc:
        print(f"\nInstallation stopped\n\n{exc}\n", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"\nInstallation stopped\n\n{detail}\n", file=sys.stderr)
        return 1
    print("\nSlidecraft is ready.\n")
    print("Open the dashboard")
    print(f"    {result['commands']['slidecraft']} console")
    print("\nConnect another MCP-compatible app with this command")
    print(f"    {result['mcp_command']}")
    print("\nYou can now ask your agent to create or continue a Slidecraft project.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
