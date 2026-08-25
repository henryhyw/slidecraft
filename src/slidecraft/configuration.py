"""Validated configuration resolution with explicit precedence and provenance."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover, Python 3.10 only
    import tomli as tomllib

from platformdirs import user_config_path, user_data_path

ENV_OVERRIDES = {
    "SLIDECRAFT_REASONING_ADAPTER": ("providers", "reasoning", "adapter"),
    "SLIDECRAFT_REASONING_MODEL": ("providers", "reasoning", "model"),
    "SLIDECRAFT_VISION_ADAPTER": ("providers", "vision", "adapter"),
    "SLIDECRAFT_VISION_MODEL": ("providers", "vision", "model"),
    "SLIDECRAFT_IMAGE_ADAPTER": ("providers", "image_generation", "adapter"),
    "SLIDECRAFT_IMAGE_MODEL": ("providers", "image_generation", "model"),
    "SLIDECRAFT_RECONSTRUCTION_BACKEND": ("reconstruction", "backend"),
    "SLIDECRAFT_SEGMENTATION_DEVICE": ("segmentation", "device"),
}


def default_config_path() -> Path:
    return Path(str(files("slidecraft").joinpath("defaults", "slidecraft.toml")))


def user_config_file() -> Path:
    override = os.environ.get("SLIDECRAFT_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    if os.environ.get("SLIDECRAFT_DATA_DIR"):
        return data_root() / "config.toml"
    return user_config_path("slidecraft", appauthor=False) / "config.toml"


def data_root() -> Path:
    override = os.environ.get("SLIDECRAFT_DATA_DIR")
    return Path(override).expanduser().resolve() if override else user_data_path("slidecraft", appauthor=False)


def _read(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _merge(target: dict[str, Any], overlay: dict[str, Any], source: str, provenance: dict[str, str], prefix: tuple[str, ...] = ()) -> None:
    for key, value in overlay.items():
        path = prefix + (key,)
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value, source, provenance, path)
        else:
            target[key] = deepcopy(value)
            provenance[".".join(path)] = source


def _assign(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cursor = target
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[path[-1]] = value


def parse_config_value(value: str) -> Any:
    """Parse a CLI value using JSON types, falling back to a plain string."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def apply_dotted_overrides(target: dict[str, Any], overrides: list[str] | None) -> dict[str, Any]:
    """Apply repeatable KEY=VALUE overrides to a copied mapping."""
    result = deepcopy(target)
    for override in overrides or []:
        if "=" not in override:
            raise ValueError(f"Runtime override must use KEY=VALUE: {override}")
        key, raw_value = override.split("=", 1)
        path = tuple(part.strip() for part in key.split(".") if part.strip())
        if not path:
            raise ValueError("Runtime override key cannot be empty")
        _assign(result, path, parse_config_value(raw_value.strip()))
    return result


def _delete(target: dict[str, Any], path: tuple[str, ...]) -> None:
    cursor = target
    for key in path[:-1]:
        child = cursor.get(key)
        if not isinstance(child, dict):
            return
        cursor = child
    cursor.pop(path[-1], None)


