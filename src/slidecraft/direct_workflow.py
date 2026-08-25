"""Direct slide reconstruction over shared local project files."""

from __future__ import annotations

import json
import subprocess
import sys
import sysconfig
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import Any

from PIL import Image

from slidecraft.configuration import data_root, resolve_config
from slidecraft.orchestration.pipeline import apply_application_defaults
from slidecraft.projects import project_manifest_path
from slidecraft.providers.file import RecordedVisualAnalysis
from slidecraft.reconstruction.contract import build_reconstruction_contract
from slidecraft.reconstruction.scene import build_reconstruction_scene
from slidecraft.runtime.artifacts import ArtifactWorkspace
from slidecraft.semantic_mapping.compiler import compile_semantic_map


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _measurement_script() -> Path:
    repository = Path(__file__).resolve().parents[2] / "scripts" / "measure_visual_scene.py"
    if repository.is_file():
        return repository
    installed = Path(sysconfig.get_path("data")) / "share" / "slidecraft" / "scripts" / "measure_visual_scene.py"
    if installed.is_file():
        return installed
    raise FileNotFoundError("The packaged OpenCV measurement script is unavailable")


def _default_design() -> Path:
    return Path(str(files("slidecraft.defaults").joinpath("deck_design.json")))


def _normalize_handoff(
    *, image: Path, design: dict[str, Any], supplied: dict[str, Any] | None
) -> dict[str, Any]:
    value = dict(supplied or {})
    with Image.open(image) as raster:
        width, height = raster.size
    region = dict(value.get("generation_region") or {})
    region.setdefault("offset_y_px", 0)
    region.setdefault("dimensions_px", [width, height])
    target = dict(value.get("target_image") or {})
    target.setdefault("path", str(image))
    target.setdefault("scope", "generation_region")
    target.setdefault("actual_dimensions_px", [width, height])
    return {
        "schema_version": value.get("schema_version", "1.0.0"),
        "handoff_type": value.get("handoff_type", "agent_generated_image_to_reconstruction"),
        "target_image": target,
        "full_slide_dimensions_px": value.get("full_slide_dimensions_px", [width, height]),
        "generation_region": region,
        "exact_title_text": value.get("exact_title_text", ""),
        "exact_source_content": value.get("exact_source_content", {}),
        "semantic_design": value.get("semantic_design", {}),
        "selected_assets": value.get("selected_assets", []),
        "icon_slot_configuration": value.get(
            "icon_slot_configuration", design.get("icon_slots", {})
        ),
        "user_asset_policy": value.get("user_asset_policy", {}),
        "connector_configuration": value.get(
            "connector_configuration", design.get("connectors", {})
        ),
        "connector_configuration_qa": value.get("connector_configuration_qa", {}),
        "style_configuration": value.get("style_configuration", design.get("style", {})),
        "visual_references": value.get("visual_references", []),
        "deck_chrome_configuration": value.get(
            "deck_chrome_configuration", {"enabled": False}
        ),
        "resolved_chrome_content": value.get("resolved_chrome_content", {}),
        **{
            key: item
            for key, item in value.items()
            if key
            not in {
                "schema_version",
                "handoff_type",
                "target_image",
                "full_slide_dimensions_px",
                "generation_region",
                "exact_title_text",
                "exact_source_content",
                "semantic_design",
                "selected_assets",
                "icon_slot_configuration",
                "user_asset_policy",
                "connector_configuration",
                "connector_configuration_qa",
                "style_configuration",
                "visual_references",
                "deck_chrome_configuration",
                "resolved_chrome_content",
            }
        },
    }


def _default_refinement_plan() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "authored_by": "agent_reasoning",
        "coordinate_space": "generation_region_px",
        "decision_rationale": "The Agent requested reconstruction without additional alignment movement.",
        "alignment_groups": [],
    }


