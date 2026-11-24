"""
Phase 5 E2E & Final QA Regression Tests:
- Full journey from URL analysis -> Download -> Verification -> History recording
- Security: injection resistance and path traversal defense
- RTL / LTR layout switching
"""
import os
import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

import core
import database

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestPhase5FinalQA(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = database.Database(Path(self.tmpdir.name) / "e2e.db")
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_e2e_download_and_history_lifecycle(self):
        """Simulate full lifecycle: valid URL -> format selection -> verify output -> history log."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=shared"
        cleaned_url = core.clean_url(url)
        self.assertNotIn("feature=shared", cleaned_url)

        # Create dummy downloaded output file to simulate successful worker completion
        download_dir = Path(self.tmpdir.name) / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        target_file = download_dir / "Rick_Astley_Never_Gonna_Give_You_Up.mp4"
        target_file.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 2048)

        # Output verification
        self.assertTrue(core.verify_output_file(target_file))

        # Record to history
        rec_id = self.db.history.add_record(
            job_id="test-job-e2e",
            title="Rick Astley - Never Gonna Give You Up",
            url=cleaned_url,
            file_path=str(target_file),
            media_type="Video",
            file_size=target_file.stat().st_size,
            duration="03:32"
        )
        self.assertGreater(rec_id, 0)

        # Query history
        history_items = self.db.history.get_history(search="Astley")
        self.assertEqual(len(history_items), 1)
        self.assertEqual(history_items[0]["title"], "Rick Astley - Never Gonna Give You Up")
        self.assertTrue(os.path.exists(history_items[0]["file_path"]))

    def test_security_path_traversal_and_injection(self):
        """Verify filenames with path traversal attempts ('../../') are neutralized."""
        malicious_input = "../../../etc/passwd_or_malicious_executable.exe"
        safe = core.sanitize_filename(malicious_input)
        self.assertNotIn("/", safe)
        self.assertNotIn("\\", safe)
        self.assertNotIn("..", safe)

    def test_rtl_ltr_direction(self):
        """Verify Qt layout direction switching between English (LTR) and Persian (RTL)."""
        app.setLayoutDirection(Qt.RightToLeft)
        self.assertEqual(app.layoutDirection(), Qt.RightToLeft)

        app.setLayoutDirection(Qt.LeftToRight)
        self.assertEqual(app.layoutDirection(), Qt.LeftToRight)


if __name__ == "__main__":
    unittest.main()
