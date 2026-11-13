import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QEvent, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from pawzura.app import Companion
from pawzura.config import Settings, default_character
from pawzura.pet import Pet, fit_pet_position, logical_to_physical, physical_center_to_logical
from pawzura.ui import SettingsDialog


class PlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.temp.name) / "settings.json")
        self.pet = Pet(default_character())
        self.pet.timer.stop()
        self.pet.show()
        self.pet.next_idle = float("inf")
        self.dialogs = []

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.connection_timer.stop()
            dialog.character_preview.timer.stop()
            dialog.deleteLater()
        self.pet.dispose()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.temp.cleanup()

    def pointer(self, kind, global_pos, local=None):
        left = Qt.MouseButton.LeftButton
        event = QMouseEvent(kind, local or global_pos - QPointF(self.pet.pos()), global_pos,
                            Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else left,
                            Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else left,
                            Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.pet, event)

    def drag(self, delta):
        start = QPointF(self.pet.pos()) + QPointF(72, 72)
        self.pointer(QEvent.Type.MouseButtonPress, start)
        self.pointer(QEvent.Type.MouseMove, start + delta)
        self.pointer(QEvent.Type.MouseButtonRelease, start + delta)

    def test_click_threshold_preserves_reactions_and_does_not_pin(self):
        for kind in ("wave", "hop", "cheer"):
            self.pet.reaction = None
            start = QPointF(self.pet.pos()) + QPointF(72, 72)
            self.pointer(QEvent.Type.MouseButtonPress, start)
            self.assertIsNone(self.pet.reaction)
            self.pointer(QEvent.Type.MouseMove, start + QPointF(1, 1))
            self.pointer(QEvent.Type.MouseButtonRelease, start + QPointF(1, 1))
            self.assertEqual(self.pet.reaction["kind"], kind)
            self.assertFalse(self.pet.pinned)
            self.assertFalse(self.pet.pointer_active)

    def test_drag_pins_and_persists_without_click_or_allowlist_changes(self):
        self.settings.save()  # Materialize the ordinary sorted Default profile first.
        before = self.settings.snapshot()
        fake = SimpleNamespace(settings=self.settings, tray=Mock(), dialog=None)
        self.pet.placement_changed.connect(lambda p: Companion.save_placement(fake, p))
        start = QPointF(self.pet.px, self.pet.py)
        self.drag(QPointF(60, -90))
        self.assertEqual(QPointF(self.pet.px, self.pet.py), start + QPointF(60, -90))
        self.assertTrue(self.pet.pinned)
        self.assertIsNone(self.pet.reaction)
        self.assertEqual(self.pet.click_count, 0)
        loaded = Settings(self.settings.path).snapshot()
        self.assertTrue(loaded["pet_pinned"])
        self.assertEqual(loaded["pet_position"], self.pet.resting_position())
        for key in ("profiles", "allowed_apps", "browsers", "guard_enabled", "preview_only"):
            self.assertEqual(loaded[key], before[key])
        point = self.pet.resting_position()
        self.pet.home()
        self.pet.set_placement(True, loaded["pet_position"])
        self.assertEqual(self.pet.resting_position(), point)

    def test_pin_stops_travel_and_hop_translation_and_unpin_resumes_floor_walk(self):
        self.pet.place_at(QPointF(self.pet.px, self.pet.py - 100))
        self.pet.set_placement(True)
        origin = self.pet.pos()
        self.pet.react("hop")
        for _ in range(3):
            self.pet.tick()
            self.assertEqual(self.pet.pos(), origin)
        self.pet.reaction = None
        self.pet.set_placement(False)
        self.assertEqual(self.pet.py, self.app.primaryScreen().availableGeometry().bottom() - self.pet.height() + 1)
        start = self.pet.px
        self.pet.last_tick = 100
        with patch("pawzura.pet.time.monotonic", return_value=100.1):
            self.pet.tick()
        self.assertGreater(self.pet.px, start)

    def test_pinned_bite_returns_to_pinned_height_and_hits_only_once(self):
        self.pet.place_at(QPointF(self.pet.px, self.pet.py - 100))
        self.pet.set_placement(True)
        origin = self.pet.resting_position()
        hits = []
        with patch("pawzura.pet.time.monotonic", return_value=100):
            self.pet.bite(QPointF(200, 100), lambda: hits.append(True))
        with patch("pawzura.pet.time.monotonic", return_value=100.8):
            self.pet.tick()
        with patch("pawzura.pet.time.monotonic", return_value=102):
            self.pet.tick()
            self.pet.tick()
        self.assertEqual(hits, [True])
        self.assertEqual(self.pet.resting_position(), origin)

    def test_drag_cancels_inflight_bite_and_invalidates_browser_tickets(self):
        hits, cancelled = [], []
        self.pet.drag_started.connect(lambda: cancelled.append(True))
        with patch("pawzura.pet.time.monotonic", return_value=100):
            self.pet.bite(QPointF(200, 100), lambda: hits.append(True), tab=True)
        with patch("pawzura.pet.time.monotonic", return_value=100.4):
            self.pet.tick()
        self.drag(QPointF(35, 25))
        self.assertIsNone(self.pet.action)
        self.assertFalse(self.pet.tab_marker.isVisible())
        with patch("pawzura.pet.time.monotonic", return_value=101):
            self.pet.tick()
        self.assertEqual(hits, [])
        self.assertEqual(cancelled, [True])

    def test_pointer_hold_blocks_new_bites_and_geometry_change_clears_gesture(self):
        start = QPointF(self.pet.pos()) + QPointF(72, 72)
        self.pointer(QEvent.Type.MouseButtonPress, start)
        self.assertFalse(self.pet.bite(QPointF(10, 10), self.fail))
        self.pet.screen_changed()
        self.assertFalse(self.pet.pointer_active)
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(self.pet.geometry()))

    def test_failed_drop_save_notifies_and_keeps_runtime_position(self):
        fake = SimpleNamespace(settings=self.settings, tray=Mock(), dialog=None)
        self.pet.placement_changed.connect(lambda p: Companion.save_placement(fake, p))
        with patch.object(self.settings, "save", side_effect=OSError("Synthetic disk failure")):
            self.drag(QPointF(50, -50))
        self.assertTrue(self.pet.pinned)
        self.assertFalse(self.settings.snapshot()["pet_pinned"])
        fake.tray.showMessage.assert_called_once()

    def test_lost_mouse_grab_does_not_leave_a_stuck_held_gesture(self):
        start = QPointF(self.pet.pos()) + QPointF(72, 72)
        self.pointer(QEvent.Type.MouseButtonPress, start)
        QApplication.sendEvent(self.pet, QEvent(QEvent.Type.UngrabMouse))
        self.assertFalse(self.pet.pointer_active)
        self.assertFalse(self.pet.dragging)
        self.assertTrue(self.pet.bite(QPointF(20, 20), lambda: None))

    def test_apply_preserves_pinned_position_and_recovery_clears_saved_location(self):
        self.settings.save({"pet_pinned": True, "pet_position": {"x": 200, "y": 100}})
        fake = SimpleNamespace(settings=self.settings, pet=self.pet, bridge=Mock(), tray=Mock(),
                               dialog=None, make_icon=Mock(), refresh_menu=Mock(), show_settings=Mock(),
                               observed={}, previewed=set())
        Companion.apply(fake)
        self.assertTrue(self.pet.pinned)
        self.assertEqual(self.pet.resting_position(), {"x": 200, "y": 100})
        Companion.recover_pet(fake)
        self.pet = fake.pet
        self.pet.timer.stop()
        self.assertTrue(self.pet.pinned)
        self.assertIsNone(self.settings.snapshot()["pet_position"])
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(self.pet.geometry()))

    def test_work_area_fit_handles_negative_origins_gaps_and_oversized_positions(self):
        areas = [QRect(-1600, -300, 1600, 900), QRect(0, 0, 1920, 1040)]
        size = QSize(144, 146)
        for point, index in ((QPointF(-1500, -200), 0), (QPointF(-9999, -9999), 0),
                             (QPointF(5000, 5000), 1), (QPointF(200, -200), 1)):
            actual, fitted = fit_pet_position(point, size, areas)
            self.assertEqual(actual, index)
            self.assertTrue(areas[actual].contains(QRect(fitted.toPoint(), size)))
        # Independent areas avoid placing the pet in gaps in an L-shaped desktop.
        actual, fitted = fit_pet_position(QPointF(1700, -500), size, areas)
        self.assertTrue(areas[actual].contains(QRect(fitted.toPoint(), size)))

    def test_settings_migrate_validate_and_reject_bad_position_without_overwriting(self):
        data = self.settings.snapshot()
        data.pop("pet_pinned")
        data.pop("pet_position")
        self.settings.path.write_text(json.dumps(data))
        loaded = Settings(self.settings.path)
        self.assertFalse(loaded.snapshot()["pet_pinned"])
        self.assertIsNone(loaded.snapshot()["pet_position"])
        original = self.settings.path.read_bytes()
        for bad in ({"x": True, "y": 1}, {"x": 1.5, "y": 2}, {"x": 1}, {"x": 10**9, "y": 0}, "bad"):
            with self.assertRaises(ValueError):
                loaded.save({"pet_pinned": True, "pet_position": bad})
            self.assertEqual(self.settings.path.read_bytes(), original)
        with self.assertRaises(ValueError):
            loaded.save({"pet_pinned": "yes"})

    def test_general_pin_saves_current_resting_location_in_both_languages(self):
        for language in ("en", "ko"):
            self.settings.save({"language": language, "pet_pinned": False, "pet_position": None})
            dialog = SettingsDialog(self.settings, position_provider=lambda: {"x": -500, "y": 100})
            self.dialogs.append(dialog)
            dialog.pin.setChecked(True)
            self.assertFalse(self.settings.snapshot()["pet_pinned"])
            dialog.save()
            self.assertTrue(self.settings.snapshot()["pet_pinned"])
            self.assertEqual(self.settings.snapshot()["pet_position"], {"x": -500, "y": 100})
            dialog.pin.setChecked(False)
            dialog.save()
            self.assertIsNone(self.settings.snapshot()["pet_position"])

    def test_mixed_dpi_bite_leap_avoids_logical_gap_and_switches_owning_screen(self):
        left = SimpleNamespace(geometry=lambda: QRect(-1920, 0, 1536, 864), availableGeometry=lambda: QRect(-1920, 0, 1536, 824), devicePixelRatio=lambda: 1.25)
        center = SimpleNamespace(geometry=lambda: QRect(0, 0, 1920, 1080), availableGeometry=lambda: QRect(0, 0, 1920, 1040), devicePixelRatio=lambda: 1.0)
        screens = [left, center]
        _, phys = logical_to_physical(QPointF(-420, 200), screens)
        self.assertAlmostEqual(phys.x(), -45.0, places=3)
        scr_l, pos_l = physical_center_to_logical(QPointF(-5, 300), 144, 146, screens)
        self.assertIs(scr_l, left)
        self.assertLessEqual(pos_l.x() + 72, -385)
        scr_c, pos_c = physical_center_to_logical(QPointF(5, 300), 144, 146, screens)
        self.assertIs(scr_c, center)
        self.assertAlmostEqual(pos_c.x(), -67.0, places=3)
        with patch.object(self.pet, "screens", return_value=screens), \
             patch.object(self.pet, "use_screen") as use_screen, \
             patch.object(self.pet, "move"):
            self.pet.px, self.pet.py = 1000.0, 894.0
            with patch("pawzura.pet.time.monotonic", return_value=100.0):
                self.pet.bite(QPointF(-420, 200), lambda: None)
            xs = []
            for ts in (100.2, 100.45, 100.55, 100.70, 100.80, 101.20, 101.50, 101.80):
                with patch("pawzura.pet.time.monotonic", return_value=ts):
                    self.pet.tick()
                chosen = use_screen.call_args.args[0] if use_screen.call_args else None
                if chosen is left:
                    self.assertLessEqual(self.pet.px, -456.0)
                xs.append((chosen, self.pet.px))
            self.assertTrue(any(c is left for c, _ in xs))
            self.assertTrue(any(c is center for c, _ in xs))


if __name__ == "__main__":
    unittest.main()
