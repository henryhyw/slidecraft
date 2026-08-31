"""User-initiated capability installation with progress and fixed trusted sources."""
from __future__ import annotations

import hashlib
import importlib
import os
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from .paths import DEFAULT_CONFIG, data_home
from .storage import read, update, write

SAM_SOURCE = "sam-2 @ git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"
SAM_CHECKPOINT = "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt"
_guard = threading.Lock()
_worker: threading.Thread | None = None


def status():
    value = read(data_home() / "install-status/sam.json", {"state": "idle"})
    if value.get("state") == "running" and (not _worker or not _worker.is_alive()):
        return {**value, "state": "interrupted", "message": "Installation was interrupted. Retry to continue."}
    if value.get("state") == "complete" and not available():
        return {
            **value,
            "state": "missing",
            "message": "SAM is not available in the Python environment running SlidePoise. Install it here to continue.",
        }
    return value


def available():
    config = read(data_home() / "config.json", read(DEFAULT_CONFIG))
    checkpoint = ((config.get("measurement") or {}).get("segmentation") or {}).get("checkpoint", "")
    if not checkpoint or not Path(checkpoint).expanduser().is_file():
        return False
    try:
        importlib.import_module("torch")
        importlib.import_module("sam2")
    except Exception:
        return False
    return True


def _progress(state, message, **extra):
    write(data_home() / "install-status/sam.json", {"state": state, "message": message, **extra})


def _install():
    log = data_home() / "install-status/sam.log"
    try:
        if sys.prefix == sys.base_prefix:
            raise RuntimeError("Start Console from the SlidePoise isolated Python environment before installing SAM.")
        _progress("running", "Installing the SAM runtime. Downloads can take several minutes.")
        environment = dict(os.environ, SAM2_BUILD_CUDA="0")
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run([sys.executable, "-m", "pip", "install", "torch>=2.5.1", "torchvision>=0.20.1", SAM_SOURCE],
                       env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=1200, check=False)
        if result.returncode:
            raise RuntimeError(f"SAM installation did not finish. Details are saved in {log}")
        _progress("running", "Downloading the SAM 2.1 Tiny model from Meta.")
        models = data_home() / "models"
        models.mkdir(parents=True, exist_ok=True)
        target = models / "sam2.1_hiera_tiny.pt"
        temporary = target.with_suffix(".download")
        digest = hashlib.sha256()
        size = 0
        try:
            with urllib.request.urlopen(SAM_CHECKPOINT, timeout=60) as response, temporary.open("wb") as stream:
                expected = int(response.headers.get("Content-Length", "0"))
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                    if size > 512 * 1024 * 1024:
                        raise ValueError("Unexpected model download size")
                if size < 1024 * 1024 or (expected and expected != size):
                    raise ValueError("The model download is incomplete")
            _progress("running", "Checking that the installed model loads correctly.")
            check = subprocess.run([sys.executable, "-c", "import sys; from sam2.build_sam import build_sam2; build_sam2('configs/sam2.1/sam2.1_hiera_t.yaml', sys.argv[1], device='cpu')", str(temporary)],
                       capture_output=True, text=True, timeout=180, check=False)
            if check.returncode:
                with log.open("a", encoding="utf-8") as stream:
                    stream.write(check.stderr)
                raise RuntimeError(f"Model verification failed. Details are saved in {log}")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        def configure(config):
            config.setdefault("measurement", {}).setdefault("segmentation", {}).update({"mode": "auto", "checkpoint": str(target), "model_config": "configs/sam2.1/sam2.1_hiera_t.yaml", "device": "auto"})
            return config
        update(data_home() / "config.json", configure, default=read(DEFAULT_CONFIG))
        write(models / "sam2.1_hiera_tiny.provenance.json", {"url": SAM_CHECKPOINT, "sha256": digest.hexdigest(), "bytes": size, "license": "Apache-2.0", "source": SAM_SOURCE})
        importlib.invalidate_caches()
        _progress("complete", "SAM is ready. It will be used automatically when useful.")
    except Exception as error:
        _progress("failed", str(error))


def start_install():
    global _worker
    with _guard:
        if _worker and _worker.is_alive():
            return status()
        _progress("running", "Preparing SAM installation.")
        _worker = threading.Thread(target=_install, name="slidepoise-sam-install", daemon=True)
        _worker.start()
        return {"state": "running", "message": "Preparing SAM installation."}


def install_and_wait():
    if available():
        _progress("complete", "SAM is ready. It will be used automatically when useful.")
        return status()
    start_install()
    _worker.join()
    return status()


def install_best_effort():
    """Install the optional enhancement when this isolated runtime can host it."""
    if available():
        return {"state": "complete", "message": "SAM is ready."}
    if sys.prefix == sys.base_prefix:
        return {"state": "skipped", "message": "SAM was skipped because setup is not running in an isolated Python environment."}
    return install_and_wait()
