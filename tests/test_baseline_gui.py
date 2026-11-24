"""
Baseline GUI Tests for YTDownloader Pro
Runs in offscreen mode to test UI creation, widgets, and token styling.
"""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from theme import Tokens
from main_window import MainWindow
from settings_dialog import SettingsDialog

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestGUIBaseline(unittest.TestCase):
    def setUp(self):
        self.main_window = MainWindow()
        self.settings_dialog = SettingsDialog()

    def tearDown(self):
        self.main_window.close()
        self.settings_dialog.close()
        self.main_window.deleteLater()
        self.settings_dialog.deleteLater()
        app.processEvents()

    def test_main_window_components(self):
        """Verify MainWindow title, layout, and key input controls."""
        self.assertEqual(self.main_window.windowTitle(), "YTDownloader Pro")
        self.assertIsNotNone(self.main_window.txt_url)
        self.assertIsNotNone(self.main_window.btn_analyze)
        self.assertIsNotNone(self.main_window.btn_download)
        self.assertIsNotNone(self.main_window.btn_cancel)
        self.assertIsNotNone(self.main_window.progress_bar)

    def test_settings_dialog_tabs(self):
        """Verify SettingsDialog tabs exist and are populated."""
        self.assertIn("Settings", self.settings_dialog.windowTitle())
        self.assertIsNotNone(self.settings_dialog.cmb_lang)
        self.assertIsNotNone(self.settings_dialog.chk_proxy)
        self.assertEqual(self.settings_dialog.tabs.count(), 5)

    def test_tokens_palette(self):
        """Verify color tokens match design specs."""
        self.assertEqual(Tokens.BG_MAIN, "#11151B")
        self.assertEqual(Tokens.BG_SECONDARY, "#171D25")
        self.assertEqual(Tokens.SURFACE_ELEVATED, "#1D2530")
        self.assertEqual(Tokens.ACCENT, "#718CF5")
        self.assertEqual(Tokens.SUCCESS, "#55AE89")
        self.assertEqual(Tokens.ERROR, "#D76F75")


if __name__ == "__main__":
    unittest.main()
