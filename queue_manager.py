"""
Queue & Concurrency Manager for YTDownloader Pro
Manages multi-job scheduling, batch ingestion, active worker tracking, and signals.
"""
import os
import sys
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtCore import QObject, Signal

import core
import database


def parse_batch_urls(text: str) -> List[str]:
    """Extracts and validates list of media URLs from multiline text input."""
    if not text:
        return []
    valid_urls = []
    lines = text.strip().splitlines()
    for line in lines:
        u = line.strip()
        if not u:
            continue
        is_valid, _ = core.validate_url(u)
        if is_valid:
            valid_urls.append(core.clean_url(u))
    return valid_urls


class QueueManager(QObject):
    sig_job_enqueued = Signal(dict)
    sig_job_status = Signal(str, str)         # job_id, status
    sig_job_progress = Signal(str, dict)      # job_id, progress_dict
    sig_job_completed = Signal(str, dict)     # job_id, result_dict
    sig_job_error = Signal(str, str)          # job_id, error_message
    sig_job_log = Signal(str, str)            # job_id, log_line

    def __init__(self, db: Optional[database.Database] = None, max_concurrent: int = 1):
        super().__init__()
        self.db = db or database.get_db()
        self.max_concurrent = max(1, max_concurrent)
        self.active_workers: Dict[str, core.DownloadWorker] = {}

    def set_max_concurrent(self, value: int):
        self.max_concurrent = max(1, value)
        self.process_queue()

    def get_queued_count(self) -> int:
        pending = self.db.jobs.get_pending_jobs(limit=100)
        return len(pending)

    def get_active_count(self) -> int:
        return len(self.active_workers)

    def enqueue_job(self, params: Dict[str, Any], auto_start: bool = True) -> str:
        """Saves job to database in 'Queued' status and optionally attempts scheduling."""
        job_data = dict(params)
        job_data["status"] = "Queued"
        job_id = self.db.jobs.add_job(job_data)
        job_data["id"] = job_id
        self.sig_job_enqueued.emit(job_data)
        if auto_start:
            self.process_queue()
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Cancels an active worker or removes pending job from queue."""
        if job_id in self.active_workers:
            worker = self.active_workers[job_id]
            worker.cancel()
            return True
        else:
            job = self.db.jobs.get_job(job_id)
            if job and job.get("status") in ("Queued", "Pending"):
                self.db.jobs.update_status(job_id, "Cancelled", error_message="Cancelled by user before start.")
                self.sig_job_status.emit(job_id, "Cancelled")
                return True
        return False

    def process_queue(self):
        """Dispatches queued jobs up to max_concurrent capacity."""
        if len(self.active_workers) >= self.max_concurrent:
            return

        needed = self.max_concurrent - len(self.active_workers)
        pending_jobs = self.db.jobs.get_pending_jobs(limit=needed)

        for job in pending_jobs:
            job_id = job["id"]
            if job_id in self.active_workers:
                continue

            self._start_worker(job)

    def _start_worker(self, job: Dict[str, Any]):
        job_id = job["id"]
        self.db.jobs.update_status(job_id, "Downloading", progress=0.0)
        self.sig_job_status.emit(job_id, "Downloading")

        worker = core.DownloadWorker(job)
        self.active_workers[job_id] = worker

        # Connect signals
        worker.sig_status.connect(lambda s, j=job_id: self._on_worker_status(j, s))
        worker.sig_progress.connect(lambda p, j=job_id: self._on_worker_progress(j, p))
        worker.sig_finished.connect(lambda res, j=job_id: self._on_worker_finished(j, res, job))
        worker.sig_error.connect(lambda err, j=job_id: self._on_worker_error(j, err))
        worker.sig_log.connect(lambda line, j=job_id: self.sig_job_log.emit(j, line))

        worker.start()

    def _on_worker_status(self, job_id: str, status: str):
        self.db.jobs.update_status(job_id, status)
        self.sig_job_status.emit(job_id, status)

    def _on_worker_progress(self, job_id: str, prog: Dict[str, Any]):
        frac = prog.get("fraction", 0.0)
        self.db.jobs.update_status(job_id, "Downloading", progress=round(frac * 100, 1))
        self.sig_job_progress.emit(job_id, prog)

    def _on_worker_finished(self, job_id: str, result: Dict[str, Any], job_data: Dict[str, Any]):
        out_file = result.get("video_file") or result.get("audio_file") or ""
        self.db.jobs.update_status(job_id, "Completed", progress=100.0, output_path=out_file)

        # Add to history
        file_size = 0
        if out_file and os.path.exists(out_file):
            try:
                file_size = os.path.getsize(out_file)
            except Exception:
                pass

        self.db.history.add_record(
            job_id=job_id,
            title=job_data.get("title", "Untitled Media"),
            url=job_data.get("url", ""),
            file_path=out_file,
            media_type=job_data.get("download_type", "Video"),
            file_size=file_size,
            duration=job_data.get("duration", "--:--")
        )

        if job_id in self.active_workers:
            del self.active_workers[job_id]

        self.sig_job_completed.emit(job_id, result)
        self.process_queue()

    def _on_worker_error(self, job_id: str, error_msg: str):
        self.db.jobs.update_status(job_id, "Failed", error_message=error_msg)
        if job_id in self.active_workers:
            del self.active_workers[job_id]

        self.sig_job_error.emit(job_id, error_msg)
        self.process_queue()
