"""Conversation-local panel selection, shared by the browser and host Agent."""
from __future__ import annotations

import re
import uuid

from .paths import data_home
from .sessions import require_run
from .storage import ConflictError, locked, read, revision, write


def binding_path(panel_id):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", panel_id):
        raise ValueError("Invalid panel identifier")
    return data_home() / "panels" / f"{panel_id}.json"


def get(panel_id):
    path = binding_path(panel_id)
    with locked(path):
        value = read(path)
        if value is None:
            raise FileNotFoundError("Panel not found")
        return {**value, "revision": revision(path)}


def ensure(panel_id=None, run=None, host_thread_id=None):
    """The Agent may explicitly create or rebind a panel. Omitted run preserves it."""
    panel_id = panel_id or uuid.uuid4().hex
    path = binding_path(panel_id)
    root = str(require_run(run)) if run else None
    with locked(path):
        value = read(path, {"id": panel_id, "run": None})
        if root is not None:
            value["run"] = root
        if host_thread_id:
            value["host_thread_id"] = host_thread_id
        write(path, value)
        return {**value, "revision": revision(path)}


def select(panel_id, run, expected):
    """The browser can select an existing run only while this panel is unbound."""
    root = str(require_run(run))
    path = binding_path(panel_id)
    with locked(path):
        value = read(path)
        if value is None:
            raise FileNotFoundError("Panel not found")
        if value.get("run") or expected != revision(path):
            raise ConflictError("A presentation has already been selected. Continue in the conversation to change it.")
        value["run"] = root
        write(path, value)
        return {**value, "revision": revision(path)}
