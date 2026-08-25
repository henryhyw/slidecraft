from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from slidecraft.intake import normalize_deck_intake


def test_path_only_material_is_recorded_without_content_interpretation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        presentation = root / "evidence.pptx"
        presentation.write_bytes(b"deliberately not an Office package")
        request = {
            "deck_id": "demo",
            "materials": [{"material_id": "PPTX_1", "modality": "presentation", "path": str(presentation)}],
        }

        intake = normalize_deck_intake(request, root)

    assert intake["materials"][0]["path"] == str(presentation.resolve())
    assert intake["materials"][0]["size_bytes"] == len(b"deliberately not an Office package")
    assert intake["materials"][0]["agent_content_present"] is False
    assert intake["materials"][0]["sha256"]
    assert intake["source_atoms"] == []
    assert intake["quality"]["path_only_material_count"] == 1
    assert "planning_ready" not in intake["quality"]


def test_agent_authored_material_content_is_preserved_as_source_evidence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        image = root / "diagram.png"
        image.write_bytes(b"source bytes")
        interpretation = {
            "source_grounded_interpretation": "Three stages converge on one outcome.",
            "exact_labels": ["Input", "Analysis", "Outcome"],
        }
        request = {
            "deck_id": "demo",
            "materials": [{
                "material_id": "VISUAL_1",
                "modality": "image",
                "path": str(image),
                "content": interpretation,
                "authority": "authoritative",
                "required_usage": True,
            }],
        }

        intake = normalize_deck_intake(request, root)

    atom = intake["source_atoms"][0]
    assert atom["value"] == interpretation
    assert atom["required_usage"] is True
    assert atom["authority"] == "authoritative"
    assert intake["materials"][0]["path"] == str(image.resolve())


def test_explicit_agent_authored_source_atoms_are_preserved() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "notes.txt"
        source.write_text("raw material", encoding="utf-8")
        authored_atom = {
            "atom_id": "FACT_001",
            "material_id": "NOTES_1",
            "locator": "paragraph:2",
            "modality": "structured_text",
            "value": {"claim": "Operating cost is primarily model usage."},
            "authority": "authoritative",
            "required_usage": False,
            "provenance": "agent_source_analysis",
        }
        request = {
            "deck_id": "demo",
            "materials": [{"material_id": "NOTES_1", "modality": "document", "path": str(source)}],
            "source_atoms": [authored_atom],
        }

        intake = normalize_deck_intake(request, root)

    assert intake["source_atoms"] == [authored_atom]


def test_source_atom_must_reference_a_known_material() -> None:
    request = {
        "deck_id": "demo",
        "materials": [],
        "source_atoms": [{
            "atom_id": "FACT_001",
            "material_id": "MISSING",
            "locator": "paragraph:1",
            "modality": "text",
            "value": "Claim",
            "authority": "supporting_evidence",
            "required_usage": False,
        }],
    }
    with pytest.raises(ValueError, match="unknown material"):
        normalize_deck_intake(request, Path.cwd())


def test_constraint_classification_must_be_agent_authored() -> None:
    with pytest.raises(TypeError, match="Agent-authored records"):
        normalize_deck_intake({"deck_id": "demo", "constraints": ["Use a table"]}, Path.cwd())

    intake = normalize_deck_intake({
        "deck_id": "demo",
        "constraints": [{
            "text": "Use a table for the cost comparison.",
            "strength": "hard",
            "classification_source": "agent_reasoning_from_user_request",
        }],
    }, Path.cwd())
    assert intake["constraint_register"][0]["strength"] == "hard"
    assert intake["constraint_register"][0]["classification_source"] == "agent_reasoning_from_user_request"
