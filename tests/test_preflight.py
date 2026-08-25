import json
import tempfile
import unittest
from pathlib import Path

from slidecraft.orchestration.asset_ingestion import apply_ingested_asset_manifest, ingest_user_asset
from slidecraft.orchestration.preflight import build_generation_preflight

ROOT = Path(__file__).resolve().parents[1]


class PreflightTests(unittest.TestCase):
    def test_current_run_requires_confirmation(self) -> None:
        deck = json.loads((ROOT / "tests" / "fixtures" / "architecture" / "design_config.json").read_text())
        slide = json.loads((ROOT / "tests" / "fixtures" / "architecture" / "generation_input.json").read_text())
        preflight_config = json.loads((ROOT / "config" / "preflight_config.json").read_text())
        intake = {
            "source_atoms": [{"atom_id": "A"}],
            "constraint_register": [],
            "unresolved_constraint_ids": [],
            "materials": [],
            "quality": {
                "authoritative_source_atom_count": 1,
                "material_count": 0,
                "hard_constraint_count": 0,
                "requires_user_resolution": False,
            },
        }
        semantic = {"main_message": "Test message"}
        guidance = {"profile_id": "consulting"}
        canvas = {"full_slide_px": [2048, 1152], "generation_canvas_px": [2048, 1070], "header_exclusion_px": 41, "footer_exclusion_px": 41}
        assets = {"assets": []}
        with tempfile.TemporaryDirectory() as directory:
            preflight, package, _ = build_generation_preflight(
                deck, slide, intake, semantic, guidance, canvas, assets, [], preflight_config, Path(directory)
            )
        self.assertEqual(preflight["approval"]["status"], "awaiting_user_confirmation")
        self.assertFalse(preflight["approval"]["generation_released"])
        self.assertTrue(preflight["quality"]["ready_for_approval"])
        self.assertEqual(preflight["slides"][0]["chrome"]["header"]["left_text"]["source"], "framework_proposed")
        self.assertEqual(package["resolved_chrome"]["geometry"]["header_height_px"], 41)

    def test_chat_attachment_is_copied_and_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Client Logo.svg"
            source.write_text("<svg></svg>")
            metadata = {"usage_class": "mandatory", "semantic_role": "client_logo"}
            first = ingest_user_asset(source, root / "store", metadata)
            second = ingest_user_asset(source, root / "store", metadata)
            self.assertEqual(first["stored_path"], second["stored_path"])
            self.assertTrue(Path(first["stored_path"]).exists())
            self.assertEqual(first["usage_class"], "mandatory")

    def test_ingested_manifest_populates_slide_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "logo.svg"
            source.write_text("<svg></svg>")
            record = ingest_user_asset(source, root / "store", {"usage_class": "mandatory", "semantic_role": "client_logo"})
            manifest = root / "assets.json"
            manifest.write_text(json.dumps({"schema_version": "1.0.0", "assets": [record]}))
            slide, notices = apply_ingested_asset_manifest({"ingested_asset_manifest": str(manifest)}, root)
            self.assertEqual(slide["user_provided_assets"][0]["canonical_file"], record["stored_path"])
            self.assertTrue(slide["user_provided_assets"][0]["mandatory"])
            self.assertEqual(len(notices), 1)


if __name__ == "__main__":
    unittest.main()
