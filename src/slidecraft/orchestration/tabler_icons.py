"""Mechanical discovery and local caching for the official Tabler icon collection."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

CATALOG_TTL_SECONDS = 24 * 60 * 60
GITHUB_API = "https://api.github.com/repos/tabler/tabler-icons"
RAW_ROOT = "https://raw.githubusercontent.com/tabler/tabler-icons"


def _read_json(url: str, *, timeout: float = 8.0) -> Any:
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Slidecraft"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_bytes(url: str, *, timeout: float = 8.0) -> bytes:
    request = Request(url, headers={"User-Agent": "Slidecraft"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read(256 * 1024)
    if b"<svg" not in payload[:2048]:
        raise ValueError("The downloaded Tabler asset is not an SVG")
    return payload


def _safe_release(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError("Invalid Tabler release")
    return value


def _resolve_release(requested: str) -> str:
    if requested != "latest":
        return _safe_release(requested)
    release = _read_json(f"{GITHUB_API}/releases/latest")
    return _safe_release(str(release["tag_name"]))


def _catalog(cache_root: Path, requested_release: str) -> dict[str, Any]:
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_path = cache_root / "catalog.json"
    if cache_path.exists() and time.time() - cache_path.stat().st_mtime < CATALOG_TTL_SECONDS:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if requested_release == "latest" or cached.get("release") == requested_release:
            return cached
    release = _resolve_release(requested_release)
    tree = _read_json(f"{GITHUB_API}/git/trees/{quote(release, safe='')}?recursive=1")
    names = sorted(
        Path(item["path"]).stem
        for item in tree.get("tree", [])
        if item.get("type") == "blob" and re.fullmatch(r"icons/outline/[a-z0-9-]+\.svg", item.get("path", ""))
    )
    if not names:
        raise ValueError("The Tabler icon catalog did not contain outline SVGs")
    catalog = {
        "schema_version": "1.0.0",
        "provider": "Tabler Icons",
        "release": release,
        "source": f"https://github.com/tabler/tabler-icons/tree/{release}/icons/outline",
        "icons": names,
    }
    cache_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return catalog


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _rank(query: str, names: list[str]) -> list[tuple[int, str, list[str]]]:
    query_tokens = _tokens(query)
    ranked = []
    for name in names:
        name_tokens = _tokens(name)
        matched = sorted(query_tokens & name_tokens)
        score = 4 * len(matched)
        normalized = name.replace("-", " ")
        if f" {normalized} " in f" {query.lower()} ":
            score += 12
        if any(token and token in name_tokens for token in query_tokens):
            score += 1
        ranked.append((score, name, matched))
    return sorted(ranked, key=lambda item: (-item[0], item[1]))


def retrieve_tabler_candidates(
    *,
    query: str,
    library_root: Path,
    release: str = "latest",
    limit: int = 8,
) -> dict[str, Any]:
    """Find matching official icons and cache their canonical SVG files locally."""
    cache_root = library_root / ".slidecraft-remote" / "tabler"
    catalog = _catalog(cache_root, release)
    destination = library_root / "downloaded" / "tabler" / catalog["release"]
    destination.mkdir(parents=True, exist_ok=True)
    candidates = []
    for score, name, matched in _rank(query, catalog["icons"]):
        if len(candidates) >= limit:
            break
        if score <= 0:
            continue
        target = destination / f"{name}.svg"
        source_url = f"{RAW_ROOT}/{catalog['release']}/icons/outline/{name}.svg"
        if not target.exists():
            target.write_bytes(_read_bytes(source_url))
        candidates.append({
            "icon_id": name,
            "asset_id": f"TABLER_OUTLINE_{name.upper().replace('-', '_')}",
            "score": score,
            "matched_concepts": matched,
            "description": name.replace("-", " "),
            "file": str(target.relative_to(library_root)),
            "canonical_file": str(target.resolve()),
            "provenance": "official_tabler_download",
            "source_url": source_url,
            "provider_release": catalog["release"],
        })
    return {
        "provider": "Tabler Icons",
        "release": catalog["release"],
        "source": catalog["source"],
        "candidates": candidates,
    }
