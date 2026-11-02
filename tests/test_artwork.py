import base64
import io
import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from types import SimpleNamespace
import sys
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPointF, Qt
from PySide6.QtGui import QImage, QPainter, QMouseEvent
from PySide6.QtCore import QEvent, QElapsedTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pawzura import art_client, art_policy, artwork
from pawzura.art_ui import ArtworkDialog
from pawzura.characters import GenerationError
from pawzura.config import Settings, default_character, safe_character
from pawzura.pet import Pet, draw_character
from art_runtime import runner
from pawzura.ui import SettingsDialog


def png():
    image = QImage(64, 64, QImage.Format.Format_ARGB32)
    image.fill(0)
    for x in range(16, 48):
        for y in range(8, 60):
            image.setPixelColor(x, y, "#91d9c7")
    image.setText("description", "synthetic metadata")
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


class ArtworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.asset_patch = patch("pawzura.artwork.asset_root", return_value=self.root / "artwork")
        self.asset_patch.start()
        artwork._IMAGES.clear()

    def tearDown(self):
        self.asset_patch.stop()
        artwork._IMAGES.clear()
        self.temp.cleanup()

    def spec(self):
        return {"kind": "artwork", "source": "artwork", "art_id": artwork.store_artwork(png()),
                "art_model": "sdxl", "seed": 42, "mouth_x": .4, "mouth_y": .3}

    def test_png_persistence_strips_metadata_and_rejects_tampering_and_paths(self):
        digest = artwork.store_artwork(png())
        loaded = artwork.load_artwork(digest)
        self.assertEqual(loaded.size().width(), 64)
        self.assertEqual(loaded.text("description"), "")
        self.assertTrue(artwork.load_artwork("../../private").isNull())
        (self.root / "artwork" / (digest + ".png")).write_bytes(png())
        artwork._IMAGES.clear()
        self.assertTrue(artwork.load_artwork(digest).isNull())
        bad = bytearray(png())
        bad[16:20] = (20000).to_bytes(4, "big")
        with self.assertRaises(ValueError):
            artwork.validate_png(bytes(bad))
        with self.assertRaises(ValueError):
            artwork.validate_png(b"<svg onload='bad'>")

    def test_settings_roundtrip_history_and_no_prompt_or_arbitrary_path(self):
        spec = self.spec()
        spec.update(prompt="session only", path="untrusted.png", model="unknown")
        settings = Settings(self.root / "settings.json")
        settings.save({"character": spec, "character_history": [default_character(), spec]})
        self.assertNotIn("session only", settings.path.read_text(encoding="utf-8"))
        self.assertNotIn("untrusted.png", settings.path.read_text(encoding="utf-8"))
        loaded = Settings(settings.path).snapshot()
        self.assertEqual(loaded["character"]["art_id"], spec["art_id"])
        self.assertNotIn("prompt", loaded["character"])
        self.assertNotIn("path", loaded["character"])
        self.assertNotIn("model", loaded["character"])
        self.assertEqual(loaded["character_history"][-1]["kind"], "artwork")
        self.assertFalse(loaded["guard_enabled"])
        for extra in ({"mouth_x": float("nan")}, {"art_id": "../x"}, {"art_model": "arbitrary"}):
            self.assertEqual(safe_character({**spec, **extra}), default_character())

    def test_art_pixels_animate_and_missing_asset_falls_back(self):
        spec = safe_character(self.spec())
        def render(phase):
            image = QImage(144, 146, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            draw_character(painter, spec, phase)
            painter.end()
            return image
        first = render(0)
        self.assertNotEqual(first, render(1.2))
        (self.root / "artwork" / (spec["art_id"] + ".png")).unlink()
        artwork._IMAGES.clear()
        self.assertNotEqual(first, render(0))

    def test_bite_uses_bounded_art_landmark_and_still_cancels(self):
        pet = Pet(self.spec())
        pet.timer.stop()
        pet.direction = -1
        target = QPointF(500, 300)
        called = []
        self.assertTrue(pet.bite(target, lambda: called.append(True)))
        self.assertAlmostEqual(pet.action["to"].x(), 500 - (144 - 144 * .4))
        self.assertAlmostEqual(pet.action["to"].y(), 300 - 144 * .3)
        pet.cancel_bite()
        self.assertIsNone(pet.action)
        self.assertEqual(called, [])
        pet.dispose()

    def test_prompt_restrictions_and_review_fail_closed(self):
        for text in ("Draw Pikachu", "ＮＳＦＷ character", "헬로키티를 그려줘"):
            with self.assertRaisesRegex(GenerationError, "art_prompt_blocked"):
                art_policy.validate_art_prompt(text)
        self.assertIn("astronomer", art_policy.validate_art_prompt("An original brass astronomer"))
        with patch("pawzura.art_policy.build_opener", side_effect=OSError()):
            with self.assertRaisesRegex(GenerationError, "art_policy_unavailable"):
                art_policy.review_art_prompt("An original brass astronomer")

    def test_prompt_review_uses_one_verdict_and_keeps_creative_details(self):
        decision = {"verdict": "allow", "prompt": "Original brass astronomer with turquoise hair and copper boots"}
        response = io.BytesIO(json.dumps({"response": json.dumps(decision)}).encode())
        with patch("pawzura.art_policy.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(art_policy.review_art_prompt("Original brass astronomer"), decision["prompt"])
            payload = json.loads(opener.return_value.open.call_args.args[0].data)
            self.assertEqual(set(payload["format"]["properties"]), {"verdict", "prompt"})

    def test_image_review_checks_flags_coordinates_and_local_endpoint(self):
        for decision in ({"verdict": "unsafe", "identity": "none"},
                         {"verdict": "replica", "identity": "known character"},
                         {"verdict": "uncertain", "identity": "none"},
                         {"verdict": "allow", "identity": "known character"}):
            response = io.BytesIO(json.dumps({"message": {"content": json.dumps(decision)}}).encode())
            with patch("pawzura.art_policy.build_opener") as opener:
                opener.return_value.open.return_value = response
                with self.assertRaisesRegex(GenerationError, "art_output_blocked"):
                    art_policy.review_art_image(png())
        good = {"verdict": "allow", "identity": "none", "mouth_x": .4, "mouth_y": .3}
        response = io.BytesIO(json.dumps({"message": {"content": json.dumps(good)}}).encode())
        with patch("pawzura.art_policy.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(art_policy.review_art_image(png()), (.4, .3))
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertEqual(json.loads(request.data)["keep_alive"], 0)
        response = io.BytesIO(json.dumps({"message": {"content": "", "thinking": json.dumps(good)}}).encode())
        with patch("pawzura.art_policy.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(art_policy.review_art_image(png()), (.4, .3))
        response = io.BytesIO(json.dumps({"message": {"content": "", "thinking": "Unfinished review"}}).encode())
        with patch("pawzura.art_policy.build_opener") as opener:
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(GenerationError, "art_policy_unavailable"):
                art_policy.review_art_image(png())

    def test_no_asset_saved_if_review_fails(self):
        result = {"png": base64.b64encode(png()).decode(), "model": "sdxl", "seed": 42}
        with patch.object(art_client, "review_art_prompt", return_value="An original brass astronomer"), \
             patch.object(art_client.secrets, "randbelow", return_value=42), \
             patch.object(art_client, "worker", return_value=result), \
             patch.object(art_client, "review_art_image", side_effect=GenerationError("art_output_blocked")), \
             patch.object(art_client, "store_artwork") as store:
            with self.assertRaisesRegex(GenerationError, "art_output_blocked"):
                art_client.generate_artwork("original", 8)
            store.assert_not_called()

    def test_art_dialog_requires_fresh_license_acknowledgement_per_model(self):
        for language in ("en", "ko"):
            dialog = ArtworkDialog(language)
            self.assertFalse(dialog.prepare.isEnabled())
            self.assertFalse(dialog.generate.isEnabled())
            dialog.agree.setChecked(True)
            self.assertTrue(dialog.prepare.isEnabled())
            dialog.tier.setCurrentIndex(0)
            self.assertFalse(dialog.agree.isChecked())
            self.assertFalse(dialog.generate.isEnabled())
            self.assertIn("OpenRAIL", dialog.model_info.text())
            dialog.preview.timer.stop()
            dialog.deleteLater()

    def test_manual_bite_point_edits_only_bounded_approved_result(self):
        dialog = ArtworkDialog()
        spec = self.spec()
        dialog.succeeded(spec)
        preview = dialog.preview
        preview.resize(200, 220)
        scale = min(preview.width() / 180, preview.height() / 180)
        position = QPointF((preview.width() - 144 * scale) / 2 + .55 * 144 * scale,
                           (preview.height() - 144 * scale) / 2 + .35 * 144 * scale)
        event = QMouseEvent(QEvent.Type.MouseButtonPress, position, position,
                            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        preview.mousePressEvent(event)
        self.assertAlmostEqual(dialog.result_spec["mouth_x"], .55)
        self.assertAlmostEqual(dialog.result_spec["mouth_y"], .35)
        self.assertEqual(dialog.result_spec["art_id"], spec["art_id"])
        preview.timer.stop()
        dialog.deleteLater()

    def test_model_download_resumes_once_and_never_fetches_pickle_weights(self):
        download = Mock(side_effect=[OSError("temporary transfer failure"), "safe-snapshot"])
        module = SimpleNamespace(snapshot_download=download)
        with patch.dict(sys.modules, {"huggingface_hub": module}), patch.object(runner.time, "sleep"):
            self.assertEqual(runner.snapshot("sdxl", self.root, True), "safe-snapshot")
        self.assertEqual(download.call_count, 2)
        arguments = download.call_args.kwargs
        self.assertFalse(arguments["token"])
        self.assertEqual(arguments["revision"], runner.CATALOG["sdxl"]["revision"])
        self.assertEqual(arguments["allow_patterns"], ["*.json", "*.txt", "*.fp16.safetensors"])
        download = Mock(side_effect=OSError("temporary transfer failure"))
        with patch.dict(sys.modules, {"huggingface_hub": SimpleNamespace(snapshot_download=download)}), patch.object(runner.time, "sleep"):
            with self.assertRaisesRegex(runner.WorkerError, "art_download_failed"):
                runner.snapshot("sdxl", self.root, True)
        self.assertEqual(download.call_count, 2)

    def test_async_art_failure_keeps_previous_result_and_releases_app_quit_guard(self):
        settings = Settings(self.root / "settings.json")
        parent = SettingsDialog(settings)
        dialog = ArtworkDialog(parent=parent)
        previous = self.spec()
        dialog.succeeded(previous)
        dialog.agree.setChecked(True)
        dialog.description.setPlainText("An original brass astronomer")
        chosen = []
        dialog.chosen.connect(chosen.append)
        with patch("pawzura.art_ui.generate_artwork", side_effect=GenerationError("art_output_blocked")):
            dialog.start(True)
            self.assertIs(parent.worker, dialog.worker)
            elapsed = QElapsedTimer()
            elapsed.start()
            while dialog.worker is not None and elapsed.elapsed() < 5000:
                QTest.qWait(10)
            self.assertIsNone(dialog.worker)
        self.assertIsNone(parent.worker)
        self.assertEqual(dialog.result_spec, previous)
        self.assertEqual(chosen, [])
        self.assertTrue(dialog.generate.isEnabled())
        self.assertTrue(dialog.use.isEnabled())
        self.assertEqual(settings.snapshot()["character"], default_character())
        dialog.preview.timer.stop()
        parent.character_preview.timer.stop()
        parent.connection_timer.stop()
        dialog.deleteLater()
        parent.deleteLater()



if __name__ == "__main__":
    unittest.main()
