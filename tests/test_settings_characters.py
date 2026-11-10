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
            self.assertEqual(data["language"], "en")
            self.assertTrue(data["preview_only"])
            self.assertFalse(data["browser_control_enabled"])
            self.assertTrue(all(not b["enabled"] and not b["allowed_sites"] for b in data["browsers"].values()))

    def test_legacy_settings_migrate_to_profile_without_losing_lists(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"version": 1, "allowed_apps": ["custom.exe"], "browsers": {"chrome": {"enabled": True, "allowed_sites": ["example.com/*"]}}}), encoding="utf-8")
            settings = Settings(path)
            self.assertEqual(settings.snapshot()["profiles"]["Default"]["allowed_apps"], ["custom.exe"])
            self.assertEqual(settings.snapshot()["browsers"]["chrome"]["allowed_sites"], ["example.com/*"])
            self.assertTrue(settings.snapshot()["browser_control_enabled"])
            self.assertTrue(settings.snapshot()["application_control_enabled"])
            self.assertNotIn("profiles", json.loads(path.read_text(encoding="utf-8")))
            settings.save()
            self.assertEqual(Settings(path).snapshot()["profiles"]["Default"]["browsers"]["chrome"]["allowed_sites"], ["example.com/*"])

    def test_generated_values_are_bounded(self):
        result = validate_character({"body": "exec('malware')", "accent": "#123456", "ears": "famous-character", "accessory": "star"}, 123)
        self.assertEqual(result["accent"], "#123456")
        self.assertRegex(result["body"], r"^#[0-9a-fA-F]{6}$")
        self.assertIn(result["ears"], ("rabbit", "cat", "bear"))
        self.assertEqual(random_character(123), random_character(123))

    def test_existing_codex_allowlist_gets_its_executable_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            import json
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"version":1,"allowed_apps":["codex.exe"]}),encoding="utf-8")
            settings = Settings(path)
            self.assertIn("chatgpt.exe", settings.snapshot()["allowed_apps"])
            settings.save({"allowed_apps":["codex.exe"]})
            self.assertIn("chatgpt.exe",Settings(path).snapshot()["allowed_apps"])


if __name__ == "__main__":
    unittest.main()
