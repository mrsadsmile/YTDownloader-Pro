# YTDownloader Pro --- Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.7.0] - Phase 2: Download Management, Queue, Playlists, Batch & Files Milestone

### Added
- **Persistent Download Queue (`queue_view.py`, `queue_manager.py`)**:
  - Full lifecycle state machine (`Pending`, `Analyzing`, `Queued`, `Downloading`, `Paused`, `Processing`, `Completed`, `Failed`, `Cancelled`).
  - Active concurrency selector (1 to 5 concurrent downloads) with thread-safe worker throttling.
  - Priority management: Up, Down, and explicit priority assignment with immediate queue redispatch.
  - Bulk actions: "Pause All", "Resume All", "Cancel All", and "Clear Finished".
  - Real-time download metrics: Live speed, ETA, and downloaded file size tracked per queue item.
  - Crash recovery: Interrupted active jobs are flagged safely upon application restart without ghost processes or duplication.
- **Playlist Explorer & Batch Importer (`playlist_batch.py`, `playlist_batch_view.py`)**:
  - **Playlist Explorer**: Flat non-blocking extraction of full playlist entries with thumbnails, video count, author, and per-video checkboxes.
  - Select All / Select None controls, dedicated playlist subfolder option, and sequential numbering template (`01 - Title.mp4`).
  - **Batch URL Importer**: Multi-line paste area and `.txt` file importer with comment stripping (`#`), syntax validation, and duplicate detection.
  - Batch format preset configuration (Video/Audio, resolution, codec) applied uniformly to all imported items.
- **Dedicated Media Library & File Manager (`files_view.py`)**:
  - Centralized management of completed downloads with live search and Video/Audio filtering.
  - Safe File Rename: Updates physical filename on disk and synchronizes the database record atomically.
  - Safe File Move: Transfers media between folders with collision avoidance via `get_unique_path()`.
  - Safe File Delete: Removes media with user confirmation dialog.
  - Direct actions: Open File in system media player and Reveal in Windows Explorer.
- **Enhanced History Management (`history_view.py`)**:
  - Searchable and filterable history by platform (YouTube, Soundcloud, etc.), media type (Video, Audio), status, and date sorting.
  - Real-time on-disk status verification with visual badges (`● On Disk` vs `○ Moved/Deleted`).
  - Relink Moved Files: File picker allowing users to restore the path for media moved externally.
  - Retry Download: Instant re-enqueue for failed or deleted media.
- **5-Tab Segmented UI Navigation (`main_window.py`)**:
  - Top segmented navigation bar (`Downloader`, `Queue`, `Playlists & Batch`, `History`, `Files`) using `QStackedWidget` for seamless switching without UI lag.
- **Database Schema Migration v2 (`database.py`)**:
  - Added columns `thumbnail`, `platform`, `speed`, `eta`, `file_size`, `priority`, `started_at`, `completed_at` to `jobs`.
  - Added indexes `idx_jobs_priority`, `idx_jobs_status_prio`, `idx_history_title`, `idx_history_platform`, `idx_history_media_type`.
  - Transaction-safe migration tracking in `schema_migrations`.
- **Comprehensive Automated Test Suite (`tests/test_phase2_management.py`)**:
  - 8 new automated tests covering queue lifecycle, priority reordering, clear completed, restart recovery, history filtering, relinking, file operations, and batch deduplication.
  - Total test suite expanded to 44 passing tests (100% pass rate).

---

## [2.6.0] - Phase 1: Core Engine & Download Experience Milestone

### Added
- **Core URL Engine**:
  - `validate_url()`: Strict protocol and hostname validation, rejecting malformed, empty, or unsupported URI schemes.
  - `clean_url()`: Automatic stripping of tracking tokens (`si=`, `feature=`, `fbclid=`, `igshid=`, `utm_*`).
  - Interactive cancellation of URL analysis: clicking "Cancel Analysis" interrupts `InspectWorker` immediately without locking the UI.
  - Universal clipboard detection: automatically identifies any valid media URL placed in the clipboard.
  - Real-time input validation feedback with semantic token colors (Success, Warning, Error).
- **Rich Media Preview Card**:
  - Displays Platform/Extractor (YouTube, SoundCloud, Vimeo, etc.), Creator, Duration, and Upload Date.
  - Codecs tag: Video Codec, Audio Codec, and FPS (e.g. `H.264 / AAC • 60fps`).
  - Available Subtitles list and approximate file size calculation (`filesize` / `filesize_approx`).
  - Graceful fallbacks for missing thumbnails, missing creator, and live streams.
- **Dynamic Download Modes & Formats**:
  - **Video Mode**: Dynamic resolution list extracted directly from media metadata (2160p down to 360p).
  - **Audio Mode**: Support for MP3, M4A, OPUS, WAV, and FLAC.
  - **Original Audio Preservation**: Added "Best Available (Original)" mode to download native source bitstream without transcoding loss.
  - Lossless format intelligence: Disables lossy bitrate selection when lossless (FLAC/WAV) or source audio is selected.
  - **Dual Mode**: Downloads the best video and simultaneously extracts high-bitrate audio via FFmpeg.
- **Filesystem & Destination Safety**:
  - `validate_destination()`: Ensures download directory exists, verifies write permissions via temporary file probe, and asserts minimum 50MB free disk space.
  - `sanitize_filename()`: Removes prohibited Windows filesystem characters (`<>:"/\\|?*`) and neutralizes path traversal tokens (`..`).
  - `get_unique_path()`: Prevents accidental file overwriting by incrementing filename counters (`(1)`, `(2)`).
  - `verify_output_file()`: Verifies that downloaded media actually exists on disk and has non-zero bytes before reporting success.
- **Workflow & Error Handling**:
  - "Open File" button: Launches the downloaded video or audio directly in the system's default media player (`os.startfile`).
  - "Retry Download" state: Allows instant retry on network or process interruption.
  - Structured error classification (`classify_error()`): Maps raw exceptions to `AppError` categories (DRM, Deleted/Unavailable, Network, Proxy, Restricted, FFmpeg, Permission, Disk Space).
- **Automated Test Coverage**:
  - Added unit, integration, and GUI tests (`test_phase1_core.py`, `test_phase1_gui.py`), bringing total passing test suite to 36 tests (100% pass rate).

---

## [2.5.0] - Initial Desktop Prototype

### Added
- PySide6 desktop GUI with dark graphite theme.
- Basic yt-dlp download integration and FFmpeg detection.
- Windows PATH sanitization to resolve WinError 448 junction conflicts.
