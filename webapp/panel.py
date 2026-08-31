"""Read-only, session-bound presentation of host-authored workflow artifacts.

File presence is a display fact. It never grants approval or marks a stage done.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlencode

from framework.storage import read, write, revision
from framework.paths import SKILL_ROOT
from framework import run_activity, run_events, run_versions

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_preview_jobs = {}
_preview_lock = threading.Lock()


def preview_source(root):
    sources = sorted((root / "deliverables").glob("*.pptx"))
    return next((p for p in sources if p.name == "slide.pptx"), sources[0] if sources else None)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_preview(root):
    """Render a local deliverable without a quality or approval decision."""
    root = root.resolve()
    source = preview_source(root)
    if source is None:
        raise FileNotFoundError("No PowerPoint deliverable yet")
    source = source.resolve()
    if root not in source.parents:
        raise ValueError("The PowerPoint must be inside this run")
    version = source.stat().st_mtime_ns
    key = str(root)
    with _preview_lock:
        existing = _preview_jobs.get(key, {})
        if existing.get("state") == "running":
            return dict(existing)
        _preview_jobs[key] = {"state": "running", "source_version": version}
    def render():
        try:
            with tempfile.TemporaryDirectory(prefix="slidepoise-panel-preview-") as directory:
                temp = Path(directory)
                frozen = temp / source.name
                shutil.copyfile(source, frozen)
                source_digest = digest(frozen)
                rendered = temp / "render.png"
                result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts/slidepoise_runtime.py"),
                    "render-preview", "--pptx", str(frozen), "--output", str(rendered)],
                    capture_output=True, text=True, timeout=180, check=False)
                if result.returncode or not rendered.is_file():
                    raise RuntimeError("A PowerPoint renderer is unavailable or could not render this file. The PPTX remains available to download.")
                if not source.is_file() or digest(source) != source_digest or source.stat().st_mtime_ns != version:
                    value = {"state": "stale", "source_version": version}
                else:
                    destination = root / "work/render.png"
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    # Stage beside the destination so replacement is atomic across filesystems.
                    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".png", delete=False) as output:
                        staged = Path(output.name)
                    try:
                        shutil.copyfile(rendered, staged)
                        staged.replace(destination)
                    finally:
                        staged.unlink(missing_ok=True)
                    write(destination.with_suffix(".source.json"), {"source_sha256": source_digest,
                          "render_sha256": digest(destination), "slide_number": 1})
                    value = {"state": "ready", "source_version": version}
        except Exception as error:
            value = {"state": "failed", "source_version": version, "message": str(error)}
        with _preview_lock:
            _preview_jobs[key] = value
    threading.Thread(target=render, daemon=True, name="slidepoise-preview").start()
    return {"state": "running", "source_version": version}


def document(root, relative):
    try:
        return read(root / relative, {})
    except (OSError, ValueError):
        return {}


def file_record(root: Path, path: Path, label: str = ""):
    path = path.resolve()
    if root not in path.parents or not path.is_file():
        return None
    stat = path.stat()
    relative = str(path.relative_to(root))
    return {"path": relative, "name": path.name, "label": label or path.stem.replace("-", " "),
            "url": "/api/artifact?" + urlencode({"run": str(root), "path": relative, "v": stat.st_mtime_ns}),
            "modified": stat.st_mtime, "version": stat.st_mtime_ns, "size": stat.st_size, "image": path.suffix.lower() in IMAGE_SUFFIXES}


def resource_file(root, group, index):
    resources = document(root, "work/resource-selection.json") or document(root, "work/resource-selection.draft.json")
    if group not in {"selected_assets", "selected_visual_references", "selected_components"}:
        raise ValueError("Unknown resource group")
    item = resources.get(group, [])[int(index)]
    value = item.get("preview_file") or item.get("canonical_file") or item.get("path")
    if not value:
        raise FileNotFoundError("This selection has no display file")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    if path.suffix.lower() not in IMAGE_SUFFIXES or not path.is_file():
        raise FileNotFoundError("The selected visual is unavailable")
    return path.resolve()


def snapshot(root: Path):
    root = root.resolve()
    intent = document(root, "work/slide-intent.json")
    resources = document(root, "work/resource-selection.json") or document(root, "work/resource-selection.draft.json")
    records = document(root, "work/human-approvals.json")
    presentation = document(root, "work/panel.json")
    metadata = document(root, "session.json")
    result = {"path": str(root), "name": metadata.get("name", root.name), "requirements": metadata.get("requirements", ""),
              "intent": intent, "approvals": records, "presentation": presentation, "resources": [],
              "stages": [], "downloads": [], "developer": [], "materials": [],
              "activity": run_activity.snapshot(root), "pending_events": run_events.pending(root)}
    result["settings_revisions"] = {name: revision(root / name) for name in
                                    ("session-overrides.json", "work/session-defaults.json")}
    def image(relative, label):
        return file_record(root, root / relative, label)
    for group, label in (("selected_visual_references", "Visual reference"), ("selected_assets", "Selected asset"), ("selected_components", "Component")):
        for index, item in enumerate(resources.get(group, [])):
            try:
                path = resource_file(root, group, index)
                url = "/api/run-resource?" + urlencode({"run": str(root), "group": group, "index": index, "v": path.stat().st_mtime_ns})
            except (FileNotFoundError, ValueError, IndexError):
                url = None
            result["resources"].append({"id": item.get("id") or item.get("asset_id") or item.get("component_id"),
                "name": item.get("name") or item.get("role") or item.get("id") or item.get("asset_id") or label,
                "kind": label, "reason": item.get("reason") or item.get("generation_description", ""), "url": url,
                "variant": item.get("style_variant"), "source": item.get("source", "")})
    for path in sorted((root / "uploads").glob("*")):
        entry = file_record(root, path)
        if entry:
            result["materials"].append(entry)
    candidates = sorted((root / "work").glob("candidate*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    accepted = image("accepted-slide.png", "Accepted design")
    candidate = image(str(candidates[0].relative_to(root)), "Generated design") if candidates else None
    current_design = candidate if candidate and (not accepted or candidate["version"] > accepted["version"]) else accepted
    render = image("work/render.png", "PowerPoint render")
    context = image("work/generation-context-sheet.png", "Retrieved design context")
    comparison = image("work/reconstruction-comparison.png", "Design and reconstruction")
    for path in sorted((root / "deliverables").glob("*")):
        if path.suffix.lower() in {".pptx", ".pdf", ".png"}:
            entry = file_record(root, path)
            if entry:
                result["downloads"].append(entry)
    source = preview_source(root)
    pptx = file_record(root, source) if source else None
    result["preview_source"] = pptx
    if render:
        binding = document(root, "work/render.source.json")
        render["may_be_older_than_pptx"] = bool(pptx and (
            binding.get("source_sha256") != digest(source) if binding else pptx["modified"] > render["modified"]))
    with _preview_lock:
        result["preview_job"] = dict(_preview_jobs.get(str(root), {}))
    result["stages"] = [
        {"id": "plan", "title": "Plan", "has_content": bool(intent)},
        {"id": "style", "title": "Style & Assets", "context": context,
         "style_context": resources.get("style_context"), "style_direction": resources.get("style_direction"),
         "has_content": bool(resources or result["materials"] or context)},
        {"id": "design", "title": "Design & Analysis", "image": current_design, "context": context,
         "has_content": bool(accepted or candidate)},
        {"id": "powerpoint", "title": "PowerPoint", "image": render, "comparison": comparison,
         "has_content": bool(render or result["downloads"])},
    ]
    result["versions"] = []
    for folder in sorted((root / "history").glob("iteration-*")):
        version = {"id": folder.name, "label": folder.name.replace("iteration-", "Version "), "stages": {}}
        for stage, names in {"plan": ["slide-intent.json"], "style": ["resource-selection.json", "generation-context-sheet.png"],
                             "design": ["accepted-slide.png", "candidate*.png", "semantic-map*.json"],
                             "powerpoint": ["render.png", "slide.pptx"]}.items():
            paths = {path for name in names for base in (folder, folder / "work", folder / "deliverables")
                     for path in base.glob(name) if path.is_file()}
            files = [file_record(root, path) for path in sorted(paths)]
            files = [item for item in files if item]
            for item in files:
                source = root / item["path"]
                if source.suffix.lower() == ".json":
                    item["data"] = read(source, {})
            if files:
                version["stages"][stage] = files
        if version["stages"]:
            result["versions"].append(version)
    result["stage_selection"] = run_versions.selections(root)
    result["selection_revision"] = revision(root / "work/stage-selections.json")
    developer_files = [
        ("slide-intent.json", "Planning details", "The agreed message and evidence for this slide.", "plan"),
        ("human-approvals.json", "Review history", "The decisions that allowed work to move between major stages.", "review"),
        ("resource-selection.json", "Selected design resources", "The references and assets chosen to support this design.", "generation"),
        ("generation-context-sheet.png", "Design context", "The visual material supplied to design generation.", "generation"),
        ("generation-prompt.txt", "Image-generation prompt", "The exact high-level prompt used to create the design.", "generation"),
        ("generation-brief.md", "Generation instructions", "The structured design direction accompanying the prompt.", "generation"),
        ("generation-review.json", "Design review", "Visual observations from the design review.", "review"),
        ("semantic-map.active.json", "Semantic groups and relationships", "Ownership, grouping, flow, and roles within the design.", "understanding"),
        ("semantic-map-evidence.json", "Semantic evidence", "Evidence used to support the semantic interpretation.", "understanding"),
        ("reconstruction-handoff.json", "Reconstruction handoff", "The design intent that must survive editable reconstruction.", "understanding"),
        ("measurement/debug_overlay.png", "Measured boundaries", "OpenCV measurement evidence overlaid on the accepted design.", "measurement"),
        ("measurement/slide_entities.json", "Measured objects", "Pixel geometry, colors, and boundary measurements used by reconstruction.", "measurement"),
        ("measurement-comparison.png", "Measurement comparison", "A visual check of the interpreted geometry against the design.", "measurement"),
        ("measurement-review.json", "Measurement review", "Visual observations alongside the pixel measurements.", "review"),
        ("reconstruction-contract.json", "PowerPoint construction contract", "The editable objects and relationships to construct.", "reconstruction"),
        ("constructor-scene.json", "Native object scene", "The concrete PowerPoint object scene produced for construction.", "reconstruction"),
        ("reconstruction-review.json", "PowerPoint visual review", "Visual observations from the editable slide review.", "review"),
        ("release-evidence.json", "Release evidence", "The final checks and supporting evidence.", "review"),
    ]
    for relative, label, purpose, group in developer_files:
        entry = image("work/" + relative, label)
        if entry:
            if relative.endswith(".json"):
                entry["data"] = document(root, "work/" + relative)
            elif relative.endswith((".md", ".txt")):
                entry["text"] = (root / "work" / relative).read_text(encoding="utf-8")[:100000]
            result["developer"].append(entry)
            entry["purpose"] = purpose
            entry["group"] = group
    result["revision"] = hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()
    return result


def select_version(root, stage, version):
    return run_versions.select(root, stage, version)
