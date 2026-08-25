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
            project.write_text('[providers.image_generation]\nmodel = "project-image"\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"SLIDECRAFT_IMAGE_MODEL": "environment-image", "SLIDECRAFT_CONFIG": str(Path(directory) / "missing.toml")}, clear=False):
                config, provenance = resolve_config(project)
        self.assertEqual(config["providers"]["image_generation"]["model"], "environment-image")
        self.assertEqual(provenance["providers.image_generation.model"], "environment:SLIDECRAFT_IMAGE_MODEL")

    def test_image_adapter_environment_override_configures_the_fallback_connection(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ,
            {
                "SLIDECRAFT_CONFIG": str(Path(directory) / "missing.toml"),
                "SLIDECRAFT_IMAGE_ADAPTER": "custom-openai-compatible",
            },
            clear=False,
        ):
            config, provenance = resolve_config()
        provider = config["providers"]["image_generation"]
        self.assertEqual(provider["adapter"], "host")
        self.assertEqual(provider["configured_adapter"], "custom-openai-compatible")
        self.assertEqual(
            provenance["providers.image_generation.configured_adapter"],
            "environment:SLIDECRAFT_IMAGE_ADAPTER",
        )

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
            modify_config_value("providers.image_generation.model", "custom-image", scope="project", project_config=project)
            config, _ = resolve_config(project)
            self.assertEqual(config["providers"]["image_generation"]["model"], "custom-image")
            modify_config_value("providers.image_generation.model", scope="project", project_config=project, unset=True)
            config, _ = resolve_config(project)
            self.assertEqual(config["providers"]["image_generation"]["model"], "gpt-image-2")

    def test_deck_request_override_supports_run_specific_slide_count(self) -> None:
        request = apply_dotted_overrides({}, ["preferred_slide_count.target=12", "density_profile=medium"])
        self.assertEqual(request["preferred_slide_count"]["target"], 12)
        self.assertEqual(request["density_profile"], "medium")
