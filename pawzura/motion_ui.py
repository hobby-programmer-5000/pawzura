"""Editable, local cutout geometry with live limb-motion preview."""
import copy
import math
import time
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QThread, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QPainterPath, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QPushButton, QCheckBox, QProgressBar, QScrollArea, QLayout)
from .art_rig import PARTS, safe_rig
from .artwork import load_artwork
from .art_client import detect_motion, prepare_motion
from .characters import GenerationError
from .config import safe_character
from .pet import CharacterPreview

TEXT = {
    "en": {
        "title": "Artwork motion · hands and feet", "parts": ("Image-left arm/hand", "Image-right arm/hand", "Image-left foot", "Image-right foot"),
        "help": "Choose a part. Drag inside its outline to move it; drag a square corner to resize, or the circle to move its joint. Drag empty space to draw a new rectangle. Keep the outline around that limb, then inspect Walk and Wave before applying.",
        "enabled": "Enable independent hand/foot motion", "walk": "Walk", "wave": "Wave", "hop": "Hop", "cheer": "Cheer",
        "auto": "Estimate joints automatically", "prepare": "Prepare CPU motion helper (~350 MB)",
        "license": 'Optional helper: <a href="https://huggingface.co/usyd-community/vitpose-base-simple">ViTPose base · Apache-2.0</a>, local CPU inference. Preparation reuses the separate image runtime and adds SciPy. Read the model/license guide before downloading. No animation/video model runs while the pet walks.',
        "limits": "This moves cutout pixels, not a 3D skeleton or AI video. Joint estimates can be wrong for animals, hidden limbs or unusual clothing. Revealed sleeve gaps use simple edge blending; check for seams and adjust the areas. The original PNG stays intact.",
        "ready": "Inspect all four areas and joints. Changes apply only when you use the motion settings and save the main settings.",
        "invalid": "Choose small nonzero areas for all four limbs and keep each joint near its area.",
        "busy": "Preparing/estimating locally… keep this window open.",
        "failed": "Automatic motion setup is unavailable or uncertain. Prepare the helper and retry, or adjust the four areas manually; no image regeneration is needed.",
        "prepared": "Helper prepared. Click Estimate joints automatically.",
        "detected": "Joint/limb suggestions are ready. Check the outlines and preview; correct anything misplaced.",
        "use": "Use motion settings", "cancel": "Cancel", "reset": "Reset suggested areas",
    },
    "ko": {
        "title": "그림 움직임 · 손발 설정", "parts": ("그림 왼쪽 팔/손", "그림 오른쪽 팔/손", "그림 왼쪽 발", "그림 오른쪽 발"),
        "help": "부위를 고르세요. 윤곽 안을 끌면 이동, 네모 모서리는 크기 조절, 동그라미는 관절 이동입니다. 빈 곳을 끌면 새 사각형을 그립니다. 해당 손발만 감싼 뒤 걷기·인사 미리보기를 확인하세요.",
        "enabled": "손발을 각각 움직이기", "walk": "걷기", "wave": "인사", "hop": "점프", "cheer": "환호",
        "auto": "관절 자동 추정", "prepare": "CPU 움직임 도우미 준비 (약 350 MB)",
        "license": '선택 도우미: <a href="https://huggingface.co/usyd-community/vitpose-base-simple">ViTPose base · Apache-2.0</a>, 로컬 CPU 추론입니다. 별도 그림 환경을 재사용하고 SciPy를 추가합니다. 다운로드 전에 모델·라이선스 안내를 확인하세요. 걷는 동안 애니메이션·영상 모델을 실행하지 않습니다.',
        "limits": "3D 뼈대·AI 영상이 아닌 그림 조각 움직임입니다. 동물·가려진 팔다리·특이한 의상은 추정이 틀릴 수 있습니다. 팔을 옮겨 드러난 틈은 단순 가장자리 혼합이므로 경계를 확인하고 영역을 조정하세요. 원본 PNG는 유지합니다.",
        "ready": "네 부위와 관절을 확인하세요. 움직임 설정 사용 후 본창의 설정 저장을 눌러야 적용됩니다.",
        "invalid": "네 손발에 적당한 크기의 영역을 만들고 관절을 해당 영역 가까이에 두세요.",
        "busy": "로컬에서 준비·추정 중… 창을 열어 두세요.",
        "failed": "자동 설정 도우미가 없거나 추정이 불확실합니다. 도우미 준비 후 재시도하거나 네 영역을 직접 조정하세요. 그림을 다시 생성할 필요는 없습니다.",
        "prepared": "도우미를 준비했습니다. 관절 자동 추정을 누르세요.",
        "detected": "관절·손발 영역을 제안했습니다. 윤곽과 미리보기를 확인하고 잘못된 곳을 조정하세요.",
        "use": "움직임 설정 사용", "cancel": "취소", "reset": "제안 영역 초기화",
    },
}


