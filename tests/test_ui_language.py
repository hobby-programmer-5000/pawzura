import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import tempfile
import unittest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pawzura.config import Settings
from pawzura.ui import SettingsDialog


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.temp.name) / "settings.json")
        self.dialogs = []

    def make_dialog(self):
        dialog = SettingsDialog(self.settings)
        self.dialogs.append(dialog)
        return dialog

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.character_preview.timer.stop()
            dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.temp.cleanup()

    def test_new_install_is_english(self):
        dialog = self.make_dialog()
        self.assertEqual(dialog.tabs.tabText(0), "General")
        self.assertEqual(dialog.language.currentData(), "en")

    def test_korean_save_notifies_and_persists(self):
        dialog = self.make_dialog()
        events = []
        dialog.language_changed.connect(lambda: events.append("refresh"))
        dialog.language.setCurrentIndex(dialog.language.findData("ko"))
        dialog.save()
        self.assertEqual(events, ["refresh"])
        self.assertEqual(Settings(self.settings.path).snapshot()["language"], "ko")
        translated = self.make_dialog()
        self.assertEqual(translated.tabs.tabText(0), "일반")
        self.assertEqual(translated.language.currentData(), "ko")

    def test_pairing_copies_only_the_connection_code(self):
        dialog = self.make_dialog()
        dialog.copy_pairing()
        self.assertEqual(self.app.clipboard().text(), self.settings.snapshot()["bridge_token"])
        self.assertNotIn("{", self.app.clipboard().text())
        self.assertIn("Connect and test", dialog.message.text())
