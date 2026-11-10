import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from types import SimpleNamespace
from queue import Queue
from unittest.mock import Mock, patch
import unittest
from pawzura.app import Companion
from pawzura.config import defaults
from pawzura.windows import Window, close_window
from PySide6.QtCore import QPointF


class RoutingTests(unittest.TestCase):
    def harness(self):
        config = defaults()
        config.update(guard_enabled=True,preview_only=False,browser_control_enabled=True,allowed_apps=["codex.exe"])
        fake = SimpleNamespace(settings=SimpleNamespace(snapshot=lambda: config),
                               pet=SimpleNamespace(action=None,pointer_active=False,bite=Mock(),tab_target_point=Mock(return_value=QPointF(480,650))),
                               bridge=SimpleNamespace(events=Queue(),pairing_events=Queue(),complete=Mock()),
                               pairing_dialog_open=False,observed={},cooldown={},previewed=set())
        return fake,config

    def window(self, exe):
        return Window(100,200,exe,"Example",(100,100,1000,700),(975,115))

    def test_pointer_hold_defers_browser_events_and_native_inspection(self):
        fake, _ = self.harness()
        fake.pet.pointer_active = True
        fake.bridge.events.put({"browser": "chrome", "ticket": "test"})
        with patch("pawzura.app.windows.list_windows") as inspect:
            Companion.tick(fake)
        inspect.assert_not_called()
        fake.pet.bite.assert_not_called()
        self.assertEqual(fake.bridge.events.qsize(), 1)

    def test_real_codex_and_browser_windows_never_reach_native_bite(self):
        fake,_ = self.harness()
        with patch("pawzura.app.windows.list_windows",return_value=[self.window("ChatGPT.exe"),self.window("chrome.exe")]):
            Companion.tick(fake)
            fake.pet.bite.assert_not_called()
            self.assertEqual(fake.observed,{})

    def test_final_close_boundary_rejects_browsers_before_win32(self):
        with patch("pawzura.windows.inspect_window") as inspect:
            self.assertFalse(close_window(self.window("chrome.exe")))
            inspect.assert_not_called()

    def test_graphics_and_renderer_helpers_are_protected_even_without_allowlist_entries(self):
        fake,config = self.harness()
        config.update(allowed_apps=[],startup_apps=[])
        targets=[self.window(name) for name in ("NVIDIA Overlay.exe","nvcontainer.exe","AMDOW.exe","RTSS.exe","msedgewebview2.exe")]
        with patch("pawzura.app.windows.list_windows",return_value=targets):
            Companion.tick(fake)
        fake.pet.bite.assert_not_called()
        with patch("pawzura.windows.inspect_window") as inspect:
            for target in targets:
                self.assertFalse(close_window(target))
            inspect.assert_not_called()

    def test_native_preview_occurs_once_and_callback_can_never_close(self):
        fake,config = self.harness()
        config["preview_only"] = True
        window=self.window("unlisted.exe")
        key=(window.hwnd,window.pid,window.executable,window.title)
        fake.observed[key]=90
        with patch("pawzura.app.time.monotonic",return_value=100), \
             patch("pawzura.app.windows.list_windows",return_value=[window]), \
             patch("pawzura.app.windows.physical_to_logical",return_value=(975,115)), \
             patch("pawzura.app.QApplication.screens",return_value=[]), \
             patch("pawzura.app.windows.close_window") as close:
            Companion.tick(fake)
            callback=fake.pet.bite.call_args.args[1]
            with patch("pawzura.app.time.monotonic",return_value=160):
                Companion.tick(fake)
            self.assertEqual(fake.pet.bite.call_count,1)
            config["preview_only"] = False
            callback()
            close.assert_not_called()

    def test_program_guardian_still_operates_with_website_control_off(self):
        fake,config = self.harness()
        config["browser_control_enabled"] = False
        window = self.window("unlisted.exe")
        fake.observed[(window.hwnd,window.pid,window.executable,window.title)] = 90
        with patch("pawzura.app.time.monotonic",return_value=100), \
             patch("pawzura.app.windows.list_windows",return_value=[window]), \
             patch("pawzura.app.windows.physical_to_logical",return_value=(975,115)), \
             patch("pawzura.app.QApplication.screens",return_value=[]), \
             patch("pawzura.app.windows.close_window") as close:
            Companion.tick(fake)
            fake.pet.bite.call_args.args[1]()
            close.assert_called_once_with(window)

    def test_tab_only_mode_skips_native_inspection_and_dispatches_browser_bite(self):
        fake, config = self.harness()
        config["application_control_enabled"] = False
        config["browsers"]["chrome"]["enabled"] = True
        with patch("pawzura.app.windows.list_windows") as inspect:
            Companion.tick(fake)
            fake.pet.bite.assert_not_called()
            fake.bridge.events.put({"browser": "chrome", "ticket": "test"})
            Companion.tick(fake)
            self.assertTrue(fake.pet.bite.call_args.kwargs["tab"])
            fake.pet.bite.call_args.args[1]()
            fake.bridge.complete.assert_called_once_with("test")
            inspect.assert_not_called()

    def test_turning_off_application_control_blocks_pending_close(self):
        fake, config = self.harness()
        window = self.window("unlisted.exe")
        fake.observed[(window.hwnd, window.pid, window.executable, window.title)] = 90
        with (
            patch("pawzura.app.time.monotonic", return_value=100),
            patch("pawzura.app.windows.list_windows", return_value=[window]),
            patch("pawzura.app.windows.physical_to_logical", return_value=(975, 115)),
            patch("pawzura.app.QApplication.screens", return_value=[]),
            patch("pawzura.app.windows.close_window") as close,
        ):
            Companion.tick(fake)
            callback = fake.pet.bite.call_args.args[1]
            config["application_control_enabled"] = False
            callback()
            close.assert_not_called()

    def test_browser_actions_use_only_synthetic_tab_target_in_preview_and_live(self):
        for active in (False, True):
            for preview in (False, True):
                with self.subTest(active=active, preview=preview):
                    fake,config = self.harness()
                    config["preview_only"] = preview
                    config["browsers"]["chrome"]["enabled"] = True
                    fake.bridge.events.put({"browser":"chrome","ticket":"test","active":active})
                    with patch("pawzura.app.windows.foreground_window") as foreground, \
                         patch("pawzura.app.windows.physical_to_logical") as coordinates, \
                         patch("pawzura.app.windows.close_window") as close:
                        Companion.tick(fake)
                        self.assertEqual(fake.pet.bite.call_args.args[0], QPointF(480,650))
                        self.assertTrue(fake.pet.bite.call_args.kwargs["tab"])
                        self.assertEqual(fake.pet.bite.call_args.kwargs["label"], "Tab preview" if preview else "Blocked tab")
                        fake.pet.bite.call_args.args[1]()
                        fake.bridge.complete.assert_called_once_with("test")
                        foreground.assert_not_called()
                        coordinates.assert_not_called()
                        close.assert_not_called()

    def test_korean_preview_has_explicit_tab_label(self):
        fake,config = self.harness()
        config.update(language="ko", preview_only=True)
        config["browsers"]["chrome"]["enabled"] = True
        fake.bridge.events.put({"browser":"chrome","ticket":"test","active":False})
        Companion.tick(fake)
        self.assertEqual(fake.pet.bite.call_args.kwargs["label"], "탭 미리보기")