def default_rig():
    parts = {}
    for name, x, y, w, h in (("left_hand", .28, .53, .13, .16), ("right_hand", .61, .53, .13, .16),
                              ("left_foot", .38, .82, .12, .13), ("right_foot", .53, .82, .12, .13)):
        parts[name] = {"polygon": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], "pivot": [x + w / 2, y + .01]}
    return {"version": 1, "parts": parts}


class RegionCanvas(QWidget):
    changed = Signal()
    COLORS = ("#f6bd60", "#8dd9cc", "#ed91ba", "#a7bfff")

    def __init__(self, spec, rig, theme="dark", parent=None):
        super().__init__(parent)
        self.image = load_artwork(spec["art_id"])
        self.rig = copy.deepcopy(rig)
        self.active = PARTS[0]
        self.theme = theme
        self.drag = None
        self.setMinimumSize(320, 380)
        self.setMouseTracking(True)

    def frame(self):
        side = max(1, min(self.width(), self.height()) - 24)
        return QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

    def to_local(self, point):
        frame = self.frame()
        return QPointF(frame.x() + point[0] * frame.width(), frame.y() + point[1] * frame.height())

    def normalized(self, point):
        frame = self.frame()
        return [max(0, min(1, (point.x() - frame.x()) / frame.width())),
                max(0, min(1, (point.y() - frame.y()) / frame.height()))]

    @staticmethod
    def bounds(item):
        xs, ys = [p[0] for p in item["polygon"]], [p[1] for p in item["polygon"]]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f0edf7" if self.theme == "light" else "#22263b"))
        painter.drawImage(self.frame(), self.image)
        for index, name in enumerate(PARTS):
            item = self.rig["parts"][name]
            color = QColor(self.COLORS[index])
            painter.setPen(QPen(color, 2 if name == self.active else 1))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 45))
            painter.drawPolygon(QPolygonF([self.to_local(p) for p in item["polygon"]]))
            painter.setBrush(color)
            painter.drawEllipse(self.to_local(item["pivot"]), 5, 5)
            if name == self.active:
                rect = self.bounds(item)
                for point in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
                    local = self.to_local([point.x(), point.y()])
                    painter.drawRect(QRectF(local.x() - 4, local.y() - 4, 8, 8))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.frame().contains(event.position()):
            return
        point = self.normalized(event.position())
        item = copy.deepcopy(self.rig["parts"][self.active])
        pivot = self.to_local(item["pivot"])
        if math.hypot(event.position().x() - pivot.x(), event.position().y() - pivot.y()) <= 10:
            self.drag = ("pivot", point, item, None)
            return
        rect = self.bounds(item)
        corners = (rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft())
        for index, corner in enumerate(corners):
            local = self.to_local([corner.x(), corner.y()])
            if math.hypot(event.position().x() - local.x(), event.position().y() - local.y()) <= 10:
                opposite = corners[(index + 2) % 4]
                self.drag = ("resize", point, item, [opposite.x(), opposite.y()])
                return
        path = QPainterPath()
        path.addPolygon(QPolygonF([QPointF(*p) for p in item["polygon"]]))
        self.drag = ("move" if path.contains(QPointF(*point)) else "new", point, item, None)

    def mouseMoveEvent(self, event):
        if self.drag is None:
            return
        mode, start, original, anchor = self.drag
        point = self.normalized(event.position())
        item = copy.deepcopy(original)
        if mode == "pivot":
            item["pivot"] = point
        elif mode == "move":
            delta = [point[i] - start[i] for i in (0, 1)]
            all_points = original["polygon"] + [original["pivot"]]
            delta = [max(-min(p[i] for p in all_points), min(delta[i], 1 - max(p[i] for p in all_points))) for i in (0, 1)]
            item = {"polygon": [[p[i] + delta[i] for i in (0, 1)] for p in original["polygon"]],
                    "pivot": [original["pivot"][i] + delta[i] for i in (0, 1)]}
        else:
            anchor = anchor or start
            rect = QRectF(QPointF(*anchor), QPointF(*point)).normalized()
            if rect.width() < .01 or rect.height() < .01:
                return
            if mode == "new":
                item = {"polygon": [[rect.left(), rect.top()], [rect.right(), rect.top()],
                                    [rect.right(), rect.bottom()], [rect.left(), rect.bottom()]],
                        "pivot": [rect.center().x(), rect.top() + min(.01, rect.height() / 4)]}
            else:
                old = self.bounds(original)
                def scaled(p):
                    return [rect.left() + (p[0] - old.left()) / max(.001, old.width()) * rect.width(),
                            rect.top() + (p[1] - old.top()) / max(.001, old.height()) * rect.height()]
                item = {"polygon": [scaled(p) for p in original["polygon"]], "pivot": scaled(original["pivot"])}
        self.rig["parts"][self.active] = item
        self.changed.emit()
        self.update()

    def mouseReleaseEvent(self, event):
        self.drag = None


