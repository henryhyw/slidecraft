from __future__ import annotations

import importlib.util
import json
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
    assert local == f"{checkout.resolve()}[cv,documents,agent,openai]"
    assert remote == "slidecraft-ai[cv,documents,agent,openai] @ https://example.com/slidecraft.zip"


def test_explicit_agent_selection_is_stable() -> None:
    assert INSTALLER.choose_agents(["codex", "claude", "codex"], None) == ["codex", "claude"]
    assert INSTALLER.choose_agents(["none"], None) == []


def test_windows_executable_paths() -> None:
    root = Path("C:/Slidecraft/runtime")
    assert INSTALLER.executable(root, "slidecraft-mcp", "Windows") == root / "Scripts" / "slidecraft-mcp.exe"


def test_copilot_workspace_configuration_preserves_other_servers(tmp_path: Path) -> None:
    config = tmp_path / ".mcp.json"
    config.write_text('{"servers":{"existing":{"command":"existing-server"}}}\n', encoding="utf-8")
    result = INSTALLER.connect_copilot(tmp_path, Path("/managed/slidecraft-mcp"))
    payload = json.loads(config.read_text(encoding="utf-8"))
    assert result["status"] == "connected"
    assert payload["servers"]["existing"]["command"] == "existing-server"
    assert payload["servers"]["slidecraft"]["command"] == "/managed/slidecraft-mcp"
