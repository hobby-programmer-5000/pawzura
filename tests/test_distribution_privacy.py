from pathlib import Path
import tempfile
import unittest
import zipfile
from scripts.check_distribution import check_distribution


class DistributionPrivacyTests(unittest.TestCase):
    def test_release_rejects_personal_artwork_runtime_and_weights(self):
        for relative in ("artwork/private.png", "art-runtime/DEPENDENCIES.json", "models/model.safetensors", "weights.gguf", "cutout.onnx",
                         "motion/private.zip", "motion-jobs/rig.npz", "motion-source/provenance.json", "weights.ckpt"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic")
                with self.assertRaises(ValueError):
                    check_distribution(root)

    def test_release_rejects_renamed_personal_motion_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(root / "renamed.zip", "w") as archive:
                archive.writestr("manifest.json", '{"source_art_id":"synthetic","clips":{}}')
            with self.assertRaises(ValueError):
                check_distribution(root)

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

    def test_build_script_copies_all_art_runtime_modules_and_manifests(self):
        build_text = Path(__file__).resolve().parents[1].joinpath("scripts", "build.py").read_text(encoding="utf-8")
        runtime_dir = Path(__file__).resolve().parents[1] / "art_runtime"
        expected = {
            path.name
            for path in runtime_dir.iterdir()
            if path.is_file() and path.name != "__init__.py" and path.suffix.lower() in (".py", ".json", ".txt", ".ps1")
        }
        missing = sorted(name for name in expected if f'"{name}"' not in build_text)
        self.assertEqual(missing, [])
