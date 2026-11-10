from __future__ import annotations

import argparse
import ctypes
import json
import logging
from pathlib import Path
from queue import Empty
import sys
import time
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QTimer, Qt
from PySide6.QtGui import QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from .bridge import Bridge
from .config import Settings, data_dir
from .pet import Pet, draw_character
from .policy import allowed_app, is_browser
from .ui import SettingsDialog, TEXT
from . import windows
from .instance import AlreadyRunningError, acquire_instance_lock


class Companion:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings
        self.pet = Pet(settings.snapshot()["character"], settings.snapshot()["language"], settings.snapshot()["walk_direction"])
        self.pet.settings_requested.connect(self.show_settings)
        self.pet.placement_changed.connect(self.save_placement)
        self.dialog = None
        self.pairing_dialog_open = False
        self.bridge = Bridge(settings)
        self.pet.drag_started.connect(self.bridge.invalidate_tickets)
        self.bridge_error = None
        try:
            self.bridge.start()
        except OSError as error:
            self.bridge_error = str(error)
        self.observed = {}
        self.previewed = set()
        self.cooldown = {}
        self.tray = QSystemTrayIcon(self.make_icon(), app)
        self.tray.setToolTip("Pawzura")
        self.tray.activated.connect(self.tray_activated)
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.refresh_menu()
        self.tray.show()
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(800)
        self.apply()
        self.app.aboutToQuit.connect(self.shutdown)

    def make_icon(self):
        pixmap = QPixmap(144, 146)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        draw_character(painter, self.settings.snapshot()["character"])
        painter.end()
        return QIcon(pixmap)

    def refresh_menu(self):
        self.menu.clear()
        config = self.settings.snapshot()
        ko = config["language"] == "ko"
        items = [
            ("설정 열기" if ko else "Open settings", self.show_settings),
            (("집중 지킴이 끄기" if config["guard_enabled"] else "집중 지킴이 켜기") if ko else ("Pause guardian" if config["guard_enabled"] else "Enable guardian"), self.toggle_guard),
            (("캐릭터 숨기기" if config["pet_visible"] else "캐릭터 보이기") if ko else ("Hide companion" if config["pet_visible"] else "Show companion"), self.toggle_pet),
            ("캐릭터 화면 복구" if ko else "Recover companion on screen", self.recover_pet),
            (("사이트 제어 끄기" if config["browser_control_enabled"] else "사이트 제어 켜기") if ko else ("Turn website control off" if config["browser_control_enabled"] else "Turn website control on"), self.toggle_browser_control),
        ]
        for title, callback in items:
            action = self.menu.addAction(title)
            action.triggered.connect(callback)
        self.menu.addSeparator()
        self.menu.addAction("종료" if ko else "Quit").triggered.connect(self.request_quit)

    def request_quit(self):
        if self.dialog and self.dialog.worker and self.dialog.worker.isRunning():
            self.dialog.message.setText(self.dialog.t["quit_wait"])
            self.dialog.show()
            return
        self.app.quit()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_settings()

    def toggle_guard(self):
        self.settings.save({"guard_enabled": not self.settings.snapshot()["guard_enabled"]})
        self.apply()

    def toggle_pet(self):
        self.settings.save({"pet_visible": not self.settings.snapshot()["pet_visible"]})
        self.apply()

    def toggle_browser_control(self):
        self.settings.save({"browser_control_enabled": not self.settings.snapshot()["browser_control_enabled"]})
        self.apply()

    def recover_pet(self):
        # Recreate the native transparent window as well as resetting its position.
        self.settings.save({"pet_visible": True, "pet_position": None})
        self.bridge.invalidate_tickets()
        self.pet.dispose()
        self.pet = Pet(self.settings.snapshot()["character"], self.settings.snapshot()["language"], self.settings.snapshot()["walk_direction"])
        self.pet.settings_requested.connect(self.show_settings)
        self.pet.placement_changed.connect(lambda position: Companion.save_placement(self, position))
        self.pet.drag_started.connect(self.bridge.invalidate_tickets)
        self.pet.set_placement(self.settings.snapshot()["pet_pinned"])
        self.pet.show()
        self.pet.raise_()
        self.refresh_menu()
        if self.dialog:
            self.dialog.visible.setChecked(True)
            self.dialog.position_provider = self.pet.resting_position
            self.dialog.message.setText(self.dialog.t["recovered"])

    def save_placement(self, position):
        try:
            self.settings.save({"pet_pinned": True, "pet_position": position})
        except (OSError, ValueError):
            # Keep the safe on-screen drop, but do not claim persistence succeeded.
            ko = self.settings.snapshot()["language"] == "ko"
            self.tray.showMessage("Pawzura", "위치를 저장하지 못했습니다. 폴더 쓰기 권한과 디스크 공간을 확인하세요." if ko else
                                  "Could not save the position. Check folder write access and free disk space.")
        if self.dialog:
            self.dialog.pin.setChecked(True)

    def apply(self):
        config = self.settings.snapshot()
        self.bridge.invalidate_tickets()
        self.pet.cancel_bite(recover=False)
        self.pet.set_placement(config["pet_pinned"], config["pet_position"])
        self.pet.spec = config["character"]
        self.pet.set_walk_direction(config["walk_direction"])
        self.pet.set_language(config["language"])
        self.pet.setVisible(config["pet_visible"])
        self.tray.setIcon(self.make_icon())
        self.tray.setToolTip("Pawzura · " + ("Preview" if config["guard_enabled"] and config["preview_only"] else "Guardian on" if config["guard_enabled"] else "Guardian off"))
        self.refresh_menu()
        self.observed.clear()
        self.previewed.clear()
        if self.dialog:
            self.dialog.website_control.blockSignals(True)
            self.dialog.website_control.setChecked(config["browser_control_enabled"])
            self.dialog.website_control.blockSignals(False)

    def show_settings(self):
        language = self.settings.snapshot()["language"]
        if self.dialog and self.dialog.config["language"] != language and not (self.dialog.worker and self.dialog.worker.isRunning()):
            self.dialog.deleteLater()
            self.dialog = None
        if not self.dialog:
            self.dialog = SettingsDialog(self.settings, connection_check=self.bridge.is_connected,
                                         position_provider=self.pet.resting_position)
            self.dialog.applied.connect(self.apply)
            self.dialog.language_changed.connect(lambda: QTimer.singleShot(0, self.show_settings))
            self.dialog.demo_requested.connect(self.demo)
            self.dialog.recovery_requested.connect(self.recover_pet)
        # Synchronize quick tray toggles without overwriting unsaved allowlist edits.
        config = self.settings.snapshot()
        self.dialog.guard.setChecked(config["guard_enabled"])
        self.dialog.visible.setChecked(config["pet_visible"])
        self.dialog.pin.setChecked(config["pet_pinned"])
        self.dialog.position_provider = self.pet.resting_position
        self.dialog.website_control.blockSignals(True)
        self.dialog.website_control.setChecked(config["browser_control_enabled"])
        self.dialog.website_control.blockSignals(False)
        if self.bridge_error:
            self.dialog.message.setText(self.dialog.t["bridge_error"] + self.bridge_error)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def demo(self):
        screen = QApplication.primaryScreen().availableGeometry()
        point = QPointF(screen.center().x(), screen.top() + 120)
        if self.dialog and self.dialog.isVisible():
            frame = self.dialog.frameGeometry()
            point = QPointF(frame.right() - 25, frame.top() + 16)
        self.pet.setVisible(True)
        self.pet.bite(point, lambda: None)

    def tick(self):
        if self.pairing_dialog_open:
            return
        try:
            request = self.bridge.pairing_events.get_nowait()
            language = self.settings.snapshot()["language"]
            text = TEXT.get(language, TEXT["en"])
            self.pairing_dialog_open = True
            try:
                answer = QMessageBox.question(self.dialog, "Pawzura", text["pair_question"].format(browser=request["browser"], origin=request["origin"]),
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                              QMessageBox.StandardButton.No)
            finally:
                self.pairing_dialog_open = False
            self.bridge.approve_pairing(request["request"], answer == QMessageBox.StandardButton.Yes)
            return
        except Empty:
            pass
        if self.pet.action or self.pet.pointer_active:
            return
        config = self.settings.snapshot()
        # Browser tickets receive the same animation acknowledgement as native windows.
        try:
            event = self.bridge.events.get_nowait()
            if config["guard_enabled"] and config.get("browser_control_enabled", False) and config["browsers"][event["browser"]]["enabled"]:
                # A browser's tab ID cannot identify a native window's X coordinates.
                # Use a separate taskbar-side tab marker, never another window's controls.
                point = self.pet.tab_target_point()
                label = ("탭 미리보기" if config["preview_only"] else "차단 탭") if config["language"] == "ko" else ("Tab preview" if config["preview_only"] else "Blocked tab")
                self.pet.bite(point, lambda: self.bridge.complete(event["ticket"]), label=label, tab=True)
            return
        except Empty:
            pass
        if not config["guard_enabled"] or not config["application_control_enabled"]:
            return
        now = time.monotonic()
        candidates = windows.list_windows()
        live = {(w.hwnd, w.pid, w.executable, w.title) for w in candidates}
        self.observed = {key: value for key, value in self.observed.items() if key in live}
        self.previewed.intersection_update(live)
        self.cooldown = {key: value for key, value in self.cooldown.items() if now - value < 30}
        for window in candidates:
            if is_browser(window.executable) or allowed_app(window.executable, config):
                continue
            key = (window.hwnd, window.pid, window.executable, window.title)
            if config["preview_only"] and key in self.previewed:
                continue
            first = self.observed.setdefault(key, now)
            if now - first < 4 or now - self.cooldown.get(key, -100) < 15:
                continue
            self.cooldown[key] = now
            x, y = windows.physical_to_logical(*window.close_point, QApplication.screens())
            def complete(target=window, was_preview=config["preview_only"]):
                if was_preview:
                    return  # A preview callback can never become a live close request.
                current = self.settings.snapshot()
                if (current["guard_enabled"] and current["application_control_enabled"]
                        and not current["preview_only"] and not is_browser(target.executable)
                        and not allowed_app(target.executable, current)):
                    windows.close_window(target)
            if self.pet.bite(QPointF(x, y), complete) and config["preview_only"]:
                self.previewed.add(key)
            break

    def shutdown(self):
        self.timer.stop()
        self.pet.timer.stop()
        self.pet.close()
        self.tray.hide()
        self.bridge.stop()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pawzura · Windows SD desktop companion")
    parser.add_argument("--settings", action="store_true", help="Open settings on launch")
    parser.add_argument("--tray", action="store_true", help="Start quietly in the system tray (Windows sign-in)")
    parser.add_argument("--settings-file", type=Path, help="Use an explicit settings file for isolated testing")
    parser.add_argument("--smoke-check", action="store_true", help="Render offscreen and exit; no monitoring or settings writes")
    parser.add_argument("--capture", type=Path, help="Capture settings PNG during --smoke-check")
    args = parser.parse_args(argv)
    if not windows.IS_WINDOWS and not args.smoke_check:
        parser.error("Desktop integration requires Windows 10/11")
    if windows.IS_WINDOWS:
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            pass
    if args.smoke_check:
        import os
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication([sys.argv[0]])
    if args.smoke_check and windows.IS_WINDOWS:
        # The offscreen Qt plugin has no Windows font database integration.
        import os
        for font in ("segoeui.ttf", "malgun.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / font))
    app.setApplicationName("Pawzura")
    app.setOrganizationName("Pawzura")
    app.setQuitOnLastWindowClosed(False)
    if args.smoke_check:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temporary:
            from . import __version__
            from .art_client import catalog, source_dir
            from .browser_setup import FILES, prepare_extension
            from .resources import resource_path
            catalog()
            staged = prepare_extension("chrome", Path(temporary) / "extensions")
            assert {p.name for p in staged.iterdir()} == set(FILES)
            for name in ("setup.ps1", "runner.py", "motion_catalog.json", "three_d.py"):
                assert (source_dir() / name).is_file(), name
            assert (resource_path("licenses") / "installed").is_dir() or not getattr(sys, "frozen", False)
            settings = Settings(Path(temporary) / "settings.json")
            dialog = SettingsDialog(settings)
            dialog.show()
            app.processEvents()
            if args.capture:
                args.capture.parent.mkdir(parents=True, exist_ok=True)
                dialog.grab().save(str(args.capture))
                for index in range(dialog.tabs.count()):
                    dialog.tabs.setCurrentIndex(index)
                    app.processEvents()
                    dialog.grab().save(str(args.capture.with_stem(args.capture.stem + f"-{index}")))
            pet = Pet(settings.snapshot()["character"])
            pet.show()
            app.processEvents()
            pet.grab()
            pet.timer.stop()
            dialog.character_preview.timer.stop()
            dialog.hide()
            pet.hide()
            tab_count = dialog.tabs.count()
            pet.deleteLater()
            dialog.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            print(json.dumps({"smoke_check": "passed", "version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
                              "qt": "6.12.0", "tabs": tab_count, "bundled_resources": "passed"}))
            return 0
    lock = None
    try:
        settings_file = args.settings_file or data_dir() / "settings.json"
        lock = acquire_instance_lock(settings_file)
        settings = Settings(settings_file)
        first_run = not settings.path.exists()
        if first_run:
            settings.save({"startup_apps": windows.startup_apps()})
        companion = Companion(app, settings)
        if first_run or args.settings or not args.tray:
            companion.show_settings()
        return app.exec()
    except AlreadyRunningError:
        QMessageBox.information(None, "Pawzura", "Already running. Check the Pawzura system tray icon.\n이미 실행 중입니다. Pawzura 트레이 아이콘을 확인하세요.")
        return 0
    except Exception as error:
        QMessageBox.critical(None, "Pawzura", str(error))
        return 1
    finally:
        if lock is not None:
            lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
