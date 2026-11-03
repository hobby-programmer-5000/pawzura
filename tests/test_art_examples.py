import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import unittest
from unittest.mock import patch

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication
from pawzura.art_ui import ArtworkDialog
from pawzura.characters import MAX_PROMPT


class ArtworkExamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialogs = []

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.worker = None
            dialog.preview.timer.stop()
            dialog.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def dialog(self, language):
        dialog = ArtworkDialog(language)
        self.dialogs.append(dialog)
        return dialog

    def test_selection_preserves_custom_text_until_insert_and_never_starts_generation(self):
        for language in ('en', 'ko'):
            dialog = self.dialog(language)
            dialog.description.setPlainText('An original custom character description')
            chosen = []
            dialog.chosen.connect(chosen.append)
            with patch('pawzura.art_ui.ArtworkWorker') as worker:
                prompts = []
                for index in range(dialog.example_choice.count()):
                    previous = dialog.description.toPlainText()
                    dialog.example_choice.setCurrentIndex(index)
                    self.assertEqual(dialog.description.toPlainText(), previous)
                    dialog.sample.click()
                    prompt = dialog.description.toPlainText()
                    self.assertGreater(len(prompt), 20)
                    self.assertLessEqual(len(prompt), MAX_PROMPT)
                    prompts.append(prompt)
                self.assertEqual(len(set(prompts)), dialog.example_choice.count())
                worker.assert_not_called()
            self.assertFalse(dialog.agree.isChecked())
            self.assertIsNone(dialog.result_spec)
            self.assertEqual(chosen, [])

    def test_busy_generation_freezes_example_controls_and_direct_insert(self):
        dialog = self.dialog('en')
        dialog.description.setPlainText('Keep this in-flight description')
        dialog.worker = object()
        dialog.controls()
        self.assertFalse(dialog.example_choice.isEnabled())
        self.assertFalse(dialog.sample.isEnabled())
        dialog.insert_example()
        self.assertEqual(dialog.description.toPlainText(), 'Keep this in-flight description')
        dialog.worker = None
        dialog.controls()
        self.assertTrue(dialog.example_choice.isEnabled())
        self.assertTrue(dialog.sample.isEnabled())


if __name__ == '__main__':
    unittest.main()
