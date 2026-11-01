import io
import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Qt
from pawzura.characters import COLORS, DETAIL_MODEL, FEATURES, LEGACY_DETAILS, MAX_PROMPT, MODEL, generate_character
from pawzura.config import Settings, default_character, safe_character
from pawzura.pet import draw_character
from pawzura.ui import CHARACTER_LABELS, GenerationWorker, SettingsDialog, TEXT


class CharacterCustomizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def output(self):
        return {key: default_character()[key] for key in (*COLORS, *FEATURES)}

    def test_prompt_and_schema_reach_only_loopback_and_explicit_choices_win(self):
        response = io.BytesIO(json.dumps({"response": json.dumps(self.output())}).encode())
        opener = Mock()
        opener.open.return_value = response
        prompt = "민트 몸, 여우 귀, 요정 날개. Original woodland friend."
        with patch("pawzura.characters.build_opener", return_value=opener) as build:
            result = generate_character(prompt, {"body": "#123456", "ears": "fox", "wings": "fairy"})
        request = opener.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/generate")
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIn(prompt, payload["prompt"])
        self.assertEqual(set(payload["format"]["required"]), set(COLORS) | set(FEATURES))
        self.assertEqual((result["body"], result["ears"], result["wings"]), ("#123456", "fox", "fairy"))
        self.assertNotIn("description", result)
        self.assertNotIn("prompt", result)

    def test_invalid_user_options_and_long_prompt_fail_before_network(self):
        with patch("pawzura.characters.build_opener") as network:
            for options in ({"body": "red"}, {"ears": "code"}, {"script": "anything"}):
                with self.assertRaises(ValueError):
                    generate_character("example", options)
            with self.assertRaises(ValueError):
                generate_character("a" * (MAX_PROMPT + 1))
            network.assert_not_called()

    def test_incomplete_model_output_does_not_become_a_random_success(self):
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'{"response":"{\\"body\\":\\"#123456\\"}"}')
        with patch("pawzura.characters.build_opener", return_value=opener):
            with self.assertRaises(ValueError):
                generate_character("example")

    def test_old_designs_keep_default_details_and_strip_unknown_data(self):
        old = {"seed": 1, "body": "#123456", "accent": "#abcdef", "ears": "rabbit", "accessory": "scarf",
               "prompt": "PRIVATE_TEST_ONLY", "script": "do not execute"}
        result = safe_character(old)
        self.assertTrue(all(result[key] == value for key, value in LEGACY_DETAILS.items()))
        self.assertNotIn("prompt", result)
        self.assertNotIn("script", result)

    def test_new_traits_survive_local_save_and_custom_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = Settings(path)
            spec = {**default_character(), "source": "custom", "eyes": "happy", "tail": "fox", "wings": "bat", "markings": "stripes"}
            settings.save({"character": spec})
            self.assertEqual(Settings(path).snapshot()["character"], spec)

    def render(self, spec):
        image = QImage(144, 146, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        draw_character(painter, spec, 0.2)
        painter.end()
        return image

    def test_larger_model_provenance_survives_manual_edits(self):
        spec = safe_character({**default_character(), "source": "qwen", "model": DETAIL_MODEL})
        edited = safe_character({**spec, "source": "custom", "tail": "fox"})
        self.assertEqual(edited["model"], DETAIL_MODEL)
        self.assertIn("1.5B", edited["model_card"])
        with patch("pawzura.characters.build_opener") as network:
            with self.assertRaises(ValueError):
                generate_character("example", model="unreviewed-model")
            network.assert_not_called()

    def test_worker_failure_keeps_design_and_reenables_controls(self):
        import time
        with tempfile.TemporaryDirectory() as folder:
            dialog = SettingsDialog(Settings(Path(folder) / "settings.json"))
            before = dict(dialog.config["character"])
            try:
                with patch("pawzura.ui.generate_character", side_effect=ValueError("test failure")):
                    dialog.generate()
                    deadline = time.monotonic() + 4
                    while dialog.worker is not None and time.monotonic() < deadline:
                        self.app.processEvents()
                        time.sleep(.01)
                self.assertIsNone(dialog.worker)
                self.assertTrue(dialog.generate_button.isEnabled())
                self.assertTrue(dialog.custom_panel.isEnabled())
                self.assertEqual(dialog.config["character"], before)
                self.assertIn("test failure", dialog.message.text())
            finally:
                if dialog.worker:
                    dialog.worker.wait()
                dialog.connection_timer.stop()
                dialog.character_preview.timer.stop()
                dialog.deleteLater()

    def test_each_supported_trait_renders_and_changes_the_default(self):
        base = default_character()
        original = self.render(base)
        for key, values in FEATURES.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    rendered = self.render({**base, key: value})
                    if value != base[key]:
                        self.assertNotEqual(rendered, original)

    def test_manual_ui_applies_without_model_and_prompt_is_not_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(Path(folder) / "settings.json")
            dialog = SettingsDialog(settings)
            try:
                dialog.character_description.setPlainText("PRIVATE_TEST_ONLY")
                dialog.character_colors["body"].setText("#123456")
                choice = dialog.character_choices["ears"]
                choice.setCurrentIndex(choice.findData("fox"))
                with patch("pawzura.ui.generate_character") as generate:
                    dialog.apply_custom_options()
                    generate.assert_not_called()
                dialog.save()
                self.assertEqual(settings.snapshot()["character"]["ears"], "fox")
                self.assertNotIn("PRIVATE_TEST_ONLY", settings.path.read_text(encoding="utf-8"))
                self.assertEqual(dialog.character_preview.spec["body"], "#123456")
                for field in dialog.character_colors.values(): field.clear()
                for field in dialog.character_choices.values(): field.setCurrentIndex(0)
                self.assertEqual(dialog.selected_character_options(), {})
            finally:
                dialog.connection_timer.stop()
                dialog.character_preview.timer.stop()
                dialog.deleteLater()

    def test_worker_uses_a_snapshot_and_clears_its_description(self):
        overrides = {"wings": "fairy"}
        worker = GenerationWorker("example", overrides)
        overrides["wings"] = "bat"
        with patch("pawzura.ui.generate_character", return_value=default_character()) as generate:
            worker.run()
            generate.assert_called_once_with("example", {"wings": "fairy"}, MODEL)
        self.assertEqual(worker.description, "")
        self.assertEqual(set(CHARACTER_LABELS["en"]), set(CHARACTER_LABELS["ko"]))
        self.assertEqual(set(TEXT["en"]), set(TEXT["ko"]))


if __name__ == "__main__":
    unittest.main()
