import io
import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel
from pawzura.characters import GPU_MODELS, DETAIL_MODEL, MODEL, GenerationError, generate_character, models_for_vram
from pawzura.config import Settings, default_character
from pawzura.ui import ModelSetupDialog, SettingsDialog


class ThemeModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "settings.json"
        self.settings = Settings(self.path)
        self.dialogs = []

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.connection_timer.stop()
            dialog.character_preview.timer.stop()
            dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.temp.cleanup()

    def dialog(self):
        dialog = SettingsDialog(self.settings)
        self.dialogs.append(dialog)
        return dialog

    def test_theme_preview_and_saved_reopen_keep_profiles_and_guard_unchanged(self):
        self.settings.save()
        dialog = self.dialog()
        before = self.settings.snapshot()
        dialog.theme.setCurrentIndex(dialog.theme.findData("light"))
        self.assertEqual(dialog.character_preview.theme, "light")
        self.assertEqual(self.settings.snapshot()["theme"], "dark")
        dialog.save()
        loaded = Settings(self.path).snapshot()
        self.assertEqual(loaded["theme"], "light")
        for key in ("profiles", "allowed_apps", "guard_enabled", "preview_only", "browser_control_enabled"):
            self.assertEqual(loaded[key], before[key])
        self.settings = Settings(self.path)
        self.assertEqual(self.dialog().theme.currentData(), "light")

    def test_old_settings_and_unknown_preferences_load_safe_defaults(self):
        saved = self.settings.snapshot()
        for key in ("theme", "advanced_models", "vram_tier", "designer_model"):
            saved.pop(key, None)
        self.path.write_text(json.dumps(saved))
        loaded = Settings(self.path).snapshot()
        self.assertEqual((loaded["theme"], loaded["vram_tier"], loaded["advanced_models"]), ("dark", 0, False))
        saved.update(theme="invalid", advanced_models="yes", vram_tier=True, designer_model="unknown")
        self.path.write_text(json.dumps(saved))
        loaded = Settings(self.path).snapshot()
        self.assertEqual((loaded["theme"], loaded["vram_tier"], loaded["advanced_models"], loaded["designer_model"]), ("dark", 0, False, DETAIL_MODEL))

    def test_vram_choices_require_opt_in_and_do_not_choose_a_large_model_automatically(self):
        dialog = self.dialog()
        self.assertFalse(dialog.advanced_models.isChecked())
        self.assertFalse(dialog.vram_tier.isEnabled())
        dialog.advanced_models.setChecked(True)
        for tier, count in ((2, 2), (4, 3), (6, 4), (8, 5)):
            dialog.vram_tier.setCurrentIndex(dialog.vram_tier.findData(tier))
            self.assertEqual(dialog.character_model.count(), count)
            self.assertEqual(dialog.character_model.currentData(), DETAIL_MODEL)
        largest = next(model for model, info in GPU_MODELS.items() if info[0] == 8)
        dialog.character_model.setCurrentIndex(dialog.character_model.findData(largest))
        self.assertEqual(dialog.model_command.text(), "ollama pull " + largest)
        dialog.save()
        self.assertEqual(Settings(self.path).snapshot()["designer_model"], largest)
        dialog.vram_tier.setCurrentIndex(dialog.vram_tier.findData(2))
        self.assertEqual(dialog.character_model.currentData(), DETAIL_MODEL)
        dialog.advanced_models.setChecked(False)
        self.assertEqual(dialog.character_model.count(), 2)

    def test_every_advanced_model_uses_exact_identifier_schema_and_non_thinking_mode(self):
        for model in GPU_MODELS:
            with self.subTest(model=model):
                opener = Mock()
                spec = default_character()
                opener.open.return_value = io.BytesIO(json.dumps({"response": json.dumps(spec)}).encode())
                with patch("pawzura.characters.build_opener", return_value=opener):
                    result = generate_character("An original forest creature", {"tail": "fox"}, model)
                payload = json.loads(opener.open.call_args.args[0].data)
                self.assertEqual(payload["model"], model)
                self.assertFalse(payload["think"])
                self.assertEqual(payload["keep_alive"], 0)
                self.assertEqual(payload["options"]["num_ctx"], 4096)
                self.assertEqual((result["tail"], result["model"]), ("fox", model))
                self.assertIn("huggingface.co/Qwen/", result["model_card"])
        self.assertEqual(models_for_vram(8, False), (DETAIL_MODEL, MODEL))

    def test_advanced_preferences_are_not_stored_inside_allowlist_profiles(self):
        self.settings.save({"theme": "light", "advanced_models": True, "vram_tier": 8})
        for profile in self.settings.snapshot()["profiles"].values():
            self.assertFalse(set(profile) & {"theme", "advanced_models", "vram_tier", "designer_model"})

    def test_model_failures_give_actionable_codes_without_echoing_backend_data(self):
        errors = (
            (HTTPError("http://127.0.0.1:11434", 404, "missing", {}, io.BytesIO(b'backend-only-data')), "model_missing"),
            (HTTPError("http://127.0.0.1:11434", 500, "error", {}, io.BytesIO(b'not enough memory backend-only-data')), "model_memory_error"),
            (URLError("backend-only-data"), "ollama_unavailable"),
        )
        for error, code in errors:
            opener = Mock()
            opener.open.side_effect = error
            with patch("pawzura.characters.build_opener", return_value=opener):
                with self.assertRaises(GenerationError) as caught:
                    generate_character("generic creature")
            self.assertEqual(str(caught.exception), code)

    def test_invalid_model_preferences_cannot_replace_saved_settings(self):
        self.settings.save()
        before = self.path.read_bytes()
        for updates in ({"theme": "invalid"}, {"vram_tier": True}, {"vram_tier": 10},
                        {"advanced_models": "yes"}, {"designer_model": next(iter(GPU_MODELS))}):
            with self.assertRaises(ValueError):
                self.settings.save(updates)
            self.assertEqual(self.path.read_bytes(), before)

    def test_each_model_command_is_visible_copyable_and_does_not_install_or_save(self):
        dialog = self.dialog()
        before = self.settings.snapshot()
        dialog.advanced_models.setChecked(True)
        dialog.vram_tier.setCurrentIndex(dialog.vram_tier.findData(8))
        with patch("pawzura.ui.generate_character") as generate:
            for index in range(dialog.character_model.count()):
                dialog.character_model.setCurrentIndex(index)
                model = dialog.character_model.currentData()
                dialog.copy_model_button.click()
                self.assertEqual(QApplication.clipboard().text(), "ollama pull " + model)
                self.assertIn("PowerShell", dialog.message.text())
                self.assertIn("GB", dialog.model_memory.text())
            generate.assert_not_called()
        self.assertEqual(self.settings.snapshot(), before)

    def test_guide_has_exact_commands_for_all_tiers_in_both_languages(self):
        expected = {MODEL, DETAIL_MODEL, *GPU_MODELS}
        before = self.settings.snapshot()
        for language in ("en", "ko"):
            guide = ModelSetupDialog(DETAIL_MODEL, language)
            try:
                guide.resize(650, 520)
                guide.show()
                self.app.processEvents()
                limits = guide.findChild(QLabel, "modelSetupLimits")
                self.assertGreater(limits.geometry().top(), max(field.geometry().bottom() for field in guide.command_fields.values()))
                self.assertEqual(set(guide.command_fields), expected)
                for model in expected:
                    guide.copy_buttons[model].click()
                    self.assertEqual(QApplication.clipboard().text(), "ollama pull " + model)
                    self.assertTrue(guide.command_fields[model].isReadOnly())
            finally:
                guide.hide()
                guide.deleteLater()
        self.assertEqual(self.settings.snapshot(), before)

    def test_missing_model_feedback_names_requested_model_and_recovery_command(self):
        from types import SimpleNamespace
        requested = next(model for model, info in GPU_MODELS.items() if info[0] == 6)
        dialog = self.dialog()
        before = dict(dialog.config["character"])
        for language in ("en", "ko"):
            from pawzura.ui import TEXT
            dialog.t = TEXT[language]
            dialog.worker = SimpleNamespace(model=requested)
            dialog.generation_failed("model_missing")
            self.assertIn(requested, dialog.message.text())
            self.assertIn("ollama pull " + requested, dialog.message.text())
            self.assertIn("success", dialog.message.text())
            self.assertEqual(dialog.config["character"], before)
        dialog.worker = None

    def test_async_missing_model_keeps_appearance_and_restores_controls(self):
        import time
        dialog = self.dialog()
        dialog.advanced_models.setChecked(True)
        dialog.vram_tier.setCurrentIndex(dialog.vram_tier.findData(8))
        requested = next(model for model, info in GPU_MODELS.items() if info[0] == 4)
        dialog.character_model.setCurrentIndex(dialog.character_model.findData(requested))
        before = dict(dialog.config["character"])
        with patch("pawzura.ui.generate_character", side_effect=GenerationError("model_missing")):
            dialog.generate()
            deadline = time.monotonic() + 4
            while dialog.worker is not None and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
        self.assertIsNone(dialog.worker)
        self.assertEqual(dialog.config["character"], before)
        self.assertIn("ollama pull " + requested, dialog.message.text())
        self.assertTrue(dialog.generate_button.isEnabled())
        self.assertTrue(dialog.vram_tier.isEnabled())
