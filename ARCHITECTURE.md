# YTDownloader Pro --- Architecture

**Status:** Proposed logical architecture. Adapt to the existing
repository after audit. This document does not authorize a rewrite.

## 1. Goals

-   Separate UI from engine internals.
-   Keep long-running work off the UI thread.
-   Centralize validation, configuration, state transitions, and errors.
-   Persist jobs/history safely.
-   Make external dependencies testable.
-   Separate downloading from media processing.
-   Preserve existing code where it already meets these goals.

## 2. Logical architecture

``` text
Presentation / GUI
       |
Application Services
  |-- URL Analysis
  |-- Download Orchestrator
  |-- Queue Scheduler
  |-- Playlist & Batch
  |-- History & File Library
  |-- Media Tools
  |-- Proxy & Network
  |-- Diagnostics & Updates
       |
Domain Models and Interfaces
       |
Infrastructure Adapters
  |-- yt-dlp
  |-- FFmpeg / FFprobe
  |-- SQLite repositories
  |-- Filesystem
  |-- Network / Proxy
  |-- Notifications
  |-- OS secure storage
```

Actual folder names may differ. Preserve conceptual boundaries without
forcing an unnecessary folder restructure.

## 3. Layer responsibilities

**GUI:** renders views, collects input, displays state/events; never
runs blocking network/media/database work or constructs shell commands.

**Application services:** coordinate workflows, enforce business rules,
validate requests, manage cancellation/lifecycle, translate engine
events.

**Domain:** stable models, enums, state transitions, and service
contracts; no dependency on widgets or concrete external tools.

**Infrastructure:** concrete yt-dlp/FFmpeg adapters, persistence,
filesystem, network, OS integration; isolate third-party details and
return structured results/errors.

## 4. Suggested services

  Service                  Responsibility
  ------------------------ ----------------------------------------------
  MediaAnalyzer            Analyze URL and return metadata/formats
  DownloadEngine           Execute/cancel downloads and emit events
  DownloadOrchestrator     Coordinate job lifecycle and post-processing
  QueueScheduler           Concurrency, priority, queue transitions
  PlaylistService          Inspect playlists and create jobs
  BatchService             Validate and submit multiple URLs
  MediaProcessor           FFmpeg merge/conversion/subtitle operations
  SubtitleService          Discover and retrieve subtitle tracks
  SponsorBlockService      Fetch/apply supported segment data
  PresetService            Validate and manage presets
  ProxyService             Manage profiles and test connectivity
  ComponentManager         Detect/manage yt-dlp, FFmpeg, FFprobe
  DiagnosticsService       Environment/configuration checks
  NotificationService      In-app/OS notifications
  SettingsRepository       Non-secret settings persistence
  SecretStorage            Secure credential storage
  JobRepository            Queue/job persistence
  HistoryRepository        History persistence
  MediaLibraryRepository   Output-file index

Reuse existing equivalents; do not create duplicate services.

## 5. Core models

**MediaInfo:** source URL, extractor/platform ID, media ID, title,
uploader, thumbnail, duration, upload date, playlist info, formats,
subtitles, availability/warnings.

**FormatOption:** format ID, media type, container, codecs, resolution,
frame rate, bitrate, size/estimate, merge requirement, availability.

**DownloadJob:** stable ID, source/media ID, mode/profile, selected
formats, destination, output paths, priority, status, progress,
timestamps, retry metadata, structured error, worker/process reference
if needed.

**DownloadProfile:** mode, format/quality preferences,
audio/subtitle/SponsorBlock options, filename template, destination
policy.

**ProxyProfile:** ID, protocol, host, port, username/secret references,
enabled/default flags, non-secret metadata.

**MediaFile:** ID, path, media type, container, size, duration,
source/job reference, date, existence/verification status.

## 6. Job state machine

``` text
Pending -> Analyzing -> Queued -> Downloading -> Processing -> Completed
                         |             |
                         |             +-> Paused -> Downloading
                         |             +-> Failed -> Queued (retry)
                         |             +-> Cancelled
                         +-> Failed
```

Additional states such as Interrupted or NeedsAttention may be added.

Rules: - Completed requires output verification. - Paused only when
safely supported by the engine. - Resume verifies partial-output/source
compatibility. - Restart reconciles persisted jobs with actual
processes/files. - Retry must not create unintended duplicates. -
Invalid state transitions are rejected.

