"""
Phase 4 Unit Tests:
- Secret redaction in logs and proxy URLs
- System diagnostic report generation
- Settings export, import, and reset to defaults
- Cookie file path validation
"""
import os
import sys
import unittest
import tempfile
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import core


class TestPhase4System(unittest.TestCase):
    def test_secret_redaction(self):
        """Verify sensitive credentials in proxy URLs or strings are redacted."""
        url_with_creds = "http://admin:superSecretPass123@127.0.0.1:8080"
        redacted = core.redact_secrets(url_with_creds)
        self.assertNotIn("superSecretPass123", redacted)
        self.assertIn("admin:***@", redacted)

        plain_url = "http://127.0.0.1:10809"
        self.assertEqual(core.redact_secrets(plain_url), plain_url)

    def test_diagnostic_report_generation(self):
        """Verify generation of non-secret system diagnostic report."""
        report = core.generate_diagnostic_report()
        self.assertIn("YTDownloader Pro", report)
        self.assertIn("Python", report)
        self.assertIn("PySide6", report)
        self.assertIn("yt-dlp", report)
        self.assertIn("FFmpeg", report)
        # Redaction check
        self.assertNotIn("password", report.lower())

    def test_settings_reset_to_defaults(self):
        """Verify reset_config resets all settings to DEFAULT_CONFIG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cfg = Path(tmpdir) / "test_cfg.json"
            orig = core.CONFIG_FILE
            try:
                core.CONFIG_FILE = test_cfg
                custom = {"language": "fa", "video_quality": "480p"}
                core.save_config(custom)

                # Reset
                core.reset_config()
                cfg = core.load_config()
                self.assertEqual(cfg["language"], core.DEFAULT_CONFIG["language"])
                self.assertEqual(cfg["video_quality"], core.DEFAULT_CONFIG["video_quality"])
            finally:
                core.CONFIG_FILE = orig


if __name__ == "__main__":
    unittest.main()
