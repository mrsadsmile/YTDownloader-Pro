"""
SQLite Database & Persistence Repositories for YTDownloader Pro
Implements versioned migrations, JobRepository, HistoryRepository, and crash recovery.
"""
import os
import sys
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Default database location in application data directory
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

DEFAULT_DB_PATH = APP_DIR / "app_data.db"


class JobRepository:
    def __init__(self, conn_getter):
        self._get_conn = conn_getter

    def add_job(self, data: Dict[str, Any]) -> str:
        job_id = data.get("id") or str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute("""
                INSERT INTO jobs (
                    id, url, title, download_type, video_quality,
                    video_format, audio_format, audio_quality,
                    status, progress, error_message, output_path,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                data.get("url", ""),
                data.get("title", "Untitled Media"),
                data.get("download_type", "Video"),
                data.get("video_quality", "Best Available"),
                data.get("video_format", "MP4"),
                data.get("audio_format", "MP3"),
                data.get("audio_quality", "320 kbps"),
                data.get("status", "Queued"),
                data.get("progress", 0.0),
                data.get("error_message"),
                data.get("output_path"),
                now,
                now
            ))
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_status(self, job_id: str, status: str, progress: Optional[float] = None,
                      error_message: Optional[str] = None, output_path: Optional[str] = None):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            updates = ["status = ?", "updated_at = ?"]
            params = [status, now]

            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            if output_path is not None:
                updates.append("output_path = ?")
                params.append(output_path)

            params.append(job_id)
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, params)

    def get_pending_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE status IN ('Queued', 'Pending') ORDER BY created_at ASC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def delete_job(self, job_id: str) -> bool:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0

    def recover_interrupted_jobs(self) -> int:
        """Recovers any jobs marked active during unexpected application termination."""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("""
                UPDATE jobs
                SET status = 'Interrupted', updated_at = ?
                WHERE status IN ('Downloading', 'Analyzing', 'Processing', 'Merging')
            """, (now,))
            return cursor.rowcount


class HistoryRepository:
    def __init__(self, conn_getter):
        self._get_conn = conn_getter

    def add_record(self, job_id: str, title: str, url: str, file_path: str,
                   media_type: str = "Video", file_size: int = 0, duration: str = "--:--") -> int:
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("""
                INSERT INTO history (
                    job_id, title, url, file_path,
                    media_type, file_size, duration, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, title, url, file_path, media_type, file_size, duration, now))
            return cursor.lastrowid

    def get_history(self, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        if search and search.strip():
            term = f"%{search.strip()}%"
            cursor = conn.execute("""
                SELECT * FROM history
                WHERE title LIKE ? OR url LIKE ? OR file_path LIKE ?
                ORDER BY completed_at DESC LIMIT ?
            """, (term, term, term, limit))
        else:
            cursor = conn.execute("SELECT * FROM history ORDER BY completed_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def delete_record(self, record_id: int) -> bool:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
            return cursor.rowcount > 0

    def clear_history(self) -> int:
        conn = self._get_conn()
        with conn:
            cursor = conn.execute("DELETE FROM history")
            return cursor.rowcount


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._conn = None
        self.jobs = JobRepository(self.get_connection)
        self.history = HistoryRepository(self.get_connection)

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode and foreign key constraints
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    def initialize(self):
        """Applies versioned schema migrations."""
        conn = self.get_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
        current_version = self.get_schema_version()
        if current_version < 1:
            self._apply_migration_v1(conn)

    def get_schema_version(self) -> int:
        conn = self.get_connection()
        cursor = conn.execute("SELECT MAX(version) FROM schema_migrations")
        row = cursor.fetchone()
        return row[0] if (row and row[0] is not None) else 0

    def _apply_migration_v1(self, conn: sqlite3.Connection):
        now = datetime.now().isoformat()
        with conn:
            # Jobs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    download_type TEXT NOT NULL,
                    video_quality TEXT,
                    video_format TEXT,
                    audio_format TEXT,
                    audio_quality TEXT,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0.0,
                    error_message TEXT,
                    output_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")

            # History table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    duration TEXT,
                    completed_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_completed ON history(completed_at);")

            # Record migration
            conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (1, ?)", (now,))

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


# Global singleton instance
_default_db: Optional[Database] = None


def get_db() -> Database:
    global _default_db
    if _default_db is None:
        _default_db = Database()
        _default_db.initialize()
    return _default_db
