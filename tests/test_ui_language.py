import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
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

    def test_add_subdomain_rules_is_explicit_deduplicated_and_saved_per_browser(self):
        dialog = self.make_dialog()
        self.assertFalse(dialog.include_subdomains.isChecked())
        dialog.site_entry.setText("https://console.example.com")
        dialog.add_site()
        self.assertEqual(dialog.sites.toPlainText(), "https://console.example.com")
        self.assertEqual(self.settings.snapshot()["browsers"]["chrome"]["allowed_sites"], [])
        dialog.site_entry.setText("console.example.com/*")
        dialog.include_subdomains.setChecked(True)
        dialog.add_site()
        self.assertEqual(dialog.sites.toPlainText().splitlines(), ["https://console.example.com", "https://*.console.example.com"])
        dialog.site_entry.setText("console.example.com")
        dialog.add_site()
        self.assertEqual(len(dialog.sites.toPlainText().splitlines()), 2)
        dialog.save()
        self.assertEqual(self.settings.snapshot()["browsers"]["chrome"]["allowed_sites"], ["https://*.console.example.com", "https://console.example.com"])
        self.assertFalse(self.settings.snapshot()["browser_control_enabled"])
        self.assertFalse(self.settings.snapshot()["browsers"]["chrome"]["enabled"])
        dialog.switch_browser("edge")
        self.assertFalse(dialog.include_subdomains.isChecked())
        self.assertEqual(dialog.sites.toPlainText(), "")

    def test_invalid_address_add_does_not_modify_list_or_private_settings(self):
        dialog = self.make_dialog()
        dialog.sites.setPlainText("example.org\nhttps://")
        original = dialog.sites.toPlainText()
        dialog.site_entry.setText("http://127.0.0.1")
        dialog.include_subdomains.setChecked(True)
        dialog.add_site()
        self.assertEqual(dialog.sites.toPlainText(), original)
        self.assertEqual(self.settings.snapshot()["browsers"]["chrome"]["allowed_sites"], [])
        self.assertIn("localhost", dialog.message.text())

    def test_website_switch_turns_off_immediately_even_with_invalid_draft(self):
        self.settings.save({"guard_enabled":True,"browser_control_enabled":True})
        dialog = self.make_dialog()
        dialog.sites.setPlainText("https://")
        dialog.website_control.setChecked(False)
        self.assertFalse(self.settings.snapshot()["browser_control_enabled"])
        self.assertTrue(self.settings.snapshot()["guard_enabled"])
        self.assertEqual(self.settings.snapshot()["browsers"]["chrome"]["allowed_sites"], [])

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

    def test_path_and_query_rules_save_together(self):
        dialog = self.make_dialog()
        dialog.sites.setPlainText("example.com\ngithub.com/my-account\nhttps://example.org/ko?viewMode=svod\nhttp://localhost:3000/home")
        dialog.store_browser()
        rules = dialog.config["browsers"]["chrome"]["allowed_sites"]
        self.assertIn("https://github.com/my-account", rules)
        self.assertIn("https://example.org/ko?viewMode=svod", rules)
        self.assertIn("http://localhost:3000/home", rules)

    def test_bad_rule_reports_its_line_in_selected_language(self):
        self.settings.data["language"] = "ko"
        dialog = self.make_dialog()
        dialog.sites.setPlainText("example.com\nhttps://")
        with self.assertRaisesRegex(ValueError, "2번째 줄"):
            dialog.store_browser()

    def test_profiles_preserve_independent_lists_and_apply_only_on_save(self):
        dialog = self.make_dialog()
        token = self.settings.snapshot()["bridge_token"]
        dialog.apps.setPlainText("work.exe")
        dialog.browser_on.setChecked(True)
        dialog.sites.setPlainText("example.com/work/*")
        with patch("pawzura.ui.QInputDialog.getText", return_value=("Leisure", True)):
            dialog.new_profile()
        dialog.apps.setPlainText("leisure.exe")
        dialog.sites.setPlainText("example.org/*")
        dialog.profile_select.setCurrentText("Default")
        self.assertEqual(dialog.apps.toPlainText(), "work.exe")
        self.assertEqual(self.settings.snapshot()["active_profile"], "Default")
        self.assertNotIn("work.exe", self.settings.snapshot()["allowed_apps"])
        dialog.profile_select.setCurrentText("Leisure")
        self.assertEqual(dialog.apps.toPlainText(), "leisure.exe")
        dialog.save()
        loaded = Settings(self.settings.path).snapshot()
        self.assertEqual(loaded["active_profile"], "Leisure")
        self.assertEqual(loaded["allowed_apps"], ["leisure.exe"])
        self.assertEqual(loaded["profiles"]["Default"]["allowed_apps"], ["work.exe"])
        self.assertEqual(loaded["profiles"]["Leisure"]["browsers"]["chrome"]["allowed_sites"], ["https://example.org"])
        self.assertEqual(loaded["bridge_token"], token)
        self.assertNotIn("bridge_token", loaded["profiles"]["Leisure"])

    def test_reset_default_keeps_allowlists(self):
        from pawzura.config import default_character
        dialog = self.make_dialog()
        dialog.apps.setPlainText("custom.exe")
        dialog.apply_character({"seed": 1, "body": "#123456", "accent": "#654321", "ears": "cat", "accessory": "star"})
        dialog.reset_button.click()
        dialog.save()
        self.assertEqual(self.settings.snapshot()["character"], default_character())
        self.assertEqual(self.settings.snapshot()["allowed_apps"], ["custom.exe"])

    def test_invalid_profile_edit_prevents_switch(self):
        dialog = self.make_dialog()
        with patch("pawzura.ui.QInputDialog.getText", return_value=("Work", True)):
            dialog.new_profile()
        dialog.sites.setPlainText("https://")
        dialog.profile_select.setCurrentText("Default")
        self.assertEqual(dialog.config["active_profile"], "Work")
        self.assertEqual(dialog.profile_select.currentText(), "Work")

    def test_profile_rename_and_delete_preserve_surviving_lists(self):
        from PySide6.QtWidgets import QMessageBox
        dialog = self.make_dialog()
        with patch("pawzura.ui.QInputDialog.getText", return_value=("Work", True)):
            dialog.new_profile()
        dialog.apps.setPlainText("work.exe")
        with patch("pawzura.ui.QInputDialog.getText", return_value=("Office", True)):
            dialog.rename_profile()
        self.assertNotIn("Work", dialog.config["profiles"])
        dialog.profile_select.setCurrentText("Default")
        with patch("pawzura.ui.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            dialog.delete_profile()
        dialog.save()
        self.assertEqual(self.settings.snapshot()["active_profile"], "Office")
        self.assertEqual(self.settings.snapshot()["allowed_apps"], ["work.exe"])
        dialog.delete_profile()
        self.assertEqual(len(dialog.config["profiles"]), 1)

    def test_recovery_recreates_window_without_executing_pending_close(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from PySide6.QtCore import QPointF
        from pawzura.app import Companion
        from pawzura.pet import Pet
        before = self.settings.snapshot()
        old = Pet(before["character"])
        close = Mock()
        old.bite(QPointF(-9999, -9999), close)
        fake = SimpleNamespace(settings=self.settings, pet=old, bridge=Mock(), dialog=None, show_settings=Mock(), refresh_menu=Mock())
        Companion.recover_pet(fake)
        self.assertIsNot(old, fake.pet)
        self.assertIsNone(old.action)
        self.assertFalse(old.timer.isActive())
        self.assertTrue(fake.pet.isVisible())
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(fake.pet.geometry()))
        self.assertEqual(set(self.settings.snapshot()["allowed_apps"]), set(before["allowed_apps"]))
        close.assert_not_called()
        fake.pet.dispose()
