"""
Phase 2 Unit Tests:
- SQLite Database creation and schema migrations
- JobRepository: add, get, update status, recovery
- HistoryRepository: add, search, delete, verify file existence
"""
import os
import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import database


class TestPhase2Database(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_data.db"
        self.db = database.Database(self.db_path)
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_schema_migrations(self):
        """Verify schema_migrations table is created and version 1 is recorded."""
        version = self.db.get_schema_version()
        self.assertEqual(version, 1)

    def test_job_crud_and_status(self):
        """Verify adding, updating, and querying jobs."""
        job_id = self.db.jobs.add_job({
            "url": "https://www.youtube.com/watch?v=12345",
            "title": "Test Video",
            "download_type": "Video",
            "video_quality": "1080p",
            "video_format": "mp4",
            "audio_format": "mp3",
            "audio_quality": "320 kbps",
            "status": "Queued",
        })
        self.assertIsNotNone(job_id)

        job = self.db.jobs.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job["title"], "Test Video")
        self.assertEqual(job["status"], "Queued")

        # Update status
        self.db.jobs.update_status(job_id, "Downloading", progress=45.5)
        updated = self.db.jobs.get_job(job_id)
        self.assertEqual(updated["status"], "Downloading")
        self.assertEqual(updated["progress"], 45.5)

    def test_recover_interrupted_jobs(self):
        """Verify interrupted jobs are recovered on startup."""
        job_id = self.db.jobs.add_job({
            "url": "https://www.youtube.com/watch?v=active",
            "title": "Active Download",
            "download_type": "Video",
            "status": "Downloading",
        })
        # Simulate app crash/restart
        recovered_count = self.db.jobs.recover_interrupted_jobs()
        self.assertGreaterEqual(recovered_count, 1)

        job = self.db.jobs.get_job(job_id)
        self.assertEqual(job["status"], "Interrupted")

    def test_history_records_and_search(self):
        """Verify history persistence, querying, and search."""
        rec_id = self.db.history.add_record(
            job_id="job-1",
            title="Cool Tutorial Video",
            url="https://youtube.com/watch?v=abc",
            file_path="C:/Downloads/video.mp4",
            media_type="Video",
            file_size=10485760,
            duration="10:00"
        )
        self.assertGreater(rec_id, 0)

        # Search matching
        results = self.db.history.get_history(search="Tutorial")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Cool Tutorial Video")

        # Search non-matching
        no_results = self.db.history.get_history(search="NonExistentKeyword")
        self.assertEqual(len(no_results), 0)

        # Delete record
        self.db.history.delete_record(rec_id)
        self.assertEqual(len(self.db.history.get_history()), 0)


if __name__ == "__main__":
    unittest.main()
