"""Versioned artifact graph for agent-controlled Slidecraft workspaces."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_NAME = "artifact_manifest.json"
INTERNAL_DIRECTORY = ".slidecraft"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class ArtifactDependency:
    logical_key: str
    artifact_id: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        return {
            "logical_key": self.logical_key,
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
        }


@dataclass
class ArtifactWorkspace:
    """Persistent graph where active artifacts form the current deck snapshot.

    The host agent chooses operations. This store only records immutable revisions,
    dependency evidence, activation decisions, and freshness.
    """

    root: Path

    @property
    def manifest_path(self) -> Path:
        root = self.root.resolve()
        hidden = root / INTERNAL_DIRECTORY / MANIFEST_NAME
        legacy = root / MANIFEST_NAME
        if hidden.exists() or not legacy.exists():
            return hidden
        return legacy

    def initialize(self, *, deck_id: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        self.root = self.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / INTERNAL_DIRECTORY).mkdir(parents=True, exist_ok=True)
        if self.manifest_path.exists():
            return self.read()
        now = _now()
        manifest = {
            "schema_version": "1.0.0",
            "workspace_id": f"ws_{uuid.uuid4().hex[:12]}",
            "deck_id": deck_id,
            "created_at": now,
            "updated_at": now,
            "control_model": "agent_host",
            "artifacts": [],
            "active": {},
            "events": [],
            "metadata": metadata or {},
        }
        self._commit(manifest, "workspace_initialized", {"deck_id": deck_id})
        return manifest

    def read(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Slidecraft workspace is not initialized at {self.root.resolve()}")
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _commit(self, manifest: dict[str, Any], event: str, details: dict[str, Any]) -> None:
        manifest["updated_at"] = _now()
        manifest.setdefault("events", []).append({"event": event, "at": manifest["updated_at"], **details})
        _atomic_write(self.manifest_path, manifest)

    @staticmethod
    def _by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {record["artifact_id"]: record for record in manifest["artifacts"]}

    def _resolve_dependencies(self, manifest: dict[str, Any], logical_keys: Iterable[str]) -> list[ArtifactDependency]:
        records = self._by_id(manifest)
        dependencies = []
        for logical_key in logical_keys:
            artifact_id = manifest["active"].get(logical_key)
            if not artifact_id:
                raise KeyError(f"No active artifact for dependency {logical_key}")
            record = records[artifact_id]
            dependencies.append(ArtifactDependency(logical_key, artifact_id, record["sha256"]))
        return dependencies

    def register(
        self,
        *,
        logical_key: str,
        kind: str,
        path: Path,
        dependencies: Iterable[str] = (),
        producer: str,
        slide_id: str | None = None,
        config_sha256: str | None = None,
        provenance: dict[str, Any] | None = None,
        activate: bool = True,
        validation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        manifest = self.read()
        resolved_path = path.expanduser().resolve()
        if not resolved_path.is_file():
            raise FileNotFoundError(resolved_path)
        dependency_records = self._resolve_dependencies(manifest, dependencies)
        content_sha256 = _sha256(resolved_path)
        active_id = manifest["active"].get(logical_key)
        if activate and active_id:
            active_record = self._by_id(manifest)[active_id]
            dependency_payload = [item.as_dict() for item in dependency_records]
            if (
                active_record["kind"] == kind
                and active_record["sha256"] == content_sha256
                and active_record["dependencies"] == dependency_payload
                and active_record.get("config_sha256") == config_sha256
            ):
                return active_record
        revisions = [item["revision"] for item in manifest["artifacts"] if item["logical_key"] == logical_key]
        record = {
            "artifact_id": f"art_{uuid.uuid4().hex[:16]}",
            "logical_key": logical_key,
            "kind": kind,
            "revision": max(revisions, default=0) + 1,
            "path": str(resolved_path),
            "sha256": content_sha256,
            "size_bytes": resolved_path.stat().st_size,
            "slide_id": slide_id,
            "producer": producer,
            "created_at": _now(),
            "dependencies": [item.as_dict() for item in dependency_records],
            "config_sha256": config_sha256,
            "provenance": provenance or {},
            "validation": validation or {"status": "unvalidated"},
            "lifecycle": "active" if activate else "candidate",
        }
        if activate:
            previous = manifest["active"].get(logical_key)
            if previous:
                self._by_id(manifest)[previous]["lifecycle"] = "superseded"
            manifest["active"][logical_key] = record["artifact_id"]
        manifest["artifacts"].append(record)
        self._commit(manifest, "artifact_registered", {
            "artifact_id": record["artifact_id"],
            "logical_key": logical_key,
            "activate": activate,
        })
        return record

    def activate(self, artifact_id: str) -> dict[str, Any]:
        manifest = self.read()
        records = self._by_id(manifest)
        if artifact_id not in records:
            raise KeyError(artifact_id)
        record = records[artifact_id]
        if record["lifecycle"] == "rejected":
            raise ValueError("A rejected artifact must be restored before activation")
        previous = manifest["active"].get(record["logical_key"])
        if previous and previous != artifact_id:
            records[previous]["lifecycle"] = "superseded"
        record["lifecycle"] = "active"
        manifest["active"][record["logical_key"]] = artifact_id
        self._commit(manifest, "artifact_activated", {"artifact_id": artifact_id, "replaced": previous})
        return record

    def reject(self, artifact_id: str, *, reason: str | None = None) -> dict[str, Any]:
        manifest = self.read()
        records = self._by_id(manifest)
        if artifact_id not in records:
            raise KeyError(artifact_id)
        record = records[artifact_id]
        if manifest["active"].get(record["logical_key"]) == artifact_id:
            raise ValueError("Activate another revision before rejecting the active artifact")
        record["lifecycle"] = "rejected"
        record["rejection_reason"] = reason
        self._commit(manifest, "artifact_rejected", {"artifact_id": artifact_id, "reason": reason})
        return record

    def freshness(self, artifact_id: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        manifest = manifest or self.read()
        records = self._by_id(manifest)
        if artifact_id not in records:
            raise KeyError(artifact_id)
        record = records[artifact_id]
        reasons: list[dict[str, Any]] = []
        path = Path(record["path"])
        if not path.is_file():
            reasons.append({"code": "file_missing", "path": record["path"]})
        elif _sha256(path) != record["sha256"]:
            reasons.append({"code": "content_changed_on_disk", "path": record["path"]})
        for dependency in record["dependencies"]:
            current_id = manifest["active"].get(dependency["logical_key"])
            if current_id != dependency["artifact_id"]:
                reasons.append({
                    "code": "dependency_revision_changed",
                    "logical_key": dependency["logical_key"],
                    "expected_artifact_id": dependency["artifact_id"],
                    "active_artifact_id": current_id,
                })
                continue
            current = records.get(current_id)
            if not current or current["sha256"] != dependency["sha256"]:
                reasons.append({"code": "dependency_content_changed", "logical_key": dependency["logical_key"]})
                continue
            nested = self.freshness(current_id, manifest)
            if not nested["fresh"]:
                reasons.append({"code": "dependency_stale", "logical_key": dependency["logical_key"]})
        return {"fresh": not reasons, "reasons": reasons}

    def inspect(self, *, include_history: bool = False) -> dict[str, Any]:
        manifest = self.read()
        records = self._by_id(manifest)
        active = []
        stale_keys = []
        for logical_key, artifact_id in sorted(manifest["active"].items()):
            record = records[artifact_id]
            status = self.freshness(artifact_id, manifest)
            active.append({
                "logical_key": logical_key,
                "artifact_id": artifact_id,
                "kind": record["kind"],
                "revision": record["revision"],
                "slide_id": record["slide_id"],
                "path": record["path"],
                "freshness": status,
                "validation": record["validation"],
            })
            if not status["fresh"]:
                stale_keys.append(logical_key)
        candidates = [
            {key: record[key] for key in ("artifact_id", "logical_key", "kind", "revision", "slide_id", "path", "lifecycle")}
            for record in manifest["artifacts"]
            if record["lifecycle"] == "candidate"
        ]
        attention = []
        for item in active:
            if not item["freshness"]["fresh"]:
                attention.append({
                    "type": "recompute_stale_artifact",
                    "logical_key": item["logical_key"],
                    "artifact_id": item["artifact_id"],
                    "producer": records[item["artifact_id"]]["producer"],
                    "reasons": item["freshness"]["reasons"],
                })
            if item["validation"].get("status") in {"failed", "blocked"}:
                attention.append({
                    "type": "resolve_validation_failure",
                    "logical_key": item["logical_key"],
                    "artifact_id": item["artifact_id"],
                    "validation": item["validation"],
                })
        for item in candidates:
            attention.append({
                "type": "candidate_decision",
                "logical_key": item["logical_key"],
                "artifact_id": item["artifact_id"],
                "allowed_actions": ["accept_artifact", "reject_artifact"],
            })
        result = {
            "schema_version": "1.0.0",
            "workspace_id": manifest["workspace_id"],
            "deck_id": manifest.get("deck_id"),
            "control_model": "agent_host",
            "active_artifacts": active,
            "candidate_artifacts": candidates,
            "stale_logical_keys": stale_keys,
            "attention": attention,
            "summary": {
                "active": len(active),
                "fresh": len(active) - len(stale_keys),
                "stale": len(stale_keys),
                "candidates_awaiting_decision": len(candidates),
            },
        }
        if include_history:
            result["history"] = manifest["artifacts"]
            result["events"] = manifest["events"]
        return result
