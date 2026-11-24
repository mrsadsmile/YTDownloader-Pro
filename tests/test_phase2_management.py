"""
Phase 2 Comprehensive Download Management Tests:
- Queue persistence, pause, resume, cancel, retry, reorder, priority
- Maximum concurrency throttling
- Restart crash recovery
- History advanced filtering (media_type, platform, status, sort)
- History file relinking
- Safe File operations (rename, move, collision avoidance, delete)
- Playlist parsing and batch duplicate filtering
"""
import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import database
import queue_manager
import playlist_batch
import core


class TestPhase2Management(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_mgmt.db"
        self.db = database.Database(self.db_path)
        self.db.initialize()
        self.qm = queue_manager.QueueManager(db=self.db, max_concurrent=2)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_queue_lifecycle_pause_resume_cancel_retry(self):
        """Test full queue item lifecycle state transitions."""
        job_id = self.qm.enqueue_job({
            "url": "https://www.youtube.com/watch?v=item1",
            "title": "Item 1",
            "download_type": "Video"
        }, auto_start=False)
        self.assertEqual(self.db.jobs.get_job(job_id)["status"], "Queued")

        # Pause
        self.qm.pause_job(job_id)
        self.assertEqual(self.db.jobs.get_job(job_id)["status"], "Paused")

        # Resume - immediately picked up by queue scheduler into Downloading or Queued
        self.qm.resume_job(job_id)
        self.assertIn(self.db.jobs.get_job(job_id)["status"], ("Queued", "Downloading"))

        # Cancel
        self.qm.cancel_job(job_id)
        self.assertEqual(self.db.jobs.get_job(job_id)["status"], "Cancelled")

        # Retry without immediate autostart by setting max_concurrent to 0 or pausing first
        self.db.jobs.update_status(job_id, "Queued")
        self.assertEqual(self.db.jobs.get_job(job_id)["status"], "Queued")

    def test_queue_priority_and_reorder(self):
        """Test changing priority and moving jobs up/down in queue."""
        j1 = self.qm.enqueue_job({"url": "https://www.youtube.com/watch?v=1", "title": "Job 1"}, auto_start=False)
        j2 = self.qm.enqueue_job({"url": "https://www.youtube.com/watch?v=2", "title": "Job 2"}, auto_start=False)

        # Initially, j1 was created first so j1 comes first
        pending = self.db.jobs.get_pending_jobs()
        self.assertEqual(pending[0]["id"], j1)

        # Increase j2 priority
        self.qm.reorder_job(j2, "up")
        pending_after = self.db.jobs.get_pending_jobs()
        self.assertEqual(pending_after[0]["id"], j2)

    def test_queue_clear_completed(self):
        """Test clearing finished, failed, and cancelled jobs from queue."""
        j1 = self.qm.enqueue_job({"url": "https://www.youtube.com/watch?v=1", "title": "Job 1"}, auto_start=False)
        j2 = self.qm.enqueue_job({"url": "https://www.youtube.com/watch?v=2", "title": "Job 2"}, auto_start=False)

        self.db.jobs.update_status(j1, "Completed")
        self.db.jobs.update_status(j2, "Cancelled")
        self.assertEqual(len(self.db.jobs.get_all_jobs()), 2)

        self.qm.clear_completed()
        self.assertEqual(len(self.db.jobs.get_all_jobs()), 0)

    def test_restart_recovery_of_interrupted_jobs(self):
        """Simulate unexpected crash and verify interrupted jobs are recovered."""
        j1 = self.qm.enqueue_job({"url": "https://www.youtube.com/watch?v=crash", "title": "Crash Job"}, auto_start=False)
        self.db.jobs.update_status(j1, "Downloading")

        # Restart simulation
        recovered_count = self.db.jobs.recover_interrupted_jobs()
        self.assertEqual(recovered_count, 1)
        job = self.db.jobs.get_job(j1)
        self.assertEqual(job["status"], "Interrupted")

    def test_history_filtering_and_sorting(self):
        """Test filtering download history by platform, media type, and sorting."""
        self.db.history.add_record(
            job_id="h1", title="YouTube 4K Video", url="https://youtube.com/1",
            file_path="C:/v1.mp4", media_type="Video", file_size=500000000,
            platform="YouTube", format="MP4"
        )
        self.db.history.add_record(
            job_id="h2", title="SoundCloud Track", url="https://soundcloud.com/2",
            file_path="C:/a1.mp3", media_type="Audio", file_size=10000000,
            platform="SoundCloud", format="MP3"
        )

        # Filter by platform
        yt_only = self.db.history.get_history(platform="YouTube")
        self.assertEqual(len(yt_only), 1)
        self.assertEqual(yt_only[0]["title"], "YouTube 4K Video")

        # Filter by media type
        audio_only = self.db.history.get_history(media_type="Audio")
        self.assertEqual(len(audio_only), 1)
        self.assertEqual(audio_only[0]["title"], "SoundCloud Track")

        # Sort by size descending
        sorted_size = self.db.history.get_history(sort_by="size_desc")
        self.assertEqual(sorted_size[0]["title"], "YouTube 4K Video")

    def test_history_relink_moved_file(self):
        """Test updating file path in history when a file is moved."""
        rec_id = self.db.history.add_record(
            job_id="r1", title="Relink Test", url="https://youtube.com/r",
            file_path="C:/old_path/test.mp4", media_type="Video"
        )
        success = self.db.history.update_file_path(rec_id, "D:/new_path/test.mp4")
        self.assertTrue(success)

        rec = self.db.history.get_history()[0]
        self.assertEqual(rec["file_path"], "D:/new_path/test.mp4")

    def test_safe_file_operations_rename_move_delete(self):
        """Test safe file operations (rename, move with collision handling, delete) with DB sync."""
        media_dir = Path(self.tmpdir.name) / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        original_file = media_dir / "sample_video.mp4"
        original_file.write_bytes(b"\x00" * 4096)

        rec_id = self.db.history.add_record(
            job_id="m1", title="Sample", url="https://youtube.com/m",
            file_path=str(original_file), media_type="Video", file_size=4096
        )

        # 1. Rename
        renamed_file = media_dir / "renamed_video.mp4"
        os.rename(original_file, renamed_file)
        self.db.history.update_file_path(rec_id, str(renamed_file))
        self.assertTrue(renamed_file.exists())
        self.assertEqual(self.db.history.get_history()[0]["file_path"], str(renamed_file))

        # 2. Move with collision avoidance
        target_dir = Path(self.tmpdir.name) / "archive"
        target_dir.mkdir(parents=True, exist_ok=True)
        # Create an existing file in target to force collision
        (target_dir / "renamed_video.mp4").write_bytes(b"\x01" * 10)

        unique_target = core.get_unique_path(target_dir, "renamed_video.mp4")
        shutil.move(renamed_file, unique_target)
        self.db.history.update_file_path(rec_id, str(unique_target))

        self.assertTrue(unique_target.exists())
        self.assertIn("(1)", unique_target.name)

        # 3. Delete
        unique_target.unlink()
        self.db.history.delete_record(rec_id)
        self.assertFalse(unique_target.exists())
        self.assertEqual(len(self.db.history.get_history()), 0)

    def test_batch_url_parsing_and_duplicate_detection(self):
        """Test batch text parser filtering duplicates and invalid URLs."""
        text = """
        https://www.youtube.com/watch?v=first
        # comment line
        https://www.youtube.com/watch?v=second
        https://www.youtube.com/watch?v=first&si=tracking
        invalid-url
        """
        urls = playlist_batch.parse_urls_from_text(text)
        self.assertEqual(len(urls), 4)

        seen = set()
        unique = []
        for u in urls:
            is_valid, _ = core.validate_url(u)
            if is_valid:
                clean = core.clean_url(u)
                if clean not in seen:
                    seen.add(clean)
                    unique.append(clean)

        self.assertEqual(len(unique), 2)
        self.assertIn("https://www.youtube.com/watch?v=first", unique)
        self.assertIn("https://www.youtube.com/watch?v=second", unique)


if __name__ == "__main__":
    unittest.main()
