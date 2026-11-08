"""Render a staged README demo offscreen; never inspect or close desktop targets.

Only in-memory scene flags are changed by Pet.bite callbacks. This is an
illustration of the interaction, not native/browser integration evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QLinearGradient, QPainter, QPen, QRawFont
from PySide6.QtWidgets import QApplication
from pawzura.config import default_character
from pawzura.pet import Crack, Pet, TabTarget, draw_character

WIDTH, HEIGHT, FPS, DURATION = 1120, 700, 24, 16
APP_START, TAB_START = 3.2, 9.2
COPY = {
    "en": {
        "tag": "FEATURE DEMO", "subtitle": "A little companion for your focus time.",
        "browser": "Demo Browser", "notes": "Focus notes", "feed": "Break feed",
        "app": "Break Arcade", "play": "One more round?", "app_detail": "Demo window",
        "focus": "Today, one thing at a time.", "focus_detail": "Draft the next small idea.",
        "check": "A clear plan", "check2": "Room to think", "check3": "Your work stays here",
        "feed_title": "A little detour...", "feed_detail": "Just one more scroll?",
        "closed": "Break Arcade closed", "kept": "Allowed work stays open", "marker": "Blocked tab",
        "foot": "Close distractions. Keep your focus. Let Pawzura handle the little interruptions.",
        "captions": [
            ("Meet your little focus companion.", "Keep the work you need. Clear the distractions you don't."),
            ("An unlisted app? Jump, bite, close.", "Close Break Arcade and get back to what you meant to do."),
            ("Keep the work you meant to do.", "Your allowed Focus notes stays right where you left it."),
            ("A distracting tab gets its own target.", "Pawzura uses a separate marker for tabs, away from the browser's X."),
            ("One tab closes. Your browser stays.", "The allowed tab is still open. Back to your focus time."),
            ("Small companion. A calmer workspace.", "Start with preview mode ON. Set your allowlists before enabling live control."),
        ],
    },
    "ko": {
        "tag": "기능 데모", "subtitle": "나만의 집중 시간을 지키는 작은 발걸음.",
        "browser": "데모 브라우저", "notes": "집중 노트", "feed": "잠깐 피드",
        "app": "딴짓 아케이드", "play": "한 판 더 할까요?", "app_detail": "가상 창",
        "focus": "오늘은 하나씩, 차근차근.", "focus_detail": "다음 작은 아이디어를 적어요.",
        "check": "분명한 계획", "check2": "생각할 여유", "check3": "내 작업은 그대로",
        "feed_title": "잠깐만 볼까…", "feed_detail": "조금만 더 내려 볼까요?",
        "closed": "딴짓 아케이드 종료", "kept": "허용한 작업은 그대로", "marker": "차단 대상 탭",
        "foot": "딴짓은 정리하고, 집중할 작업은 그대로. 작은 방해는 Pawzura에게 맡기세요.",
        "captions": [
            ("작은 친구와 함께하는 집중 시간.", "필요한 작업은 지키고, 집중을 방해하는 딴짓은 정리해요."),
            ("허용하지 않은 프로그램? 점프, 콱, 종료!", "딴짓 아케이드를 닫고, 하려던 작업으로 돌아가요."),
            ("하려던 작업은 그대로 남겨 두고.", "허용한 집중 노트는 열려 있어요."),
            ("딴짓 탭에는 별도의 표적을 띄워요.", "브라우저의 실제 X 위치를 추측하지 않고, 따로 만든 표적에 반응합니다."),
            ("탭 하나만 닫고, 브라우저는 그대로.", "허용한 탭은 열려 있어요. 다시 내 작업에 집중하세요."),
            ("작은 친구, 조금 더 차분한 작업 공간.", "미리보기 ON으로 시작하세요. 실제 제어 전 허용 목록을 설정하세요."),
        ],
    },
}


def rounded(p, x, y, w, h, color, radius=12, border=None):
    p.setPen(QPen(QColor(border), 1) if border else Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(x, y, w, h), radius, radius)


def label(p, language, value, x, y, w, h=28, size=16, color="#eaeaf5", bold=False):
    font = QFont("Malgun Gothic" if language == "ko" else "Segoe UI")
    font.setPixelSize(size)
    font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    p.setFont(font)
    p.setPen(QColor(color))
    p.drawText(QRectF(x, y, w, h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)


def cross(p, x, y, color="#d6d9e6", size=4):
    p.setPen(QPen(QColor(color), 1.7))
    p.drawLine(QPointF(x - size, y - size), QPointF(x + size, y + size))
    p.drawLine(QPointF(x - size, y + size), QPointF(x + size, y - size))


def checkmark(p, x, y, color="#c3b2f4"):
    p.setPen(QPen(QColor(color), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(x, y), QPointF(x + 4, y + 4))
    p.drawLine(QPointF(x + 4, y + 4), QPointF(x + 12, y - 5))


def caption_index(t):
    return 0 if t < 2.7 else 1 if t < 5.8 else 2 if t < 8.3 else 3 if t < 11.5 else 4 if t < 13.6 else 5


def render_scene(language, t, pet, state, marker, crack, hits):
    c = COPY[language]
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_RGB888)
    image.fill(QColor("#111522"))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    label(p, language, "Pawzura", 32, 17, 450, 44, 35, "#cdb9fa", True)
    label(p, language, c["subtitle"], 34, 63, 760, 28, 17, "#acb4ca")
    rounded(p, 920, 31, 166, 35, "#29293d", 17)
    label(p, language, c["tag"], 939, 34, 150, 28, 14, "#d4c4fa", True)
    gradient = QLinearGradient(28, 114, 1092, 560)
    gradient.setColorAt(0, QColor("#25364b")); gradient.setColorAt(1, QColor("#30304e"))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(gradient)
    p.drawRoundedRect(QRectF(28, 114, 1064, 446), 18, 18)
    # The entire desktop, including window chrome, is drawn from original shapes.
    if state["app"]:
        rounded(p, 65, 156, 338, 252, "#151b2d", 13)
        rounded(p, 62, 150, 338, 252, "#333149", 13, "#626078")
        label(p, language, c["app"], 79, 158, 270, 31, 15, bold=True)
        rounded(p, 359, 159, 30, 28, "#7d4558", 7); cross(p, 374, 173)
        rounded(p, 76, 196, 310, 192, "#242239", 10)
        for row in range(2):
            for col in range(5):
                rounded(p, 100 + col * 49, 216 + row * 29, 37, 17,
                        ("#b7a4e9", "#e2bb86", "#8abbb9")[(row + col) % 3], 5)
        label(p, language, c["play"], 99, 287, 280, 33, 21, "#f6dcad", True)
        label(p, language, c["app_detail"], 99, 328, 280, 25, 14, "#b6b2cc")
    else:
        rounded(p, 80, 231, 298, 88, "#252b40", 13)
        checkmark(p, 104, 258)
        label(p, language, c["closed"], 128, 245, 236, 28, 19, "#c3b2f4", True)
        label(p, language, c["kept"], 102, 279, 262, 24, 14, "#a8c9c8")
    # Fictional tab list: closing a tab updates only the in-memory scene list.
    rounded(p, 439, 156, 612, 330, "#141b2d", 13)
    rounded(p, 436, 150, 612, 330, "#212a3b", 13, "#647087")
    label(p, language, c["browser"], 451, 158, 170, 28, 13, "#b0bad1")
    cross(p, 1026, 173, size=4)
    rounded(p, 453, 194, 203, 34, "#45566b" if not state["tab"] else "#323e52", 8)
    label(p, language, c["notes"], 466, 197, 166, 27, 14)
    cross(p, 639, 211, size=3)
    if state["tab"]:
        rounded(p, 664, 194, 207, 34, "#594b63", 8)
        label(p, language, c["feed"], 679, 197, 167, 27, 14, "#f2d4b2")
        cross(p, 852, 211, size=3)
    rounded(p, 453, 238, 578, 28, "#161f30", 7)
    label(p, language, "break.example/feed" if state["tab"] else "focus.example/notes", 467, 238, 550, 28, 13, "#b0bad1")
    rounded(p, 453, 277, 578, 186, "#2d354b" if state["tab"] else "#293e4c", 9)
    if state["tab"]:
        label(p, language, c["feed_title"], 476, 292, 510, 37, 25, "#f3d2ac", True)
        label(p, language, c["feed_detail"], 477, 332, 510, 27, 15, "#b6b9ce")
        for col in range(3):
            rounded(p, 478 + col * 178, 377, 158, 60, ("#58455c", "#3c5068", "#5d5146")[col], 9)
            for bar in range(2):
                rounded(p, 491 + col * 178, 393 + bar * 17, 93 - bar * 25, 6, "#b9afc8", 3)
    else:
        label(p, language, c["focus"], 476, 290, 525, 36, 24, "#cce5df", True)
        label(p, language, c["focus_detail"], 478, 330, 510, 27, 15, "#a9c8c5")
        for i, key in enumerate(("check", "check2", "check3")):
            checkmark(p, 482, 381 + i * 26, "#d5e9df")
            label(p, language, c[key], 505, 369 + i * 26, 475, 25, 15, "#d5e9df")
    # An invented taskbar, not a screenshot of the user's shell.
    rounded(p, 40, 529, 1040, 22, "#1d2437", 10)
    for i, color in enumerate(("#bba4ed", "#8cbdb7", "#d6b686")):
        rounded(p, 518 + i * 33, 533, 16, 14, color, 4)
    if TAB_START <= t < TAB_START + 1.75:
        p.drawPixmap(marker.pos(), marker.grab())
    # The same Pet state and painter used by the app drive the character.
    p.save(); p.translate(pet.px, pet.py)
    draw_character(p, pet.spec, pet.phase, pet.direction,
                   bool(pet.action and pet.action["hit"]), "walk")
    p.restore()
    for kind, hit_time in hits:
        if 0 <= t - hit_time < .85:
            point = QPointF(374, 173) if kind == "app" else QPointF(870, 479)
            crack.move(round(point.x()) - 75, round(point.y()) - 75)
            crack.born = 1000 + hit_time
            p.drawPixmap(crack.pos(), crack.grab())
    headline, detail = c["captions"][caption_index(t)]
    label(p, language, headline, 34, 573, 1050, 42, 26, "#f1edf9", True)
    label(p, language, detail, 35, 619, 1050, 28, 17, "#b2bad0")
    label(p, language, c["foot"], 35, 660, 1020, 25, 12, "#8d99b1")
    rounded(p, 32, 692, (WIDTH - 64) * min(1, t / (DURATION - 1 / FPS)), 3, "#bca5ec", 1)
    p.end()
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=tuple(COPY), default="en")
    parser.add_argument("--output", type=Path, required=True, help="New frame directory; refuses overwrite")
    args = parser.parse_args()
    app = QApplication([])
    if QGuiApplication.platformName() != "offscreen":
        raise SystemExit("This renderer requires the offscreen Qt platform")
    # Like the application's smoke renderer, offscreen Qt needs its fonts
    # registered explicitly. Only rendered pixels are exported, never fonts.
    fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("segoeui.ttf", "seguisb.ttf", "malgun.ttf", "malgunbd.ttf"):
        if QFontDatabase.addApplicationFont(str(fonts / name)) < 0:
            raise SystemExit(f"Required Windows system font unavailable: {name}")
    font = QFont("Malgun Gothic" if args.language == "ko" else "Segoe UI", 10)
    app.setFont(font)
    raw = QRawFont.fromFont(font)
    assert all(raw.supportsCharacter(ord(char)) for char in ("Pawzura" if args.language == "en" else "가상집중노트"))
    args.output.mkdir(parents=True, exist_ok=False)
    pet = Pet(default_character(), args.language)
    pet.timer.stop(); pet.pinned = True; pet.next_idle = float("inf")
    pet.px, pet.py, pet.last_tick = 108., 398., 1000.
    marker = TabTarget(QPointF(870, 479), COPY[args.language]["marker"])
    marker.hide()
    crack = Crack(QPointF(374, 173)); crack.timer.stop(); crack.hide()
    state = {"app": True, "tab": True, "allowed_tab": True}
    hits, started = [], set()
    previous_t = 0.
    def close_mock(kind, t):
        assert state[kind] is True and state["allowed_tab"] is True
        state[kind] = False; hits.append((kind, t))
    try:
        for frame in range(FPS * DURATION):
            t = frame / FPS
            with patch("pawzura.pet.time.monotonic", return_value=1000 + t):
                for kind, start, point in (("app", APP_START, QPointF(374, 173)),
                                           ("tab", TAB_START, QPointF(870, 479))):
                    if t >= start and kind not in started:
                        assert pet.bite(point, lambda k=kind: close_mock(k, frame / FPS), tab=kind == "tab")
                        started.add(kind)
                if pet.action is None:
                    pet.px += (t - previous_t) * 31
                pet.tick()
                image = render_scene(args.language, t, pet, state, marker, crack, hits)
                assert image.save(str(args.output / f"frame-{frame:04d}.png"))
            previous_t = t
        assert state == {"app": False, "tab": False, "allowed_tab": True}
        assert [kind for kind, t in hits] == ["app", "tab"]
        record = {"language": args.language, "size": [WIDTH, HEIGHT], "fps": FPS,
                  "frames": FPS * DURATION, "duration_seconds": DURATION,
                  "qt_platform": QGuiApplication.platformName(), "simulation_only": True,
                  "callbacks": hits, "final_scene": state, "desktop_capture": False,
                  "native_close_calls": 0, "browser_connections": 0,
                  "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (args.output / "render.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record))
    finally:
        pet.dispose(); marker.close(); crack.close()


if __name__ == "__main__":
    main()
