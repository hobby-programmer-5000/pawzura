from pathlib import Path
import tempfile
import unittest
from pawzura.config import Settings
from pawzura.characters import random_character, validate_character


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_snapshot_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            settings = Settings(path)
            settings.save({"allowed_apps": ["custom.exe"]})
            snapshot = settings.snapshot()
            snapshot["allowed_apps"].clear()
            self.assertEqual(Settings(path).snapshot()["allowed_apps"], ["custom.exe"])
            self.assertFalse(path.with_suffix(".tmp").exists())

    def test_corrupt_settings_do_not_reset_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                Settings(path)

    def test_safe_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Settings(Path(directory) / "settings.json").snapshot()
            self.assertFalse(data["guard_enabled"])
            self.assertTrue(data["preview_only"])
            self.assertTrue(all(not b["enabled"] and not b["allowed_sites"] for b in data["browsers"].values()))

    def test_generated_values_are_bounded(self):
        result = validate_character({"body": "exec('malware')", "accent": "#123456", "ears": "famous-character", "accessory": "star"}, 123)
        self.assertEqual(result["accent"], "#123456")
        self.assertRegex(result["body"], r"^#[0-9a-fA-F]{6}$")
        self.assertIn(result["ears"], ("rabbit", "cat", "bear"))
        self.assertEqual(random_character(123), random_character(123))


if __name__ == "__main__":
    unittest.main()
