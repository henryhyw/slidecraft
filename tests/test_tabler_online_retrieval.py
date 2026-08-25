from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from slidecraft.configuration import resolve_config
from slidecraft.orchestration.icon_retrieval import search_icons
from slidecraft.orchestration.tabler_icons import retrieve_tabler_candidates


def test_online_icon_retrieval_is_enabled_by_default() -> None:
    with tempfile.TemporaryDirectory() as directory, patch.dict(
        os.environ, {"SLIDECRAFT_DATA_DIR": str(Path(directory) / "data")}
    ):
        config, _ = resolve_config()
    assert config["resources"]["icons"]["allow_online_retrieval"] is True
    assert config["resources"]["icons"]["provider"] == "tabler"


def test_tabler_candidates_are_downloaded_as_canonical_svg_files() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        catalog = {
            "release": "v3.46.0",
            "source": "https://github.com/tabler/tabler-icons/tree/v3.46.0/icons/outline",
            "icons": ["chart-bar", "hierarchy", "photo"],
        }
        with patch("slidecraft.orchestration.tabler_icons._catalog", return_value=catalog), patch(
            "slidecraft.orchestration.tabler_icons._read_bytes",
            return_value=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        ):
            result = retrieve_tabler_candidates(query="hierarchy diagram", library_root=root, limit=2)

        assert result["candidates"][0]["icon_id"] == "hierarchy"
        assert Path(result["candidates"][0]["canonical_file"]).is_file()
        assert result["candidates"][0]["provenance"] == "official_tabler_download"


def test_icon_search_uses_local_only_when_online_retrieval_is_disabled() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "idea.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        result = search_icons(
            root,
            [{"semantic_role": "idea", "purpose": "idea", "requirement": "optional"}],
            online_policy={"allow_online_retrieval": False},
        )
    assert result["search_scope"] == "local_only"
    assert result["online_retrieval"]["status"] == "disabled"
    assert result["candidate_sets"][0]["candidates"][0]["provenance"] == "local_icon_collection"


def test_icon_search_combines_online_candidates_without_transferring_the_decision() -> None:
    remote = {
        "release": "v3.46.0",
        "source": "https://github.com/tabler/tabler-icons/tree/v3.46.0/icons/outline",
        "candidates": [{
            "icon_id": "bulb",
            "asset_id": "TABLER_OUTLINE_BULB",
            "score": 10,
            "matched_concepts": ["idea"],
            "description": "bulb",
            "file": "downloaded/tabler/v3.46.0/bulb.svg",
            "canonical_file": "/tmp/bulb.svg",
            "provenance": "official_tabler_download",
            "source_url": "https://example.invalid/bulb.svg",
            "provider_release": "v3.46.0",
        }],
    }
    with tempfile.TemporaryDirectory() as directory, patch(
        "slidecraft.orchestration.tabler_icons.retrieve_tabler_candidates", return_value=remote
    ):
        result = search_icons(
            Path(directory),
            [{"semantic_role": "idea", "purpose": "idea", "requirement": "optional"}],
            online_policy={"allow_online_retrieval": True, "provider": "tabler"},
        )
    assert result["decision_owner"] == "host_agent"
    assert result["search_scope"] == "local_and_online"
    assert result["candidate_sets"][0]["candidates"][0]["icon_id"] == "bulb"