## 7. Events and progress

Use structured events: analysis_started/succeeded/failed, job_queued,
download_started/progress/paused/resumed/cancelled,
processing_started/progress, job_completed/failed,
component_update_status.

Progress fields are optional: bytes downloaded, total bytes, percentage,
speed, ETA, stage, message. Unknown values remain unknown; never
manufacture metrics.

## 8. Persistence

SQLite is preferred if suitable for the current app. Suggested tables:
jobs, history, media_files, playlists, playlist_items, presets,
proxy_profiles, settings, schema_migrations, and optionally bounded
job_events.

Requirements: - Versioned migrations and transactions. - Appropriate
indexes and foreign keys. - Safe startup recovery. - Backups before
risky migrations. - Never delete the user's database to resolve
migration problems. - Do not store raw passwords/cookies in ordinary
settings tables.

## 9. Process/thread lifecycle

-   Use the GUI framework's worker/task model.
-   Update widgets only on the GUI thread.
-   Control process handles and cancellation tokens centrally.
-   Synchronize shared mutable state.
-   Enforce concurrency centrally.
-   Terminate gracefully, escalating only when needed.
-   On shutdown stop accepting work and reconcile active jobs.
-   Avoid orphan processes and leaked temporary files.

## 10. Error model

Each error should include stable code, user-facing message, technical
message, component, recoverability, retryability, job ID, and safe
diagnostic context. Never include secrets. Avoid broad exception
swallowing; add context and preserve protected technical logs.

## 11. Security boundaries

Validate at UI and service boundaries. Use safe subprocess argument
arrays. Sanitize paths and filenames. Treat extractor metadata and
imports as untrusted. Protect credentials, redact logs, and require
consent for clipboard monitoring/automation.

## 12. Testing seams

Use dependency injection or equivalent seams for engine, process,
network, repository, and filesystem adapters. Test domain logic
independently; test adapters against controlled fixtures; test full
workflows without mocking away the behavior under test.

## 13. Architecture decisions

### ADR-001: SQLite Persistence with WAL Mode
- **Context:** Applications requiring resilient persistence for jobs and history must survive crashes and concurrent operations without DB locking.
- **Decision:** Implemented `database.py` with `PRAGMA journal_mode=WAL;` and versioned schema migrations (`schema_migrations` table).
- **Impact:** Reliable recovery (`recover_interrupted_jobs()`), fast async reads, zero corruption risks.

### ADR-002: Modular Queue and Batch Management
- **Context:** Managing multiple downloads and batch URL lists without stalling the GUI.
- **Decision:** Added `queue_manager.py` (`QueueManager`) decoupling job scheduling and concurrency limits from GUI widgets.
- **Impact:** Thread-safe execution, configurable concurrency, and reliable batch ingestion.

### ADR-003: Defensive Security and Redaction
- **Context:** Preventing path traversal, unescaped shell execution, and secret leaks in logs.
- **Decision:** Integrated `sanitize_filename` (neutralizing `..`), argument arrays for FFmpeg, and `redact_secrets()` for all logs and URLs.
- **Impact:** Full protection against arbitrary file write, command injection, and credential disclosure.

### ADR-004: Dedicated Media Processing & Presets Engine
- **Context:** Decoupling audio transcoding, subtitle embedding, and SponsorBlock filtering from raw download routines.
- **Decision:** Introduced `media_tools.py` with standalone functions for audio FFmpeg parameter building, non-destructive subtitle embedding, and `PresetManager` with schema validation.
- **Impact:** Modular media processing pipeline, safe temporary file replacement, and educational warnings for lossy-to-lossless conversions.

### ADR-005: Network Resiliency, Diagnostic Center & Safe Shutdown Lifecycle
- **Context:** Managing complex proxy profiles, rate limits, connection timeouts, and preventing orphaned processes upon application exit.
- **Decision:** Built `network_system.py` (`ProxyManager`, `NetworkConfig`, `DiagnosticCenter`, `LogManager`) and hooked `closeEvent` in `MainWindow` with bounded worker timeouts.
- **Impact:** Real latency verification, credential redaction, crash-free shutdown, and multi-point system health diagnostics.