def _write_toml(path: Path, value: dict[str, Any]) -> None:
    try:
        import tomli_w
    except ImportError:
        # Keep editable source checkouts usable before dependency installation.  The
        # package still declares tomli-w, while this small writer covers the scalar
        # and nested-table values accepted by Slidecraft configuration.
        def scalar(item: Any) -> str:
            if isinstance(item, bool):
                return "true" if item else "false"
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                return str(item)
            if isinstance(item, str):
                return json.dumps(item, ensure_ascii=False)
            if isinstance(item, list):
                return "[" + ", ".join(scalar(child) for child in item) + "]"
            raise TypeError(f"Unsupported configuration value type: {type(item).__name__}")

        lines: list[str] = []

        def emit(table: dict[str, Any], prefix: tuple[str, ...] = ()) -> None:
            scalars = [(key, item) for key, item in table.items() if not isinstance(item, dict)]
            children = [(key, item) for key, item in table.items() if isinstance(item, dict)]
            if prefix:
                lines.append(f"[{'/'.join(prefix).replace('/', '.')}]")
            lines.extend(f"{key} = {scalar(item)}" for key, item in scalars)
            if scalars and children:
                lines.append("")
            for index, (key, child) in enumerate(children):
                emit(child, (*prefix, key))
                if index < len(children) - 1:
                    lines.append("")

        emit(value)
        rendered = "\n".join(lines).rstrip() + "\n"
    else:
        rendered = tomli_w.dumps(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def modify_config_value(
    key: str,
    value: Any = None,
    *,
    scope: str = "user",
    project_config: Path | None = None,
    unset: bool = False,
) -> Path:
    """Persist one user or project overlay value and validate the resolved result."""
    if scope not in {"user", "project"}:
        raise ValueError("Configuration scope must be user or project")
    path = user_config_file() if scope == "user" else project_config
    if path is None:
        raise ValueError("--project is required for project-scoped configuration changes")
    path = path.expanduser().resolve()
    overlay = _read(path) if path.exists() else {}
    dotted = tuple(part.strip() for part in key.split(".") if part.strip())
    if not dotted:
        raise ValueError("Configuration key cannot be empty")
    if unset:
        _delete(overlay, dotted)
    else:
        _assign(overlay, dotted, value)
    previous = path.read_bytes() if path.exists() else None
    try:
        if path.suffix.lower() == ".json":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(overlay, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            _write_toml(path, overlay)
        resolve_config(path if scope == "project" else project_config)
    except Exception:
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(previous)
        raise
    return path


def resolve_config(
    project_config: Path | None = None,
    runtime_overrides: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    default_path = default_config_path()
    config = _read(default_path)
    provenance = {key: f"default:{default_path}" for key in flatten(config)}
    user_path = user_config_file()
    if user_path.exists():
        _merge(config, _read(user_path), f"user:{user_path}", provenance)
    if project_config:
        resolved = project_config.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(resolved)
        _merge(config, _read(resolved), f"project:{resolved}", provenance)
    for variable, path in ENV_OVERRIDES.items():
        if variable in os.environ:
            _assign(config, path, os.environ[variable])
            provenance[".".join(path)] = f"environment:{variable}"
    if runtime_overrides:
        config = apply_dotted_overrides(config, runtime_overrides)
        for override in runtime_overrides:
            provenance[override.split("=", 1)[0].strip()] = "runtime:--set"
    validate_config(config)
    return config, provenance


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "1.0.0":
        raise ValueError("Unsupported configuration schema_version")
    adapters = {"host", "host-file", "openai", "custom-openai-compatible"}
    for role in ("reasoning", "vision", "image_generation"):
        adapter = config["providers"][role]["adapter"]
        if adapter not in adapters:
            raise ValueError(f"Unsupported {role} adapter: {adapter}")
    image_provider = config["providers"]["image_generation"]
    if image_provider.get("selection_policy", "prefer_host") not in {"prefer_host", "force_configured"}:
        raise ValueError("Unsupported image generation selection policy")
    if image_provider.get("configured_adapter", "openai") not in {"openai", "custom-openai-compatible"}:
        raise ValueError("Configured image generation adapter must be an API connection")
    if config["reconstruction"]["backend"] not in {"auto", "pptxgenjs"}:
        raise ValueError("Unsupported reconstruction backend")
    if config["segmentation"]["device"] not in {"auto", "cpu", "mps", "cuda"}:
        raise ValueError("Unsupported segmentation device")
    if config["interaction"]["prompt_during_run"]:
        raise ValueError("Production runs must remain non-interactive")


def constructor_node_modules() -> Path:
    override = os.environ.get("SLIDECRAFT_NODE_MODULES")
    return Path(override).expanduser().resolve() if override else data_root() / "runtime" / "node_modules"


def _install_constructor_runtime() -> dict[str, Any]:
    target = data_root() / "runtime"
    modules = constructor_node_modules()
    if (modules / "pptxgenjs").exists() and (modules / "jszip").exists():
        return {"status": "ready", "node_modules": str(modules), "installed": False}
    npm = shutil.which("npm")
    node = shutil.which("node")
    if not npm or not node:
        return {
            "status": "unavailable",
            "reason": "Node.js and npm are required for editable PowerPoint construction.",
            "node_modules": str(modules),
        }
    target.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        [npm, "install", "--prefix", str(target), "--no-audit", "--no-fund", "--silent", "pptxgenjs@^4.0.1", "jszip@^3.10.1"],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if process.returncode or not (modules / "pptxgenjs").exists() or not (modules / "jszip").exists():
        return {
            "status": "failed",
            "reason": process.stderr.strip() or process.stdout.strip() or "npm installation failed",
            "node_modules": str(modules),
        }
    return {"status": "ready", "node_modules": str(modules), "installed": True}


def initialize_user_environment(*, force: bool = False, install_constructor: bool = False) -> dict[str, Any]:
    config_path = user_config_file()
    root = data_root()
    created: list[str] = []
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists() or force:
        shutil.copyfile(default_config_path(), config_path)
        created.append(str(config_path))
    for relative in ("libraries/visual_references", "libraries/icons", "libraries/components", "libraries/styles", "projects", "models", "cache", "logs"):
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        created.append(str(path))
    for library in ("visual_references", "icons", "components"):
        destination = root / "libraries" / library
        # Merge missing starter files without overwriting user-managed resources.
        # This also delivers new preview or metadata sidecars on package upgrades.
        _copy_starter_resources(files("slidecraft").joinpath("starter_resources", library), destination)
    result = {"status": "ok", "config": str(config_path), "data_root": str(root), "created": created}
    if install_constructor:
        result["constructor_runtime"] = _install_constructor_runtime()
        if result["constructor_runtime"]["status"] != "ready":
            result["status"] = "incomplete"
    return result


def _copy_starter_resources(source: Any, destination: Path) -> None:
    for item in source.iterdir():
        target = destination / (".slidecraft-library.json" if item.name == "catalog.json" else item.name)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _copy_starter_resources(item, target)
        elif not target.exists():
            target.write_bytes(item.read_bytes())


def flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result
