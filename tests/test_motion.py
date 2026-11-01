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

    def test_home_fits_entire_character_above_taskbar(self):
        area = self.app.primaryScreen().availableGeometry()
        self.pet.home()
        self.assertTrue(area.contains(self.pet.geometry()))

    def test_tab_marker_stays_near_taskbar_and_disappears_on_cancel(self):
        self.pet.show()
        point = self.pet.tab_target_point()
        screen = self.app.screenAt(point.toPoint())
        area = screen.availableGeometry()
        self.assertGreater(point.y(), area.center().y())
        self.assertAlmostEqual(point.x(), area.center().x())
        self.pet.bite(point, lambda: self.fail("Cancelled tab bite executed"), label="Tab preview", tab=True)
        marker = self.pet.action["marker"]
        self.assertTrue(area.contains(marker.geometry()))
        self.assertTrue(marker.isVisible())
        self.pet.cancel_bite()
        self.assertFalse(marker.isVisible())

    def test_display_change_cancels_pending_close_and_recovers_position(self):
        hits = []
        self.pet.bite(QPointF(-9000, -9000), lambda: hits.append("closed"))
        self.pet.px, self.pet.py = -9000, -9000
        self.pet.screen_changed()
        self.assertIsNone(self.pet.action)
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(self.pet.geometry()))
        self.pet.tick()
        self.assertEqual(hits, [])

    def test_corrupt_appearance_still_renders(self):
        broken = Pet({"body": None, "ears": "invalid", "seed": []})
        broken.timer.stop()
        broken.show()
        self.app.processEvents()
        self.assertFalse(broken.grab().isNull())
        broken.dispose()



if __name__ == "__main__":
    unittest.main()
