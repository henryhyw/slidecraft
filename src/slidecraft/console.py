"""Local, dependency-light control console for Slidecraft."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from slidecraft.agent import list_capabilities
from slidecraft.configuration import (
    data_root,
    flatten,
    initialize_user_environment,
    modify_config_value,
    parse_config_value,
    resolve_config,
)
from slidecraft.credentials import delete_credential, resolve_provider_credential, set_credential
from slidecraft.library_manager import (
    add_library_item,
    delete_library_item,
    library_root,
    list_library_items,
    resolve_library_item,
    set_library_location,
    update_library_item_metadata,
)
from slidecraft.project_assets import (
    add_uploaded_asset,
    deactivate_project_asset,
    list_project_assets,
    update_project_asset,
)
from slidecraft.project_events import acknowledge_project_events, list_project_events
from slidecraft.project_materials import add_uploaded_material
from slidecraft.project_resource_selections import (
    add_project_library_resource,
    project_library_options,
    remove_project_resource,
)
from slidecraft.project_resources import project_resource_catalog, resolve_project_resource
from slidecraft.projects import create_project, list_projects, project_detail, project_manifest_path
from slidecraft.resource_preview import build_path_preview, build_resource_preview
from slidecraft.runtime.doctor import collect_diagnostics

_HEALTH_CACHE: dict[str, Any] = {"at": 0.0, "value": None}


def open_local_path(path: str | Path, *, expected: str = "file") -> dict[str, Any]:
    """Open a trusted local file or folder with the operating system."""
    resolved = Path(path).expanduser().resolve(strict=True)
    if expected == "file" and not resolved.is_file():
        raise FileNotFoundError(f"This file could not be found at {resolved}")
    if expected == "directory" and not resolved.is_dir():
        raise FileNotFoundError(f"This folder could not be found at {resolved}")

    if sys.platform == "darwin":
        command = ["open", str(resolved)]
    elif os.name == "nt":
        os.startfile(str(resolved))  # type: ignore[attr-defined]
        return {"status": "opened", "path": str(resolved), "method": "system_default"}
    else:
        launcher = shutil.which("xdg-open") or shutil.which("gio")
        if not launcher:
            raise RuntimeError("No desktop file opener is available on this system")
        command = [launcher, "open", str(resolved)] if Path(launcher).name == "gio" else [launcher, str(resolved)]

    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"status": "opened", "path": str(resolved), "method": "system_default"}


def open_local_file(path: str | Path) -> dict[str, Any]:
    return open_local_path(path, expected="file")


def open_local_folder(path: str | Path) -> dict[str, Any]:
    return open_local_path(path, expected="directory")


def _latest_presentation(projects: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates: list[tuple[int, float, dict[str, Any]]] = []
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    for project in projects:
        if not project.get("available"):
            continue
        try:
            deliverables = project_resource_catalog(project["path"])["categories"]["deliverables"]
        except (FileNotFoundError, KeyError, ValueError):
            continue
        presentations = [
            item for item in deliverables
            if Path(item["path"]).suffix.lower() == ".pptx"
            and item.get("presentation_role") in {"final", "current_progress"}
        ]
        images = [item for item in deliverables if Path(item["path"]).suffix.lower() in image_suffixes]
        for presentation in presentations:
            presentation_path = Path(presentation["path"])
            preview = next(
                (
                    image
                    for image in images
                    if Path(image["path"]).stem.startswith(presentation_path.stem)
                    or presentation_path.stem.startswith(Path(image["path"]).stem)
                ),
                None,
            )
            presentation_priority = 2 if presentation.get("presentation_role") == "final" else 1
            candidates.append((presentation_priority, presentation_path.stat().st_mtime, {
                "project_name": project["name"],
                "project_path": project["path"],
                "resource_id": presentation["resource_id"],
                "preview_resource_id": preview["resource_id"] if preview else None,
                "name": presentation["name"],
            }))
    return max(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None


def _library_summary(config: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for name, value in config["libraries"].items():
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = data_root() / path
        count = list_library_items(name)["item_count"] if name in {"visual_references", "icons", "components"} else (
            len([item for item in path.glob("**/*") if item.is_file()]) if path.is_dir() else 0
        )
        record = {"name": name, "path": str(path), "available": path.is_dir(), "item_count": count}
        if name == "icons":
            icon_policy = config.get("resources", {}).get("icons", {})
            record["online_retrieval"] = {
                "enabled": bool(icon_policy.get("allow_online_retrieval", True)),
                "provider": "Tabler Icons",
            }
        result.append(record)
    return result


def _design_summary(config: dict[str, Any]) -> dict[str, Any]:
    design = config.get("design", {})
    profiles = []
    profile_root = files("slidecraft").joinpath("guidance_profiles")
    if profile_root.is_dir():
        for path in sorted((item for item in profile_root.iterdir() if item.name.endswith(".json")), key=lambda item: item.name):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            profiles.append({
                "profile_id": value.get("profile_id", Path(path.name).stem),
                "name": value.get("name", Path(path.name).stem.replace("_", " ").title()),
                "description": value.get("description", ""),
            })
    return {
        "settings": design,
        "guidance_profiles": profiles,
        "font_choices": _font_choices(),
        "choices": {
            "density_profile": ["low", "medium", "high_consulting"],
            "color_system": ["warm_orange", "neutral", "custom"],
            "icon_style": ["tabler_warm_slot", "tabler_plain", "custom"],
        },
    }


def _project_config(query: dict[str, list[str]]) -> Path | None:
    if not query.get("path"):
        return None
    root = Path(query["path"][0]).expanduser().resolve()
    project_manifest_path(root)
    path = root / ".slidecraft" / "config.toml"
    return path if path.is_file() else None


def _font_choices() -> list[dict[str, Any]]:
    preferred = [
        "Aptos", "Arial", "Avenir Next", "Baskerville", "Calibri", "Futura", "Georgia",
        "Gill Sans", "Helvetica Neue", "Optima", "Palatino", "Times New Roman", "Trebuchet MS", "Verdana",
    ]
    available: set[str] = set()
    command = shutil.which("fc-list")
    if command:
        try:
            completed = subprocess.run(
                [command, "--format", "%{family}\n"], capture_output=True, text=True, timeout=3, check=False
            )
            for line in completed.stdout.splitlines():
                available.update(part.strip() for part in line.split(",") if part.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    return [{"name": name, "installed": not available or name in available} for name in preferred]


def _provider_summary(config: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {"image_generation": "Image generation"}
    result = []
    for role, value in config["providers"].items():
        if role != "image_generation":
            continue
        credential = resolve_provider_credential(value, role)
        result.append({
            "role": role,
            "label": labels[role],
            "adapter": value.get("adapter", "host"),
            "selection_policy": value.get("selection_policy", "prefer_host"),
            "configured_adapter": value.get("configured_adapter", "openai"),
            "model": value.get("model", ""),
            "base_url": value.get("base_url", ""),
            "api_key_env": value.get("api_key_env", ""),
            "credential_id": credential["credential_id"],
            "credential_source": credential["source"],
            "credential_available": credential["available"],
        })
    return result


def _health(*, force: bool = False) -> dict[str, Any]:
    now = time.monotonic()
    if force or _HEALTH_CACHE["value"] is None or now - _HEALTH_CACHE["at"] > 60:
        _HEALTH_CACHE.update(at=now, value=collect_diagnostics())
    return {**_HEALTH_CACHE["value"], "checked_at_epoch": time.time(), "cache_seconds": 60}


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "SlidecraftConsole/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, error: Exception, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._json({"status": "failed", "error_type": type(error).__name__, "reason": str(error)}, status)

    def _body(self) -> dict[str, Any]:
        length = min(int(self.headers.get("Content-Length", "0")), 32 * 1024 * 1024)
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._static(parsed.path, include_body=False)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/overview":
                config, provenance = resolve_config()
                projects = list_projects()
                self._json({
                    "projects": projects,
                    "project_count": len(projects),
                    "available_project_count": sum(item["available"] for item in projects),
                    "libraries": _library_summary(config),
                    "runtime": {"mode": config["runtime"]["mode"], "compute": config["runtime"]["compute"]},
                    "providers": config["providers"],
                    "provider_connections": _provider_summary(config),
                    "editable_presentation_count": sum(
                        item.get("progress", {}).get("editable_presentation_count", 0) for item in projects
                    ),
                    "active_project_count": sum(
                        item.get("progress", {}).get("status") not in {"complete", "starting"} for item in projects if item["available"]
                    ),
                    "source_material_count": sum(item.get("source_material_count", 0) for item in projects),
                    "latest_presentation": _latest_presentation(projects),
                    "configuration_sources": len(set(provenance.values())),
                })
                return
            if parsed.path == "/api/projects":
                self._json({"projects": list_projects()})
                return
            if parsed.path == "/api/project":
                query = parse_qs(parsed.query)
                self._json(project_detail(query["path"][0], include_internal=query.get("internal", ["0"])[0] == "1"))
                return
            if parsed.path == "/api/config":
                query = parse_qs(parsed.query)
                config, provenance = resolve_config(_project_config(query))
                values = flatten(config)
                self._json({
                    "config": config,
                    "scope": "project" if query.get("path") else "user",
                    "values": [{"key": key, "value": values[key], "source": provenance.get(key, "default")} for key in sorted(values)],
                })
                return
            if parsed.path == "/api/capabilities":
                self._json(list_capabilities())
                return
            if parsed.path == "/api/health":
                query = parse_qs(parsed.query)
                self._json(_health(force=query.get("refresh", ["0"])[0] == "1"))
                return
            if parsed.path == "/api/libraries":
                config, _ = resolve_config()
                self._json({"libraries": _library_summary(config)})
                return
            if parsed.path == "/api/assets":
                query = parse_qs(parsed.query)
                self._json(list_project_assets(query["path"][0], sync_folder=True))
                return
            if parsed.path == "/api/resources":
                query = parse_qs(parsed.query)
                self._json(project_resource_catalog(query["path"][0]))
                return
            if parsed.path == "/api/project-library-options":
                query = parse_qs(parsed.query)
                self._json(project_library_options(query["path"][0], query["category"][0]))
                return
            if parsed.path == "/api/resource-preview":
                query = parse_qs(parsed.query)
                self._json(build_resource_preview(query["path"][0], query["resource_id"][0]))
                return
            if parsed.path == "/api/resource-file":
                query = parse_qs(parsed.query)
                resource = resolve_project_resource(query["path"][0], query["resource_id"][0])
                self._resource_file(Path(resource["resolved_path"]))
                return
            if parsed.path == "/api/project-events":
                query = parse_qs(parsed.query)
                self._json(list_project_events(query["path"][0], pending_only=query.get("all", ["0"])[0] != "1"))
                return
            if parsed.path == "/api/design":
                query = parse_qs(parsed.query)
                config, _ = resolve_config(_project_config(query))
                self._json({**_design_summary(config), "scope": "project" if query.get("path") else "user"})
                return
            if parsed.path == "/api/providers":
                config, _ = resolve_config()
                self._json({"providers": _provider_summary(config)})
                return
            if parsed.path == "/api/library-items":
                query = parse_qs(parsed.query)
                self._json(list_library_items(query["name"][0]))
                return
            if parsed.path == "/api/library-file":
                query = parse_qs(parsed.query)
                item = resolve_library_item(query["name"][0], query["item_id"][0])
                requested_path = item.get("preview_path") if query.get("preview", ["0"])[0] == "1" else None
                self._resource_file(Path(requested_path or item["path"]))
                return
            if parsed.path == "/api/library-preview":
                query = parse_qs(parsed.query)
                item = resolve_library_item(query["name"][0], query["item_id"][0])
                self._json(build_path_preview(item["path"], {**item, "category": query["name"][0]}))
                return
            self._static(parsed.path)
        except (FileNotFoundError, KeyError) as error:
            self._error(error, HTTPStatus.NOT_FOUND)
        except Exception as error:  # noqa: BLE001
            self._error(error)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self._body()
            if parsed.path == "/api/projects":
                self._json({"status": "ok", "project": create_project(
                    name=body["name"],
                    location=body.get("location"),
                    deck_id=body.get("deck_id"),
                    description=body.get("description", ""),
                )}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/open-resource":
                resource = resolve_project_resource(body["location"], body["resource_id"])
                self._json(open_local_file(resource["resolved_path"]))
                return
            if parsed.path == "/api/open-project-folder":
                project_detail(body["location"])
                self._json(open_local_folder(Path(body["location"]).expanduser().resolve()))
                return
            if parsed.path == "/api/open-library-folder":
                self._json(open_local_folder(library_root(body["name"])))
                return
            if parsed.path == "/api/config":
                path = modify_config_value(
                    body["key"],
                    parse_config_value(json.dumps(body.get("value"), ensure_ascii=False)),
                    scope=body.get("scope", "user"),
                    project_config=Path(body["project_config"]).expanduser().resolve() if body.get("project_config") else None,
                    unset=bool(body.get("unset", False)),
                )
                self._json({"status": "ok", "path": str(path), "key": body["key"]})
                return
            if parsed.path == "/api/initialize":
                self._json(initialize_user_environment(force=False))
                return
            if parsed.path == "/api/assets":
                if body.get("action") == "update":
                    self._json({"status": "ok", "asset": update_project_asset(
                        body["location"],
                        body["asset_id"],
                        semantic_role=body.get("semantic_role"),
                        usage_policy=body.get("usage_policy"),
                        slide_ids=body.get("slide_ids"),
                        actor=body.get("actor", "local_console"),
                    )})
                elif body.get("action") == "remove":
                    self._json({"status": "ok", "asset": deactivate_project_asset(
                        body["location"], body["asset_id"], actor=body.get("actor", "local_console")
                    )})
                else:
                    self._json({"status": "ok", "asset": add_uploaded_asset(
                        body["location"],
                        filename=body["filename"],
                        content_base64=body["content_base64"],
                        semantic_role=body.get("semantic_role"),
                        usage_policy=body.get("usage_policy", "available"),
                    )}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/materials":
                self._json({"status": "ok", "material": add_uploaded_material(
                    body["location"],
                    filename=body["filename"],
                    content_base64=body["content_base64"],
                    actor=body.get("actor", "user_console"),
                )}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/project-resources":
                if body.get("action") == "remove":
                    result = remove_project_resource(
                        body["location"],
                        category=body["category"],
                        resource_id=body["resource_id"],
                        actor=body.get("actor", "user_console"),
                    )
                else:
                    result = add_project_library_resource(
                        body["location"],
                        category=body["category"],
                        item_id=body["item_id"],
                        actor=body.get("actor", "user_console"),
                    )
                self._json({"status": "ok", "resource": result})
                return
            if parsed.path == "/api/provider-credential":
                credential_id = body.get("credential_id", "providers.image_generation")
                result = (
                    delete_credential(credential_id)
                    if body.get("action") == "delete"
                    else set_credential(credential_id, body["credential"])
                )
                self._json({"status": "ok", **result})
                return
            if parsed.path == "/api/provider-connection-test":
                from slidecraft.providers.openai import OpenAIImageGenerationProvider

                role = body.get("role", "image_generation")
                config, _ = resolve_config()
                provider_config = config["providers"][role]
                credential = body.get("credential") or resolve_provider_credential(provider_config, role)["secret"]
                if not credential:
                    raise ValueError("Enter an API key before testing this connection")
                adapter = body.get("configured_adapter", provider_config.get("configured_adapter", "openai"))
                base_url = body.get("base_url", provider_config.get("base_url", ""))
                if adapter == "custom-openai-compatible" and not base_url:
                    raise ValueError("Enter the compatible endpoint URL before testing")
                provider = OpenAIImageGenerationProvider(
                    model=body.get("model") or provider_config.get("model", "gpt-image-2"),
                    api_key=credential,
                    base_url=base_url or None,
                )
                self._json(provider.test_connection())
                return
            if parsed.path == "/api/project-events":
                self._json(acknowledge_project_events(body["location"], body.get("event_ids", [])))
                return
            if parsed.path == "/api/library-location":
                self._json({"status": "ok", "library": set_library_location(body["name"], body["location"])})
                return
            if parsed.path == "/api/library-items":
                if body.get("action") == "delete":
                    self._json(delete_library_item(body["name"], body["item_id"]))
                elif body.get("action") == "update":
                    self._json({"status": "ok", "item": update_library_item_metadata(
                        body["name"], body["item_id"], body.get("metadata", {})
                    )})
                else:
                    self._json({"status": "ok", "item": add_library_item(
                        body["name"], body["filename"], body["content_base64"], body.get("metadata")
                    )}, HTTPStatus.CREATED)
                return
            self._error(FileNotFoundError(parsed.path), HTTPStatus.NOT_FOUND)
        except Exception as error:  # noqa: BLE001
            self._error(error)

    def _resource_file(self, path: Path) -> None:
        payload = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f'inline; filename="{path.name.replace(chr(34), "")}"')
        self.send_header("Cache-Control", "private, max-age=60")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _static(self, requested: str, *, include_body: bool = True) -> None:
        relative = "index.html" if requested in {"", "/"} else requested.lstrip("/")
        if ".." in Path(relative).parts:
            raise FileNotFoundError(relative)
        resource = files("slidecraft").joinpath("ui", relative)
        if not resource.is_file():
            resource = files("slidecraft").joinpath("ui", "index.html")
        payload = resource.read_bytes()
        content_type = mimetypes.guess_type(str(resource))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if include_body:
            self.wfile.write(payload)


def serve(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    initialize_user_environment(force=False)
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    url = f"http://{host}:{port}"
    print(json.dumps({"status": "running", "url": url, "local_only": host in {"127.0.0.1", "localhost"}}))
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Slidecraft control console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    main()
