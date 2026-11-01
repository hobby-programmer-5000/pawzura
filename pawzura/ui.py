from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget, QInputDialog,
)
from . import __version__, windows
from .characters import MODEL, generate_character, random_character
from .config import BROWSERS
from .pet import CharacterPreview
from .policy import SiteRuleError, normalize_app, site_rule

TEXT = {
    "ko": {
        "subtitle": "작은 발걸음으로 지키는 나만의 집중 시간",
        "general": "일반", "apps": "프로그램", "web": "브라우저", "character": "캐릭터", "about": "정보",
        "guard": "집중 지킴이 켜기", "preview": "미리보기 모드 · 애니메이션만 표시하고 닫지 않기",
        "visible": "바탕화면에 캐릭터 표시", "startup": "Windows 로그인 시 자동 실행", "language": "언어",
        "save": "설정 저장", "close": "트레이로 돌아가기", "saved": "설정을 저장했습니다.",
        "intro": "먼저 미리보기로 허용 목록을 확인하세요.\n미리보기를 끄면 미허용 프로그램에 일반 닫기 요청을 보내고 미허용 탭을 닫습니다.",
        "apps_help": "허용할 실행 파일 이름을 한 줄에 하나씩 입력하세요. 경로를 붙여넣으면 파일명만 사용합니다.\nWindows 시스템 창과 이 앱은 항상 보호합니다. 같은 이름의 실행 파일은 모두 허용됩니다.",
        "browse": "실행 파일 추가…", "running": "열려 있는 프로그램 추가…", "startup_scan": "시작프로그램 다시 탐색",
        "browser_help": "브라우저마다 확장을 설치하고 연결해야 합니다. 기본 허용은 새 탭/기본 홈 화면뿐입니다.\n도메인은 사이트 전체를, 경로를 넣은 주소는 해당 구역만 허용합니다. http://와 https:// 모두 입력할 수 있습니다.",
        "browser_on": "이 브라우저의 사이트 허용 목록 적용", "pair": "연결 코드 복사", "extension": "확장 폴더 열기",
        "connection_code": "연결 코드", "port": "포트", "startup_list": "시작프로그램",
        "rules": "허용 주소 · 한 줄에 하나 (example.com 또는 github.com/my-account)",
        "site_line": "허용 주소 {line}번째 줄: {message}",
        "invalid_url": "도메인 또는 호스트가 포함된 완전한 http://·https:// 주소를 넣으세요.",
        "invalid_port": "포트는 1부터 65535 사이여야 합니다.",
        "invalid_path": "경로에서 .·.. 구역, 역슬래시와 인코딩된 구분자를 제거하세요.",
        "random": "임의 캐릭터", "generate": "Qwen으로 생성", "restore": "이전 캐릭터로 변경",
        "model_help": "Qwen이 외형 설계값을 만들고 앱이 직접 그립니다. 애니메이션 모델은 필요 없습니다.\n최초 1회 Ollama에서 아래 명령으로 Hugging Face 모델을 내려받으세요.",
        "generating": "로컬 모델로 생성 중…", "generated": "새 캐릭터를 만들었습니다. 설정 저장을 눌러 적용하세요.",
        "credit": "기획·요구사항·관리: hobby-programmer-5000\n구현·문서·검증 지원: ChatGPT (Codex, OpenAI)\n\n앱 코드: MIT · Qt/Python/모델: 각각의 라이선스 적용",
        "status": "감시가 꺼져 있습니다. 캐릭터와 설정만 동작합니다.",
        "demo": "깨물기 애니메이션 미리보기", "pair_help": "코드를 복사했습니다. 확장 설정에서 같은 브라우저와 포트를 선택하고 ‘연결 코드’에 붙여넣은 뒤 ‘연결하고 확인’을 누르세요.",
        "connection_help": "확장 설정에 아래 코드를 붙여넣고 같은 브라우저와 포트를 선택하세요. JSON을 편집할 필요가 없습니다.",
        "quit_wait": "캐릭터 생성이 끝난 뒤 종료하세요.", "bridge_error": "브라우저 연결을 시작할 수 없습니다: ",
        "bad_exe": "실행 파일 이름은 .exe로 끝나야 합니다.", "exe_filter": "Windows 실행 파일 (*.exe)",
    },
    "en": {
        "subtitle": "A little companion for a more focused desktop",
        "general": "General", "apps": "Applications", "web": "Browsers", "character": "Character", "about": "About",
        "guard": "Enable focus guardian", "preview": "Preview mode · animate without closing anything",
        "visible": "Show desktop companion", "startup": "Run when I sign in to Windows", "language": "Language",
        "save": "Save settings", "close": "Back to tray", "saved": "Settings saved.",
        "intro": "Check your allowlist in preview mode first.\nWith preview off, unlisted apps receive a normal close request and unlisted tabs close.",
        "apps_help": "Enter one executable filename per line. Pasted paths are reduced to filenames.\nWindows system windows and this app are always protected. All files with the same name are allowed.",
        "browse": "Add executable…", "running": "Add open application…", "startup_scan": "Rescan startup apps",
        "browser_help": "Install and pair the extension in each browser. Only built-in new-tab/home pages are allowed initially.\nDomains allow whole sites; a URL path limits access to that section. Both http:// and https:// URLs work.",
        "browser_on": "Apply website allowlist to this browser", "pair": "Copy connection code", "extension": "Open extension folder",
        "connection_code": "Connection code", "port": "Port", "startup_list": "Startup applications",
        "rules": "Allowed addresses · one per line (example.com or github.com/my-account)",
        "site_line": "Allowed address, line {line}: {message}",
        "invalid_url": "Enter a domain or a complete http:// or https:// URL including its hostname.",
        "invalid_port": "Enter a port between 1 and 65535.",
        "invalid_path": "Remove dot segments, backslashes and encoded separators from the path.",
        "random": "Random character", "generate": "Generate with Qwen", "restore": "Use previous character",
        "model_help": "Qwen designs appearance parameters; the app draws and animates them. No motion model is required.\nFirst download the Hugging Face model once using this Ollama command.",
        "generating": "Generating with local model…", "generated": "Character created. Save settings to apply it.",
        "credit": "Product direction, requirements, maintenance: hobby-programmer-5000\nImplementation, documentation, validation assistance: ChatGPT (Codex, OpenAI)\n\nApp code: MIT · Qt, Python and model retain their own licenses",
        "status": "Guardian is off. Only the companion and settings are active.",
        "demo": "Preview bite animation", "pair_help": "Code copied. In extension settings, choose this browser and port, paste into Connection code, then click Connect and test.",
        "connection_help": "Paste this code into the installed extension's settings. Choose the same browser and port. No JSON editing is needed.",
        "quit_wait": "Wait for character generation to finish before quitting.", "bridge_error": "Browser connection unavailable: ",
        "bad_exe": "Executable names must end with .exe.", "exe_filter": "Windows application (*.exe)",
    },
}