class MotionWorker(QThread):
    progress = Signal(object)
    succeeded = Signal(object)
    failed = Signal()

    def __init__(self, spec, prepare=False, parent=None):
        super().__init__(parent)
        self.spec, self.prepare = spec, prepare

    def run(self):
        try:
            if self.prepare:
                prepare_motion(self.progress.emit)
                result = None
            else:
                result = detect_motion(self.spec, self.progress.emit)
            self.succeeded.emit(result)
        except Exception:
            self.failed.emit()


class MotionDialog(QDialog):
    chosen = Signal(dict)

    def __init__(self, spec, language="en", theme="dark", parent=None, owner=None):
        super().__init__(parent)
        self.spec = safe_character(spec)
        self.t = TEXT.get(language, TEXT["en"])
        from .art_ui import TEXT as ART_TEXT
        self.art_text = ART_TEXT.get(language, ART_TEXT["en"])
        self.owner = owner or parent
        self.worker = None
        self.setWindowTitle(self.t["title"])
        self.resize(920, 720)
        self.setMinimumSize(800, 600)
        frame_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        outer = QVBoxLayout(body)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        outer.addWidget(self.label(self.t["help"]))
        self.enabled = QCheckBox(self.t["enabled"])
        self.enabled.setChecked(True)
        outer.addWidget(self.enabled)
        row = QHBoxLayout()
        self.canvas = RegionCanvas(self.spec, safe_rig(self.spec.get("rig")) or default_rig(), theme)
        row.addWidget(self.canvas, 1)
        controls = QVBoxLayout()
        self.select = QComboBox()
        for name, caption in zip(PARTS, self.t["parts"]):
            self.select.addItem(caption, name)
        self.select.currentIndexChanged.connect(self.selection)
        controls.addWidget(self.select)
        self.preview = CharacterPreview(self.spec)
        self.preview.theme = theme
        self.preview.setFixedSize(240, 260)
        controls.addWidget(self.preview)
        self.pose = QComboBox()
        for key in ("walk", "wave", "hop", "cheer"):
            self.pose.addItem(self.t[key], key)
        self.pose.currentIndexChanged.connect(lambda: setattr(self.preview, "pose", self.pose.currentData()))
        controls.addWidget(self.pose)
        self.auto = QPushButton(self.t["auto"])
        self.auto.clicked.connect(lambda: self.start(False))
        controls.addWidget(self.auto)
        self.prepare = QPushButton(self.t["prepare"])
        self.prepare.clicked.connect(lambda: self.start(True))
        controls.addWidget(self.prepare)
        self.reset_button = QPushButton(self.t["reset"])
        self.reset_button.clicked.connect(self.reset)
        controls.addWidget(self.reset_button)
        controls.addStretch()
        row.addLayout(controls)
        outer.addLayout(row, 1)
        license_label = self.label(self.t["license"])
        license_label.setOpenExternalLinks(True)
        outer.addWidget(license_label)
        outer.addWidget(self.label(self.t["limits"]))
        scroll.setWidget(body)
        frame_layout.addWidget(scroll, 1)
        self.status = self.label(self.t["ready"])
        frame_layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        frame_layout.addWidget(self.progress)
        self.timing = self.label("")
        frame_layout.addWidget(self.timing)
        self.helper_timer = QTimer(self)
        self.helper_timer.setInterval(1000)
        self.helper_timer.timeout.connect(self.update_timing)
        self.helper_started = self.helper_last = None
        self.helper_stage_started = None
        self.helper_stage = None
        footer = QHBoxLayout()
        self.use = QPushButton(self.t["use"])
        self.use.setObjectName("primary")
        self.use.clicked.connect(self.choose)
        footer.addWidget(self.use)
        cancel = QPushButton(self.t["cancel"])
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        frame_layout.addLayout(footer)
        self.canvas.changed.connect(self.refresh)
        self.enabled.toggled.connect(self.refresh)
        self.refresh()

    @staticmethod
    def label(text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        return label

    def selection(self):
        self.canvas.active = self.select.currentData()
        self.canvas.update()

    def reset(self):
        self.canvas.rig = safe_rig(self.spec.get("rig")) or default_rig()
        self.canvas.update()
        self.refresh()

    def refresh(self):
        rig = safe_rig(self.canvas.rig)
        spec = copy.deepcopy(self.spec)
        spec.pop("rig", None)
        if self.enabled.isChecked() and rig is not None:
            spec["rig"] = rig
        self.preview.spec = spec
        self.preview.update()
        self.use.setEnabled(self.worker is None and (not self.enabled.isChecked() or rig is not None))
        if self.enabled.isChecked() and rig is None:
            self.status.setText(self.t["invalid"])

    def start(self, prepare):
        if self.worker is not None:
            return
        self.worker = MotionWorker(self.spec, prepare, self)
        for target in (self.owner, self.parent()):
            if target is not None:
                target.worker = self.worker
        self.worker.succeeded.connect(self.helper_succeeded)
        self.worker.progress.connect(self.helper_progress)
        self.worker.failed.connect(lambda: self.status.setText(self.t["failed"]))
        self.worker.finished.connect(self.finished_work)
        for control in (self.canvas, self.auto, self.prepare, self.enabled, self.select, self.use, self.reset_button):
            control.setEnabled(False)
        self.progress.show()
        self.progress.setRange(0, 0)
        self.helper_started = self.helper_last = time.monotonic()
        self.helper_stage_started = self.helper_started
        self.helper_stage = None
        self.helper_timer.start()
        self.update_timing()
        self.status.setText(self.t["busy"])
        self.worker.start()

    def helper_progress(self, event):
        if self.worker is None:
            return
        event = {"stage": event} if isinstance(event, str) else event
        stage = event.get("stage")
        if stage not in self.art_text:
            return
        now = time.monotonic()
        if stage != self.helper_stage:
            self.helper_stage_started = now
            self.helper_stage = stage
        self.helper_last = now
        self.status.setText(self.art_text[stage])
        if "completed" in event:
            self.progress.setRange(0, event["total"])
            self.progress.setValue(event["completed"])
        else:
            self.progress.setRange(0, 0)
        self.update_timing()

    def update_timing(self):
        if self.helper_started is None:
            return
        now = time.monotonic()
        def duration(seconds):
            minutes, seconds = divmod(max(0, int(seconds)), 60)
            return f"{minutes}:{seconds:02}"
        quiet = duration(now - self.helper_last)
        text = self.art_text["progress_time"].format(elapsed=duration(now - self.helper_started), stage=duration(now - self.helper_stage_started), quiet=quiet)
        if self.worker is not None and now - self.helper_last >= 60:
            text += "\n" + self.art_text["progress_wait"].format(quiet=quiet)
        self.timing.setText(text)

    def helper_succeeded(self, rig):
        if rig is not None:
            self.canvas.rig = rig
            self.canvas.update()
        self.status.setText(self.t["detected"] if rig else self.t["prepared"])

    def finished_work(self):
        self.helper_timer.stop()
        self.worker.deleteLater()
        self.worker = None
        self.update_timing()
        for target in (self.owner, self.parent()):
            if target is not None:
                target.worker = None
        for control in (self.canvas, self.auto, self.prepare, self.enabled, self.select, self.reset_button):
            control.setEnabled(True)
        self.progress.hide()
        self.refresh()

    def choose(self):
        if self.worker is not None:
            return
        self.chosen.emit(safe_character(self.preview.spec))
        self.accept()

    def reject(self):
        if self.worker is None:
            super().reject()
        else:
            self.status.setText(self.t["busy"])

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.status.setText(self.t["busy"])
        else:
            super().closeEvent(event)