def reconstruct_slide_files(
    *,
    image: Path,
    visual_analysis: Path,
    slide_id: str,
    output_dir: Path,
    output: Path,
    handoff: Path | None = None,
    design: Path | None = None,
    refinement_plan: Path | None = None,
    sam: str = "auto",
    checkpoint: Path | None = None,
    device: str = "auto",
    project: Path | None = None,
) -> dict[str, Any]:
    """Run the existing Slidecraft reconstruction logic over Agent-authored files."""

    image = image.expanduser().resolve()
    visual_analysis = visual_analysis.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output = output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    project_root = project.expanduser().resolve() if project else None
    project_config = None
    if project_root is not None:
        project_manifest_path(project_root)
        candidate = project_root / ".slidecraft" / "config.toml"
        project_config = candidate if candidate.is_file() else None
    application, config_provenance = resolve_config(project_config)
    default_project_design = project_root / ".slidecraft" / "deck_design.json" if project_root else None
    design_path = (
        design
        or (default_project_design if default_project_design and default_project_design.is_file() else None)
        or _default_design()
    ).expanduser().resolve()
    design_value = apply_application_defaults(
        _read_json(design_path),
        design_path.parent,
        project_config=project_config,
    )
    resolved_design_path = output_dir / "resolved_deck_design.json"
    _write_json(resolved_design_path, design_value)
    segmentation = application.get("segmentation", {})
    if sam == "auto" and segmentation.get("enabled") in {False, "off", "never"}:
        sam = "never"
    if device == "auto":
        device = str(segmentation.get("device", "auto"))
    if checkpoint is None and sam == "auto" and segmentation.get("checkpoint"):
        configured_checkpoint = Path(str(segmentation["checkpoint"])).expanduser()
        checkpoint = configured_checkpoint if configured_checkpoint.is_absolute() else data_root() / configured_checkpoint
    handoff_value = _normalize_handoff(
        image=image,
        design=design_value,
        supplied=_read_json(handoff.expanduser().resolve()) if handoff else None,
    )
    handoff_path = output_dir / "reconstruction_handoff.json"
    _write_json(handoff_path, handoff_value)

    semantic_value = compile_semantic_map(
        analysis=RecordedVisualAnalysis(visual_analysis),
        image_path=image,
        upstream_handoff=handoff_value,
        segmentation_mode="off" if sam == "never" else "auto",
    )
    semantic_path = output_dir / "semantic_scene.json"
    _write_json(semantic_path, semantic_value)

    measurement_dir = output_dir / "measurement"
    command = [
        sys.executable,
        str(_measurement_script()),
        str(image),
        "--semantic-map",
        str(semantic_path),
        "--upstream-handoff",
        str(handoff_path),
        "--output-dir",
        str(measurement_dir),
        "--device",
        device,
    ]
    if sam == "never":
        command.append("--no-sam")
    if checkpoint:
        command.extend(["--checkpoint", str(checkpoint.expanduser().resolve())])
    measured = subprocess.run(command, capture_output=True, text=True, check=False)
    if measured.returncode:
        raise RuntimeError(measured.stderr.strip() or measured.stdout.strip() or "Slide measurement failed")
    measured_path = measurement_dir / "slide_entities.json"
    measured_value = _read_json(measured_path)

    refinement_value = (
        _read_json(refinement_plan.expanduser().resolve())
        if refinement_plan
        else _default_refinement_plan()
    )
    contract_value = build_reconstruction_contract(
        measured_value, design_value, refinement_value
    )
    contract_path = output_dir / "reconstruction_contract.json"
    _write_json(contract_path, contract_value)

    scene_value = build_reconstruction_scene(
        measured_scene=measured_value,
        contract=contract_value,
        design=design_value,
        slide_id=slide_id,
    )
    scene_path = output_dir / "constructor_scene.json"
    _write_json(scene_path, scene_value)

    rendered = subprocess.run(
        [
            sys.executable,
            "-m",
            "slidecraft.cli",
            "render-scenes",
            "--scene",
            str(scene_path),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if rendered.returncode:
        raise RuntimeError(rendered.stderr.strip() or rendered.stdout.strip() or "PowerPoint construction failed")
    with zipfile.ZipFile(output) as archive:
        damaged = archive.testzip()
        if damaged:
            raise RuntimeError(f"PowerPoint package contains a damaged entry: {damaged}")
        slide_parts = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
        if len(slide_parts) != 1:
            raise RuntimeError(f"Single-slide reconstruction produced {len(slide_parts)} slides")
    if project_root is not None:
        workspace = ArtifactWorkspace(project_root)
        workspace.register(
            logical_key="deck/resolved_design",
            kind="deck_design_configuration",
            path=resolved_design_path,
            producer="reconstruct_slide",
            validation={"status": "passed", "source": "shared_application_configuration"},
        )
        records = (
            ("generated_image", image, "generated_image"),
            ("visual_analysis", visual_analysis, "semantic_analysis"),
            ("semantic_scene", semantic_path, "semantic_scene"),
            ("measurement", measured_path, "visual_measurement"),
            ("reconstruction_contract", contract_path, "reconstruction_contract"),
            ("constructor_scene", scene_path, "constructor_scene"),
            ("editable_pptx", output, "editable_powerpoint"),
        )
        for suffix, path, kind in records:
            workspace.register(
                logical_key=f"slides/{slide_id}/{suffix}",
                kind=kind,
                path=path,
                producer="reconstruct_slide",
                slide_id=slide_id,
                validation={"status": "passed"},
            )
    return {
        "status": "ok",
        "slide_id": slide_id,
        "powerpoint": str(output),
        "artifacts": {
            "handoff": str(handoff_path),
            "semantic_scene": str(semantic_path),
            "measured_scene": str(measured_path),
            "measurement_debug": str(measurement_dir / "debug_overlay.png"),
            "reconstruction_contract": str(contract_path),
            "constructor_scene": str(scene_path),
            "resolved_design": str(resolved_design_path),
        },
        "object_count": len(scene_value.get("objects", [])),
        "sam_mode": sam,
        "project": str(project_root) if project_root else None,
        "configuration_sources": sorted(set(config_provenance.values())),
    }