STYLE = """
QWidget { background: #171b2a; color: #e9e8f2; font-family: 'Segoe UI', 'Malgun Gothic'; font-size: 13px; }
QDialog { background: #171b2a; }
QLabel#brand { font-size: 30px; font-weight: 700; color: #d2c1ff; }
QLabel#subtitle { color: #a9afc5; font-size: 14px; }
QLabel#status { color: #a8dace; padding: 10px; background: #202d35; border-radius: 8px; }
QTabWidget::pane { border: 1px solid #353b53; border-radius: 12px; background: #1d2234; }
QTabBar::tab { padding: 12px 19px; color: #a9afc5; margin: 0 2px 7px 0; border-radius: 8px; }
QTabBar::tab:selected { background: #363047; color: #e1cfff; }
QTabWidget QWidget { background-color: transparent; }
QPushButton { background: #2c334b; border: 1px solid #414962; border-radius: 8px; padding: 9px 15px; }
QPushButton:hover { background: #3d4563; border-color: #b6a0eb; }
QPushButton:disabled { color: #6d738d; }
QPushButton#primary { background: #c5b0f4; color: #211b32; border: 0; font-weight: 600; }
QPushButton#primary:hover { background: #dac9ff; }
QPlainTextEdit, QLineEdit, QListWidget { background: #131725; border: 1px solid #3c435b; border-radius: 8px; padding: 8px; selection-background-color: #625182; }
QComboBox { background: #242b40; border: 1px solid #414962; border-radius: 7px; padding: 7px; min-width: 125px; }
QComboBox QAbstractItemView { background: #242b40; selection-background-color: #625182; }
QCheckBox { spacing: 10px; padding: 6px 0; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #66708b; border-radius: 5px; background: #151929; }
QCheckBox::indicator:checked { background: #bba2ed; border-color: #d8c6ff; }
QToolTip { background: #303650; color: #fff; border: 0; }
"""


class GenerationWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            self.succeeded.emit(generate_character())
        except Exception as error:
            self.failed.emit(str(error))


class SettingsDialog(QDialog):
    applied = Signal()
    language_changed = Signal()
    demo_requested = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.config = settings.snapshot()
        self.t = TEXT.get(self.config["language"], TEXT["en"])
        self.worker = None
        self.setWindowTitle("Pawzura")
        self.resize(920, 720)
        self.setMinimumSize(820, 640)
        self.setStyleSheet(STYLE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(13)
        brand = QLabel("Pawzura / 파우주라" if self.config["language"] == "ko" else "Pawzura")
        brand.setObjectName("brand")
        outer.addWidget(brand)
        subtitle = QLabel(self.t["subtitle"])
        subtitle.setObjectName("subtitle")
        outer.addWidget(subtitle)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self.build_general()
        self.build_apps()
        self.build_browsers()
        self.build_character()
        self.build_about()
        self.message = QLabel(self.t["status"] if not self.config["guard_enabled"] else self.t["preview"] if self.config["preview_only"] else self.t["guard"])
        self.message.setObjectName("status")
        self.message.setWordWrap(True)
        outer.addWidget(self.message)
        footer = QHBoxLayout()
        footer.addWidget(QLabel(f"v{__version__}  ·  Windows companion"))
        footer.addStretch()
        close = QPushButton(self.t["close"])
        close.clicked.connect(self.hide)
        save = QPushButton(self.t["save"])
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        footer.addWidget(close)
        footer.addWidget(save)
        outer.addLayout(footer)

    def page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(13)
        self.tabs.addTab(page, self.t[title])
        return layout

    def label(self, text):
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    def build_general(self):
        layout = self.page("general")
        layout.addWidget(self.label(self.t["intro"]))
        self.guard = QCheckBox(self.t["guard"])
        self.preview = QCheckBox(self.t["preview"])
        self.visible = QCheckBox(self.t["visible"])
        self.startup = QCheckBox(self.t["startup"])
        for widget, key in ((self.guard, "guard_enabled"), (self.preview, "preview_only"), (self.visible, "pet_visible"), (self.startup, "start_at_login")):
            widget.setChecked(self.config[key])
            layout.addWidget(widget)
        form = QFormLayout()
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("한국어", "ko")
        self.language.setCurrentIndex(self.language.findData(self.config["language"]))
        form.addRow(self.t["language"], self.language)
        layout.addLayout(form)
        demo = QPushButton(self.t["demo"])
        demo.clicked.connect(self.demo_requested.emit)
        layout.addWidget(demo, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

    def build_apps(self):
        layout = self.page("apps")
        layout.addWidget(self.label(self.t["apps_help"]))
        self.apps = QPlainTextEdit("\n".join(self.config["allowed_apps"]))
        layout.addWidget(self.apps, 1)
        buttons = QHBoxLayout()
        browse = QPushButton(self.t["browse"])
        browse.clicked.connect(self.browse_app)
        running = QPushButton(self.t["running"])
        running.clicked.connect(self.add_running)
        scan = QPushButton(self.t["startup_scan"])
        scan.clicked.connect(self.rescan_startup)
        for button in (browse, running, scan):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.startup_label = self.label(self.t["startup_list"] + ": " + ", ".join(self.config["startup_apps"]))
        self.startup_label.setMaximumHeight(65)
        layout.addWidget(self.startup_label)

    def browse_app(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.t["browse"], "", self.t["exe_filter"])
        if filename:
            self.apps.appendPlainText(normalize_app(filename))

    def add_running(self):
        names = sorted({normalize_app(w.executable) for w in windows.list_windows()})
        item, ok = QInputDialog.getItem(self, "Pawzura", self.t["running"], names, 0, False)
        if ok and item:
            self.apps.appendPlainText(item)

    def rescan_startup(self):
        self.config["startup_apps"] = windows.startup_apps()
        self.startup_label.setText(self.t["startup_list"] + ": " + ", ".join(self.config["startup_apps"]))

    def build_browsers(self):
        layout = self.page("web")
        layout.addWidget(self.label(self.t["browser_help"]))
        self.browser_select = QComboBox()
        self.browser_select.addItems(BROWSERS)
        layout.addWidget(self.browser_select)
        self.browser_on = QCheckBox(self.t["browser_on"])
        layout.addWidget(self.browser_on)
        layout.addWidget(self.label(self.t["rules"]))
        self.sites = QPlainTextEdit()
        self.sites.setPlaceholderText("example.com\ngithub.com/my-account\nhttps://example.org/courses?view=video\nhttp://localhost:3000")
        layout.addWidget(self.sites, 1)
        self.current_browser = BROWSERS[0]
        self.load_browser()
        self.browser_select.currentTextChanged.connect(self.switch_browser)
        buttons = QHBoxLayout()
        pair = QPushButton(self.t["pair"])
        pair.clicked.connect(self.copy_pairing)
        extension = QPushButton(self.t["extension"])
        extension.clicked.connect(self.open_extension)
        buttons.addWidget(pair)
        buttons.addWidget(extension)
        layout.addLayout(buttons)
        layout.addWidget(self.label(self.t["connection_help"]))
        connection = QFormLayout()
        self.connection_code = QLineEdit(self.config["bridge_token"])
        self.connection_code.setReadOnly(True)
        self.connection_code.setEchoMode(QLineEdit.EchoMode.Password)
        connection.addRow(self.t["connection_code"], self.connection_code)
        connection.addRow(self.t["port"], QLabel(str(self.config["bridge_port"])))
        layout.addLayout(connection)

    def store_browser(self):
        rules = []
        for number, line in enumerate(self.sites.toPlainText().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rules.append(site_rule(line))
            except SiteRuleError as error:
                raise ValueError(self.t["site_line"].format(line=number, message=self.t[error.code])) from error
        self.config["browsers"][self.current_browser] = {"enabled": self.browser_on.isChecked(), "allowed_sites": sorted(set(rules))}
        self.sites.setPlainText("\n".join(sorted(set(rules))))

    def load_browser(self):
        entry = self.config["browsers"][self.current_browser]
        self.browser_on.setChecked(entry["enabled"])
        self.sites.setPlainText("\n".join(entry["allowed_sites"]))

    def switch_browser(self, name):
        try:
            self.store_browser()
        except ValueError as error:
            self.message.setText(str(error))
            self.browser_select.blockSignals(True)
            self.browser_select.setCurrentText(self.current_browser)
            self.browser_select.blockSignals(False)
            return
        self.current_browser = name
        self.load_browser()

    def copy_pairing(self):
        config = self.settings.snapshot()
        QApplication.clipboard().setText(config["bridge_token"])
        self.message.setText(self.t["pair_help"])

    def open_extension(self):
        root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        folder = root / "extensions"
        if not folder.exists():
            folder = Path(getattr(sys, "_MEIPASS", root)) / "extensions"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def build_character(self):
        layout = self.page("character")
        row = QHBoxLayout()
        self.character_preview = CharacterPreview(self.config["character"])
        row.addWidget(self.character_preview, 1)
        controls = QVBoxLayout()
        self.random_button = QPushButton(self.t["random"])
        self.random_button.clicked.connect(lambda: self.apply_character(random_character()))
        self.generate_button = QPushButton(self.t["generate"])
        self.generate_button.setObjectName("primary")
        self.generate_button.clicked.connect(self.generate)
        previous = QPushButton(self.t["restore"])
        previous.clicked.connect(self.restore_character)
        controls.addStretch()
        controls.addWidget(self.random_button)
        controls.addWidget(self.generate_button)
        controls.addWidget(previous)
        controls.addStretch()
        row.addLayout(controls, 1)
        layout.addLayout(row, 1)
        layout.addWidget(self.label(self.t["model_help"]))
        command = QLineEdit("ollama pull " + MODEL)
        command.setReadOnly(True)
        layout.addWidget(command)

    def apply_character(self, spec):
        old = self.config["character"]
        self.config["character_history"] = (self.config["character_history"] + [old])[-20:]
        self.config["character"] = spec
        self.character_preview.spec = spec
        self.character_preview.update()
        self.message.setText(self.t["generated"])

    def restore_character(self):
        if self.config["character_history"]:
            spec = self.config["character_history"].pop()
            self.config["character"] = spec
            self.character_preview.spec = spec
            self.character_preview.update()

    def generate(self):
        if self.worker and self.worker.isRunning():
            return
        self.generate_button.setEnabled(False)
        self.language.setEnabled(False)
        self.message.setText(self.t["generating"])
        self.worker = GenerationWorker(self)
        self.worker.succeeded.connect(self.apply_character)
        self.worker.failed.connect(lambda error: self.message.setText("Ollama: " + error))
        self.worker.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.worker.finished.connect(lambda: self.language.setEnabled(True))
        self.worker.start()

    def build_about(self):
        layout = self.page("about")
        layout.addWidget(self.label(self.t["credit"]))
        language = "ko" if self.config["language"] == "ko" else "en"
        layout.addWidget(self.label(f"Qwen2.5-0.5B-Instruct-GGUF · Apache-2.0\nhttps://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF\n\nREADME.md · doc/{language}/MODELS.md\nTHIRD-PARTY-NOTICES.md · CONTRIBUTORS.md"))
        layout.addWidget(self.label("https://github.com/hobby-programmer-5000/pawzura"))
        layout.addStretch()

    def save(self):
        try:
            self.store_browser()
            apps = sorted({normalize_app(line) for line in self.apps.toPlainText().splitlines() if line.strip()})
            if any(not app.endswith(".exe") for app in apps):
                raise ValueError(self.t["bad_exe"])
            updates = {"guard_enabled": self.guard.isChecked(), "preview_only": self.preview.isChecked(),
                       "pet_visible": self.visible.isChecked(), "start_at_login": self.startup.isChecked(),
                       "language": self.language.currentData(), "allowed_apps": apps,
                       "startup_apps": self.config["startup_apps"], "browsers": self.config["browsers"],
                       "character": self.config["character"], "character_history": self.config["character_history"]}
            old_startup = self.settings.snapshot()["start_at_login"]
            if updates["start_at_login"] != old_startup:
                windows.set_startup(updates["start_at_login"])
            try:
                self.settings.save(updates)
            except OSError:
                windows.set_startup(old_startup)
                raise
            self.applied.emit()
            self.message.setText(self.t["saved"])
            if updates["language"] != self.config["language"]:
                self.language_changed.emit()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Pawzura", str(error))

    def closeEvent(self, event):
        self.hide()
        event.ignore()
