# YTDownloader Pro --- Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
