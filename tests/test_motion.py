import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from unittest.mock import patch
from PySide6.QtCore import QPointF, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pawzura.characters import random_character
from pawzura.pet import Pet


class MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.pet = Pet(random_character(42))
        self.pet.timer.stop()

    def tearDown(self):
        self.pet.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_hit_callback_occurs_once_then_returns_home(self):
        hits = []
        origin = (self.pet.px, self.pet.py)
        with patch("pawzura.pet.time.monotonic", return_value=100):
            self.assertTrue(self.pet.bite(QPointF(200, 100), lambda: hits.append("hit")))
            self.assertFalse(self.pet.bite(QPointF(10, 10), lambda: hits.append("wrong")))
        with patch("pawzura.pet.time.monotonic", return_value=100.5):
            self.pet.tick()
            self.assertEqual(hits, [])
        with patch("pawzura.pet.time.monotonic", return_value=100.8):
            self.pet.tick()
            self.pet.tick()
            self.assertEqual(hits, ["hit"])
        with patch("pawzura.pet.time.monotonic", return_value=102):
            self.pet.tick()
            self.assertIsNone(self.pet.action)
            self.assertEqual((self.pet.px, self.pet.py), origin)

    def test_cancel_does_not_close_target(self):
        hits = []
        self.pet.bite(QPointF(200, 100), lambda: hits.append("hit"))
        self.pet.cancel_bite()
        self.pet.tick()
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
