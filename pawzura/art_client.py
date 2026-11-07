"""Main-app boundary for the optional, isolated image runtime."""
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time

from .characters import DETAIL_MODEL, GenerationError
from .art_policy import VISION_MODEL, review_art_image, review_art_prompt
from .artwork import store_artwork, validate_png
from .model_jobs import serialized

TIERS = {2: ("sd15", 384, "sequential"), 4: ("sd15", 512, "model"),
         6: ("sdxl", 768, "sequential"), 8: ("sdxl", 1024, "model")}
PROGRESS_PREFIX = b"PAWZURA_PROGRESS "
PROGRESS_STAGES = frozenset({"art_loading", "art_sampling", "art_decoding", "art_scanning",
                             "art_cutting", "art_downloading", "art_runtime_tool", "art_runtime_python",
                             "art_runtime_torch", "art_runtime_packages", "art_runtime_notices", "art_rigging", "art_pose_downloading",
                             "motion_downloading", "motion_reconstructing", "motion_views", "motion_rigging", "motion_baking", "motion_validating", "motion_cached"})


def progress_event(line):
    """Only bounded counters and known codes cross the subprocess/UI boundary."""
    if len(line) > 4096 or not line.startswith(PROGRESS_PREFIX):
        return None
    try:
        raw = json.loads(line[len(PROGRESS_PREFIX):])
        if not isinstance(raw, dict) or raw.get("stage") not in PROGRESS_STAGES:
            return None
        result = {"stage": raw["stage"]}
        if "completed" in raw or "total" in raw:
            done, total = raw.get("completed"), raw.get("total")
            if type(done) is not int or type(total) is not int or not 0 <= done <= total <= 100000 or total == 0:
                return None
            result.update(completed=done, total=total)
        return result
    except (ValueError, TypeError):
        return None


def source_dir():
    from .resources import resource_path
    return resource_path("art_runtime")


def catalog():
    return json.loads((source_dir() / "catalog.json").read_text(encoding="utf-8"))


def runtime_root():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "Pawzura" / "art-runtime"


def runtime_python(root=None):
    return (root or runtime_root()) / "venv" / "Scripts" / "python.exe"


