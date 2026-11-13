"""Bounded, source-bound PNG animation packs. Never execute model-supplied code."""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import zipfile
from collections import OrderedDict

from PySide6.QtGui import QImage
from .artwork import valid_art_id, validate_png

CLIPS = frozenset({"idle_front", "walk_left", "walk_right", "turn_left", "turn_right",
                   "return_left", "return_right", "wave", "hop", "cheer", "bite_left", "bite_right"})
MAX_PACK = 24 * 1024 * 1024
_PACKS = OrderedDict()
_FRAMES = OrderedDict()


def asset_root():
    from .config import data_dir
    return data_dir() / "motion"


def _point(value):
    return (isinstance(value, list) and len(value) == 2 and
            all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in value))


def validate_pack(data, source_id):
    if not valid_art_id(source_id) or not isinstance(data, bytes) or len(data) > MAX_PACK:
        raise ValueError("Invalid motion pack")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [x.filename for x in entries]
            if (len(names) != len(set(names)) or not 13 <= len(names) <= 501 or
                    sum(x.file_size for x in entries) > 80 * 1024 * 1024 or
                    any(x.file_size > 2 * 1024 * 1024 or x.flag_bits & 1 or
                        x.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or
                        (x.external_attr >> 16) & 0o170000 == 0o120000 for x in entries)):
                raise ValueError("Invalid motion archive")
            raw = archive.read("manifest.json")
            if len(raw) > 256 * 1024:
                raise ValueError("Motion manifest too large")
            manifest = json.loads(raw)
            if (not isinstance(manifest, dict) or manifest.get("version") != 1 or
                    type(manifest.get("version")) is not int or manifest.get("source_art_id") != source_id or
                    manifest.get("backend") not in ("triposr-pose-v1", "triposr-pose-v2") or manifest.get("size") != 256 or
                    type(manifest.get("fps")) is not int or manifest["fps"] != 30 or
                    not isinstance(manifest.get("clips"), dict) or set(manifest["clips"]) != CLIPS):
                raise ValueError("Incompatible motion manifest")
            clean = {"version": 1, "source_art_id": source_id, "backend": manifest["backend"],
                     "size": 256, "fps": 30, "clips": {}}
            expected = {"manifest.json"}
            images = {}
            for clip, frames in manifest["clips"].items():
                if not isinstance(frames, list) or not 4 <= len(frames) <= 96:
                    raise ValueError("Invalid motion frames")
                clean["clips"][clip] = []
                for i, frame in enumerate(frames):
                    name = f"frames/{clip}-{i:03}.png"
                    if (not isinstance(frame, dict) or frame.get("file") != name or
                            not valid_art_id(frame.get("sha256")) or not _point(frame.get("mouth"))):
                        raise ValueError("Invalid frame or anchor")
                    png = archive.read(name)
                    if hashlib.sha256(png).hexdigest() != frame["sha256"]:
                        raise ValueError("Motion frame checksum mismatch")
                    image = validate_png(png)
                    if image.width() != 256 or image.height() != 256 or not image.hasAlphaChannel():
                        raise ValueError("Invalid motion dimensions")
                    images[name] = png
                    expected.add(name)
                    clean["clips"][clip].append({"file": name, "sha256": frame["sha256"], "mouth": frame["mouth"]})
            if set(names) != expected:
                raise ValueError("Unexpected motion archive contents")
            return clean, images
    except (OSError, KeyError, TypeError, RuntimeError, NotImplementedError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise ValueError("Invalid motion pack") from error


def store_pack(data, source_id, root=None):
    validate_pack(data, source_id)
    digest = hashlib.sha256(data).hexdigest()
    folder = (root or asset_root()).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (digest + ".zip")
    if target.exists() and target.resolve().parent != folder:
        raise ValueError("Invalid motion destination")
    descriptor, name = tempfile.mkstemp(prefix="motion-", suffix=".tmp", dir=folder)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return digest


def load_pack(digest, source_id, root=None):
    if not valid_art_id(digest) or not valid_art_id(source_id):
        return None
    folder = (root or asset_root()).resolve()
    key = (str(folder), digest, source_id)
    if key in _PACKS:
        _PACKS.move_to_end(key)
        return _PACKS[key]
    path = folder / (digest + ".zip")
    try:
        if path.resolve().parent != folder or path.stat().st_size > MAX_PACK:
            return None
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            return None
        result = validate_pack(data, source_id)
    except (OSError, ValueError):
        return None
    _PACKS[key] = result
    while len(_PACKS) > 2:
        _PACKS.popitem(last=False)
    return result


def frame(spec, clip, seconds):
    pack = load_pack(spec.get("animation_id"), spec.get("art_id"))
    if pack is None or clip not in CLIPS:
        return None
    manifest, images = pack
    frames = manifest["clips"][clip]
    index = max(0, int(max(0, seconds) * manifest["fps"]))
    index = min(index, len(frames) - 1) if clip.startswith(("turn_", "return_", "bite_")) or clip == "hop" else index % len(frames)
    entry = frames[index]
    key = (spec["animation_id"], entry["file"])
    if key not in _FRAMES:
        _FRAMES[key] = QImage.fromData(images[entry["file"]], "PNG")
        while len(_FRAMES) > 48:
            _FRAMES.popitem(last=False)
    else:
        _FRAMES.move_to_end(key)
    return _FRAMES[key], entry["mouth"]


class MotionPlayer:
    """Orientation transitions independent of guardian callbacks and target identity."""
    def __init__(self):
        self.clip = "idle_front"
        self.target = "idle_front"
        self.started = None

    def update(self, moving, direction, pose, now):
        if self.started is None:
            self.started = now
        target = ("walk_right" if direction >= 0 else "walk_left") if moving else pose if pose in ("wave", "hop", "cheer") else "idle_front"
        self.target = target
        transition = self.clip.startswith(("turn_", "return_"))
        if transition and now - self.started < 8 / 30:
            return self.clip, now - self.started, False
        if transition:
            self.clip = "idle_front" if self.clip.startswith("return_") else "walk_" + self.clip[5:]
            self.started = now
        if self.clip != target:
            if self.clip.startswith("walk_"):
                self.clip = "return_" + self.clip[5:]
            elif target.startswith("walk_"):
                self.clip = "turn_" + target[5:]
            else:
                self.clip = target
            self.started = now
        return self.clip, now - self.started, self.clip.startswith("walk_") and self.clip == target
