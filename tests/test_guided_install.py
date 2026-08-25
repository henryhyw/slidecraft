from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("slidecraft_guided_install", ROOT / "install.py")
assert SPEC and SPEC.loader
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


def test_default_install_roots_are_platform_native(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert INSTALLER.default_install_root("Darwin", tmp_path) == tmp_path / "Library" / "Application Support" / "Slidecraft" / "app"
    assert INSTALLER.default_install_root("Linux", tmp_path) == tmp_path / ".local" / "share" / "slidecraft" / "app"
    assert INSTALLER.default_install_root("Windows", tmp_path) == tmp_path / "AppData" / "Local" / "Slidecraft" / "app"


def test_package_requirement_supports_release_and_local_sources(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    local = INSTALLER.package_requirement(str(checkout))
    remote = INSTALLER.package_requirement("https://example.com/slidecraft.zip")
    assert local == f"{checkout.resolve()}[cv,documents,openai]"
    assert remote == "slidecraft-ai[cv,documents,openai] @ https://example.com/slidecraft.zip"


def test_explicit_agent_selection_is_stable() -> None:
    assert INSTALLER.choose_agents(["codex", "claude", "codex"]) == ["codex", "claude"]
    assert INSTALLER.choose_agents(["none"]) == []


def test_windows_executable_paths() -> None:
    root = Path("C:/Slidecraft/runtime")
    assert INSTALLER.executable(root, "slidecraft", "Windows") == root / "Scripts" / "slidecraft.exe"


def test_agent_skill_is_installed_for_hosts_with_skill_support(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: slidecraft\n---\n", encoding="utf-8")

    cli = Path("/managed/slidecraft")
    codex = INSTALLER.install_agent_skill("codex", source, cli_path=cli, home=tmp_path)
    claude = INSTALLER.install_agent_skill("claude", source, home=tmp_path)
    copilot = INSTALLER.install_agent_skill("copilot", source, home=tmp_path)

    assert Path(codex["path"], "SKILL.md").is_file()
    runtime = Path(codex["path"], "references", "runtime.md")
    assert str(cli) in runtime.read_text(encoding="utf-8")
    assert Path(claude["path"], "SKILL.md").is_file()
    assert copilot["status"] == "unsupported"
