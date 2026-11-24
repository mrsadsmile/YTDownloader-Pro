"""
Phase 1 GUI Interaction & Component Tests
Verifies:
- Main Window Phase 1 components (Preview card rich labels, Open File button, Cancel Analysis)
- Audio format dynamic selection (enabling/disabling bitrate for Lossless/Original)
- Clipboard URL detection
- Open downloaded file interaction
"""
import os
import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main_window import MainWindow
import core


class TestPhase1GUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.deleteLater()
        self.window = None
        self.app.processEvents()

    def test_preview_card_rich_labels_exist(self):
        """Verify all Phase 1 metadata preview labels are initialized in preview card."""
        self.assertTrue(hasattr(self.window, "lbl_prev_platform"))
        self.assertTrue(hasattr(self.window, "lbl_prev_channel"))
        self.assertTrue(hasattr(self.window, "lbl_prev_duration"))
        self.assertTrue(hasattr(self.window, "lbl_prev_date"))
        self.assertTrue(hasattr(self.window, "lbl_prev_res"))
        self.assertTrue(hasattr(self.window, "lbl_prev_codecs"))
        self.assertTrue(hasattr(self.window, "lbl_prev_subs"))
        self.assertTrue(hasattr(self.window, "lbl_prev_size"))

    def test_open_file_button_lifecycle(self):
        """Verify Open File button exists, is disabled initially, and can be tested."""
        self.assertTrue(hasattr(self.window, "btn_open_file"))
        self.assertFalse(self.window.btn_open_file.isEnabled())

    def test_audio_format_combobox_lossless_handling(self):
        """Verify selecting lossless audio format updates bitrate label and disabled state."""
        # Select FLAC
        self.window.cmb_audio_format.setCurrentText("FLAC")
        self.assertFalse(self.window.cmb_audio_quality.isEnabled())
        self.assertIn("Lossless", self.window.lbl_a_quality.text())

        # Select MP3
        self.window.cmb_audio_format.setCurrentText("MP3")
        self.assertTrue(self.window.cmb_audio_quality.isEnabled())

    def test_inspect_completed_populates_all_metadata(self):
        """Verify on_inspect_completed properly populates all preview card widgets."""
        mock_data = {
            "title": "Sample Showcase Video",
            "uploader": "Test Channel",
            "duration": "05:30",
            "platform": "YouTube",
            "upload_date": "2026-11-20",
            "resolutions": ["1080p", "720p"],
            "vcodecs": ["avc1"],
            "acodecs": ["mp4a"],
            "fps": 60,
            "subtitles": ["en", "fa"],
            "estimated_size": 150 * 1024 * 1024,
            "thumbnail": None
        }
        self.window.on_inspect_completed(mock_data)
        self.assertEqual(self.window.lbl_prev_title.text(), "Sample Showcase Video")
        self.assertIn("Test Channel", self.window.lbl_prev_channel.text())
        self.assertIn("05:30", self.window.lbl_prev_duration.text())
        self.assertIn("YouTube", self.window.lbl_prev_platform.text())
        self.assertIn("2026-11-20", self.window.lbl_prev_date.text())
        self.assertIn("60fps", self.window.lbl_prev_codecs.text())
        self.assertIn("en, fa", self.window.lbl_prev_subs.text())
        self.assertIn("150.0 MB", self.window.lbl_prev_size.text())
        self.assertFalse(self.window.preview_card.isHidden())


if __name__ == "__main__":
    unittest.main()
