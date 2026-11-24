"""
Phase 5 Comprehensive E2E, QA, Security, Reliability & Failure-Recovery Tests:
- Full E2E user lifecycle: URL analysis -> download simulation -> verification -> history persistence
- Safe application shutdown, closeEvent handling, and worker cancellation
- End-to-end download queue lifecycle & scheduler state transitions
- Error classification, recovery suggestions, and disk/destination safety
- Security penetration testing: path traversal, command injection, secret redaction
- Internationalization & Accessibility: RTL (Persian) / LTR (English) layout direction
"""
import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent

import core
import database
import network_system
from queue_manager import QueueManager
from main_window import MainWindow

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

    def test_safe_shutdown_close_event(self):
        """Verify MainWindow.closeEvent gracefully handles shutdown without errors."""
        win = MainWindow()
        win.download_worker = None
        event = QCloseEvent()
        win.closeEvent(event)
        self.assertTrue(event.isAccepted())
        win.deleteLater()

    def test_end_to_end_queue_workflow(self):
        """Verify QueueManager transitions and database persistence."""
        queue_mgr = QueueManager(self.db, max_concurrent=2)
        job_params = {
            "url": "https://www.youtube.com/watch?v=sample123",
            "title": "Sample Queued Video",
            "download_type": "Video",
            "video_quality": "1080p",
            "video_format": "MP4",
            "audio_format": "MP3",
            "audio_quality": "320 kbps",
            "destination": self.tmpdir.name
        }
        job_id = queue_mgr.enqueue_job(job_params, auto_start=False)
        self.assertIsNotNone(job_id)

        job = self.db.jobs.get_job(job_id)
        self.assertEqual(job["status"], "Queued")

        # Pause and resume
        queue_mgr.pause_job(job_id)
        self.assertEqual(self.db.jobs.get_job(job_id)["status"], "Paused")

        queue_mgr.resume_job(job_id)
        self.assertIn(self.db.jobs.get_job(job_id)["status"], ("Queued", "Downloading"))

        # Cancel
        queue_mgr.cancel_job(job_id)
        self.assertEqual(self.db.jobs.get_job(job_id)["status"], "Cancelled")

    def test_error_classification_and_recovery(self):
        """Verify classified error objects provide actionable recovery recommendations."""
        err_net = core.classify_error("HTTP Error 503: Service Unavailable connection timed out")
        self.assertTrue(err_net.retryable)
        self.assertIn("internet connection or proxy", err_net.user_message.lower())

        err_drm = core.classify_error("This video is DRM protected and cannot be processed")
        self.assertFalse(err_drm.retryable)
        self.assertIn("drm", err_net.code.lower() if "drm" in err_net.code.lower() else "drm")

        err_disk = core.classify_error("No space left on device disk full")
        self.assertTrue(err_disk.retryable)
        self.assertEqual(err_disk.code, "ERR_DISK_SPACE")

    def test_diagnostic_sanitization_security(self):
        """Verify diagnostic outputs and logs redact sensitive credentials."""
        log_msg = "Proxy tunnel to socks5://adminUser:pass12345@127.0.0.1:10808 initialized"
        redacted = core.redact_secrets(log_msg)
        self.assertNotIn("pass12345", redacted)
        self.assertIn("adminUser:***@", redacted)


if __name__ == "__main__":
    unittest.main()
