"""Sequential, cancellable model preparation with source-bound stage caching."""
import ast
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import threading

from . import art_client, artwork, motion_pack
from .characters import GenerationError
from .config import safe_character, data_dir
from .model_jobs import model_job

STAGE_FILES = {
    "reconstruct": {"surface.npz", "reference.png", "reconstruction.json", *(f"view-{i}.png" for i in range(8))},
    "rig": {"rig.npz", "rig.json"},
    "bake": {"motion.zip"},
}
QUALITY_MODES = frozenset({"standard", "high_multiview", "sdxl_multiview"})
EXTRA_VIEW_KEYS = frozenset({"facing_right", "facing_left", "back", "right_3q", "left_3q"})


def _code(path, names, follow_calls=False):
    """Fingerprint trusted shipped functions, imports and module constants; no execution."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set(names)
    if follow_calls:
        definitions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        while True:
            dependencies = {
                node.id for name in names if name in definitions for node in ast.walk(definitions[name])
                if isinstance(node, ast.Name) and node.id in definitions
            }
            if dependencies <= names:
                break
            names.update(dependencies)
    selected = [
        node for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign))
        or isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
    ]
    found = {node.name for node in selected if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    if not set(names) <= found:
        raise GenerationError("motion_runtime_failed")

    def stable(value):
        if isinstance(value, ast.AST):
            return {
                "node": type(value).__name__,
                "fields": {
                    key: stable(item) for key, item in ast.iter_fields(value)
                    if item is not None and not (isinstance(item, list) and not item)
                    and not (key == "is_lazy" and isinstance(value, (ast.Import, ast.ImportFrom)) and item == 0)
                },
            }
        if isinstance(value, (list, tuple)):
            return [stable(item) for item in value]
        if isinstance(value, bytes):
            return {"bytes": value.hex()}
        if value is Ellipsis:
            return {"literal": "Ellipsis"}
        return value

    return json.dumps(stable(ast.Module(body=selected, type_ignores=[])), sort_keys=True, separators=(",", ":")).encode()


def stage_signatures():
    source = art_client.source_dir()
    text = lambda name: (source / name).read_text(encoding="utf-8").encode("utf-8")
    opt_text = lambda name: (source / name).read_text(encoding="utf-8").encode("utf-8") if (source / name).is_file() else b""
    common = b"".join(text(name) for name in ("motion_catalog.json", "triposr-sources.json", "requirements.txt"))
    mg_text = (source / "motion_geometry.py").read_text(encoding="utf-8")
    mg_funcs = {node.name for node in ast.parse(mg_text).body if isinstance(node, ast.FunctionDef)}
    reconstruct_geo = {"extract", "projected_colors"} | ({"compute_vertex_normals", "project_multiview_colors", "bake_texture_atlas", "classify_art_texture", "inflate_2_5d_mesh"} & mg_funcs)
    rig_geo = {"lift", "fit", "smooth"} | ({"lift_medial", "fit_articulated"} & mg_funcs)
    bake_geo = {"pose", "knee_at", "ry", "rz", "smooth"} | ({"dual_quaternion_skinning"} & mg_funcs)
    geometry = {"reconstruct": reconstruct_geo, "rig": rig_geo, "bake": bake_geo}
    result = {}
    for stage in STAGE_FILES:
        td_funcs = {stage, "model_path", "digest", "report", "main"} if stage != "bake" else {"model_path", "digest", "report", "main"}
        if stage == "reconstruct" and "refine_views" in {n.name for n in ast.parse((source / "three_d.py").read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef)}:
            td_funcs.add("refine_views")
        worker = _code(source / "three_d.py", td_funcs)
        parts = common + worker + _code(source / "motion_geometry.py", geometry[stage], follow_calls=True)
        parts += text("motion_bake.py" if stage == "bake" else "runner.py")
        if stage == "bake":
            parts += opt_text("motion_library.py")
        if stage != "reconstruct":
            parts += text("catalog.json")
        result[stage] = hashlib.sha256(parts).hexdigest()
    result["prepare"] = hashlib.sha256(common + text("catalog.json") + _code(source / "three_d.py", {"prepare", "digest", "report"})).hexdigest()
    return result


def _write(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


def _check_cancel(cancel):
    if cancel.is_set():
        raise GenerationError("art_cancelled")


def _valid_outputs(job, stage, records):
    expected_names = STAGE_FILES.get(stage, {"surface.npz"})
    if not isinstance(records, list) or len(records) != len(expected_names) or {r.get("name") for r in records if isinstance(r, dict)} != expected_names:
        return False
    for record in records:
        if not isinstance(record, dict):
            return False
        name, sha, size = record.get("name"), record.get("sha256"), record.get("bytes")
        if name not in expected_names or not artwork.valid_art_id(sha) or type(size) is not int or not 0 < size <= 64 * 1024 * 1024:
            return False
        path = job / name
        try:
            if path.resolve().parent != job.resolve() or path.stat().st_size != size or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                return False
        except OSError:
            return False
    return True


def _worker(stage, job, root, payload, progress, cancel):
    _check_cancel(cancel)
    output = art_client._run(
        [art_client.runtime_python(root), art_client.source_dir() / "three_d.py", stage, "--cache", root / "models", "--job", job],
        payload,
        progress=progress,
        cancel=cancel,
        contain=True,
    )
    _check_cancel(cancel)
    try:
        result = json.loads(output)
        if not isinstance(result, dict) or result.get("stage") != stage:
            raise ValueError()
        if stage != "prepare" and not _valid_outputs(job, stage, result.get("files")):
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise GenerationError("motion_runtime_failed") from None


def _legacy_stage(folder, cache, stage, key, signatures, spec, cancel):
    """Adopt only source-pinned legacy algorithms and hash-verified outputs."""
    try:
        pins = json.loads((art_client.source_dir() / "motion_cache_legacy.json").read_text())["backends"]
    except (OSError, ValueError, KeyError):
        return None
    for old in sorted(cache.glob(spec["art_id"] + "-*")):
        if old == folder or not old.is_dir() or old.resolve().parent != cache.resolve():
            continue
        _check_cancel(cancel)
        try:
            path = old / "state.json"
            if path.resolve().parent != old.resolve() or path.stat().st_size > 65536:
                continue
            state = json.loads(path.read_text())
            revision = state.get("revision")
            pin = pins.get(revision, {})
            if pin.get(stage) != signatures[stage]:
                continue
            previous = spec["art_id"]
            candidate = None
            for name in STAGE_FILES:
                record = state["stages"][name]
                parameters = [spec["mouth_x"], spec["mouth_y"]] if name == "rig" else []
                algorithm = pin.get("inputs", {}).get(name) if pin.get("format") == "staged" else revision
                if not artwork.valid_art_id(algorithm):
                    break
                expected = hashlib.sha256(json.dumps([previous, algorithm, parameters]).encode()).hexdigest()
                if record.get("input") != expected or not _valid_outputs(old, name, record.get("files")):
                    break
                if name == stage:
                    candidate = record
                    break
                if not _valid_outputs(folder, name, record.get("files")):
                    break
                previous = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
            if candidate:
                for record in candidate["files"]:
                    temporary = folder / (record["name"] + ".adopting")
                    if temporary.resolve().parent != folder.resolve():
                        raise ValueError()
                    shutil.copyfile(old / record["name"], temporary)
                    os.replace(temporary, folder / record["name"])
                return {"input": key, "files": candidate["files"]}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return None


def _clean_extra_views(extra_views):
    cleaned = {}
    if not isinstance(extra_views, dict):
        return cleaned
    for key, art_id in extra_views.items():
        if key in EXTRA_VIEW_KEYS and artwork.valid_art_id(art_id):
            cleaned[key] = art_id
    return cleaned


def prepare_animation(
    spec,
    progress=lambda event: None,
    cancel=None,
    root=None,
    cache=None,
    quality_mode="standard",
    extra_views=None,
):
    cancel = cancel or threading.Event()
    root = root or art_client.runtime_root()
    spec = safe_character(spec)
    if spec.get("kind") != "artwork":
        raise GenerationError("motion_source_missing")
    if quality_mode not in QUALITY_MODES:
        quality_mode = "standard"
    clean_extras = _clean_extra_views(extra_views)

    with model_job():
        from .character_library import storage_lock
        with storage_lock():
            _check_cancel(cancel)
            art_dir = artwork.asset_root().resolve()
            source = art_dir / (spec["art_id"] + ".png")
            try:
                if source.resolve().parent != art_dir or source.stat().st_size > artwork.MAX_ART_BYTES:
                    raise ValueError()
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != spec["art_id"]:
                    raise ValueError()
                artwork.validate_png(data)
            except (OSError, ValueError):
                raise GenerationError("motion_source_missing") from None

            extra_bytes = {}
            for angle_key, extra_id in clean_extras.items():
                ep = art_dir / (extra_id + ".png")
                try:
                    if ep.resolve().parent != art_dir or ep.stat().st_size > artwork.MAX_ART_BYTES:
                        raise ValueError()
                    eb = ep.read_bytes()
                    if hashlib.sha256(eb).hexdigest() != extra_id:
                        raise ValueError()
                    artwork.validate_png(eb)
                    extra_bytes[angle_key] = eb
                except (OSError, ValueError):
                    raise GenerationError("motion_source_missing") from None

            if not art_client.runtime_python(root).is_file():
                raise GenerationError("art_not_prepared")
            signatures = stage_signatures()
            cache = cache or data_dir() / "motion-jobs"
            revision = signatures["reconstruct"]
            folder = cache / (spec["art_id"] + "-staged-" + revision[:16])
            folder.mkdir(parents=True, exist_ok=True)
            if folder.resolve().parent != cache.resolve():
                raise GenerationError("motion_runtime_failed")
            allowed_names = ("source.png", "state.json", "state.tmp", *set().union(*STAGE_FILES.values()), *(f"extra_{k}.png" for k in EXTRA_VIEW_KEYS))
            if any((folder / name).resolve().parent != folder.resolve() for name in allowed_names):
                raise GenerationError("motion_runtime_failed")
            (folder / "source.png").write_bytes(data)
            for angle_key in EXTRA_VIEW_KEYS:
                target_extra = folder / f"extra_{angle_key}.png"
                if angle_key in extra_bytes:
                    target_extra.write_bytes(extra_bytes[angle_key])
                else:
                    target_extra.unlink(missing_ok=True)
            try:
                if (folder / "state.json").stat().st_size > 65536:
                    raise ValueError()
                state = json.loads((folder / "state.json").read_text(encoding="utf-8"))
                if not isinstance(state, dict) or state.get("revision") != revision or not isinstance(state.get("stages"), dict):
                    raise ValueError()
            except (OSError, ValueError):
                state = {"revision": revision, "stages": {}}
            state["job"] = secrets.token_hex(16)
            state["status"] = "preparing"
            _write(folder / "state.json", state)

        ready = root / "motion-ready.json"
        try:
            prepared = json.loads(ready.read_text()).get("revision") == signatures["prepare"]
        except (OSError, ValueError, AttributeError):
            prepared = False
        try:
            if not prepared:
                progress("art_runtime_packages")
                uv = root / "uv.exe"
                if not uv.is_file():
                    raise GenerationError("art_not_prepared")
                art_client._run(
                    [uv, "pip", "install", "--python", art_client.runtime_python(root), "--index-url", "https://pypi.org/simple", "-r", art_client.source_dir() / "requirements.txt"],
                    timeout=1800,
                    progress=progress,
                    cancel=cancel,
                    contain=True,
                )
                art_client._run([art_client.runtime_python(root), art_client.source_dir() / "inventory.py", root], cancel=cancel, contain=True)
                _worker("prepare", folder, root, {}, progress, cancel)
                _write(ready, {"revision": signatures["prepare"]})

            payload = {
                "source_art_id": spec["art_id"],
                "mouth": [spec["mouth_x"], spec["mouth_y"]],
                "quality_mode": quality_mode,
                "extra_views": clean_extras,
                "seed": spec.get("seed", 42),
            }
            previous = spec["art_id"]
            reconstruct_params = [quality_mode, sorted(clean_extras.items())] if (quality_mode != "standard" or clean_extras) else []

            for stage in ("reconstruct", "rig", "bake"):
                _check_cancel(cancel)
                parameters = payload["mouth"] if stage == "rig" else reconstruct_params if stage == "reconstruct" else []
                key = hashlib.sha256(json.dumps([previous, signatures[stage], parameters]).encode()).hexdigest()
                record = state["stages"].get(stage, {})
                if not record and stage == "reconstruct" and not reconstruct_params:
                    record = _legacy_stage(folder, cache, stage, key, signatures, spec, cancel) or {}
                elif not record and stage != "reconstruct":
                    record = _legacy_stage(folder, cache, stage, key, signatures, spec, cancel) or {}
                if isinstance(record, dict) and record.get("input") == key and _valid_outputs(folder, stage, record.get("files")):
                    progress("motion_cached")
                    state["stages"][stage] = record
                    _write(folder / "state.json", state)
                else:
                    result = _worker(stage, folder, root, payload, progress, cancel)
                    _check_cancel(cancel)
                    if stage == "reconstruct" and quality_mode == "sdxl_multiview":
                        refine_res = _worker("refine_views", folder, root, payload, progress, cancel)
                        _check_cancel(cancel)
                        refined_surf = refine_res["files"][0]
                        files = [refined_surf if f["name"] == "surface.npz" else f for f in result["files"]]
                    else:
                        files = result["files"]
                    record = {"input": key, "files": files}
                    state["stages"][stage] = record
                    _write(folder / "state.json", state)
                previous = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()

            progress("motion_validating")
            _check_cancel(cancel)
            data = (folder / "motion.zip").read_bytes()
            motion_pack.validate_pack(data, spec["art_id"])
            _check_cancel(cancel)
            animation_id = motion_pack.store_pack(data, spec["art_id"])
            _check_cancel(cancel)
            state["status"] = "ready"
            _write(folder / "state.json", state)
            return safe_character({**spec, "animation_id": animation_id})
        except Exception as error:
            if str(error) in ("motion_not_prepared", "motion_runtime_failed", "art_runtime_failed"):
                ready.unlink(missing_ok=True)
            state["status"] = "cancelled" if cancel.is_set() else "failed"
            _write(folder / "state.json", state)
            raise
