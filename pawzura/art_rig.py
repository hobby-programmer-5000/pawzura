"""Bounded cutout-limb rigs rendered from approved artwork pixels."""
import json
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPolygonF
from .artwork import load_artwork

PARTS = ("left_hand", "right_hand", "left_foot", "right_foot")
_LAYERS = {}


def _point(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2 and
            all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in value))


def safe_rig(raw):
    if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != 1 or not isinstance(raw.get("parts"), dict):
        return None
    if set(raw["parts"]) != set(PARTS):
        return None
    parts = {}
    for name in PARTS:
        item = raw["parts"][name]
        if not isinstance(item, dict):
            return None
        polygon, pivot = item.get("polygon"), item.get("pivot")
        if not isinstance(polygon, list) or not 3 <= len(polygon) <= 32 or not all(_point(p) for p in polygon) or not _point(pivot):
            return None
        area = abs(sum(polygon[i][0] * polygon[(i + 1) % len(polygon)][1] -
                       polygon[(i + 1) % len(polygon)][0] * polygon[i][1] for i in range(len(polygon)))) / 2
        if not .00005 <= area <= .20:
            return None
        xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
        if not min(xs) - .06 <= pivot[0] <= max(xs) + .06 or not min(ys) - .06 <= pivot[1] <= max(ys) + .06:
            return None
        parts[name] = {"polygon": [[float(x), float(y)] for x, y in polygon],
                       "pivot": [float(pivot[0]), float(pivot[1])]}
    for a, b in (("left_hand", "right_hand"), ("left_foot", "right_foot")):
        centers = [[sum(p[i] for p in parts[name]["polygon"]) / len(parts[name]["polygon"]) for i in (0, 1)] for name in (a, b)]
        if math.dist(*centers) < .025:
            return None
    return {"version": 1, "parts": parts}


def _path(points, side):
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(x * side, y * side) for x, y in points]))
    path.closeSubpath()
    return path


