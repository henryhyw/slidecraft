from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.agent import call_capability, list_capabilities
from slidecraft.runtime.artifacts import ArtifactWorkspace


class ArtifactWorkspaceTests(unittest.TestCase):
    def test_replacing_an_input_makes_descendants_stale_without_deleting_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            output = root / "output.json"
            source.write_text('{"version": 1}\n', encoding="utf-8")
            output.write_text('{"derived": 1}\n', encoding="utf-8")
            workspace = ArtifactWorkspace(root / "run")
            workspace.initialize(deck_id="deck_1")
            workspace.register(logical_key="slides/s1/source", kind="source", path=source, producer="test")
            derived = workspace.register(
                logical_key="slides/s1/derived",
                kind="derived",
                path=output,
                dependencies=["slides/s1/source"],
                producer="test",
            )
            source.write_text('{"version": 2}\n', encoding="utf-8")
            workspace.register(logical_key="slides/s1/source", kind="source", path=source, producer="test")
            inspection = workspace.inspect(include_history=True)

        active = {item["logical_key"]: item for item in inspection["active_artifacts"]}
        self.assertFalse(active["slides/s1/derived"]["freshness"]["fresh"])
        self.assertEqual(active["slides/s1/derived"]["artifact_id"], derived["artifact_id"])
        self.assertIn("slides/s1/derived", inspection["stale_logical_keys"])
        self.assertEqual(len([item for item in inspection["history"] if item["logical_key"] == "slides/s1/source"]), 2)

    def test_candidate_does_not_invalidate_active_descendants_until_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_a = root / "a.png"
            image_b = root / "b.png"
            scene = root / "scene.json"
            image_a.write_bytes(b"a")
            image_b.write_bytes(b"b")
            scene.write_text("{}\n", encoding="utf-8")
            workspace = ArtifactWorkspace(root / "run")
            workspace.initialize()
            workspace.register(logical_key="slides/s1/image", kind="image", path=image_a, producer="test")
            workspace.register(logical_key="slides/s1/scene", kind="scene", path=scene, dependencies=["slides/s1/image"], producer="test")
            candidate = workspace.register(logical_key="slides/s1/image", kind="image", path=image_b, producer="test", activate=False)
            before = workspace.inspect()
            workspace.activate(candidate["artifact_id"])
            after = workspace.inspect()

        before_active = {item["logical_key"]: item for item in before["active_artifacts"]}
        after_active = {item["logical_key"]: item for item in after["active_artifacts"]}
        self.assertTrue(before_active["slides/s1/scene"]["freshness"]["fresh"])
        self.assertFalse(after_active["slides/s1/scene"]["freshness"]["fresh"])

    def test_agent_surface_has_no_pause_or_resume_control(self) -> None:
        names = {item["name"] for item in list_capabilities()["capabilities"]}
        self.assertIn("inspect_workspace", names)
        self.assertNotIn("pause", names)
        self.assertNotIn("resume", names)

    def test_json_style_capability_call_is_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "run"
            result = call_capability("create_workspace", {"workspace": str(workspace), "deck_id": "D1"})
            inspection = call_capability("inspect_workspace", {"workspace": str(workspace)})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(inspection["result"]["control_model"], "agent_host")


if __name__ == "__main__":
    unittest.main()
