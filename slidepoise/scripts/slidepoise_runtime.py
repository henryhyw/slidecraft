#!/usr/bin/env python3
"""Thin deterministic execution wrapper for the self-contained SlidePoise Skill."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
SRC = RUNTIME / "src"
sys.path.insert(0, str(SRC))

from slidepoise.reconstruction.contract import build_reconstruction_contract  # noqa: E402
from slidepoise.reconstruction.scene import build_reconstruction_scene  # noqa: E402


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_scene_paths(scene: dict, scene_file: Path) -> dict:
    """Bind relative raster paths to a portable scene or run directory."""
    for item in scene.get("objects", []):
        value = item.get("source_path")
        if not value:
            continue
        source = Path(str(value)).expanduser()
        if source.is_absolute():
            continue
        candidates = [scene_file.parent / source, scene_file.parent.parent / source]
        resolved = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
        if resolved is None:
            raise SystemExit(f"Scene raster source does not exist relative to the scene or run root: {value}")
        item["source_path"] = str(resolved)
    return scene


def run_checked(command: list[str], *, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, text=True, capture_output=True, env=env)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout or "command failed").strip())
    if result.stdout.strip():
        print(result.stdout.strip())


def command_measure(args: argparse.Namespace) -> None:
    cmd = [sys.executable, str(RUNTIME / "scripts/measure_visual_scene.py"), str(args.image), "--semantic-map", str(args.semantic_map), "--output-dir", str(args.output_dir), "--config", str(args.config)]
    if args.upstream_handoff:
        cmd += ["--upstream-handoff", str(args.upstream_handoff)]
    if args.sam:
        cmd += ["--sam", args.sam]
    run_checked(cmd)


def command_build_contract(args: argparse.Namespace) -> None:
    measured = read(args.measured_scene)
    config = read(args.config)
    contract = build_reconstruction_contract(measured, config["design"])
    write(args.output, contract)
    print(json.dumps({"units": len(contract.get("reconstruction_units", [])), "assets": len(contract.get("canonical_asset_mappings", [])), "connectors": len(contract.get("connector_reconstruction_plans", []))}, indent=2))


def command_compile_scene(args: argparse.Namespace) -> None:
    scene = build_reconstruction_scene(
        measured_scene=read(args.measured_scene),
        contract=read(args.contract),
        design=read(args.config)["design"],
        slide_id=args.slide_id,
    )
    write(args.output, scene)
    print(json.dumps({"objects": len(scene.get("objects", [])), "slide_id": args.slide_id}, indent=2))


def node_environment() -> dict[str, str]:
    env = dict(os.environ)
    framework_home = Path(env.get("SLIDEPOISE_HOME", str(Path.home() / ".slidepoise"))).expanduser()
    local_runtime = framework_home / "node" / "node_modules"
    roots = [str(local_runtime)] if local_runtime.is_dir() else []
    npm = shutil.which("npm")
    if npm:
        root = subprocess.run([npm, "root", "-g"], text=True, capture_output=True).stdout.strip()
        if root:
            roots.append(root)
    if env.get("NODE_PATH"):
        roots.append(env["NODE_PATH"])
    if roots:
        env["NODE_PATH"] = os.pathsep.join(roots)
    return env


def command_render_pptx(args: argparse.Namespace) -> None:
    scene = resolve_scene_paths(read(args.scene), args.scene)
    config = read(args.config)
    spec = {
        "title": args.title or "SlidePoise single-slide presentation",
        "language": args.language,
        "theme": {"display_font": config["design"]["style"].get("display_font", "Georgia"), "body_font": config["design"]["style"].get("body_font", "Arial")},
        "slide": scene,
    }
    with tempfile.TemporaryDirectory(prefix="slidepoise-pptx-") as temp:
        spec_path = Path(temp) / "presentation.json"
        write(spec_path, spec)
        run_checked(["node", str(RUNTIME / "js/scene_to_pptx.mjs"), "--input", str(spec_path), "--output", str(args.output)], env=node_environment())
    print(json.dumps({"pptx": str(args.output.resolve())}, indent=2))


def command_render_preview(args: argparse.Namespace) -> None:
    env = dict(os.environ)
    font_config = getattr(args, "font_config", None)
    if font_config:
        if not font_config.is_file():
            raise SystemExit(f"Fontconfig file does not exist: {font_config}")
        env["FONTCONFIG_FILE"] = str(font_config.resolve())
    office = shutil.which("libreoffice") or shutil.which("soffice")
    if not office:
        raise SystemExit("No LibreOffice/soffice renderer is available. Use the host's native PPTX rendering capability and persist a raster if possible.")
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise SystemExit("pdftoppm is required for the packaged render-preview path. Use the host's native PPTX rendering capability instead.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source_digest = hashlib.sha256(args.pptx.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="slidepoise-render-") as temp:
        temp_path = Path(temp)
        run_checked([office, "-env:UserInstallation=" + (temp_path / "office-profile").as_uri(),
                     "--headless", "--convert-to", "pdf", "--outdir", str(temp_path), str(args.pptx.resolve())], env=env)
        pdf = temp_path / (args.pptx.stem + ".pdf")
        if not pdf.is_file():
            candidates = list(temp_path.glob("*.pdf"))
            if not candidates:
                raise SystemExit("PPTX render did not produce a PDF")
            pdf = candidates[0]
        prefix = temp_path / "slide"
        page = getattr(args, "slide_number", 1)
        if page < 1:
            raise SystemExit("Slide number must be positive")
        run_checked([pdftoppm, "-png", "-f", str(page), "-singlefile", "-r", str(args.dpi), str(pdf), str(prefix)])
        rendered = prefix.with_suffix(".png")
        if not rendered.is_file():
            raise SystemExit("PPTX render did not produce a PNG")
        if hashlib.sha256(args.pptx.read_bytes()).hexdigest() != source_digest:
            raise SystemExit("PowerPoint changed during rendering. Retry with the latest file.")
        with tempfile.NamedTemporaryFile(dir=args.output.parent, suffix=".png", delete=False) as staged:
            staged_path = Path(staged.name)
        try:
            shutil.copyfile(rendered, staged_path)
            staged_path.replace(args.output)
        finally:
            staged_path.unlink(missing_ok=True)
        write(args.output.with_suffix(".source.json"), {"source_sha256": source_digest,
              "render_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(), "slide_number": page})
    print(json.dumps({"render": str(args.output.resolve())}, indent=2))

def command_audit_text(args: argparse.Namespace) -> None:
    run_checked([sys.executable, str(RUNTIME / "scripts/audit_powerpoint_text.py"), str(args.pptx)])



def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="command", required=True)

    measure = sub.add_parser("measure")
    measure.add_argument("--image", type=Path, required=True)
    measure.add_argument("--semantic-map", type=Path, required=True)
    measure.add_argument("--output-dir", type=Path, required=True)
    measure.add_argument("--upstream-handoff", type=Path)
    measure.add_argument("--config", type=Path, required=True)
    measure.add_argument("--sam", choices=["auto", "never", "required"])
    measure.set_defaults(func=command_measure)

    contract = sub.add_parser("build-contract")
    contract.add_argument("--measured-scene", type=Path, required=True)
    contract.add_argument("--config", type=Path, required=True)
    contract.add_argument("--output", type=Path, required=True)
    contract.set_defaults(func=command_build_contract)

    compile_scene = sub.add_parser("compile-scene")
    compile_scene.add_argument("--measured-scene", type=Path, required=True)
    compile_scene.add_argument("--contract", type=Path, required=True)
    compile_scene.add_argument("--config", type=Path, required=True)
    compile_scene.add_argument("--slide-id", default="slide-01")
    compile_scene.add_argument("--output", type=Path, required=True)
    compile_scene.set_defaults(func=command_compile_scene)

    render = sub.add_parser("render-pptx")
    render.add_argument("--scene", type=Path, required=True)
    render.add_argument("--config", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--title")
    render.add_argument("--language", default="en-US")
    render.set_defaults(func=command_render_pptx)

    preview = sub.add_parser("render-preview")
    preview.add_argument("--pptx", type=Path, required=True)
    preview.add_argument("--output", type=Path, required=True)
    preview.add_argument("--dpi", type=int, default=160)
    preview.add_argument("--slide-number", type=int, default=1)
    preview.add_argument("--font-config", type=Path, help="Optional run-local Fontconfig file for the preview renderer")
    preview.set_defaults(func=command_render_preview)

    audit = sub.add_parser("audit-text")
    audit.add_argument("--pptx", type=Path, required=True)
    audit.set_defaults(func=command_audit_text)

    return root


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
