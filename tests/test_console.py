from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.console import ConsoleHandler, open_local_file, open_local_folder


class ConsoleTests(unittest.TestCase):
    def test_open_local_file_uses_the_system_default_application(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deck.pptx"
            path.write_bytes(b"pptx")
            with patch("slidecraft.console.sys.platform", "darwin"), patch("slidecraft.console.subprocess.Popen") as launch:
                result = open_local_file(path)

        self.assertEqual(result["status"], "opened")
        self.assertEqual(result["path"], str(path.resolve()))
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], ["open", str(path.resolve())])

    def test_open_local_folder_uses_the_system_file_browser(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch("slidecraft.console.sys.platform", "darwin"), patch("slidecraft.console.subprocess.Popen") as launch:
                result = open_local_folder(path)

        self.assertEqual(result["status"], "opened")
        self.assertEqual(result["path"], str(path.resolve()))
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], ["open", str(path.resolve())])

    def test_console_serves_ui_and_api_without_external_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                origin = f"http://127.0.0.1:{server.server_address[1]}"
                with urlopen(f"{origin}/api/overview") as response:
                    payload = json.load(response)
                with urlopen(Request(f"{origin}/", method="HEAD")) as response:
                    content_type = response.headers["Content-Type"]
                project_path = str(Path(directory) / "deck")
                project_body = json.dumps({"name": "Deck", "location": project_path}).encode()
                with urlopen(Request(f"{origin}/api/projects", data=project_body, headers={"Content-Type": "application/json"})):
                    pass
                deliverables = Path(project_path) / "deliverables"
                deliverables.mkdir(parents=True, exist_ok=True)
                (deliverables / "current_deck.pptx").write_bytes(b"pptx")
                (deliverables / "current_deck.preview.png").write_bytes(b"png")
                with urlopen(f"{origin}/api/overview") as response:
                    populated_overview = json.load(response)
                open_body = json.dumps({
                    "location": project_path,
                    "resource_id": populated_overview["latest_presentation"]["resource_id"],
                }).encode()
                with patch("slidecraft.console.sys.platform", "darwin"), patch("slidecraft.console.subprocess.Popen") as launch:
                    with urlopen(Request(
                        f"{origin}/api/open-resource",
                        data=open_body,
                        headers={"Content-Type": "application/json"},
                    )) as response:
                        opened = json.load(response)
                    with urlopen(Request(
                        f"{origin}/api/open-project-folder",
                        data=json.dumps({"location": project_path}).encode(),
                        headers={"Content-Type": "application/json"},
                    )) as response:
                        opened_project = json.load(response)
                    with urlopen(Request(
                        f"{origin}/api/open-library-folder",
                        data=json.dumps({"name": "icons"}).encode(),
                        headers={"Content-Type": "application/json"},
                    )) as response:
                        opened_library = json.load(response)
                asset_body = json.dumps({
                    "location": project_path,
                    "filename": "logo.svg",
                    "content_base64": base64.b64encode(b"<svg/>").decode(),
                    "semantic_role": "client logo",
                    "usage_policy": "available",
                }).encode()
                with urlopen(Request(f"{origin}/api/assets", data=asset_body, headers={"Content-Type": "application/json"})):
                    pass
                with urlopen(f"{origin}/api/assets?path={project_path}") as response:
                    assets = json.load(response)
                asset_id = assets["assets"][0]["asset_id"]
                with urlopen(f"{origin}/api/resource-preview?path={project_path}&resource_id={asset_id}") as response:
                    preview = json.load(response)
                with urlopen(f"{origin}/api/design") as response:
                    design = json.load(response)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertEqual(payload["project_count"], 0)
        self.assertEqual(len(payload["libraries"]), 4)
        self.assertEqual(populated_overview["latest_presentation"]["name"], "current_deck.pptx")
        self.assertIsNotNone(populated_overview["latest_presentation"]["preview_resource_id"])
        self.assertEqual(opened["status"], "opened")
        self.assertEqual(opened_project["status"], "opened")
        self.assertEqual(opened_library["status"], "opened")
        self.assertEqual(launch.call_count, 3)
        self.assertIn("text/html", content_type)
        self.assertEqual(assets["assets"][0]["semantic_role"], "client logo")
        self.assertEqual(preview["kind"], "image")
        self.assertEqual(design["settings"]["guidance_profile"], "consulting")


if __name__ == "__main__":
    unittest.main()
