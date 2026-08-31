"""Transparent workflow activity authored by the host Agent.

This module records what is happening. It never decides whether work is valid,
approved, or visually acceptable.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .sessions import require_run
from .storage import read, revision, update


STEPS = {
    "understand_request": ("plan", "Understanding your goal", "Clarifying what this presentation needs to say."),
    "shape_story": ("plan", "Shaping the story", "Organizing the message, evidence, and reading order."),
    "plan_review": ("plan", "Reviewing the direction", "Checking the plan against what you want to communicate."),
    "resolve_style": ("style", "Setting the visual direction", "Applying the selected profile to this presentation."),
    "inspect_user_assets": ("style", "Reviewing your assets", "Checking how your images, logos, and source files can support the slide."),
    "retrieve_references": ("style", "Finding references", "Gathering useful visual references and public assets."),
    "assemble_context": ("style", "Bringing the direction together", "Combining the selected style, references, and assets."),
    "resource_review": ("style", "Reviewing style and assets", "Checking the visual direction and selected materials with you."),
    "prepare_generation": ("design", "Preparing the design", "Turning the approved direction into clear design instructions."),
    "generate_design": ("design", "Creating the design", "Creating the proposed slide from the approved message and visual direction."),
    "design_review": ("design", "Reviewing the design", "Checking hierarchy, composition, legibility, and visual fit."),
    "semantic_mapping": ("design", "Understanding the design", "Identifying meaningful regions that need to remain editable."),
    "relationship_mapping": ("design", "Mapping relationships", "Capturing groups, alignment, flow, and connections between elements."),
    "measure_geometry": ("design", "Measuring the design", "Measuring boundaries, colors, and placement for reconstruction."),
    "measurement_review": ("design", "Reviewing the measurements", "Checking the measured structure against the approved design."),
    "build_contract": ("powerpoint", "Preparing editable objects", "Defining the text, shapes, images, and connections to build."),
    "reconstruct": ("powerpoint", "Building the PowerPoint", "Recreating the slide with editable PowerPoint objects."),
    "render_preview": ("powerpoint", "Rendering the preview", "Showing how the current PowerPoint looks."),
    "compare": ("powerpoint", "Comparing with the design", "Checking the editable slide against the approved design."),
    "refine": ("powerpoint", "Refining the slide", "Correcting the most important visual and structural differences."),
    "final_review": ("powerpoint", "Reviewing the final slide", "Checking the finished slide for any remaining visual problem."),
    "deliver": ("powerpoint", "Preparing your files", "Preparing the editable slide and final preview."),
}
STATUSES = {"running", "waiting_for_user", "complete", "paused", "failed"}


def path(root):
    return require_run(root) / "work/activity.json"


def snapshot(root):
    target = path(root)
    value = read(target, {"current": None, "entries": []})
    value["revision"] = revision(target)
    # Display current product copy without rewriting saved activity or user messages.
    for entry in [value.get("current"), *value.get("entries", [])]:
        if entry and entry.get("step") in STEPS:
            _, entry["label"], entry["purpose"] = STEPS[entry["step"]]
    value["steps"] = [
        {"id": key, "stage": stage, "label": label, "purpose": purpose}
        for key, (stage, label, purpose) in STEPS.items()
    ]
    return value


def record(root, step, status, message=""):
    if step not in STEPS:
        raise ValueError(f"Unknown workflow step: {step}")
    if status not in STATUSES:
        raise ValueError(f"Unknown activity status: {status}")
    stage, label, purpose = STEPS[step]
    now = datetime.now(timezone.utc).isoformat()
    entry = {"id": uuid.uuid4().hex, "step": step, "stage": stage, "label": label,
             "purpose": purpose, "status": status, "message": message.strip(), "updated_at": now}

    def change(value):
        entries = value.get("entries", [])
        entries.append(entry)
        value["entries"] = entries[-120:]
        value["current"] = entry
        return value

    update(path(root), change, default={"current": None, "entries": []})
    return snapshot(root)
