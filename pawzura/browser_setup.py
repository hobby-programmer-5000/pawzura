"""Local extension preparation and guided browser setup; no policy/profile editing."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlencode

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from .config import BROWSERS, BROWSER_EXECUTABLES, data_dir

FILES = ("manifest.json", "background.js", "options.html", "options.js", "options-i18n.js", "options.css")
MANAGERS = {name: f"{name}://extensions" for name in BROWSERS}
MANAGERS.update(edge="edge://extensions", firefox="about:debugging#/runtime/this-firefox", zen="about:debugging#/runtime/this-firefox", arc="chrome://extensions")
FIREFOX = {"firefox", "zen"}


def extension_source(browser: str) -> Path:
    if browser not in BROWSERS:
        raise ValueError("Unknown browser")
    from .resources import resource_path
    return resource_path("extensions") / ("firefox" if browser in FIREFOX else "chromium")


def prepare_extension(browser: str, destination: Path | None = None, source: Path | None = None) -> Path:
    if browser not in BROWSERS:
        raise ValueError("Unknown browser")
    source = source or extension_source(browser)
    target = (destination or data_dir() / "extensions") / ("firefox" if browser in FIREFOX else "chromium")
    # Fixed public files only: never copy settings, pairing data or browser profiles.
    for name in FILES:
        if not (source / name).is_file():
            raise FileNotFoundError("Extension files are missing; extract the complete application ZIP")
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copy2(source / name, target / name)
    return target


def extension_id(manifest: Path) -> str:
    public_key = json.loads(manifest.read_text(encoding="utf-8"))["key"]
    digest = hashlib.sha256(base64.b64decode(public_key, validate=True)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(char, 16)) for char in digest)


def connection_url(browser: str, folder: Path, port: int, language: str) -> str:
    if browser not in BROWSERS or not 1024 <= port <= 65535:
        raise ValueError("Invalid browser or port")
    if browser in FIREFOX:
        return "about:addons"  # Firefox assigns a per-install moz-extension UUID.
    query = urlencode({"browser": browser, "port": port, "lang": "ko" if language == "ko" else "en", "setup": 1})
    return f"chrome-extension://{extension_id(folder / 'manifest.json')}/options.html?{query}"


def find_browser(browser: str) -> Path | None:
    names = [exe for exe, name in BROWSER_EXECUTABLES.items() if name == browser]
    if sys.platform == "win32":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for name in names:
                for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{name}", 0, winreg.KEY_READ | view) as key:
                            candidate = Path(os.path.expandvars(winreg.QueryValue(key, None)).strip('"'))
                            if candidate.is_file() and candidate.name.casefold() in names:
                                return candidate
                    except (OSError, TypeError, ValueError):
                        pass
    relative = {
        "chrome": "Google/Chrome/Application/chrome.exe", "edge": "Microsoft/Edge/Application/msedge.exe",
        "brave": "BraveSoftware/Brave-Browser/Application/brave.exe", "firefox": "Mozilla Firefox/firefox.exe",
        "vivaldi": "Vivaldi/Application/vivaldi.exe", "opera": "Programs/Opera/opera.exe", "zen": "Zen Browser/zen.exe",
    }.get(browser)
    if relative:
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            if os.environ.get(variable):
                candidate = Path(os.environ[variable]) / relative
                if candidate.is_file():
                    return candidate
    for name in names:
        if candidate := shutil.which(name):
            return Path(candidate)
    return None


def launch_browser(browser: str, executable: Path, url: str):
    # Argument arrays, never a shell command or a registry policy/forced install.
    subprocess.Popen([str(executable), "-new-tab" if browser in FIREFOX else "--new-tab", url])


WORDS = {
    "en": {
        "title": "Install and connect the browser extension", "open": "1. Open install page + copy folder",
        "copy": "Copy folder again", "next": "I loaded the extension → Next", "connect": "2. Open connection and request pairing",
        "back": "Back", "done": "Done", "close": "Close", "choose": "Choose browser executable…",
        "intro": "The app opens the right page and copies the exact folder. You approve installation in the browser; nothing is installed silently.",
        "chromium": "① On the EXTENSIONS page opened by the button below, switch on Developer mode. Chrome: chrome://extensions → upper-right switch. Edge: edge://extensions → left sidebar switch. Other browsers may place it differently.\nCtrl+Shift+I opens Developer Tools, not this switch. Close Developer Tools if you opened it.\n\n② On that same extensions page, click Load unpacked. This button appears after step ①.\n\n③ In the folder picker: Alt+D → Ctrl+V → Enter → Select Folder.\nChoose the folder, not options.html or the app folder.",
        "firefox": "In Firefox/Zen: click Load Temporary Add-on, open the folder below and select manifest.json. This temporary installation disappears when the browser restarts; permanent installation requires Mozilla signing.",
        "loaded": "The folder is copied. Finish the browser steps above, then click Next here. Keep this installed folder; it remains stable across app upgrades.",
        "pair": "Click the connection button below, then approve Yes in the Pawzura desktop prompt. Browser and port are filled automatically. If the page says it cannot be opened, go Back and finish loading the extension first.",
        "firefox_pair": "On about:addons, open Extensions → Pawzura → Preferences/Options (possibly under ⋯), or click the Pawzura extension icon. Choose this browser and Connect automatically, then approve Yes in Pawzura.",
        "connected": "Connected. Installation/pairing is complete. Website control is not enabled automatically. Close this helper, choose allowed sites, and turn on website control only if you want it.",
        "waiting": "Waiting for extension connection…", "missing": "Browser not found. Choose its executable below, then retry.",
        "start": "Start with Open install page below. Installation is not automatic.",
        "error": "Could not open the setup page. Check the complete ZIP and selected browser.",
        "old": "If an older Pawzura extension is already installed under another folder/ID, remove that older copy before loading this one. Your desktop allowlists are retained.",
    },
    "ko": {
        "title": "브라우저 확장 설치·연결", "open": "1. 설치 화면 열기 + 폴더 자동 복사",
        "copy": "폴더 경로 다시 복사", "next": "확장을 불러왔어요 → 다음", "connect": "2. 연결 화면 열고 연결 요청",
        "back": "이전", "done": "완료", "close": "닫기", "choose": "브라우저 실행 파일 선택…",
        "intro": "앱이 설치 화면을 열고 정확한 폴더를 복사합니다. 설치 승인은 브라우저에서 직접 하며 몰래 설치하지 않습니다.",
        "chromium": "① 아래 버튼으로 열린 ‘확장 프로그램’ 관리 화면에서 ‘개발자 모드’ 스위치를 켜세요. Chrome: chrome://extensions 화면 오른쪽 위. Edge: edge://extensions 화면 왼쪽 사이드바. 다른 브라우저는 위치가 다를 수 있습니다.\nCtrl+Shift+I는 ‘개발자 도구’를 여는 단축키입니다. 이 스위치와 다르므로 도구를 열었다면 닫으세요.\n\n② 같은 확장 관리 화면에서 새로 나타난 ‘압축해제된 확장 프로그램을 로드합니다’(Load unpacked)를 누르세요.\n\n③ 폴더 선택창에서 Alt+D → Ctrl+V → Enter → ‘폴더 선택’을 누르세요.\noptions.html 파일이나 앱 전체 폴더를 고르는 것이 아닙니다.",
        "firefox": "Firefox/Zen에서 ‘임시 부가 기능 로드’를 누르고 아래 폴더의 manifest.json을 고릅니다. 브라우저를 다시 시작하면 해제되는 임시 설치입니다. 영구 설치에는 Mozilla 서명이 필요합니다.",
        "loaded": "폴더를 복사했습니다. 브라우저에서 위 설치 단계를 마친 뒤 여기서 ‘다음’을 누르세요. 설치된 폴더는 유지하며 앱 업그레이드 후에도 같은 경로를 사용합니다.",
        "pair": "아래 연결 버튼을 누른 뒤 Pawzura 앱의 확인창에서 ‘예’를 누르세요. 브라우저·포트는 자동 입력됩니다. 페이지를 열 수 없다고 나오면 ‘이전’으로 돌아가 확장 불러오기를 먼저 마치세요.",
        "firefox_pair": "about:addons의 확장 기능 → Pawzura → 설정/옵션(⋯ 메뉴 안에 있을 수 있음)을 열거나 Pawzura 확장 아이콘을 누르세요. 현재 브라우저를 선택하고 ‘자동 연결’을 누른 뒤 Pawzura에서 ‘예’를 누르세요.",
        "connected": "연결됐습니다. 설치·연결은 완료되었으며 사이트 제어를 자동으로 켜지는 않습니다. 도우미를 닫고 필요할 때 허용 사이트와 사이트 제어를 설정하세요.",
        "waiting": "확장 연결을 기다리는 중…", "missing": "브라우저를 찾지 못했습니다. 아래에서 실행 파일을 선택한 뒤 다시 눌러주세요.",
        "start": "먼저 ‘설치 화면 열기’ 버튼을 누르세요. 아직 설치한 상태는 아닙니다.",
        "error": "설치 화면을 열지 못했습니다. ZIP 전체 압축 해제와 선택한 브라우저를 확인하세요.",
        "old": "다른 폴더·ID로 설치한 예전 Pawzura 확장이 있다면 먼저 그 항목을 제거한 뒤 불러오세요. 데스크톱 허용 목록은 유지됩니다.",
    },
}


class BrowserSetupDialog(QDialog):
    def __init__(self, browser, port, language, connection_check=None, parent=None):
        super().__init__(parent)
        self.browser, self.port, self.language = browser, port, language
        self.t = WORDS["ko" if language == "ko" else "en"]
        self.connection_check = connection_check or (lambda _: False)
        self.executable = find_browser(browser)
        self.folder = None
        self.setWindowTitle("Pawzura · " + self.t["title"])
        self.resize(760, 610)
        layout = QVBoxLayout(self)
        title = self.label(self.t["title"] + " — " + browser.capitalize())
        title.setObjectName("setupTitle")
        layout.addWidget(title)
        layout.addWidget(self.label(self.t["intro"]))
        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        first = QWidget()
        install = QVBoxLayout(first)
        install.addWidget(self.label(self.t["firefox"] if browser in FIREFOX else self.t["chromium"]))
        self.folder_field = QLineEdit()
        self.folder_field.setReadOnly(True)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_field)
        copy = QPushButton(self.t["copy"])
        copy.clicked.connect(self.copy_folder)
        folder_row.addWidget(copy)
        install.addLayout(folder_row)
        for key, callback in (("open", self.open_install), ("choose", self.choose_browser), ("next", lambda: self.pages.setCurrentIndex(1))):
            button = QPushButton(self.t[key])
            button.clicked.connect(callback)
            install.addWidget(button)
            if key == "open": button.setObjectName("primary")
            if key == "choose":
                self.choose_button = button
                button.setVisible(self.executable is None)
        install.addWidget(self.label(self.t["old"]))
        self.pages.addWidget(first)
        second = QWidget()
        pair = QVBoxLayout(second)
        pair.addWidget(self.label(self.t["firefox_pair"] if browser in FIREFOX else self.t["pair"]))
        connect = QPushButton(self.t["connect"])
        connect.setObjectName("primary")
        connect.clicked.connect(self.open_connection)
        pair.addWidget(connect)
        back = QPushButton(self.t["back"])
        back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        pair.addWidget(back)
        pair.addStretch()
        self.pages.addWidget(second)
        third = QWidget()
        complete = QVBoxLayout(third)
        complete.addWidget(self.label(self.t["connected"]))
        done = QPushButton(self.t["done"])
        done.clicked.connect(self.hide)
        complete.addWidget(done)
        complete.addStretch()
        self.pages.addWidget(third)
        self.status = self.label(self.t["start"])
        layout.addWidget(self.status)
        close = QPushButton(self.t["close"])
        close.clicked.connect(self.hide)
        layout.addWidget(close)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_connection)
        self.timer.start(1000)

    def label(self, text):
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    def stage(self):
        self.folder = prepare_extension(self.browser)
        self.folder_field.setText(str(self.folder))
        return self.folder

    def copy_folder(self):
        try:
            QApplication.clipboard().setText(str(self.stage()))
            self.status.setText(self.t["loaded"])
        except OSError:
            self.status.setText(self.t["error"])

    def choose_browser(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.t["choose"], "", "Browser (*.exe)")
        if filename:
            if Path(filename).name.casefold() in {exe for exe, browser in BROWSER_EXECUTABLES.items() if browser == self.browser}:
                self.executable = Path(filename)
                self.choose_button.hide()
                self.status.setText(self.t["start"])
            else:
                self.status.setText(self.t["missing"])

    def launch(self, url):
        if not self.executable:
            self.status.setText(self.t["missing"])
            return
        try:
            launch_browser(self.browser, self.executable, url)
        except OSError:
            self.choose_button.show()
            self.status.setText(self.t["error"])

    def open_install(self):
        try:
            self.stage()
            QApplication.clipboard().setText(str(self.folder))
            self.status.setText(self.t["loaded"])
            self.launch(MANAGERS[self.browser])
        except OSError:
            self.status.setText(self.t["error"])

    def open_connection(self):
        try:
            self.stage()
            self.status.setText(self.t["waiting"])
            self.launch(connection_url(self.browser, self.folder, self.port, self.language))
        except (OSError, ValueError, KeyError):
            self.status.setText(self.t["error"])

    def refresh_connection(self):
        if self.isVisible() and self.connection_check(self.browser):
            self.pages.setCurrentIndex(2)
            self.status.setText(self.t["connected"])
