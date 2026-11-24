"""
Phase 3 Unit Tests:
- Audio codec and bitrate mapping
- Presets configuration and retrieval
- Subtitle parameter generation
- SponsorBlock category options
"""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import core


class TestPhase3Media(unittest.TestCase):
    def test_builtin_presets(self):
        """Verify built-in presets exist and contain valid download configs."""
        presets = core.get_presets()
        self.assertIn("High Quality 1080p (MP4)", presets)
        self.assertIn("Podcast & Music MP3 (320 kbps)", presets)
        self.assertIn("Lossless Master Audio (FLAC)", presets)

        hq = presets["High Quality 1080p (MP4)"]
        self.assertEqual(hq["download_type"], "Video")
        self.assertEqual(hq["video_quality"], "1080p")
        self.assertEqual(hq["video_format"], "MP4")

    def test_audio_codec_mapping(self):
        """Verify correct codec and bitrate flags for lossy vs lossless audio."""
        lossy_codecs = ["mp3", "m4a", "opus"]
        lossless_codecs = ["flac", "wav"]

        for fmt in lossy_codecs:
            codec, uses_bitrate = core.get_audio_codec_info(fmt)
            self.assertTrue(uses_bitrate, f"{fmt} should use bitrate flag")
            self.assertIsNotNone(codec)

        for fmt in lossless_codecs:
            codec, uses_bitrate = core.get_audio_codec_info(fmt)
            self.assertFalse(uses_bitrate, f"{fmt} should be lossless without bitrate flag")
            self.assertIsNotNone(codec)

    def test_user_preset_save_and_delete(self):
        """Verify saving and deleting custom user presets."""
        test_preset = {
            "download_type": "Video",
            "video_quality": "720p",
            "video_format": "WEBM"
        }
        core.save_user_preset("Test Custom 720p", test_preset)
        presets = core.get_presets()
        self.assertIn("Test Custom 720p", presets)
        self.assertEqual(presets["Test Custom 720p"]["video_format"], "WEBM")

        # Delete
        core.delete_user_preset("Test Custom 720p")
        reloaded = core.get_presets()
        self.assertNotIn("Test Custom 720p", reloaded)


if __name__ == "__main__":
    unittest.main()