def layers(spec):
    rig = safe_rig(spec.get("rig"))
    if rig is None:
        return None
    key = (spec.get("art_id"), json.dumps(rig, sort_keys=True))
    if key in _LAYERS:
        return _LAYERS[key]
    source = load_artwork(spec.get("art_id"))
    if source.isNull():
        return None
    side = 288
    source = source.scaled(side, side, Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    core = source.copy()
    pieces = {}
    core_painter = QPainter(core)
    core_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    core_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    for name, item in rig["parts"].items():
        path = _path(item["polygon"], side)
        image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(path)
        painter.drawImage(0, 0, source)
        painter.end()
        pivot = QPointF(item["pivot"][0] * side, item["pivot"][1] * side)
        joint = QPainterPath()
        joint.addEllipse(pivot, 3.5, 3.5)
        # A retained joint overlap hides a tiny seam without reconstructing pixels.
        core_painter.fillPath(path.subtracted(joint), Qt.GlobalColor.white)
        pieces[name] = (image, pivot)
    core_painter.end()
    # Blend a narrow revealed sleeve/cape gap only where both sides were opaque.
    # Outside the original silhouette remains transparent; no invented drawing.
    for name in ("left_hand", "right_hand"):
        item = rig["parts"][name]
        path = _path(item["polygon"], side)
        bounds = path.boundingRect().toAlignedRect().intersected(core.rect())
        pivot = QPointF(item["pivot"][0] * side, item["pivot"][1] * side)
        for y in range(bounds.top(), bounds.bottom() + 1):
            xs = [x for x in range(bounds.left(), bounds.right() + 1) if path.contains(QPointF(x + .5, y + .5))]
            if not xs:
                continue
            left, right = max(0, xs[0] - 4), min(side - 1, xs[-1] + 4)
            a, b = source.pixelColor(left, y), source.pixelColor(right, y)
            if a.alpha() < 200 or b.alpha() < 200:
                continue
            for x in xs:
                if math.hypot(x - pivot.x(), y - pivot.y()) < 3.5:
                    continue
                fraction = (x - left) / max(1, right - left)
                core.setPixelColor(x, y, QColor(*(round(av * (1 - fraction) + bv * fraction)
                                                  for av, bv in zip(a.getRgb(), b.getRgb()))))
    result = core, pieces
    if len(_LAYERS) >= 8:
        _LAYERS.clear()
    _LAYERS[key] = result
    return result


def draw_rig(painter, spec, phase, pose="walk", facing=1):
    cached = layers(spec)
    if cached is None:
        return False
    core, pieces = cached
    painter.save()
    painter.scale(.5, .5)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    swing = math.sin(phase)

    is_parallax = spec.get("representation") == "2.5d_parallax"
    if is_parallax:
        # Step 2: 2.5D Multiplane Parallax Representation (Live2D / Spine style)
        # Separates the flat 2D artwork into 4 depth planes (Far limbs -> Torso -> Head -> Near limbs)
        # with subtle spine breathing, follow-through head tilt, and depth-scale perspective shift.
        neck_y = max(80.0, min(200.0, (float(spec.get("mouth_y", 0.38)) + 0.05) * 288.0))
        neck_x = max(70.0, min(218.0, float(spec.get("mouth_x", 0.50)) * 288.0))

        # 1. Background limbs (far plane, Z = -1)
        for name in ("left_foot", "left_hand"):
            image, pivot = pieces[name]
            hand = name.endswith("hand")
            angle = swing * (22 if hand else 12)
            lift = max(0, math.cos(phase)) * 6 if not hand else 0
            if pose in ("wave", "hover"):
                angle = 5 if hand else 0
                lift = 0
            elif pose in ("hop", "cheer"):
                angle = (62 + math.sin(phase * 2) * 12) if hand else -swing * 16
            elif pose == "bite":
                angle, lift = 0, 0

            painter.save()
            painter.translate(pivot.x() - 1.5, pivot.y() - lift)
            painter.scale(0.97, 0.97)
            painter.rotate(angle)
            painter.translate(-pivot.x(), -pivot.y())
            painter.drawImage(0, 0, image)
            painter.restore()

        # 2. Torso core (mid plane, Z = 0)
        torso_sway = math.sin(phase) * 1.2
        torso_tilt = math.sin(phase) * 1.5
        torso_breath = math.sin(phase * 2.0) * 1.2
        if pose in ("hop", "cheer"):
            torso_breath += math.sin(phase * 2.5) * 3.5

        painter.save()
        painter.translate(144.0 + torso_sway, 240.0 - torso_breath)
        painter.rotate(torso_tilt)
        painter.translate(-144.0, -240.0)
        painter.save()
        painter.setClipRect(QRectF(0, neck_y - 2.0, 288, 288 - neck_y + 2.0))
        painter.drawImage(0, 0, core)
        painter.restore()
        painter.restore()

        # 3. Head core (near-mid plane, Z = +0.5) with follow-through lag
        head_lag = phase - 0.35
        head_sway = math.sin(head_lag) * 1.5
        head_tilt = math.sin(head_lag) * 2.6
        if pose == "hover":
            head_tilt = math.sin(phase * 1.5) * 3.5 + 2.0
            head_sway = math.sin(phase * 1.5) * 2.0

        painter.save()
        painter.translate(neck_x + head_sway, neck_y - torso_breath * 0.7)
        painter.rotate(head_tilt)
        painter.translate(-neck_x, -neck_y)
        painter.save()
        painter.setClipRect(QRectF(0, 0, 288, neck_y + 2.0))
        painter.drawImage(0, 0, core)
        painter.restore()
        painter.restore()

        # 4. Foreground limbs (near plane, Z = +1)
        for name in ("right_foot", "right_hand"):
            image, pivot = pieces[name]
            hand = name.endswith("hand")
            angle = -swing * (22 if hand else 12)
            lift = max(0, math.cos(phase + math.pi)) * 6 if not hand else 0
            if pose in ("wave", "hover"):
                angle = -(50 + math.sin(phase * 2) * 22) if hand else 0
                lift = 0
            elif pose in ("hop", "cheer"):
                angle = -(62 + math.sin(phase * 2) * 12) if hand else swing * 16
            elif pose == "bite":
                angle, lift = 0, 0

            painter.save()
            painter.translate(pivot.x() + 1.5, pivot.y() - lift)
            painter.scale(1.03, 1.03)
            painter.rotate(angle)
            painter.translate(-pivot.x(), -pivot.y())
            painter.drawImage(0, 0, image)
            painter.restore()

        painter.restore()
        return True

    for name in ("left_foot", "right_foot", "core", "left_hand", "right_hand"):
        if name == "core":
            painter.drawImage(0, 0, core)
            continue
        image, pivot = pieces[name]
        left = name.startswith("left")
        hand = name.endswith("hand")
        angle = swing * (22 if hand else 12) * (1 if left else -1)
        lift = max(0, math.cos(phase + (0 if left else math.pi))) * 6 if not hand else 0
        if pose in ("wave", "hover"):
            angle = (-(50 + math.sin(phase * 2) * 22) if not left else 5) if hand else 0
            lift = 0
        elif pose in ("hop", "cheer"):
            angle = ((62 + math.sin(phase * 2) * 12) * (1 if left else -1)) if hand else -swing * 16 * (1 if left else -1)
        elif pose == "bite":
            angle, lift = 0, 0
        painter.save()
        painter.translate(pivot.x(), pivot.y() - lift)
        painter.rotate(angle)
        painter.translate(-pivot.x(), -pivot.y())
        painter.drawImage(0, 0, image)
        painter.restore()
    painter.restore()
    return True
