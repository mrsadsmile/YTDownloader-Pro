"""
Baseline Unit Tests for YTDownloader Pro Core Engine
"""
import os
import sys
import unittest
import tempfile
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import core


class TestCoreBaseline(unittest.TestCase):
    def test_sanitize_environment_path(self):
        """Verify that PATH sanitization removes non-existent/invalid directories without error."""
        original_path = os.environ.get("PATH", "")
        # Add a fake non-existent path
        os.environ["PATH"] = original_path + os.pathsep + r"C:\NonExistent_Junction_Folder_12345"
        core.sanitize_environment_path()
        sanitized = os.environ.get("PATH", "").split(os.pathsep)
        self.assertNotIn(r"C:\NonExistent_Junction_Folder_12345", sanitized)
        # Restore
        os.environ["PATH"] = original_path

    def test_ffmpeg_detection(self):
        """Verify ffmpeg is detected on system or in project path."""
        path = core.get_ffmpeg_path()
        self.assertIsNotNone(path, "FFmpeg should be detected on this system")
        self.assertTrue(os.path.exists(path), f"FFmpeg binary at {path} must exist")

    def test_config_load_and_save(self):
        """Verify loading and saving configuration with fallback values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cfg_file = Path(tmpdir) / "config.json"
            original_cfg_file = core.CONFIG_FILE
            try:
                core.CONFIG_FILE = test_cfg_file
                # Load default
                cfg = core.load_config()
                self.assertEqual(cfg["download_type"], "Video")
                self.assertEqual(cfg["video_quality"], "Best Available")
                self.assertEqual(cfg["language"], "en")

                # Modify and save
                cfg["language"] = "fa"
                cfg["video_quality"] = "1080p"
                core.save_config(cfg)
                self.assertTrue(test_cfg_file.exists())

                # Reload
                reloaded = core.load_config()
                self.assertEqual(reloaded["language"], "fa")
                self.assertEqual(reloaded["video_quality"], "1080p")
            finally:
                core.CONFIG_FILE = original_cfg_file

    def test_download_canceled_exception(self):
        """Verify DownloadCanceled exception can be raised and caught cleanly."""
        with self.assertRaises(core.DownloadCanceled):
            raise core.DownloadCanceled("User cancelled")


if __name__ == "__main__":
    unittest.main()
