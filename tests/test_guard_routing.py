import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from types import SimpleNamespace
from queue import Queue
from unittest.mock import Mock, patch
import unittest
from pawzura.app import Companion
from pawzura.config import defaults
from pawzura.windows import Window, close_window


class RoutingTests(unittest.TestCase):
    def harness(self):
        config = defaults()
        config.update(guard_enabled=True,preview_only=False,allowed_apps=["codex.exe"])
        fake = SimpleNamespace(settings=SimpleNamespace(snapshot=lambda: config),
                               pet=SimpleNamespace(action=None,bite=Mock()),
                               bridge=SimpleNamespace(events=Queue(),pairing_events=Queue(),complete=Mock()),
                               pairing_dialog_open=False,observed={},cooldown={})
        return fake,config

    def window(self, exe):
        return Window(100,200,exe,"Example",(100,100,1000,700),(975,115))

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

    def test_tab_animation_is_below_titlebar_and_never_closes_native_window(self):
        fake,config = self.harness()
        config["browsers"]["chrome"]["enabled"] = True
        fake.bridge.events.put({"browser":"chrome","ticket":"test","active":True})
        with patch("pawzura.app.windows.foreground_window",return_value=self.window("chrome.exe")), \
             patch("pawzura.app.windows.physical_to_logical",side_effect=lambda x,y,s:(x,y)), \
             patch("pawzura.app.QApplication.screens",return_value=[]), \
             patch("pawzura.app.windows.close_window") as close:
            Companion.tick(fake)
            point = fake.pet.bite.call_args.args[0]
            self.assertGreater(point.y(),150)
            self.assertEqual(fake.pet.bite.call_args.kwargs["label"],"TAB")
            fake.pet.bite.call_args.args[1]()
            fake.bridge.complete.assert_called_once_with("test")
            close.assert_not_called()
