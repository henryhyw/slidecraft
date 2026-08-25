from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slidecraft.runtime.state import RunStateStore, initialize_run_state


class RunStateTests(unittest.TestCase):
    def test_valid_transitions_are_atomic_and_resumable(self) -> None:
        manifest = {"run_id": "R1", "deck_id": "D1", "fingerprint": "abc", "jobs": [{"slide_id": "S1", "status": "ready_for_semantic_planning"}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run_state.json"
            initialize_run_state(manifest, path)
            store = RunStateStore(path)
            store.transition_slide("S1", "awaiting_generation", artifact={"kind": "semantic_design", "path": "semantic.json"})
            state = json.loads(path.read_text())
        self.assertEqual(state["slides"][0]["status"], "awaiting_generation")
        self.assertEqual(state["slides"][0]["artifacts"][0]["kind"], "semantic_design")

    def test_invalid_transition_is_rejected(self) -> None:
        manifest = {"run_id": "R1", "deck_id": "D1", "fingerprint": "abc", "jobs": [{"slide_id": "S1", "status": "ready_for_semantic_planning"}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run_state.json"
            initialize_run_state(manifest, path)
            with self.assertRaisesRegex(ValueError, "Invalid slide transition"):
                RunStateStore(path).transition_slide("S1", "ready_for_assembly")

    def test_approval_requires_current_fingerprint(self) -> None:
        manifest = {"run_id": "R1", "deck_id": "D1", "fingerprint": "abc", "jobs": [{"slide_id": "S1", "status": "ready_for_semantic_planning"}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run_state.json"
            initialize_run_state(manifest, path)
            store = RunStateStore(path)
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                store.approve("stale")
            state = store.approve("abc")
        self.assertEqual(state["status"], "approved")


if __name__ == "__main__":
    unittest.main()
