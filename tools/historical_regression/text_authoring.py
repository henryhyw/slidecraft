"""Recover logical authored text from raster-oriented semantic text evidence."""

from __future__ import annotations

import re
from typing import Any


def authored_text(entity: dict[str, Any]) -> tuple[str, bool]:
    """Return logical text and whether authored explicit breaks were preserved."""
    if entity.get("authored_text") is not None:
        return str(entity["authored_text"]), bool(entity.get("preserve_explicit_breaks", True))

    raw = str(entity.get("text", ""))
    paragraphs = re.split(r"\n\s*\n", raw)
    normalized = []
    for paragraph in paragraphs:
        paragraph = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "-", paragraph)
        paragraph = re.sub(r"\s*\n\s*", " ", paragraph)
        paragraph = re.sub(r"[ \t]+", " ", paragraph).strip()
        normalized.append(paragraph)
    return "\n\n".join(normalized), False


def logical_paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
