"""Validated local PNG assets; no arbitrary paths, SVG or generated code."""
import hashlib
import os
from pathlib import Path
import re
import tempfile

from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage

MAX_ART_BYTES = 8 * 1024 * 1024
MAX_ART_SIDE = 1024
_IMAGES = {}


def has_large_separate_figures(image):
    """Reject substantial detached upright silhouettes, not a semantic counter.

    Helps catch reference sheets missed by the local vision reviewer. Large
    detached accessories can be false positives; connected collages can escape.
    """
    from collections import deque
    from PySide6.QtCore import Qt
    small = image.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.FastTransformation)
    width, height = small.width(), small.height()
    remaining = {(x, y) for y in range(height) for x in range(width)
                 if small.pixelColor(x, y).alpha() > 64}
    components = []
    while remaining:
        start = remaining.pop()
        queue = deque([start])
        count = 0
        left = right = start[0]
        top = bottom = start[1]
        while queue:
            x, y = queue.popleft()
            count += 1
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in remaining:
                    remaining.remove(point)
                    queue.append(point)
        components.append((count, right - left + 1, bottom - top + 1))
    components.sort(reverse=True)
    if not components:
        return False
    largest = components[0][0]
    return any(area >= largest * .12 and h >= height * .35 and h >= w * 1.4
               for area, w, h in components[1:])


def asset_root():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "Pawzura" / "artwork"


def valid_art_id(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_png(data):
    if not isinstance(data, bytes) or len(data) > MAX_ART_BYTES or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid artwork PNG")
    if len(data) < 24:
        raise ValueError("Invalid artwork PNG")
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if not (16 <= width <= MAX_ART_SIDE and 16 <= height <= MAX_ART_SIDE):
        raise ValueError("Artwork dimensions out of range")
    image = QImage.fromData(data, "PNG")
    if image.isNull() or (image.width(), image.height()) != (width, height):
        raise ValueError("Invalid artwork image")
    return image


def store_artwork(data, root=None):
    image = validate_png(data)
    # Re-encode pixels only; strip input text/metadata before local persistence.
    clean = QImage(image.size(), QImage.Format.Format_ARGB32)
    clean.fill(0)
    from PySide6.QtGui import QPainter
    painter = QPainter(clean)
    painter.drawImage(0, 0, image)
    painter.end()
    encoded = QByteArray()
    buffer = QBuffer(encoded)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not clean.save(buffer, "PNG"):
        raise ValueError("Cannot encode artwork")
    content = bytes(encoded)
    digest = hashlib.sha256(content).hexdigest()
    folder = (root or asset_root()).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (digest + ".png")
    if target.exists() and target.resolve().parent != folder:
        raise ValueError("Invalid artwork destination")
    descriptor, name = tempfile.mkstemp(prefix="art-", suffix=".tmp", dir=folder)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    _IMAGES.clear()
    return digest


def load_artwork(digest, root=None):
    if not valid_art_id(digest):
        return QImage()
    folder = (root or asset_root()).resolve()
    key = (str(folder), digest)
    if key in _IMAGES:
        return _IMAGES[key]
    target = folder / (digest + ".png")
    try:
        if target.resolve().parent != folder or target.stat().st_size > MAX_ART_BYTES:
            return QImage()
        content = target.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            return QImage()
        image = validate_png(content)
    except (OSError, ValueError):
        return QImage()
    if len(_IMAGES) >= 20:
        _IMAGES.clear()
    _IMAGES[key] = image
    return image
