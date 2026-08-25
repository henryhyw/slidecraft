"""Project-scoped ingestion for chat attachments and local user assets."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any


def _safe_name(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return stem or "asset"


def ingest_user_asset(source: Path, project_store: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Copy an accessible attachment into the project store and register provenance."""
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    usage_class = metadata.get("usage_class")
    if usage_class not in {"mandatory", "optional", "reference_only", "do_not_use"}:
        raise ValueError("usage_class must be mandatory, optional, reference_only, or do_not_use")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    project_store.mkdir(parents=True, exist_ok=True)
    destination = project_store / f"{digest[:12]}_{_safe_name(source.name)}"
    if not destination.exists():
        shutil.copy2(source, destination)
    return {
        "asset_id": metadata.get("asset_id", f"USER_{digest[:12].upper()}"),
        "original_name": source.name,
        "stored_path": str(destination.resolve()),
        "source_locator": metadata.get("source_locator", str(source)),
        "sha256": digest,
        "size_bytes": destination.stat().st_size,
        "media_type": metadata.get("media_type") or mimetypes.guess_type(source.name)[0] or "application/octet-stream",
        "usage_class": usage_class,
        "semantic_role": metadata["semantic_role"],
        "description": metadata.get("description", ""),
        "allowed_transformations": metadata.get("allowed_transformations", ["uniform_scale", "translate"]),
        "provenance": metadata.get("provenance", "user_chat_attachment"),
    }


def apply_ingested_asset_manifest(slide: dict[str, Any], base_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """Resolve an ingested manifest into canonical assets and reference-only materials."""
    manifest_value = slide.get("ingested_asset_manifest")
    if not manifest_value:
        return slide, []
    manifest_path = Path(manifest_value)
    if not manifest_path.is_absolute():
        manifest_path = (base_dir / manifest_path).resolve()
        if not manifest_path.exists():
            manifest_path = (Path.cwd() / manifest_value).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing = {item["asset_id"] for item in slide.get("user_provided_assets", [])}
    assets = list(slide.get("user_provided_assets", []))
    materials = list(slide.get("materials", []))
    notices = []
    for item in manifest.get("assets", []):
        usage = item["usage_class"]
        if usage in {"mandatory", "optional"} and item["asset_id"] not in existing:
            assets.append({
                "asset_id": item["asset_id"],
                "semantic_role": item["semantic_role"],
                "dimension_role": item.get("dimension_role", "technology_logo"),
                "name": item["original_name"],
                "description": item.get("description", ""),
                "canonical_file": item["stored_path"],
                "required_usage": usage == "mandatory",
                "mandatory": usage == "mandatory",
                "allowed_transformations": item.get("allowed_transformations", ["uniform_scale", "translate"]),
                "attachment_status": "available",
                "provenance": item.get("provenance", "user_chat_attachment"),
            })
            existing.add(item["asset_id"])
        elif usage in {"reference_only", "do_not_use"}:
            materials.append({
                "material_id": item["asset_id"],
                "modality": "image",
                "path": item["stored_path"],
                "role": item["semantic_role"],
                "description": item.get("description", ""),
                "authority": "supporting",
                "required_usage": False,
                "provenance": item.get("provenance", "user_chat_attachment"),
                "excluded_from_generation": usage == "do_not_use",
            })
        notices.append(f"Resolved ingested asset {item['asset_id']} with usage class {usage}.")
    slide["user_provided_assets"] = assets
    slide["materials"] = materials
    slide["ingested_asset_manifest_resolved_path"] = str(manifest_path)
    return slide, notices
