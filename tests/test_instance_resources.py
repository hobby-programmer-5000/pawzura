import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication, QLockFile
from pawzura.app import main
from pawzura.config import Settings
from pawzura.instance import AlreadyRunningError, acquire_instance_lock
from pawzura.resources import resource_path


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "settings.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_same_directory_blocks_second_lock_and_releases(self):
        first = acquire_instance_lock(self.path)
        try:
            with self.assertRaises(AlreadyRunningError):
                acquire_instance_lock(self.path.parent / "." / self.path.name)
            self.assertEqual(first.staleLockTime(), 0)
        finally:
            first.unlock()
        second = acquire_instance_lock(self.path)
        second.unlock()

    def test_permission_failure_is_a_storage_error(self):
        fake = Mock()
        fake.tryLock.return_value = False
        fake.error.return_value = QLockFile.LockError.PermissionError
        with patch("pawzura.instance.QLockFile", return_value=fake):
            with self.assertRaisesRegex(OSError, "write access"):
                acquire_instance_lock(self.path)

    def test_duplicate_main_never_constructs_guardian_or_reads_settings(self):
        first = acquire_instance_lock(self.path)
        try:
            with patch("pawzura.app.QApplication"), patch("pawzura.app.ctypes.windll", create=True), \
                 patch("pawzura.app.windows.IS_WINDOWS", True), patch("pawzura.app.QMessageBox") as messages, \
                 patch("pawzura.app.Companion") as companion, patch("pawzura.app.Settings") as settings:
                self.assertEqual(main(["--settings-file", str(self.path)]), 0)
                messages.information.assert_called_once()
                messages.critical.assert_not_called()
                companion.assert_not_called()
                settings.assert_not_called()
        finally:
            first.unlock()

    def test_lock_is_held_for_event_loop_and_released_on_exception(self):
        settings = Settings(self.path)
        settings.save()
        def event_loop():
            with self.assertRaises(AlreadyRunningError):
                acquire_instance_lock(self.path)
            raise RuntimeError("synthetic event loop failure")
        app = Mock()
        app.exec.side_effect = event_loop
        with patch("pawzura.app.QApplication", return_value=app), patch("pawzura.app.ctypes.windll", create=True), \
             patch("pawzura.app.windows.IS_WINDOWS", True), patch("pawzura.app.QMessageBox") as messages, \
             patch("pawzura.app.Companion"):
            self.assertEqual(main(["--settings-file", str(self.path)]), 1)
            messages.critical.assert_called_once()
        lock = acquire_instance_lock(self.path)
        lock.unlock()

    def test_process_crash_recovery(self):
        script = (
            "import sys;from pathlib import Path;"
            "from PySide6.QtCore import QCoreApplication;"
            "from pawzura.instance import acquire_instance_lock;"
            "app=QCoreApplication([]);lock=acquire_instance_lock(Path(sys.argv[1]));"
            "print('LOCKED',flush=True);sys.stdin.read()"
        )
        first = subprocess.Popen([sys.executable, "-c", script, str(self.path)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True)
        try:
            self.assertEqual(first.stdout.readline().strip(), "LOCKED")
            with self.assertRaises(AlreadyRunningError):
                acquire_instance_lock(self.path)
        finally:
            first.terminate()
            first.communicate(timeout=10)
        lock = acquire_instance_lock(self.path)
        lock.unlock()


class ResourceTests(unittest.TestCase):
    def test_folder_and_onefile_resolve_runtime_and_extensions(self):
        from pawzura.art_client import source_dir
        from pawzura.browser_setup import extension_source, prepare_extension, FILES
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            unpacked = folder / "unpacked"
            (unpacked / "art_runtime").mkdir(parents=True)
            source = unpacked / "extensions/chromium"
            source.mkdir(parents=True)
            for name in FILES:
                (source / name).write_text("synthetic public resource")
            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(unpacked), create=True), \
                 patch.object(sys, "executable", str(folder / "standalone.exe")):
                self.assertEqual(source_dir(), unpacked / "art_runtime")
                self.assertEqual(extension_source("chrome"), source)
                staged = prepare_extension("chrome", folder / "stable")
                self.assertEqual({p.name for p in staged.iterdir()}, set(FILES))
            # Folder builds retain support files beside their executable.
            (folder / "art_runtime").mkdir()
            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(folder / "_internal"), create=True), \
                 patch.object(sys, "executable", str(folder / "Pawzura.exe")):
                self.assertEqual(source_dir(), folder / "art_runtime")

    def test_source_resource_path(self):
        with patch.object(sys, "frozen", False, create=True):
            self.assertTrue((resource_path("art_runtime") / "catalog.json").is_file())


if __name__ == "__main__":
    unittest.main()
