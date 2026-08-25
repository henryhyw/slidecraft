from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from slidecraft.configuration import modify_config_value
from slidecraft.direct_workflow import reconstruct_slide_files
from slidecraft.projects import create_project
from slidecraft.runtime.artifacts import ArtifactWorkspace


def test_direct_reconstruction_builds_an_editable_slide_from_agent_files() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        image = root / "generated.png"
        canvas = Image.new("RGB", (1000, 563), "white")
        ImageDraw.Draw(canvas).text((100, 70), "A direct editable slide", fill="black")
        canvas.save(image)
        analysis = root / "visual-analysis.json"
        analysis.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "slide": {
                        "intent": "Communicate one direct message",
                        "reading_order": ["T_title"],
                    },
                    "groups": [],
                    "entities": [
                        {
                            "id": "T_title",
                            "kind": "text",
                            "role": "slide_title",
                            "bbox_norm": [100, 100, 800, 140],
                            "reconstruction_route": "native_textbox",
                            "visible_text": "A direct editable slide",
                            "style_hint": {"alignment": "left", "font_weight": "bold"},
                        }
                    ],
                    "relationships": [],
                }
            ),
            encoding="utf-8",
        )
        output = root / "slide.pptx"
        result = reconstruct_slide_files(
            image=image,
            visual_analysis=analysis,
            slide_id="direct-slide",
            output_dir=root / "working",
            output=output,
            sam="never",
        )

        assert result["status"] == "ok"
        assert output.is_file()
        assert result["object_count"] >= 1
        assert Path(result["artifacts"]["measurement_debug"]).is_file()
        assert Path(result["artifacts"]["constructor_scene"]).is_file()


def test_project_reconstruction_uses_shared_console_configuration_and_records_artifacts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SLIDECRAFT_DATA_DIR", str(tmp_path / "application-data"))
    root = tmp_path / "shared-project"
    create_project(name="Shared project", location=root)
    project_config = root / ".slidecraft" / "config.toml"
    modify_config_value(
        "design.display_font",
        "Aptos",
        scope="project",
        project_config=project_config,
    )
    image = root / "generated.png"
    canvas = Image.new("RGB", (1000, 563), "white")
    ImageDraw.Draw(canvas).text((100, 70), "Shared control surface", fill="black")
    canvas.save(image)
    analysis = root / "visual-analysis.json"
    analysis.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "slide": {"intent": "Verify shared state", "reading_order": ["T_title"]},
                "groups": [],
                "entities": [
                    {
                        "id": "T_title",
                        "kind": "text",
                        "role": "slide_title",
                        "bbox_norm": [100, 100, 800, 140],
                        "reconstruction_route": "native_textbox",
                        "visible_text": "Shared control surface",
                    }
                ],
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )
    output = root / "deliverables" / "slides" / "shared-slide.pptx"
    result = reconstruct_slide_files(
        image=image,
        visual_analysis=analysis,
        slide_id="shared-slide",
        output_dir=root / ".slidecraft" / "working" / "shared-slide",
        output=output,
        sam="never",
        project=root,
    )

    resolved_design = json.loads(Path(result["artifacts"]["resolved_design"]).read_text(encoding="utf-8"))
    assert resolved_design["style"]["display_font"] == "Aptos"
    active = {
        item["logical_key"]
        for item in ArtifactWorkspace(root).inspect()["active_artifacts"]
    }
    assert "slides/shared-slide/constructor_scene" in active
    assert "slides/shared-slide/editable_pptx" in active
