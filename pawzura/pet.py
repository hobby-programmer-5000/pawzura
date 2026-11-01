"""Original vector SD character, articulated at runtime; no sprite/video dependencies."""
from __future__ import annotations

import math
import random
import time
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QWidget
from .config import safe_character


def draw_character(painter: QPainter, spec: dict, phase=0.0, facing=1, biting=False):
    p = painter
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.save()
    if facing < 0:
        p.translate(144, 0)
        p.scale(-1, 1)
    outline = QColor("#34304a")
    body = QColor(spec["body"])
    accent = QColor(spec["accent"])
    p.setPen(QPen(outline, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    bounce = abs(math.sin(phase)) * 3
    p.translate(0, -bounce)
    # Tail and articulated feet.
    p.setBrush(body.lighter(110))
    p.drawEllipse(QRectF(28, 99 + math.sin(phase) * 2, 24, 20))
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
    elif ear == "cat":
        p.drawPolygon(QPolygonF([QPointF(32, 49), QPointF(32, 18), QPointF(58, 34)]))
        p.drawPolygon(QPolygonF([QPointF(86, 34), QPointF(110, 18), QPointF(112, 51)]))
    else:
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
    for x in (53, 94):
        p.setBrush(outline)
        if blink:
            p.setPen(QPen(outline, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x - 5, 67), QPointF(x + 5, 67))
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.drawEllipse(QRectF(x - 5, 57, 11, 17))
            p.setBrush(QColor("#fffdf7"))
            p.drawEllipse(QRectF(x - 2, 59, 4, 5))
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
    else:
        p.drawEllipse(QRectF(66, 101, 20, 12))
        p.drawLine(QPointF(67, 112), QPointF(84, 103))
    p.setBrush(body)
    p.drawEllipse(QRectF(38, 103 + math.sin(phase) * 4, 16, 19))
    p.drawEllipse(QRectF(98, 103 - math.sin(phase) * 4, 16, 19))
    p.restore()


class CharacterPreview(QWidget):
    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.phase = 0.0
        self.setMinimumSize(200, 220)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40)

    def tick(self):
        if self.isVisible():
            self.phase += 0.14
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#22263b"))
        p.drawRoundedRect(self.rect(), 22, 22)
        scale = min(self.width() / 180, self.height() / 180)
        p.translate((self.width() - 144 * scale) / 2, (self.height() - 144 * scale) / 2)
        p.scale(scale, scale)
        p.setBrush(QColor("#171b2b"))
        p.drawEllipse(QRectF(37, 137, 72, 7))
        draw_character(p, self.spec, self.phase)


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

    def __init__(self, spec):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Pawzura companion")
        self.resize(144, 146)
        self.spec = safe_character(spec)
        self.phase = 0.0
        self.direction = 1
        self.last_tick = time.monotonic()
        self.action = None
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

    def watch_screen(self, screen):
        screen.availableGeometryChanged.connect(self.screen_changed)
        screen.geometryChanged.connect(self.screen_changed)

    def screen_changed(self, *_):
        self.cancel_bite()
        self.update()

    def screens(self):
        return sorted(QApplication.screens(), key=lambda s: (s.geometry().x(), s.geometry().y()))

    def home(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.px, self.py = 0.0, 0.0
            return
        area = screen.availableGeometry()
        self.px = float(area.x() + max(0, (area.width() - self.width()) // 2))
        self.py = float(max(area.top(), area.bottom() - self.height() + 1))
        self.move(round(self.px), round(self.py))

    def tab_target_point(self):
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        return QPointF(area.center().x(), max(area.top() + 100, area.bottom() - 200))

    def bite(self, point: QPointF, callback, label="", tab=False):
        if self.action:
            return False
        marker = None
        if tab and self.isVisible():
            if self.tab_marker is None:
                self.tab_marker = TabTarget(point, label, self)
            else:
                self.tab_marker.show_at(point, label)
            marker = self.tab_marker
        self.action = {"start": time.monotonic(), "from": QPointF(self.px, self.py),
                       "to": point - QPointF(77, 82), "point": point, "callback": callback, "hit": False, "label": label,
                       "marker": marker}
        # Even when the pet is hidden, preserve the timing for browser close acknowledgements.
        return True

    def cancel_bite(self):
        self.clear_marker()
        self.action = None
        self.home()

    def clear_marker(self):
        marker = self.action.get("marker") if self.action else None
        if marker:
            marker.hide()
            self.action["marker"] = None

    def dispose(self):
        self.timer.stop()
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
        action = self.action
        if action:
            elapsed = now - action["start"]
            if elapsed <= 0.72:
                t = elapsed / 0.72
                pos = action["from"] * (1 - t) + action["to"] * t
                pos.setY(pos.y() - math.sin(t * math.pi) * 120)
            elif elapsed < 1.0:
                pos = action["to"]
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
            self.px += self.direction * dt * 42
            # At each edge, continue onto the next extended display; wrap at the outer edge.
            if self.px + 72 > area.right():
                index = (screens.index(screen) + 1) % len(screens)
                area = screens[index].availableGeometry()
                self.px = float(area.left())
            self.py = float(max(area.top(), area.bottom() - self.height() + 1))
        self.move(round(self.px), round(self.py))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        # Clear the full translucent backing surface before each articulated frame.
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        draw_character(p, self.spec, self.phase, self.direction, bool(self.action and self.action["hit"]))

    def mouseDoubleClickEvent(self, _):
        self.settings_requested.emit()

    def contextMenuEvent(self, event):
        self.settings_requested.emit()
        event.accept()
