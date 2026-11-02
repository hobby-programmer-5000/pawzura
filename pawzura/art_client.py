"""Main-app boundary for the optional, isolated image runtime."""
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from .characters import DETAIL_MODEL, GenerationError
from .art_policy import VISION_MODEL, review_art_image, review_art_prompt
from .artwork import store_artwork, validate_png

TIERS = {2: ("sd15", 384, "sequential"), 4: ("sd15", 512, "model"),
         6: ("sdxl", 768, "sequential"), 8: ("sdxl", 1024, "model")}


def source_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "art_runtime"
    return Path(__file__).resolve().parent.parent / "art_runtime"


def catalog():
    return json.loads((source_dir() / "catalog.json").read_text(encoding="utf-8"))


def runtime_root():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "Pawzura" / "art-runtime"


def runtime_python(root=None):
    return (root or runtime_root()) / "venv" / "Scripts" / "python.exe"


def _run(command, payload=None, timeout=1800):
    # No shell, no prompt in argv, no console window and no generated executable content.
    environment = os.environ.copy()
    environment.update(PYTHONUTF8="1", OLLAMA_HOST="127.0.0.1:11434")
    try:
        result = subprocess.run([str(part) for part in command],
                                input=json.dumps(payload).encode() if payload is not None else None,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout,
                                env=environment,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise GenerationError("art_runtime_failed") from None
    if result.returncode:
        try:
            code = json.loads(result.stdout).get("error")
        except (ValueError, AttributeError):
            code = None
        allowed = {"art_gpu_required", "model_memory_error", "art_output_blocked", "art_cutout_failed", "art_download_failed"}
        raise GenerationError(code if code in allowed else "art_runtime_failed")
    return result.stdout


def worker(action, tier, payload=None, root=None):
    if tier not in TIERS or type(tier) is not int:
        raise GenerationError("art_gpu_required")
    root = root or runtime_root()
    if not runtime_python(root).is_file():
        raise GenerationError("art_not_prepared")
    output = _run([runtime_python(root), source_dir() / "runner.py", action,
                   "--tier", tier, "--cache", root / "models", "--accept-model-license"], payload)
    if len(output) > 12 * 1024 * 1024:
        raise GenerationError("art_runtime_failed")
    try:
        result = json.loads(output)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise GenerationError("art_runtime_failed") from None


def prepare_artwork(tier, progress=lambda code: None, root=None):
    if type(tier) is not int or tier not in TIERS:
        raise GenerationError("art_gpu_required")
    root = root or runtime_root()
    progress("art_installing")
    _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
          "-File", source_dir() / "setup.ps1", "-RuntimeRoot", root], timeout=3600)
    progress("art_downloading")
    worker("prepare", tier, root=root)
    progress("art_review_models")
    # Fixed public model names only. Ollama must already be installed/running.
    for model in (DETAIL_MODEL, VISION_MODEL):
        _run(["ollama.exe", "pull", model], timeout=3600)


def generate_artwork(description, tier, progress=lambda code: None, root=None, assets=None):
    progress("art_reviewing")
    prompt = review_art_prompt(description)
    progress("art_drawing")
    seed = secrets.randbelow(2**31)
    result = worker("generate", tier, {"prompt": prompt, "seed": seed}, root)
    try:
        data = base64.b64decode(result["png"], validate=True)
        validate_png(data)
        if result.get("model") != TIERS[tier][0] or result.get("seed") != seed:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise GenerationError("art_runtime_failed") from None
    progress("art_checking")
    mouth_x, mouth_y = review_art_image(data)
    digest = store_artwork(data, assets)
    return {"kind": "artwork", "source": "artwork", "art_id": digest, "art_model": result["model"],
            "seed": seed, "mouth_x": mouth_x, "mouth_y": mouth_y}
