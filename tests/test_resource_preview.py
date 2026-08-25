from __future__ import annotations

import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.project_resources import project_resource_catalog
from slidecraft.projects import create_project
from slidecraft.resource_preview import build_path_preview, build_resource_preview


class ResourcePreviewTests(unittest.TestCase):
    def test_text_and_docx_materials_have_human_readable_previews(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
        ):
            root = Path(directory) / "deck"
            create_project(name="Deck", location=root)
            brief = root / "materials/brief.txt"
            brief.write_text("Clear project brief", encoding="utf-8")
            document = root / "materials/notes.docx"
            with zipfile.ZipFile(document, "w") as archive:
                archive.writestr("word/document.xml", '<w:document xmlns:w="x"><w:body><w:p><w:r><w:t>Decision memo</w:t></w:r></w:p></w:body></w:document>')
            catalog = project_resource_catalog(root)
            identifiers = {item["name"]: item["resource_id"] for item in catalog["categories"]["materials"]}

            self.assertEqual(build_resource_preview(root, identifiers["brief.txt"])["text"], "Clear project brief")
            self.assertEqual(build_resource_preview(root, identifiers["notes.docx"])["text"], "Decision memo")

    def test_component_manifest_uses_available_preview_variant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preview = root / "preview.svg"
            preview.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
            manifest = root / "map.component.json"
            manifest.write_text(
                '{"component_id":"map","preview":{"image":"preview.png"},"implementation":{"type":"pptx_fragment"}}',
                encoding="utf-8",
            )

            result = build_path_preview(manifest)

            self.assertEqual(result["kind"], "embedded_image")
            self.assertTrue(result["source"].startswith("data:image/svg+xml;base64,"))


if __name__ == "__main__":
    unittest.main()