def _run(command, payload=None, timeout=1800, progress=None, cancel=None, contain=False):
    # No shell, no prompt in argv, no console window and no generated executable content.
    environment = os.environ.copy()
    environment.update(PYTHONUTF8="1", OLLAMA_HOST="127.0.0.1:11434")
    chunks, overflow = [], []
    stopped = threading.Event()

    def read_output(pipe):
        size = 0
        while data := pipe.read(65536):
            size += len(data)
            if size <= 12 * 1024 * 1024:
                chunks.append(data)
            else:
                if not overflow:
                    overflow.append(True)

    def read_progress(pipe):
        fragment = False
        while line := pipe.readline(4097):
            previous_fragment = fragment
            fragment = not line.endswith(b"\n")
            if not stopped.is_set() and not previous_fragment and not fragment and progress is not None:
                event = progress_event(line)
                if event is not None:
                    progress(event)

    process = None
    job = None
    readers = []
    writer = None
    def drain(reader, pipe):
        try:
            reader(pipe)
        finally:
            pipe.close()

    input_data = json.dumps(payload).encode() if payload is not None else b""
    def write_input(pipe):
        try:
            if input_data:
                pipe.write(input_data)
        except OSError:
            pass  # A child may fail before it reads its request.
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    try:
        process = subprocess.Popen([str(part) for part in command], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | (4 if contain and os.name == "nt" else 0))
        if contain:
            from .process_job import OwnedProcessJob
            job = OwnedProcessJob(process)
        readers = [threading.Thread(target=drain, args=(read_output, process.stdout), daemon=True),
                   threading.Thread(target=drain, args=(read_progress, process.stderr), daemon=True)]
        for reader in readers:
            reader.start()
        writer = threading.Thread(target=write_input, args=(process.stdin,), daemon=True)
        writer.start()
        deadline = time.monotonic() + timeout
        while True:
            if cancel is not None and cancel.is_set():
                stopped.set()
                raise GenerationError("art_cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                process.wait(timeout=min(.2, remaining))
                break
            except subprocess.TimeoutExpired:
                pass
    except subprocess.TimeoutExpired:
        stopped.set()
        raise GenerationError("art_timed_out") from None
    except OSError:
        stopped.set()
        raise GenerationError("art_runtime_failed") from None
    finally:
        if process is not None:
            if process.poll() is None:
                if job is not None:
                    job.terminate()
                process.kill()
                process.wait()
            if job is not None:
                try:
                    job.close()
                except OSError:
                    raise GenerationError("motion_cleanup_failed") from None
            if writer is not None:
                writer.join(timeout=.5 if stopped.is_set() else None)
            # An installer descendant can inherit a pipe. Never let that pipe
            # turn an expired wait into an unbounded UI worker hang.
            for reader, pipe in zip(readers, (process.stdout, process.stderr)):
                reader.join(timeout=.5 if stopped.is_set() else None)
                if not reader.is_alive():
                    pipe.close()
    if overflow:
        raise GenerationError("art_runtime_failed")
    if job is not None and getattr(job, "forced", False) and not stopped.is_set():
        raise GenerationError("motion_runtime_failed")
    output = b"".join(chunks)
    if process.returncode:
        try:
            code = json.loads(output).get("error")
        except (ValueError, AttributeError):
            code = None
        allowed = {"art_gpu_required", "model_memory_error", "art_output_blocked", "art_cutout_failed", "art_download_failed", "art_pose_unavailable",
                   "motion_not_prepared", "motion_download_failed", "motion_reconstruction_failed", "motion_gpu_required", "motion_pose_uncertain", "motion_runtime_failed"}
        raise GenerationError(code if code in allowed else "art_runtime_failed")
    return output


def worker(action, tier, payload=None, root=None, progress=None):
    if tier not in TIERS or type(tier) is not int:
        raise GenerationError("art_gpu_required")
    root = root or runtime_root()
    if not runtime_python(root).is_file():
        raise GenerationError("art_not_prepared")
    output = _run([runtime_python(root), source_dir() / "runner.py", action,
                   "--tier", tier, "--cache", root / "models", "--accept-model-license"], payload, progress=progress, contain=True)
    if len(output) > 12 * 1024 * 1024:
        raise GenerationError("art_runtime_failed")
    try:
        result = json.loads(output)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise GenerationError("art_runtime_failed") from None


@serialized
def prepare_artwork(tier, progress=lambda code: None, root=None):
    if type(tier) is not int or tier not in TIERS:
        raise GenerationError("art_gpu_required")
    root = root or runtime_root()
    progress("art_installing")
    _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
          "-File", source_dir() / "setup.ps1", "-RuntimeRoot", root], timeout=3600, progress=progress)
    progress("art_downloading")
    worker("prepare", tier, root=root, progress=progress)
    progress("art_review_models")
    # Fixed public model names only. Ollama must already be installed/running.
    for index, model in enumerate((DETAIL_MODEL, VISION_MODEL)):
        progress({"stage": "art_review_models", "completed": index, "total": 2})
        _run(["ollama.exe", "pull", model], timeout=3600)
    progress({"stage": "art_review_models", "completed": 2, "total": 2})


@serialized
def prepare_motion(progress=lambda code: None, root=None):
    root = root or runtime_root()
    progress("art_installing")
    _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
          "-File", source_dir() / "setup.ps1", "-RuntimeRoot", root], timeout=3600, progress=progress)
    progress("art_pose_downloading")
    worker("prepare-motion", 8, root=root, progress=progress)


@serialized
def detect_motion(spec, progress=lambda code: None, root=None):
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice
    from .artwork import load_artwork
    from .art_rig import safe_rig
    image = load_artwork(spec.get("art_id"))
    if image.isNull():
        raise GenerationError("art_pose_unavailable")
    encoded = QByteArray()
    buffer = QBuffer(encoded)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    progress("art_rigging")
    result = worker("rig", 8, {"png": base64.b64encode(bytes(encoded)).decode("ascii")}, root=root, progress=progress)
    rig = safe_rig(result.get("rig"))
    if rig is None:
        raise GenerationError("art_pose_unavailable")
    return rig


@serialized
def generate_artwork(description, tier, progress=lambda code: None, root=None, assets=None):
    progress("art_reviewing")
    prompt = review_art_prompt(description, progress=progress)
    progress("art_drawing")
    seed = secrets.randbelow(2**31)
    result = worker("generate", tier, {"prompt": prompt, "seed": seed}, root, progress=progress)
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
    from .art_rig import safe_rig
    spec = {"kind": "artwork", "source": "artwork", "art_id": digest, "art_model": result["model"],
            "seed": seed, "mouth_x": mouth_x, "mouth_y": mouth_y}
    rig = safe_rig(result.get("rig"))
    if rig is not None:
        spec["rig"] = rig
    return spec
