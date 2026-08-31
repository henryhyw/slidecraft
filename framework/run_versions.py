"""Version storage and display bindings. These operations never grant approval."""
from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime, timezone

from .sessions import require_run
from .storage import read, revision, update

STAGES = ("plan", "style", "design", "powerpoint")
PATTERNS = {
    "plan": ("work/slide-intent.json",),
    "style": ("work/resource-selection.json", "work/generation-context-sheet.png"),
    "design": ("accepted-slide.png", "work/candidate*.png"),
    "powerpoint": ("deliverables/*.pptx", "work/render.png"),
}


def signature(root, stage):
    files = sorted({p for pattern in PATTERNS[stage] for p in root.glob(pattern) if p.is_file()})
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def selections(root):
    document = read(root / "work/stage-selections.json", {})
    baselines = document.get("_baselines", {})
    return {stage: "current" if stage in baselines and signature(root, stage) != baselines[stage] else value
            for stage, value in document.items() if stage in STAGES}


def select(root, stage, version):
    root = require_run(root)
    if stage not in STAGES:
        raise ValueError("Unknown stage")
    if version != "current":
        if not re.fullmatch(r"iteration-[A-Za-z0-9_-]+", version) or not (root / "history" / version).is_dir():
            raise FileNotFoundError(version)
    def change(value):
        value[stage] = version
        baselines = value.setdefault("_baselines", {})
        for current in STAGES[STAGES.index(stage):]:
            if current != stage:
                value[current] = "previous"
            baselines[current] = signature(root, current)
        return value
    update(root / "work/stage-selections.json", change, default={})
    from . import run_events
    run_events.record(root, "stage_version_selected", "Presentation version changed", {"stage": stage, "version": version})
    return selections(root)


def archive(root):
    root = require_run(root)
    name = "iteration-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = root / "history" / name
    target.mkdir(parents=True)
    for folder in ("work", "deliverables", "uploads"):
        if (root / folder).is_dir():
            shutil.copytree(root / folder, target / folder)
    if (root / "accepted-slide.png").is_file():
        shutil.copy2(root / "accepted-slide.png", target / "accepted-slide.png")
    return {"id": name, "path": str(target)}


def publish(root, stage, expected):
    root = require_run(root)
    if stage not in STAGES or not signature(root, stage):
        raise ValueError("Publish a stage only after writing its artifacts")
    def change(value):
        value[stage] = "current"
        value.setdefault("_baselines", {}).pop(stage, None)
        return value
    target = root / "work/stage-selections.json"
    update(target, change, expected=expected, default={})
    return {"selection": selections(root), "revision": revision(target)}
