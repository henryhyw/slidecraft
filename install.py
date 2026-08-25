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
EXTRAS = "cv,documents,openai"


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
        suffix = ".exe" if name in {"python", "slidecraft", "slidecraft-console"} else ""
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
    commands = ("slidecraft", "slidecraft-console")
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


def install_agent_skill(
    agent: str,
    source: Path,
    *,
    cli_path: Path | None = None,
    dry_run: bool = False,
    home: Path | None = None,
) -> dict[str, Any]:
    """Install the reasoning workflow for hosts with a local skill convention."""
    roots = {
        "codex": ".codex/skills/slidecraft",
        "claude": ".claude/skills/slidecraft",
    }
    if agent not in roots:
        return {"host": agent, "status": "unsupported"}
    target = (home or Path.home()) / roots[agent]
    if dry_run:
        print(f"    install agent skill in {_quote(str(target))}")
        return {"host": agent, "status": "installed", "path": str(target)}
    if not (source / "SKILL.md").is_file():
        raise InstallError(f"The packaged Slidecraft skill is missing from {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    if cli_path is not None:
        references = target / "references"
        references.mkdir(parents=True, exist_ok=True)
        (references / "runtime.md").write_text(
            "# Installed runtime\n\n"
            "Use this local Slidecraft command for every CLI example in the skill.\n\n"
            f"```text\n{cli_path}\n```\n",
            encoding="utf-8",
        )
    return {"host": agent, "status": "installed", "path": str(target)}


def packaged_skill_source(python: Path, runner: Runner, venv: Path) -> Path:
    if runner.dry_run:
        data_root = venv
    else:
        result = runner.run(
            [python, "-c", "import sysconfig; print(sysconfig.get_path('data'))"],
            capture=True,
        )
        data_root = Path(result.stdout.strip()).expanduser().resolve()
    return data_root / "share" / "slidecraft" / "integrations" / "skills" / "slidecraft"


def choose_agents(requested: list[str]) -> list[str]:
    if "none" in requested:
        return []
    explicit = [item for item in requested if item != "auto"]
    if explicit:
        return list(dict.fromkeys(explicit))
    detected = [name for name in ("codex", "claude") if shutil.which(name)]
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
    launchers = create_launchers(install_root, venv, args.dry_run)

    print("4 of 5  Preparing presentation tools")
    runner.run([cli, "init"], capture=True)
    runner.run([cli, "check-install"], capture=True)

    print("5 of 5  Installing agent skills")
    skill_installations: list[dict[str, Any]] = []
    agents = choose_agents(args.agent)
    skill_source = packaged_skill_source(python, runner, venv)
    for agent in agents:
        skill_installations.append(
            install_agent_skill(
                agent,
                skill_source,
                cli_path=Path(launchers["slidecraft"]),
                dry_run=args.dry_run,
            )
        )
    if not skill_installations:
        print("    No supported agent skill was selected. The runtime is ready for manual use.")
    for skill in skill_installations:
        if skill["status"] == "installed":
            print(f"    {skill['host']} reasoning skill  installed")

    receipt = {
        "status": "ready" if not args.dry_run else "dry_run",
        "release": RELEASE,
        "install_root": str(install_root),
        "commands": launchers,
        "skills": skill_installations,
        "source": source,
    }
    if not args.dry_run:
        receipt_path = install_root / "install.json"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipt["receipt"] = str(receipt_path)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install Slidecraft and its local agent skill")
    parser.add_argument("--install-dir", help="choose the managed installation folder")
    parser.add_argument("--source", help="install from a local checkout or another package URL")
    parser.add_argument(
        "--agent",
        action="append",
        choices=("auto", "codex", "claude", "none"),
        default=[],
        help="choose an agent app, repeat to select more than one",
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
    print("\nYou can now ask your agent to create or revise an editable presentation.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
