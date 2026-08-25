from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from slidecraft.configuration import apply_dotted_overrides, modify_config_value, resolve_config, user_config_file


class ConfigurationTests(TestCase):
    def test_data_root_override_is_an_isolated_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ,
            {"SLIDECRAFT_DATA_DIR": directory},
            clear=False,
        ):
            self.assertEqual(user_config_file(), Path(directory).resolve() / "config.toml")
            config, _ = resolve_config()
            self.assertEqual(config["libraries"]["visual_references"], "libraries/visual_references")

    def test_project_and_environment_precedence_is_explainable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project.toml"
            project.write_text('[providers.vision]\nadapter = "openai"\nmodel = "project-vision"\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"SLIDECRAFT_VISION_MODEL": "environment-vision", "SLIDECRAFT_CONFIG": str(Path(directory) / "missing.toml")}, clear=False):
                config, provenance = resolve_config(project)
        self.assertEqual(config["providers"]["vision"]["adapter"], "openai")
        self.assertEqual(config["providers"]["vision"]["model"], "environment-vision")
        self.assertTrue(provenance["providers.vision.adapter"].startswith("project:"))
        self.assertEqual(provenance["providers.vision.model"], "environment:SLIDECRAFT_VISION_MODEL")

    def test_interactive_production_config_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project.toml"
            project.write_text("[interaction]\nprompt_during_run = true\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-interactive"):
                resolve_config(project)

    def test_runtime_override_is_typed_and_has_highest_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_user = Path(directory) / "missing.toml"
            with mock.patch.dict(os.environ, {"SLIDECRAFT_CONFIG": str(missing_user)}, clear=False):
                config, provenance = resolve_config(runtime_overrides=["segmentation.device=cpu", "validation.powerpoint_native=true"])
        self.assertEqual(config["segmentation"]["device"], "cpu")
        self.assertTrue(config["validation"]["powerpoint_native"])
        self.assertEqual(provenance["segmentation.device"], "runtime:--set")

    def test_project_configuration_can_be_persistently_set_and_unset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "slidecraft.toml"
            modify_config_value("providers.vision.model", "custom-vision", scope="project", project_config=project)
            config, _ = resolve_config(project)
            self.assertEqual(config["providers"]["vision"]["model"], "custom-vision")
            modify_config_value("providers.vision.model", scope="project", project_config=project, unset=True)
            config, _ = resolve_config(project)
            self.assertEqual(config["providers"]["vision"]["model"], "gpt-5.6-terra")

    def test_deck_request_override_supports_run_specific_slide_count(self) -> None:
        request = apply_dotted_overrides({}, ["preferred_slide_count.target=12", "density_profile=medium"])
        self.assertEqual(request["preferred_slide_count"]["target"], 12)
        self.assertEqual(request["density_profile"], "medium")
