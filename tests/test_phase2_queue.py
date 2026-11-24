"""
Phase 2 Unit Tests:
- QueueManager concurrency and job transitions
- Batch URL parsing
"""
import os
import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import database
import queue_manager


class TestPhase2Queue(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_queue.db"
        self.db = database.Database(self.db_path)
        self.db.initialize()
        self.qm = queue_manager.QueueManager(db=self.db, max_concurrent=2)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_batch_url_parsing(self):
        """Verify parsing multiline text and filtering valid URLs."""
        raw_text = """
        https://www.youtube.com/watch?v=aaa
        some invalid text
        https://youtu.be/bbb
        http://example.com/notmedia
        https://www.youtube.com/watch?v=ccc
        """
        urls = queue_manager.parse_batch_urls(raw_text)
        self.assertEqual(len(urls), 4)
        self.assertIn("https://www.youtube.com/watch?v=aaa", urls)
        self.assertIn("https://youtu.be/bbb", urls)
        self.assertIn("https://www.youtube.com/watch?v=ccc", urls)

    def test_enqueue_job(self):
        """Verify enqueuing a job updates database with Queued status."""
        job_id = self.qm.enqueue_job({
            "url": "https://www.youtube.com/watch?v=test",
            "title": "Enqueued Test",
            "download_type": "Video"
        }, auto_start=False)
        self.assertIsNotNone(job_id)
        job = self.db.jobs.get_job(job_id)
        self.assertEqual(job["status"], "Queued")
        self.assertEqual(self.qm.get_queued_count(), 1)


if __name__ == "__main__":
    unittest.main()
