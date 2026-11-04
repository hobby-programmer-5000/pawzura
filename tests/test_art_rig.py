import copy
import base64
import hashlib
import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QEvent, QPointF, QRect, Qt, QElapsedTimer
from PySide6.QtGui import QImage, QPainter, QColor, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from pawzura import art_rig, artwork, art_client
from pawzura.config import Settings, default_character, safe_character
from pawzura.pet import draw_character, Pet
from pawzura.motion_ui import MotionDialog
from pawzura.ui import SettingsDialog
from pawzura.characters import GenerationError


def fixture():
    image = QImage(288, 288, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.fillRect(80, 15, 128, 110, QColor("#0000ff"))
    painter.fillRect(100, 110, 88, 130, QColor("#0000ff"))
    pieces = {"left_hand": (60, 145, 44, 58, "#ff0000", 100),
              "right_hand": (184, 145, 44, 58, "#00ff00", 188),
              "left_foot": (103, 240, 36, 34, "#ffff00", 121),
              "right_foot": (151, 240, 36, 34, "#ff00ff", 169)}
    parts = {}
    for name, (x, y, w, h, color, pivot_x) in pieces.items():
        painter.fillRect(x, y, w, h, QColor(color))
        parts[name] = {"polygon": [[x / 288, y / 288], [(x + w) / 288, y / 288],
                                   [(x + w) / 288, (y + h) / 288], [x / 288, (y + h) / 288]],
                       "pivot": [pivot_x / 288, (y + 2) / 288]}
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data), {"version": 1, "parts": parts}


class RigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.asset_patch = patch("pawzura.artwork.asset_root", return_value=self.root / "artwork")
        self.asset_patch.start()
        artwork._IMAGES.clear()
        art_rig._LAYERS.clear()
        self.png, self.rig = fixture()
        self.spec = {"kind": "artwork", "source": "artwork", "art_id": artwork.store_artwork(self.png),
                     "art_model": "sdxl", "seed": 1, "mouth_x": .5, "mouth_y": .3, "rig": self.rig}
        self.pets, self.dialogs = [], []

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.preview.timer.stop()
            dialog.deleteLater()
        for pet in self.pets:
            pet.dispose()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.asset_patch.stop()
        artwork._IMAGES.clear()
        art_rig._LAYERS.clear()
        self.temp.cleanup()

    def pet(self):
        pet = Pet(self.spec)
        pet.timer.stop()
        self.pets.append(pet)
        return pet

    def test_geometry_rejects_nonfinite_huge_degenerate_or_duplicate_parts(self):
        self.assertIsNotNone(art_rig.safe_rig(self.rig))
        for changed in ({"pivot": [float("nan"), .5]}, {"pivot": [20, 20]},
                        {"polygon": [[0, 0], [0, 0], [0, 0]]},
                        {"polygon": [[0, 0]] * 33}):
            rig = copy.deepcopy(self.rig)
            rig["parts"]["left_hand"].update(changed)
            self.assertIsNone(art_rig.safe_rig(rig))
        duplicate = copy.deepcopy(self.rig)
        duplicate["parts"]["right_hand"] = duplicate["parts"]["left_hand"]
        self.assertIsNone(art_rig.safe_rig(duplicate))
        self.assertIsNone(art_rig.safe_rig({**self.rig, "version": True}))
        self.assertNotIn("rig", safe_character({**self.spec, "rig": duplicate}))
        self.assertEqual(safe_character({**self.spec, "rig": duplicate})["art_id"], self.spec["art_id"])

    def test_limbs_move_independently_while_head_pixels_and_source_are_unchanged(self):
        def render(phase, pose="walk"):
            image = QImage(144, 144, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            draw_character(painter, safe_character(self.spec), phase, pose=pose)
            painter.end()
            return image
        first, second = render(1.5), render(4.6)
        self.assertEqual(first.copy(45, 12, 50, 35), second.copy(45, 12, 50, 35))
        def center(image, color):
            points = [(x, y) for x in range(144) for y in range(144) if image.pixelColor(x, y).name() == color and image.pixelColor(x, y).alpha() > 200]
            self.assertGreater(len(points), 10)
            return tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))
        for color in ("#ff0000", "#00ff00", "#ffff00", "#ff00ff"):
            self.assertNotEqual(center(first, color), center(second, color))
        self.assertNotEqual(render(1, "wave"), render(1, "walk"))
        path = self.root / "artwork" / (self.spec["art_id"] + ".png")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.spec["art_id"])

    def test_rig_history_roundtrip_strips_unknown_data_and_preserves_guard_defaults(self):
        self.spec["rig"]["prompt"] = "synthetic private field"
        self.spec["rig"]["parts"]["left_hand"]["path"] = "untrusted.png"
        settings = Settings(self.root / "settings.json")
        settings.save({"character": self.spec, "character_history": [self.spec]})
        self.assertNotIn("synthetic private field", settings.path.read_text())
        self.assertNotIn("untrusted.png", settings.path.read_text())
        loaded = Settings(settings.path).snapshot()
        self.assertEqual(set(loaded["character"]["rig"]["parts"]), set(art_rig.PARTS))
        self.assertFalse(loaded["guard_enabled"])
        self.assertTrue(loaded["preview_only"])
        self.assertFalse(loaded["browser_control_enabled"])

    def test_motion_editor_uses_bounded_geometry_and_accepts_without_modifying_png(self):
        dialog = MotionDialog(self.spec)
        self.dialogs.append(dialog)
        dialog.canvas.resize(400, 400)
        start = dialog.canvas.to_local([.10, .52])
        end = dialog.canvas.to_local([.25, .72])
        press = QMouseEvent(QEvent.Type.MouseButtonPress, start, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        move = QMouseEvent(QEvent.Type.MouseMove, end, end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        dialog.canvas.mousePressEvent(press)
        dialog.canvas.mouseMoveEvent(move)
        dialog.canvas.mouseReleaseEvent(move)
        self.assertIsNotNone(art_rig.safe_rig(dialog.canvas.rig))
        self.assertNotEqual(dialog.preview.spec["rig"], self.spec["rig"])
        chosen = []
        dialog.chosen.connect(chosen.append)
        dialog.choose()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(chosen[0]["art_id"], self.spec["art_id"])
        self.assertNotEqual(chosen[0]["rig"], self.spec["rig"])

    def test_failed_helper_keeps_manual_regions_and_releases_quit_guard(self):
        settings = Settings(self.root / "settings.json")
        parent = SettingsDialog(settings)
        dialog = MotionDialog(self.spec, parent=parent)
        self.dialogs.append(dialog)
        previous = copy.deepcopy(dialog.canvas.rig)
        with patch("pawzura.motion_ui.detect_motion", side_effect=GenerationError("art_pose_unavailable")):
            dialog.start(False)
            self.assertIs(parent.worker, dialog.worker)
            clock = QElapsedTimer()
            clock.start()
            while dialog.worker is not None and clock.elapsed() < 5000:
                QTest.qWait(10)
            self.assertIsNone(dialog.worker)
        self.assertIsNone(parent.worker)
        self.assertEqual(dialog.canvas.rig, previous)
        self.assertTrue(dialog.use.isEnabled())
        self.assertEqual(settings.snapshot()["character"], default_character())
        parent.character_preview.timer.stop()
        parent.connection_timer.stop()
        parent.deleteLater()

    def test_detection_sends_only_approved_pixels_and_validates_returned_rig(self):
        with patch.object(art_client, "worker", return_value={"rig": self.rig}) as worker:
            self.assertEqual(art_client.detect_motion(self.spec), self.rig)
            self.assertEqual(worker.call_args.args[0], "rig")
            self.assertEqual(set(worker.call_args.args[2]), {"png"})
        with patch.object(art_client, "worker", return_value={"rig": {"bad": "geometry"}}):
            with self.assertRaisesRegex(GenerationError, "art_pose_unavailable"):
                art_client.detect_motion(self.spec)

    def test_generation_attaches_only_valid_motion_after_image_review(self):
        for rig in (self.rig, {"version": 1, "parts": {}}, None):
            result = {"png": base64.b64encode(self.png).decode(), "model": "sdxl", "seed": 41, "rig": rig}
            with patch.object(art_client, "review_art_prompt", return_value="An original synthetic character"), \
                 patch.object(art_client, "worker", return_value=result), \
                 patch.object(art_client, "review_art_image", return_value=(.5, .3)), \
                 patch.object(art_client.secrets, "randbelow", return_value=41):
                spec = art_client.generate_artwork("An original synthetic character", 8)
            self.assertEqual(spec["art_id"], self.spec["art_id"])
            self.assertEqual("rig" in spec, rig is self.rig)
        with patch.object(art_client, "review_art_prompt", return_value="An original synthetic character"), \
             patch.object(art_client, "worker", return_value=result), \
             patch.object(art_client, "review_art_image", side_effect=GenerationError("art_output_blocked")), \
             patch.object(art_client, "store_artwork") as store, \
             patch.object(art_client.secrets, "randbelow", return_value=41):
            with self.assertRaises(GenerationError):
                art_client.generate_artwork("An original synthetic character", 8)
            store.assert_not_called()

    def test_disabling_motion_preserves_original_and_history_can_restore_it(self):
        dialog = MotionDialog(self.spec)
        self.dialogs.append(dialog)
        dialog.enabled.setChecked(False)
        chosen = []
        dialog.chosen.connect(chosen.append)
        dialog.choose()
        self.assertNotIn("rig", chosen[0])
        self.assertEqual(chosen[0]["art_id"], self.spec["art_id"])
        settings = Settings(self.root / "settings.json")
        settings.save({"character": chosen[0], "character_history": [self.spec, chosen[0]]})
        loaded = Settings(settings.path).snapshot()
        self.assertNotIn("rig", loaded["character"])
        self.assertEqual(loaded["character_history"][0]["rig"], self.rig)

    def test_pointer_reactions_never_complete_or_replace_a_guardian_bite(self):
        pet = self.pet()
        called = []
        self.assertTrue(pet.react("hop"))
        pet.bite(QPointF(300, 200), lambda: called.append(True))
        action = pet.action
        self.assertIsNone(pet.reaction)
        self.assertFalse(pet.react("cheer"))
        press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(72, 72), QPointF(72, 72), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        pet.mousePressEvent(press)
        self.assertIs(pet.action, action)
        self.assertEqual(called, [])
        pet.cancel_bite()
        self.assertIsNone(pet.action)
        self.assertIsNone(pet.reaction)
        self.assertEqual(called, [])

    def test_left_click_cycles_reactions_and_double_click_opens_settings(self):
        pet = self.pet()
        for expected in ("wave", "hop", "cheer"):
            press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(72, 72), QPointF(72, 72), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            pet.mousePressEvent(press)
            release = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(72, 72), QPointF(72, 72), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            pet.mouseReleaseEvent(release)
            self.assertEqual(pet.reaction["kind"], expected)
            self.assertIsNone(pet.action)
        signals = []
        pet.settings_requested.connect(lambda: signals.append(True))
        pet.mouseDoubleClickEvent(None)
        self.assertEqual(signals, [True])
        self.assertIsNone(pet.reaction)

    def test_hop_stays_in_negative_origin_work_area_and_recovers(self):
        pet = self.pet()
        pet.px, pet.py = -800, 254
        screen = Mock()
        screen.availableGeometry.return_value = QRect(-1200, -400, 1200, 800)
        pet.next_idle = 1000
        pet.last_tick = 100
        with patch("pawzura.pet.time.monotonic", return_value=100):
            pet.react("hop")
        with patch.object(pet, "isVisible", return_value=True), patch.object(pet, "screens", return_value=[screen]), \
             patch("pawzura.pet.QApplication.screenAt", return_value=screen), patch("pawzura.pet.time.monotonic", return_value=100.45):
            pet.tick()
        self.assertEqual(pet.py, 254)
        self.assertLess(pet.y(), pet.py)
        self.assertGreaterEqual(pet.y(), -400)
        pet.cancel_bite()
        self.assertIsNone(pet.reaction)


if __name__ == "__main__":
    unittest.main()
