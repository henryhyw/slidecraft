"""Central manager for deck state, specialist artifacts, and coherence gates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from slidecraft.providers.base import StructuredReasoningProvider
from slidecraft.runtime.artifacts import ArtifactWorkspace
from slidecraft.runtime.state import initialize_run_state

from .planning import plan_deck
from .slide_jobs import build_slide_request
from .system_layouts import build_system_scene, load_layouts


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass
class DeckManager:
    """Materialize an Agent-authored deck plan and its bounded typed artifacts."""

    run_dir: Path
    reasoning_provider: StructuredReasoningProvider

    def initialize(
        self,
        *,
        request: dict[str, Any],
        intake: dict[str, Any],
        design_system: dict[str, Any],
        system_layouts_path: Path | None = None,
    ) -> dict[str, Any]:
        self.run_dir = self.run_dir.resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if intake.get("quality", {}).get("pending_extraction_count"):
            pending = ", ".join(intake["quality"].get("pending_material_ids", []))
            raise ValueError(f"Deck planning requires source-grounded interpretation for visual materials: {pending}")
        storage_dir = self.run_dir / ".slidecraft" if (self.run_dir / "slidecraft.project.json").exists() else self.run_dir
        storage_dir.mkdir(parents=True, exist_ok=True)
        plan, validation = plan_deck(
            self.reasoning_provider,
            request=request,
            intake=intake,
            design=design_system,
        )
        _write_json(storage_dir / "deck_request.json", request)
        _write_json(storage_dir / "intake_manifest.json", intake)
        _write_json(storage_dir / "design_system_snapshot.json", design_system)
        _write_json(storage_dir / "deck_plan.json", plan)
        jobs = []
        resolved_layouts_path = system_layouts_path or Path(str(files("slidecraft.defaults").joinpath("system_slide_layouts.json")))
        layouts = load_layouts(resolved_layouts_path)
        sections = {section["section_id"]: section for section in plan["sections"]}
        for slide in plan["slides"]:
            job = {
                "schema_version": "1.0.0",
                "deck_id": plan["deck_id"],
                "slide_id": slide["slide_id"],
                "ordinal": slide["ordinal"],
                "section_id": slide["section_id"],
                "role": slide["role"],
                "route": slide["route"],
                "system_layout_id": slide.get("system_layout_id"),
                "status": "ready_for_system_render" if slide["route"] == "system_layout" else "ready_for_semantic_planning",
                "communication_job": slide["communication_job"],
                "message_title": slide["message_title"],
                "source_atoms": [atom for atom in intake["source_atoms"] if atom["atom_id"] in slide["source_atom_ids"]],
                "relationships": slide["relationships"],
                "dependencies": slide.get("dependencies", []),
                "asset_ids": slide.get("asset_ids", []),
                "terminology": slide.get("terminology", []),
                "cross_slide_requirements": slide.get("cross_slide_requirements", []),
                "design_system_snapshot": design_system,
            }
            job_path = storage_dir / "slides" / slide["slide_id"] / "job.json"
            _write_json(job_path, job)
            if job["route"] == "system_layout":
                from slidecraft.orchestration.preflight import resolve_slide_chrome

                layout_id = job["system_layout_id"]
                if layout_id not in layouts:
                    raise ValueError(f"System layout {layout_id} is unavailable")
                structural_request = build_slide_request(
                    job=job,
                    deck_request=request,
                    project_assets=request.get("project_assets", []),
                )
                resolved_chrome = (
                    resolve_slide_chrome(design_system, structural_request)
                    if design_system.get("deck_chrome", {}).get("enabled")
                    else {}
                )
                scene = build_system_scene(
                    job=job,
                    layout=layouts[layout_id],
                    design=design_system,
                    deck_context={
                        "section": sections[slide["section_id"]],
                        "sections": plan["sections"],
                        "project_name": request.get("project_name", request.get("objective", "")),
                        "metadata": request.get("metadata", ""),
                        "footer_left": request.get("footer", "Internal working draft"),
                        "resolved_chrome": resolved_chrome,
                    },
                )
                _write_json(storage_dir / "slides" / slide["slide_id"] / "system_scene.json", scene)
            jobs.append({"slide_id": slide["slide_id"], "job": str(job_path), "status": job["status"]})
        fingerprint_source = json.dumps({"request": request, "plan": plan, "design": design_system}, sort_keys=True).encode()
        manifest = {
            "schema_version": "1.0.0",
            "deck_id": plan["deck_id"],
            "run_id": self.run_dir.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "planned",
            "manager_pattern": "agent_host_with_passive_artifact_ledger",
            "fingerprint": hashlib.sha256(fingerprint_source).hexdigest(),
            "validation": validation,
            "jobs": jobs,
            "next_gate": "agent_slide_execution",
            "interaction_policy": {
                "planning_confirmation": "conversational_and_optional",
                "delegated_execution": bool(request.get("delegated_execution")),
                "workflow_state_source": "artifact_ledger",
            },
        }
        _write_json(storage_dir / "run_manifest.json", manifest)
        initialize_run_state(manifest, storage_dir / "run_state.json")
        workspace = ArtifactWorkspace(self.run_dir)
        workspace.initialize(deck_id=plan["deck_id"], metadata={"run_id": manifest["run_id"]})
        workspace.register(logical_key="deck/request", kind="deck_request", path=storage_dir / "deck_request.json", producer="plan_deck")
        workspace.register(logical_key="deck/intake", kind="intake_manifest", path=storage_dir / "intake_manifest.json", dependencies=["deck/request"], producer="plan_deck")
        workspace.register(logical_key="deck/design", kind="deck_design_configuration", path=storage_dir / "design_system_snapshot.json", producer="plan_deck")
        workspace.register(logical_key="deck/plan", kind="deck_plan", path=storage_dir / "deck_plan.json", dependencies=["deck/intake", "deck/design"], producer="plan_deck", validation={"status": "passed", **validation})
        for job in jobs:
            slide_id = job["slide_id"]
            workspace.register(
                logical_key=f"slides/{slide_id}/job",
                kind="slide_job",
                path=Path(job["job"]),
                dependencies=["deck/plan"],
                producer="plan_deck",
                slide_id=slide_id,
            )
            system_scene = storage_dir / "slides" / slide_id / "system_scene.json"
            if system_scene.exists():
                workspace.register(
                    logical_key=f"slides/{slide_id}/constructor_scene",
                    kind="constructor_scene_ir",
                    path=system_scene,
                    dependencies=[f"slides/{slide_id}/job", "deck/design"],
                    producer="system_layout",
                    slide_id=slide_id,
                )
        return manifest
