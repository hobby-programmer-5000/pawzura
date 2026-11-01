from pathlib import Path
import tempfile
import unittest
from scripts.check_distribution import check_distribution


class DistributionPrivacyTests(unittest.TestCase):
    def test_release_rejects_local_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "settings.json").write_text('{"browsers":{}}',encoding="utf-8")
            with self.assertRaises(ValueError):
                check_distribution(root)

    def test_release_rejects_renamed_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "export.json").write_text('{"browsers":{},"allowed_apps":[]}',encoding="utf-8")
            with self.assertRaises(ValueError):
                check_distribution(root)

    def test_example_data_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text('https://example.com',encoding="utf-8")
            self.assertTrue(check_distribution(root))

    def test_release_rejects_profile_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "export.json").write_text('{"profiles":{"Work":{}}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                check_distribution(root)
