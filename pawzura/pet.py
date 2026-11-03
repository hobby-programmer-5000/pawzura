"""Original vector SD character, articulated at runtime; no sprite/video dependencies."""
from __future__ import annotations

import math
import random
import time
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF, QCursor
from PySide6.QtWidgets import QApplication, QWidget
from .config import safe_character


def draw_character(painter: QPainter, spec: dict, phase=0.0, facing=1, biting=False, pose="walk", motion_clip=None, motion_time=None):
    p = painter
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.save()
    if spec.get("kind") == "artwork" and spec.get("animation_id"):
        from .motion_pack import frame
        clip = motion_clip or (("bite_right" if facing >= 0 else "bite_left") if biting else
                               ("walk_right" if facing >= 0 else "walk_left") if pose == "walk" else
                               pose if pose in ("wave", "hop", "cheer") else "idle_front")
        item = frame(spec, clip, phase / 9 if motion_time is None else motion_time)
        if item is not None:
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(QRectF(0, 0, 144, 144), item[0])
            p.restore()
            return
    if facing < 0:
        p.translate(144, 0)
        p.scale(-1, 1)
    if spec.get("kind") == "artwork":
        from .artwork import load_artwork
        image = load_artwork(spec.get("art_id"))
        if not image.isNull():
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if not biting and not spec.get("rig"):
                p.translate(72, 136)
                p.rotate(math.sin(phase) * 2)
                p.translate(-72, -136 - abs(math.sin(phase)) * 3)
            from .art_rig import draw_rig
            if not draw_rig(p, spec, phase, "bite" if biting else pose):
                p.drawImage(QRectF(0, 0, 144, 144), image)
            if biting:
                x, y = 144 * spec["mouth_x"], 144 * spec["mouth_y"]
                p.setPen(QPen(QColor("#34304a"), 1.5))
                p.setBrush(QColor("#fff4e5"))
                p.drawEllipse(QRectF(x - 4, y - 2, 8, 5))
            p.restore()
            return
    outline = QColor("#34304a")
    body = QColor(spec["body"])
    accent = QColor(spec["accent"])
    p.setPen(QPen(outline, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    bounce = abs(math.sin(phase)) * 3
    p.translate(0, -bounce)
    wings = spec.get("wings", "none")
    if wings != "none":
        p.setBrush(accent.lighter(115))
        for mirrored in (False, True):
            p.save()
            if mirrored:
                p.translate(144, 0)
                p.scale(-1, 1)
            p.translate(0, math.sin(phase * 1.5) * 3)
            if wings == "fairy":
                p.drawEllipse(QRectF(8, 69, 39, 25))
                p.drawEllipse(QRectF(14, 92, 30, 20))
            else:
                path = QPainterPath(QPointF(46, 103))
                path.cubicTo(28, 81, 18, 68, 7, 65)
                path.lineTo(10, 103)
                path.quadTo(23, 94, 25, 113)
                path.quadTo(34, 101, 46, 111)
                path.closeSubpath()
                p.drawPath(path)
            p.restore()
    # Tail and articulated feet.
    p.setBrush(body.lighter(110))
    tail = spec.get("tail", "puff")
    if tail == "puff":
        p.drawEllipse(QRectF(28, 99 + math.sin(phase) * 2, 24, 20))
    elif tail == "cat":
        path = QPainterPath(QPointF(48, 120))
        path.cubicTo(15, 126, 12, 100 + math.sin(phase) * 5, 24, 91)
        p.setPen(QPen(body.darker(110), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(path)
        p.setPen(QPen(outline, 2.5))
    elif tail == "fox":
        p.drawPolygon(QPolygonF([QPointF(52, 113), QPointF(21, 91 + math.sin(phase) * 3),
                                QPointF(13, 116), QPointF(31, 132), QPointF(54, 123)]))
        p.setBrush(accent)
        p.drawPolygon(QPolygonF([QPointF(21, 91 + math.sin(phase) * 3), QPointF(13, 116), QPointF(29, 111)]))
    for side, offset in ((0, 0), (1, math.pi)):
        x = 51 + side * 29 + math.sin(phase + offset) * 6
        y = 126 - max(0, math.cos(phase + offset)) * 6
        p.setBrush(accent)
        p.drawEllipse(QRectF(x, y, 22, 12))
    p.setBrush(body)
    p.drawRoundedRect(QRectF(47, 85, 55, 44), 20, 20)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(body.lighter(125))
    p.drawEllipse(QRectF(59, 99, 30, 23))
    p.setPen(QPen(outline, 2.5))
    p.setBrush(body)
    ear = spec["ears"]
    sway = math.sin(phase / 2) * 3
    if ear == "rabbit":
        p.save()
        p.translate(44, 43)
        p.rotate(-12 + sway)
        p.drawRoundedRect(QRectF(-9, -37, 20, 45), 10, 10)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawRoundedRect(QRectF(-3, -30, 8, 30), 4, 4)
        p.restore()
        p.save()
        p.translate(98, 43)
        p.rotate(16 - sway)
        p.drawRoundedRect(QRectF(-9, -37, 20, 45), 10, 10)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawRoundedRect(QRectF(-3, -30, 8, 30), 4, 4)
        p.restore()
    elif ear in ("cat", "fox"):
        tip = 7 if ear == "fox" else 18
        p.drawPolygon(QPolygonF([QPointF(32, 49), QPointF(32, tip), QPointF(58, 34)]))
        p.drawPolygon(QPolygonF([QPointF(86, 34), QPointF(110, tip), QPointF(112, 51)]))
        if ear == "fox":
            p.setBrush(accent)
            p.drawPolygon(QPolygonF([QPointF(36, 38), QPointF(36, 18), QPointF(49, 34)]))
            p.drawPolygon(QPolygonF([QPointF(95, 34), QPointF(106, 18), QPointF(108, 40)]))
    elif ear == "bear":
        p.drawEllipse(QRectF(27, 23, 30, 30))
        p.drawEllipse(QRectF(88, 23, 30, 30))
        p.setBrush(accent)
        p.drawEllipse(QRectF(34, 30, 16, 16))
        p.drawEllipse(QRectF(95, 30, 16, 16))
    p.setBrush(body)
    p.drawRoundedRect(QRectF(26, 34, 94, 65), 31, 31)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(body.lighter(112))
    p.drawEllipse(QRectF(36, 38, 72, 32))
    # A tiny fringe, varied by seed but never a named character design.
    p.setBrush(body.darker(108))
    p.drawPolygon(QPolygonF([QPointF(56, 37), QPointF(77, 38), QPointF(69, 52)]))
    blink = math.sin(phase / 9) > 0.995
    eyes = spec.get("eyes", "round")
    eye_color = QColor(spec.get("eye_color", "#34304a"))
    for x in (53, 94):
        p.setBrush(eye_color)
        if blink or eyes == "sleepy":
            p.setPen(QPen(eye_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x - 5, 67), QPointF(x + 5, 67))
            p.setPen(Qt.PenStyle.NoPen)
        elif eyes == "happy":
            p.setPen(QPen(eye_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(x - 6, 61, 12, 14), 15 * 16, 150 * 16)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.drawEllipse(QRectF(x - 5, 57, 11, 17))
            p.setBrush(QColor("#fffdf7"))
            p.drawEllipse(QRectF(x - 2, 59, 4, 5))
    markings = spec.get("markings", "none")
    p.setBrush(accent)
    if markings in ("freckles", "spots"):
        radius = 1.6 if markings == "freckles" else 3.2
        for x in (40, 46, 100, 106):
            p.drawEllipse(QPointF(x, 78 + (x % 4)), radius, radius)
    elif markings == "stripes":
        p.setPen(QPen(accent, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for x in (40, 103):
            p.drawLine(QPointF(x, 72), QPointF(x + 7, 76))
            p.drawLine(QPointF(x, 81), QPointF(x + 7, 83))
        p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ee92aa"))
    p.setOpacity(0.6)
    p.drawEllipse(QRectF(38, 74, 15, 7))
    p.drawEllipse(QRectF(97, 74, 15, 7))
    p.setOpacity(1)
    p.setPen(QPen(outline, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if biting:
        p.setBrush(QColor("#65405d"))
        p.drawEllipse(QRectF(66, 73, 24, 20))
        p.setBrush(QColor("#fffdf7"))
        p.drawPolygon(QPolygonF([QPointF(70, 75), QPointF(76, 75), QPointF(73, 82)]))
        p.drawPolygon(QPolygonF([QPointF(81, 75), QPointF(87, 75), QPointF(84, 82)]))
    else:
        p.drawArc(QRectF(64, 73, 12, 10), 180 * 16, 165 * 16)
        p.drawArc(QRectF(75, 73, 12, 10), 195 * 16, 165 * 16)
    p.setBrush(accent)
    accessory = spec["accessory"]
    if accessory == "scarf":
        p.drawRoundedRect(QRectF(43, 93, 61, 10), 5, 5)
        p.drawRoundedRect(QRectF(87, 100, 12, 21 + math.sin(phase) * 3), 4, 4)
    elif accessory == "star":
        points = []
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            radius = 10 if i % 2 == 0 else 4.5
            points.append(QPointF(75 + radius * math.cos(angle), 109 + radius * math.sin(angle)))
        p.drawPolygon(QPolygonF(points))
    elif accessory == "leaf":
        p.drawEllipse(QRectF(66, 101, 20, 12))
        p.drawLine(QPointF(67, 112), QPointF(84, 103))
    elif accessory == "bow":
        p.drawPolygon(QPolygonF([QPointF(75, 103), QPointF(56, 96), QPointF(56, 116)]))
        p.drawPolygon(QPolygonF([QPointF(75, 103), QPointF(94, 96), QPointF(94, 116)]))
        p.drawEllipse(QRectF(70, 100, 10, 10))
    elif accessory == "bell":
        p.drawRoundedRect(QRectF(43, 93, 61, 8), 4, 4)
        p.drawEllipse(QRectF(66, 100, 20, 20))
        p.drawLine(QPointF(70, 114), QPointF(82, 114))
    p.setBrush(body)
    p.drawEllipse(QRectF(38, 103 + math.sin(phase) * 4 - (18 if pose in ("hop", "cheer") else 0), 16, 19))
    p.drawEllipse(QRectF(98, 103 - math.sin(phase) * 4 - (30 if pose in ("wave", "hover", "hop", "cheer") else 0), 16, 19))
    p.restore()


class CharacterPreview(QWidget):
    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.theme = "dark"
        self.phase = 0.0
        self.pose = "walk"
        self.facing = 1
        self.setMinimumSize(200, 220)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40)

    def tick(self):
        if self.isVisible():
            self.phase += .36 if self.spec.get("animation_id") else .14
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#f0edf7" if self.theme == "light" else "#22263b"))
        p.drawRoundedRect(self.rect(), 22, 22)
        scale = min(self.width() / 180, self.height() / 180)
        p.translate((self.width() - 144 * scale) / 2, (self.height() - 144 * scale) / 2)
        p.scale(scale, scale)
        if self.pose == "hop":
            p.translate(0, -abs(math.sin(self.phase)) * 10)
        p.setBrush(QColor("#ddd5e9" if self.theme == "light" else "#171b2b"))
        p.drawEllipse(QRectF(37, 137, 72, 7))
        from .motion_pack import CLIPS
        draw_character(p, self.spec, self.phase, facing=self.facing, pose=self.pose,
                       motion_clip=self.pose if self.spec.get("animation_id") and self.pose in CLIPS else None)


class Crack(QWidget):
    def __init__(self, point: QPointF, label="", parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(150, 150)
        self.move(round(point.x()) - 75, round(point.y()) - 75)
        self.born = time.monotonic()
        self.label = label
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.show_at(point, label)

    def show_at(self, point, label):
        self.move(round(point.x()) - 75, round(point.y()) - 75)
        self.label = label
        self.born = time.monotonic()
        self.timer.start(30)
        self.show()

    def tick(self):
        if time.monotonic() - self.born > 1.8:
            self.timer.stop()
            self.hide()
        else:
            self.update()

    def paintEvent(self, _):
        age = time.monotonic() - self.born
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(max(0, 1 - age / 1.8))
        if self.label:
            p.setPen(QColor("#eadfff"))
            p.drawText(QRectF(25, 112, 100, 24), Qt.AlignmentFlag.AlignCenter, self.label)
        rng = random.Random(347)
        for i in range(7):
            angle = i * math.tau / 7
            points = [QPointF(75, 75)]
            for distance in (15, 31, 53):
                a = angle + rng.uniform(-0.25, 0.25)
                points.append(QPointF(75 + math.cos(a) * distance, 75 + math.sin(a) * distance))
            for color, width in (("#393148", 3.5), ("#e5e2ff", 1.3)):
                p.setPen(QPen(QColor(color), width))
                p.drawPolyline(QPolygonF(points))
            p.drawLine(points[1], points[1] + QPointF(math.sin(angle) * 15, -math.cos(angle) * 15))


class TabTarget(QWidget):
    """A synthetic tab X, kept separate from every browser/window caption."""
    def __init__(self, point, label, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(180, 44)
        self.move(round(point.x()) - 158, round(point.y()) - 22)
        self.label = label
        self.show()

    def show_at(self, point, label):
        self.move(round(point.x()) - 158, round(point.y()) - 22)
        self.label = label
        self.show()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#29233e"))
        p.setPen(QPen(QColor("#c5b0f4"), 2))
        p.drawRoundedRect(QRectF(1, 1, 178, 42), 10, 10)
        p.setPen(QColor("#f1eaff"))
        p.drawText(QRectF(8, 2, 130, 40), Qt.AlignmentFlag.AlignCenter, self.label)
        p.drawLine(QPointF(153, 17), QPointF(163, 27))
        p.drawLine(QPointF(163, 17), QPointF(153, 27))


class Pet(QWidget):
    settings_requested = Signal()

    def __init__(self, spec, language="en", walk_direction="right"):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Pawzura companion")
        self.setFixedSize(144, 146)
        self.spec = safe_character(spec)
        self.phase = 0.0
        self.walk_direction = -1 if walk_direction == "left" else 1
        self.direction = self.walk_direction
        self.last_tick = time.monotonic()
        self.action = None
        self.reaction = None
        self.hovered = False
        self.look_direction = 1
        self.click_count = 0
        self.next_idle = time.monotonic() + 12
        from .motion_pack import MotionPlayer
        self.motion_player = MotionPlayer()
        self.motion_clip = "idle_front"
        self.motion_time = 0.0
        self.next_pause = time.monotonic() + random.uniform(7, 13)
        self.pause_until = 0.0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_language(language)
        self.cracks = []
        self.tab_marker = None
        self.home()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        QApplication.instance().screenAdded.connect(self.screen_changed)
        QApplication.instance().screenRemoved.connect(self.screen_changed)
        for screen in QApplication.screens():
            self.watch_screen(screen)
        QApplication.instance().screenAdded.connect(self.watch_screen)

    def set_language(self, language):
        self.setToolTip("커서: 인사 · 클릭: 인사/점프/환호 · 더블 클릭/우클릭: 설정" if language == "ko" else
                        "Hover: greet · Click: wave / hop / cheer · Double-click / right-click: settings")

    def set_walk_direction(self, direction):
        self.walk_direction = -1 if direction == "left" else 1
        if self.action is None:
            self.direction = self.walk_direction

    def react(self, kind):
        if self.action or kind not in ("wave", "hop", "cheer"):
            return False
        self.reaction = {"kind": kind, "start": time.monotonic(), "duration": .9 if kind == "hop" else 1.6}
        return True

    def enterEvent(self, event):
        self.hovered = True
        self.look_direction = -1 if QCursor.pos().x() < self.geometry().center().x() else 1
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def mouseMoveEvent(self, event):
        self.look_direction = -1 if event.position().x() < self.width() / 2 else 1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.action:
            kind = ("wave", "hop", "cheer")[self.click_count % 3]
            self.click_count += 1
            self.react(kind)
            event.accept()

    def watch_screen(self, screen):
        screen.availableGeometryChanged.connect(self.screen_changed)
        screen.geometryChanged.connect(self.screen_changed)

    def screen_changed(self, *_):
        self.cancel_bite()
        self.update()

    def screens(self):
        return sorted(QApplication.screens(), key=lambda s: (s.geometry().x(), s.geometry().y()))

    def use_screen(self, screen):
        handle = self.windowHandle()
        if handle is not None and handle.screen() != screen:
            handle.setScreen(screen)
        self.setFixedSize(144, 146)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # A Windows per-monitor DPI transition can deliver a suggested native
        # size even for a constrained tool window. Keep our painter/anchor
        # coordinate system in logical pixels, including during that event.
        if (self.width(), self.height()) != (144, 146) and not getattr(self, "_repairing_size", False):
            self._repairing_size = True
            try:
                self.resize(144, 146)
            finally:
                self._repairing_size = False

    def home(self):
        self.direction = self.walk_direction
        screen = QApplication.primaryScreen()
        if screen is None:
            self.px, self.py = 0.0, 0.0
            return
        area = screen.availableGeometry()
        self.use_screen(screen)
        self.px = float(area.x() + max(0, (area.width() - self.width()) // 2))
        self.py = float(max(area.top(), area.bottom() - self.height() + 1))
        self.move(round(self.px), round(self.py))

    def tab_target_point(self):
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        return QPointF(area.center().x(), max(area.top() + 100, area.bottom() - 200))

    def has_motion(self):
        key = (self.spec.get("art_id"), self.spec.get("animation_id"))
        if key != getattr(self, "_motion_key", None):
            from .motion_pack import load_pack, MotionPlayer
            self._motion_key = key
            self._motion_available = bool(load_pack(key[1], key[0]))
            self.motion_player = MotionPlayer()
            self.motion_clip, self.motion_time = "idle_front", 0.0
        return self._motion_available

    def bite(self, point: QPointF, callback, label="", tab=False):
        if self.action:
            return False
        # Pointer reactions never replace or complete a guardian action.
        self.reaction = None
        self.move(round(self.px), round(self.py))
        marker = None
        if tab and self.isVisible():
            if self.tab_marker is None:
                self.tab_marker = TabTarget(point, label, self)
            else:
                self.tab_marker.show_at(point, label)
            marker = self.tab_marker
        # An action can face its target without changing the saved walking preference.
        self.direction = 1 if point.x() >= self.px + 72 else -1
        anchor = QPointF(77 if self.direction >= 0 else 144 - 77, 82)
        if self.spec.get("kind") == "artwork":
            from .artwork import load_artwork
            if not load_artwork(self.spec.get("art_id")).isNull():
                x = 144 * self.spec["mouth_x"]
                anchor = QPointF(x if self.direction >= 0 else 144 - x, 144 * self.spec["mouth_y"])
        if self.has_motion():
            from .motion_pack import frame
            # Latch the target-facing clip for the entire action, independent of cursor gaze.
            item = frame(self.spec, "bite_right" if self.direction >= 0 else "bite_left", .72)
            if item is not None:
                anchor = QPointF(144 * item[1][0], 144 * item[1][1])
        self.action = {"start": time.monotonic(), "from": QPointF(self.px, self.py),
                       "to": point - anchor, "point": point, "callback": callback, "hit": False, "label": label,
                       "marker": marker}
        # Even when the pet is hidden, preserve the timing for browser close acknowledgements.
        return True

    def cancel_bite(self):
        self.clear_marker()
        self.action = None
        self.reaction = None
        self.hovered = False
        self._motion_key = None
        from .motion_pack import MotionPlayer
        self.motion_player = MotionPlayer()
        self.motion_clip = "idle_front"
        self.motion_time = 0.0
        self.home()

    def clear_marker(self):
        marker = self.action.get("marker") if self.action else None
        if marker:
            marker.hide()
            self.action["marker"] = None

    def dispose(self):
        self.timer.stop()
        self.reaction = None
        self.hovered = False
        self.clear_marker()
        self.action = None
        app = QApplication.instance()
        app.screenAdded.disconnect(self.screen_changed)
        app.screenRemoved.disconnect(self.screen_changed)
        app.screenAdded.disconnect(self.watch_screen)
        for screen in app.screens():
            screen.availableGeometryChanged.disconnect(self.screen_changed)
            screen.geometryChanged.disconnect(self.screen_changed)
        for crack in self.cracks:
            crack.timer.stop()
            crack.close()
            crack.deleteLater()
        self.cracks.clear()
        if self.tab_marker:
            self.tab_marker.close()
            self.tab_marker.deleteLater()
            self.tab_marker = None
        self.close()
        self.deleteLater()

    def tick(self):
        now = time.monotonic()
        dt = min(0.1, now - self.last_tick)
        self.last_tick = now
        self.phase += dt * 9
        if self.reaction and now - self.reaction["start"] >= self.reaction["duration"]:
            self.reaction = None
        if not self.action and not self.reaction and not self.hovered and now >= self.next_idle:
            self.react("wave")
            self.next_idle = now + random.uniform(12, 20)
        action = self.action
        if action:
            elapsed = now - action["start"]
            if self.has_motion():
                self.motion_clip = "bite_right" if self.direction >= 0 else "bite_left"
                self.motion_time = min(elapsed, .99)
            if elapsed <= 0.72:
                t = elapsed / 0.72
                pos = action["from"] * (1 - t) + action["to"] * t
                pos.setY(pos.y() - math.sin(t * math.pi) * 120)
            elif elapsed < 1.0:
                pos = action["to"]
                if self.has_motion():
                    from .motion_pack import frame
                    item = frame(self.spec, self.motion_clip, elapsed)
                    if item is not None:
                        pos = action["point"] - QPointF(item[1][0] * 144, item[1][1] * 144)
                if not action["hit"]:
                    action["hit"] = True
                    if self.isVisible():
                        if not self.cracks:
                            self.cracks.append(Crack(action["point"], action["label"], self))
                        else:
                            self.cracks[0].show_at(action["point"], action["label"])
                    if self.action is not action:
                        self.update()
                        return
                    action["callback"]()
                    if self.action is not action:
                        self.update()
                        return  # Cancellation/recovery must not restore the stale jump coordinates.
            elif elapsed < 1.75:
                t = (elapsed - 1.0) / 0.75
                pos = action["to"] * (1 - t) + action["from"] * t
                pos.setY(pos.y() - math.sin(t * math.pi) * 80)
            else:
                pos = action["from"]
                self.clear_marker()
                self.action = None
                self.direction = self.walk_direction
                # Return to the current desktop floor, even if the saved launch
                # point was stale after a display/overlay geometry transition.
                screen = QApplication.screenAt((pos + QPointF(72,72)).toPoint()) or QApplication.primaryScreen()
                if screen:
                    area = screen.availableGeometry()
                    pos.setX(max(area.left(), min(pos.x(), area.right() - self.width() + 1)))
                    pos.setY(max(area.top(), area.bottom() - self.height() + 1))
            self.px, self.py = pos.x(), pos.y()
        elif self.isVisible():
            screens = self.screens()
            if not screens:
                return
            screen = QApplication.screenAt(QPointF(self.px + 72, self.py + 72).toPoint())
            if screen not in screens:
                self.home()
                screen = QApplication.primaryScreen()
            area = screen.availableGeometry()
            travel = not self.hovered and self.reaction is None
            if self.has_motion():
                if now >= self.next_pause and now >= self.pause_until:
                    self.pause_until = now + random.uniform(1.5, 2.5)
                    self.next_pause = self.pause_until + random.uniform(7, 13)
                desired_travel = travel and now >= self.pause_until
                pose = self.reaction["kind"] if self.reaction else "idle_front"
                self.motion_clip, self.motion_time, travel = self.motion_player.update(desired_travel, self.direction, pose, now)
            if travel:
                self.px += self.direction * dt * 42
            # At each edge, continue onto the next extended display; wrap at the outer edge.
            if self.px + 72 > area.right():
                index = (screens.index(screen) + 1) % len(screens)
                area = screens[index].availableGeometry()
                self.use_screen(screens[index])
                self.px = float(area.left())
            elif self.px + 72 < area.left():
                index = (screens.index(screen) - 1) % len(screens)
                area = screens[index].availableGeometry()
                self.use_screen(screens[index])
                self.px = float(area.right() - 72)
            self.py = float(max(area.top(), area.bottom() - self.height() + 1))
        display_y = self.py
        if not self.action and self.reaction and self.reaction["kind"] == "hop":
            elapsed = max(0, min(1, (now - self.reaction["start"]) / self.reaction["duration"]))
            screen = QApplication.screenAt(QPointF(self.px + 72, self.py + 72).toPoint()) or QApplication.primaryScreen()
            display_y = max(screen.availableGeometry().top(), self.py - math.sin(elapsed * math.pi) * 28) if screen else self.py
        self.move(round(self.px), round(display_y))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        # Clear the full translucent backing surface before each articulated frame.
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        pose = "walk" if self.action else self.reaction["kind"] if self.reaction else "hover" if self.hovered else "walk"
        facing = self.look_direction if self.hovered and not self.action else self.direction
        draw_character(p, self.spec, self.phase, facing, bool(self.action and self.action["hit"]), pose,
                       self.motion_clip if self.has_motion() else None, self.motion_time)
        if not self.action and (self.hovered or self.reaction):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#f9ce80"))
            for index in range(3):
                x = 19 + index * 50
                y = 16 + math.sin(self.phase * .8 + index) * 5
                p.drawEllipse(QPointF(x, y), 2.5, 2.5)

    def mouseDoubleClickEvent(self, _):
        self.reaction = None
        self.settings_requested.emit()

    def contextMenuEvent(self, event):
        self.settings_requested.emit()
        event.accept()
