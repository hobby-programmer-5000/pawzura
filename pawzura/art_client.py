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
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

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
                             "art_review_models",
                             "motion_downloading", "motion_reconstructing", "motion_views", "motion_refining", "motion_rigging", "motion_baking", "motion_validating", "motion_cached"})


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
        for key in ("item_name", "model_name", "status_text"):
            val = raw.get(key)
            if isinstance(val, str) and 0 < len(val) <= 128:
                result[key] = val
        for key in ("bytes_completed", "bytes_total"):
            val = raw.get(key)
            if type(val) is int and 0 <= val <= 200 * 1024 * 1024 * 1024:
                result[key] = val
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


def model_friendly_name(model_id):
    if "Qwen2.5-1.5B" in model_id or "qwen2.5:1.5b" in model_id:
        return "Qwen2.5 1.5B"
    if "qwen3-vl" in model_id:
        return "Qwen3-VL 2B"
    return model_id.split("/")[-1].split(":")[0]


def _pull_ollama_model(model, index, total, progress):
    """Pull an Ollama model using local HTTP streaming API with live byte and percent reporting.
    Falls back to subprocess ollama.exe pull if the local API is unreachable."""
    friendly = model_friendly_name(model)
    progress({
        "stage": "art_review_models",
        "completed": index,
        "total": total,
        "model_name": friendly,
        "status_text": "connecting",
    })

    url = "http://127.0.0.1:11434/api/pull"
    payload = json.dumps({"model": model, "stream": True}).encode("utf-8")
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})
    opener = build_opener(ProxyHandler({}))

    pulled_via_http = False
    try:
        with opener.open(req, timeout=120) as resp:
            max_total = 0
            last_report = 0.0
            last_completed = -1
            for raw_line in resp:
                if not raw_line:
                    continue
                try:
                    data = json.loads(raw_line.decode("utf-8", errors="replace"))
                except Exception:
                    continue
                pulled_via_http = True
                status = data.get("status", "")
                tot = data.get("total")
                done = data.get("completed")

                if tot and isinstance(tot, int) and tot > max_total:
                    max_total = tot

                now = time.monotonic()
                reported_done = done if (done and tot and tot >= max_total) else (max_total if max_total > 0 and status in ("verifying sha256 digest", "writing manifest", "success") else None)
                reported_tot = max_total if max_total > 0 else (tot if isinstance(tot, int) else None)

                should_report = (
                    now - last_report >= 0.15 or
                    status == "success" or
                    (reported_done is not None and reported_done != last_completed and reported_tot and (reported_done == reported_tot or abs(reported_done - (last_completed or 0)) >= 10 * 1024 * 1024))
                )
                if should_report:
                    event = {
                        "stage": "art_review_models",
                        "completed": index,
                        "total": total,
                        "model_name": friendly,
                        "status_text": status,
                    }
                    if reported_tot is not None:
                        event["bytes_total"] = reported_tot
                    if reported_done is not None:
                        event["bytes_completed"] = reported_done
                    progress(event)
                    last_report = now
                    if reported_done is not None:
                        last_completed = reported_done
    except Exception:
        if not pulled_via_http:
            _run(["ollama.exe", "pull", model], timeout=3600)

    progress({
        "stage": "art_review_models",
        "completed": index + 1,
        "total": total,
        "model_name": friendly,
        "status_text": "success",
    })


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
        _pull_ollama_model(model, index, 2, progress)
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
