"""
Phase 1 Unit and Integration Tests:
- URL validation and cleaning
- Filename sanitization and collision avoidance
- Output file verification
- Structured error classification
- InspectWorker & DownloadWorker behavior
"""
import os
import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import core


class TestPhase1Core(unittest.TestCase):
    def test_url_validation_and_cleaning(self):
        """Test URL validation and stripping of tracking query params."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abcdef12345",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://vimeo.com/12345678",
            "https://soundcloud.com/artist/track",
        ]
        for u in valid_urls:
            is_valid, _ = core.validate_url(u)
            self.assertTrue(is_valid, f"URL should be valid: {u}")

        invalid_urls = [
            "",
            "   ",
            "not a url",
            "ftp://invalid-scheme.com",
            "http://",
        ]
        for u in invalid_urls:
            is_valid, _ = core.validate_url(u)
            self.assertFalse(is_valid, f"URL should be invalid: {u}")

        # Tracking params stripping
        dirty = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&si=tracking123&feature=shared"
        cleaned = core.clean_url(dirty)
        self.assertNotIn("si=", cleaned)
        self.assertNotIn("feature=shared", cleaned)
        self.assertIn("v=dQw4w9WgXcQ", cleaned)

    def test_filename_sanitization(self):
        """Test removal of illegal filesystem characters."""
        dangerous_name = 'Video: "Cool" <Test> / Review | 2026? *Awesome*'
        sanitized = core.sanitize_filename(dangerous_name)
        for char in '<>:"/\\|?*':
            self.assertNotIn(char, sanitized)
        self.assertGreater(len(sanitized), 0)

    def test_get_unique_path(self):
        """Test unique path generation to prevent unintended overwrites."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            orig = p / "test_file.mp4"
            orig.touch()

            # First collision
            unique1 = core.get_unique_path(p, "test_file.mp4")
            self.assertEqual(unique1.name, "test_file (1).mp4")
            unique1.touch()

            # Second collision
            unique2 = core.get_unique_path(p, "test_file.mp4")
            self.assertEqual(unique2.name, "test_file (2).mp4")

    def test_verify_output_file(self):
        """Test non-zero file output verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            valid_file = p / "valid.mp4"
            valid_file.write_bytes(b"\x00" * 1024)
            self.assertTrue(core.verify_output_file(valid_file))

            empty_file = p / "empty.mp4"
            empty_file.touch()
            self.assertFalse(core.verify_output_file(empty_file))

            non_existent = p / "missing.mp4"
            self.assertFalse(core.verify_output_file(non_existent))

    def test_error_classification(self):
        """Test classifying raw error strings into structured AppError."""
        err_net = core.classify_error(Exception("Unable to download webpage: <urlopen error timed out>"))
        self.assertEqual(err_net.code, "ERR_NETWORK")
        self.assertTrue(err_net.retryable)

        err_priv = core.classify_error(Exception("Private video. Sign in if you've been granted access to this video"))
        self.assertEqual(err_priv.code, "ERR_RESTRICTED")
        self.assertFalse(err_priv.retryable)

        err_ff = core.classify_error(Exception("ffmpeg not found or failed to execute"))
        self.assertEqual(err_ff.code, "ERR_FFMPEG")

        err_drm = core.classify_error(Exception("This video contains DRM encrypted content"))
        self.assertEqual(err_drm.code, "ERR_DRM")
        self.assertFalse(err_drm.retryable)

        err_del = core.classify_error(Exception("Video unavailable: This video has been removed by user"))
        self.assertEqual(err_del.code, "ERR_DELETED")
        self.assertFalse(err_del.retryable)

        err_perm = core.classify_error(Exception("[WinError 5] Access is denied"))
        self.assertEqual(err_perm.code, "ERR_PERMISSION")

        err_unsupported = core.classify_error(Exception("Unsupported URL: no suitable extractor found"))
        self.assertEqual(err_unsupported.code, "ERR_UNSUPPORTED_URL")

    def test_destination_validation(self):
        """Test destination path existence, write permissions, and disk space checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Valid writable path
            valid, msg = core.validate_destination(tmpdir)
            self.assertTrue(valid, msg)

            # Subdirectory creation
            sub = os.path.join(tmpdir, "nested", "downloads")
            valid, msg = core.validate_destination(sub)
            self.assertTrue(valid, msg)
            self.assertTrue(os.path.isdir(sub))

            # Empty path
            valid, msg = core.validate_destination("")
            self.assertFalse(valid)

    def test_inspect_worker_cancellation(self):
        """Test cancellation state flag in InspectWorker."""
        worker = core.InspectWorker("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertFalse(worker.cancel_requested)
        worker.cancel()
        self.assertTrue(worker.cancel_requested)

    def test_audio_preservation_options(self):
        """Test audio codec detection and bitrate handling for lossless and compressed formats."""
        codec_mp3, uses_bitrate_mp3 = core.get_audio_codec_info("mp3")
        self.assertEqual(codec_mp3, "libmp3lame")
        self.assertTrue(uses_bitrate_mp3)

        codec_flac, uses_bitrate_flac = core.get_audio_codec_info("flac")
        self.assertEqual(codec_flac, "flac")
        self.assertFalse(uses_bitrate_flac)

        codec_wav, uses_bitrate_wav = core.get_audio_codec_info("wav")
        self.assertEqual(codec_wav, "pcm_s16le")
        self.assertFalse(uses_bitrate_wav)


if __name__ == "__main__":
    unittest.main()
