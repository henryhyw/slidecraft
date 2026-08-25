"""Capability-oriented installation diagnostics."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from slidecraft.runtime.powerpoint import powerpoint_is_authorized


def _module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def collect_diagnostics(checkpoint: Path | None = None) -> dict[str, Any]:
    torch_record: dict[str, Any] = {"installed": _module("torch")}
    if torch_record["installed"]:
        import torch

        torch_record.update(
            version=torch.__version__,
            mps_built=bool(torch.backends.mps.is_built()),
            mps_available=bool(torch.backends.mps.is_available()),
        )
    powerpoint_path = Path("/Applications/Microsoft PowerPoint.app")
    diagnostics = {
        "slidecraft": {"python": sys.version.split()[0], "platform": platform.platform()},
        "required": {
            "pillow": _module("PIL"),
            "jsonschema": _module("jsonschema"),
        },
        "measurement": {
            "opencv": _module("cv2"),
            "tesseract_binary": shutil.which("tesseract"),
        },
        "segmentation": {
            "sam2": _module("sam2"),
            "torch": torch_record,
            "checkpoint": str(checkpoint.resolve()) if checkpoint else None,
            "checkpoint_exists": checkpoint.exists() if checkpoint else None,
            "policy": "optional_lazy_local_worker",
        },
        "providers": {
            "openai_python": _module("openai"),
            "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
            "host_file_bridge": True,
        },
        "construction": {
            "node": shutil.which("node"),
            "microsoft_powerpoint_mac": powerpoint_path.exists(),
            "powerpoint_automation_authorized": powerpoint_is_authorized(),
            "permission_policy": "explicit_setup_only",
        },
    }
    diagnostics["ready_for_host_mode"] = all(diagnostics["required"].values()) and diagnostics["measurement"]["opencv"]
    diagnostics["ready_for_openai_mode"] = diagnostics["ready_for_host_mode"] and diagnostics["providers"]["openai_python"] and diagnostics["providers"]["openai_api_key_present"]
    return diagnostics
