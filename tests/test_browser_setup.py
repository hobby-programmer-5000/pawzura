import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pawzura.browser_setup import BrowserSetupDialog, FILES, WORDS, connection_url, extension_source, prepare_extension


class BrowserSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_staging_copies_only_public_files_to_a_stable_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            for name in FILES:
                (source / name).write_bytes((extension_source("chrome") / name).read_bytes())
            (source / "settings.json").write_text('{"private":"test-only"}', encoding="utf-8")
            first = prepare_extension("chrome", root / "installed", source)
            self.assertEqual({path.name for path in first.iterdir()}, set(FILES))
            (source / "options.css").write_text("/* updated */", encoding="utf-8")
            second = prepare_extension("chrome", root / "installed", source)
            self.assertEqual(first, second)
            self.assertEqual((second / "options.css").read_text(encoding="utf-8"), "/* updated */")

    def test_connection_link_contains_only_browser_port_language_and_request_flag(self):
        url = urlsplit(connection_url("edge", extension_source("edge"), 47831, "ko"))
        self.assertEqual(url.scheme, "chrome-extension")
        self.assertEqual(len(url.hostname), 32)
        self.assertTrue(set(url.hostname) <= set("abcdefghijklmnop"))
        self.assertEqual(parse_qs(url.query), {"browser":["edge"],"port":["47831"],"lang":["ko"],"setup":["1"]})
        self.assertEqual(connection_url("firefox", extension_source("firefox"),47831,"en"), "about:addons")

    def test_helper_launches_install_page_then_connection_with_no_code_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            staged = prepare_extension("chrome", Path(directory))
            with patch("pawzura.browser_setup.find_browser", return_value=Path("chrome.exe")), \
                 patch("pawzura.browser_setup.prepare_extension", return_value=staged), \
                 patch("pawzura.browser_setup.launch_browser") as launch:
                dialog = BrowserSetupDialog("chrome",47831,"en")
                try:
                    dialog.open_install()
                    self.assertEqual(self.app.clipboard().text(),str(staged))
                    launch.assert_called_with("chrome",Path("chrome.exe"),"chrome://extensions")
                    dialog.open_connection()
                    self.assertIn("setup=1",launch.call_args.args[2])
                    self.assertNotIn("token",launch.call_args.args[2])
                    self.assertEqual(set(WORDS["en"]),set(WORDS["ko"]))
                finally:
                    dialog.timer.stop()
                    dialog.deleteLater()
                    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def test_missing_browser_reports_failure_instead_of_claiming_installation(self):
        with patch("pawzura.browser_setup.find_browser",return_value=None), patch("pawzura.browser_setup.launch_browser") as launch:
            dialog = BrowserSetupDialog("chrome",47831,"ko")
            try:
                dialog.launch("chrome://extensions")
                self.assertEqual(dialog.status.text(),WORDS["ko"]["missing"])
                launch.assert_not_called()
                self.assertEqual(dialog.pages.currentIndex(),0)
            finally:
                dialog.timer.stop()
                dialog.deleteLater()
                QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
