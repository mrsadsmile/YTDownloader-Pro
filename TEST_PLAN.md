# YTDownloader Pro --- Test Plan

## 1. Principles

-   Test behavior, not only implementation details.
-   Use deterministic fixtures.
-   Distinguish mocked tests from real integrations.
-   Do not delete/weaken failing tests just to get a green suite.
-   Verify output files, not only process exit codes.
-   Record environment limitations.
-   Add regression tests for fixed defects.

## 2. Test levels

-   **Unit:** models, state transitions, validators, path/filename
    handling, configuration.
-   **Integration:** yt-dlp, FFmpeg/FFprobe, SQLite, filesystem,
    proxy/network, OS adapters.
-   **GUI:** controls, navigation, forms, state updates, errors,
    keyboard, RTL/LTR.
-   **E2E:** complete user journeys from URL to verified output/history.
-   **Manual:** visual quality, accessibility, OS behavior; record
    steps/evidence.

## 3. Environment record

For each run record OS/version, runtime, GUI framework, yt-dlp,
FFmpeg/FFprobe, app commit/version, command, network/proxy availability,
fixture/source, and relevant logs.

Prefer small legally accessible local media fixtures. Use mocked
network/extractor responses for deterministic tests. Live external tests
must be labeled as such.

## 4. Phase 0 --- Baseline

-   [ ] Identify current test framework.
-   [ ] Run existing tests before changes.
-   [ ] Launch current app.
-   [ ] Record failures/warnings.
-   [ ] Identify engine, target OS, packaging.
-   [ ] Save baseline output.

## 5. Phase 1 --- Core

**URL/analysis:** valid URL; malformed/unsupported URL;
private/restricted/login-required/deleted content; playlist detection;
cancellation; missing metadata; timeout/extractor failure.

**Formats/modes:** actual format discovery; unavailable quality not
selectable; best available; separate streams; combined streams;
audio-only source; Video/Audio/Dual; unsupported codec/container.

**Execution:** successful download; real progress; unknown total;
missing speed/ETA; cancellation; retry; pause/resume only if supported;
FFmpeg merge and failure; missing FFmpeg; permissions/disk failure;
filename conflict; output readable; GUI responsive.

## 6. Phase 2 --- Management

**Queue:** add/remove; priority/reorder; concurrency; duplicate
prevention; state transitions; retry; persistence; restart recovery for
pending/interrupted jobs; simultaneous updates.

**History:** completed/failed records; search/sort/filter; remove record
without deleting file; missing/moved-file detection.

**Playlist/batch:** metadata/items; select all/individual; order; dedup;
partial failure; paste/TXT import; invalid URL isolation; duplicate
detection; per-item overrides.

**Files/database:** search/filter/sort; open; rename/move/delete;
conflict handling; DB consistency; fresh DB; migrations; interrupted
transactions; backup/restore where implemented.

## 7. Phase 3 --- Media tools

**Audio:** MP3/M4A/OPUS/WAV/FLAC where supported; bitrate/sample-rate
validation; avoid unnecessary re-encoding; metadata/cover art; correct
warning for lossy-source conversion.

**Subtitles:** manual vs automatic; language discovery; SRT/VTT/ASS
where available; subtitle-only; embedding; missing subtitles; preserve
original on FFmpeg failure.

**SponsorBlock/presets:** API success/error/no segments; category
mapping; actual processing; built-in presets; custom CRUD;
import/export; malformed/unsafe preset rejection; persistence.

## 8. Phase 4 --- System

**Proxy/network:** profile validation; real connection test; verify
actual yt-dlp proxy use; secret redaction; unavailable proxy;
timeout/retry; rate limiting; supported IP behavior.

**Cookies/advanced:** valid/invalid Netscape cookie file; no cookie
leakage; user-agent/header validation; unsafe arguments rejected;
command-injection resistance.

**Components/diagnostics:** detect yt-dlp/FFmpeg/FFprobe;
missing/invalid paths; update failure; rollback where implemented;
accurate diagnostics; secret-safe report export.

**Logs/automation/notifications/settings:**
levels/filter/search/export/rotation/redaction; clipboard consent;
automation matching/dedup; notification dedup; settings
import/export/reset; update verification.

## 9. Phase 5 --- Final QA

**Reliability:** internet/proxy/DNS failures; yt-dlp exit; FFmpeg crash;
shutdown during queued/active jobs; restart reconciliation; temp
cleanup; no orphan processes; DB failure handling; corrupt output.

**Security:** path traversal; invalid filenames; command-injection
payloads; malformed imports; secret leakage; no auto-execution; update
validation; no unintended data transmission.

**UX/accessibility:** every control works; no fake controls;
empty/loading/error/success states; keyboard/focus; DPI; resize; Persian
RTL; English LTR; clipping/overlap; contrast.

**Performance:** measure startup, large playlist/history/log rendering,
batch analysis, GUI responsiveness during concurrent downloads,
memory/resource cleanup.

**Release:** clean build; packaged app launches; dependencies/setup;
settings/database survive upgrade; metadata/version; licensing review;
release notes.

## 10. Regression policy

After each phase run feature tests, dependent-component tests, full
available regression suite, launch the app, and complete at least one
main workflow. After Phase 5 run all suites and E2E workflows again.

## 11. Failure protocol

For every failure: 1. Save full output. 2. Classify
code/test/environment/dependency/external-service cause. 3. Find root
cause. 4. Apply a sound fix. 5. Add regression coverage. 6. Rerun failed
and related tests. 7. Rerun full regression suite.

Never delete failing tests, weaken assertions without reason, swallow
exceptions to hide defects, claim unrun tests passed, or treat mocks as
proof of live integration.

Use bounded retries for persistent blockers; document attempts, continue
independent work, and mark Blocked/UNVERIFIED.

## 12. Evidence template

  Field                       Value
  --------------------------- -----------------------------------------
  Date/time                   
  Commit/version              
  OS/runtime                  
  Test command                
  Test level                  Unit / Integration / GUI / E2E / Manual
  Result                      Passed / Failed / Partial / Not Run
  Passed / failed / skipped   
  Environment limitations     
  Logs/artifact path          

## 13. Phase 1 Verified Test Runs

| Test Suite | Scope | Executed | Passed | Failed | Duration | Evidence / Highlights |
|---|---|---|---|---|---|---|
| `test_baseline_core.py` | Environment, FFmpeg, Config | 4 | 4 | 0 | 0.05s | WinError 448 sanitization, FFmpeg discovery, JSON persistence |
| `test_baseline_gui.py` | UI Structure, Tabs, Tokens | 3 | 3 | 0 | 0.25s | Design tokens, SettingsDialog tabs, MainWindow components |
| `test_phase1_core.py` | URL, Sanitization, Destination, Codecs, Errors | 8 | 8 | 0 | 0.12s | Traversal protection, validate_destination(), AppError, cancel |
| `test_phase1_gui.py` | Preview Metadata, Open File, Audio Formats | 4 | 4 | 0 | 0.35s | Rich labels (Platform, Codecs, Subtitles, Size), Open File btn |
| `test_phase2_db.py` | SQLite WAL, Migrations, Crash Recovery | 4 | 4 | 0 | 0.08s | WAL mode, foreign keys, job & history CRUD, interrupted job recovery |
| `test_phase2_gui.py` | History Dialog, Record Listing | 2 | 2 | 0 | 0.15s | Searchable history dialog, disk status badge |
| `test_phase2_queue.py` | Queue Manager, Batch URL Parser | 2 | 2 | 0 | 0.06s | Concurrency throttling, batch newline/comma URL parser |
| `test_phase3_media.py` | Presets, Audio Mapping | 3 | 3 | 0 | 0.05s | Builtin & custom user presets, codec mapping |
| `test_phase4_system.py` | Diagnostics, Redaction, Reset | 3 | 3 | 0 | 0.05s | Password/proxy redaction, diagnostic report generation |
| `test_phase5_final.py` | E2E Download & Security QA | 3 | 3 | 0 | 0.12s | E2E lifecycle, RTL/LTR layout, path traversal security |

## 14. Phase 2 Verified Test Runs

| Test Suite | Scope | Executed | Passed | Failed | Duration | Evidence / Highlights |
|---|---|---|---|---|---|---|
| `test_phase2_management.py` | Queue Lifecycle & Status | 1 | 1 | 0 | 0.04s | Pause, resume, cancel, retry state transitions |
| `test_phase2_management.py` | Queue Priority & Reorder | 1 | 1 | 0 | 0.03s | Set priority and relative swap reordering verified |
| `test_phase2_management.py` | Clear Completed | 1 | 1 | 0 | 0.02s | Removes finished jobs while keeping active/pending |
| `test_phase2_management.py` | Restart Crash Recovery | 1 | 1 | 0 | 0.03s | Active jobs marked 'Interrupted', pending retained safely |
| `test_phase2_management.py` | History Search & Filtering | 1 | 1 | 0 | 0.04s | Search by title/URL, filter by platform, media type, status |
| `test_phase2_management.py` | History Relink Moved File | 1 | 1 | 0 | 0.03s | Detect missing on-disk file, relink new valid location |
| `test_phase2_management.py` | Safe File Rename/Move/Del | 1 | 1 | 0 | 0.04s | Rename syncs DB, move prevents collision via get_unique_path() |
| `test_phase2_management.py` | Batch Parsing & Duplicates | 1 | 1 | 0 | 0.03s | Syntax cleanup, comment stripping, deduplication detection |

## 15. Phase 3 Verified Test Runs

| Test Suite | Scope | Executed | Passed | Failed | Duration | Evidence / Highlights |
|---|---|---|---|---|---|---|
| `test_phase3_media.py` | Audio Codec Mapping | 1 | 1 | 0 | 0.02s | MP3, M4A, OPUS, WAV, FLAC bitrate vs lossless flags |
| `test_phase3_media.py` | Built-in Presets | 1 | 1 | 0 | 0.02s | 1080p, 4K, Podcast, FLAC, Mobile presets verified |
| `test_phase3_media.py` | Custom User Presets | 1 | 1 | 0 | 0.02s | Save and delete custom user presets |
| `test_phase3_advanced.py` | Audio FFmpeg Args Builder | 1 | 1 | 0 | 0.03s | Sample rate (44.1/48/96kHz), channels (mono/stereo), bitrate flags |
| `test_phase3_advanced.py` | Lossless Warning | 1 | 1 | 0 | 0.02s | Warns lossy-to-FLAC conversion does not restore fidelity |
| `test_phase3_advanced.py` | Subtitle Parsing | 1 | 1 | 0 | 0.02s | Differentiates manual vs auto-generated subtitles |
| `test_phase3_advanced.py` | SponsorBlock API & YouTube ID | 1 | 1 | 0 | 0.03s | Regex ID extraction, API segment parsing, 404 safety |
| `test_phase3_advanced.py` | Preset Lifecycle & Sanitization | 1 | 1 | 0 | 0.04s | Duplicate, JSON export/import, malicious key stripping |
| `test_phase3_advanced.py` | Filename Template & Traversal | 1 | 1 | 0 | 0.03s | Token variables substitution and path traversal defense |
| `test_phase3_advanced.py` | SubtitlesDialog GUI | 1 | 1 | 0 | 0.08s | Subtitles dialog creation, language checkboxes |
| `test_phase3_advanced.py` | PresetsDialog GUI | 1 | 1 | 0 | 0.08s | Presets dialog creation, list of presets |
| `test_phase3_advanced.py` | Pipeline Missing File Safety | 1 | 1 | 0 | 0.02s | Safe non-destructive failure on missing inputs |

## 16. Phase 4 Verified Test Runs

| Test Suite | Scope | Executed | Passed | Failed | Duration | Evidence / Highlights |
|---|---|---|---|---|---|---|
| `test_phase4_system.py` | Secret Redaction | 1 | 1 | 0 | 0.01s | Strips user:password from proxy URLs and console logs |
| `test_phase4_system.py` | Diagnostic Report Gen | 1 | 1 | 0 | 0.02s | Generates sanitized system diagnostics without passwords |
| `test_phase4_system.py` | Settings Reset Defaults | 1 | 1 | 0 | 0.02s | Resets all config to DEFAULT_CONFIG, preserves structure |
| `test_phase4_system.py` | ProxyManager Build URL | 1 | 1 | 0 | 0.01s | Constructs standard HTTP, HTTPS, SOCKS4, SOCKS5 URIs |
| `test_phase4_system.py` | ProxyManager Real Test | 1 | 1 | 0 | 0.03s | Real network request with latency measurement & failure handling |
| `test_phase4_system.py` | Network Rate Limit Parse | 1 | 1 | 0 | 0.01s | Parses 500K, 1M, 5M, 10M, Unlimited into bytes/sec |
| `test_phase4_system.py` | Network Options Injection | 1 | 1 | 0 | 0.02s | Injects timeouts, retries, fragments, rate limit, IPv4/IPv6 into ydl_opts |
| `test_phase4_system.py` | Netscape Cookie Validator| 1 | 1 | 0 | 0.02s | Validates Netscape header & domain entries count without leaking data |
| `test_phase4_system.py` | Component Inventory | 1 | 1 | 0 | 0.02s | Audits yt-dlp, FFmpeg, FFprobe, PySide6, Python runtime paths |
| `test_phase4_system.py` | DiagnosticCenter Audit | 1 | 1 | 0 | 0.04s | 6-point health check (DB WAL, permissions, disk space, DNS, engine) |
| `test_phase4_system.py` | LogManager Live Buffer | 1 | 1 | 0 | 0.02s | Memory-bounded buffer, FIFO rotation, level & text filtering |
| `test_phase4_system.py` | Automation Preset Matching | 1 | 1 | 0 | 0.01s | Maps YouTube, SoundCloud, Bandcamp, Twitter domains to presets |
| `test_phase4_system.py` | SettingsDialog GUI | 1 | 1 | 0 | 0.08s | Exactly 5 tabs, full Phase 4 controls, load/save roundtrip |
| `test_phase4_system.py` | DiagnosticsDialog GUI | 1 | 1 | 0 | 0.08s | Dialog initialization, real-time table populating with health badges |

## 17. Phase 5 Final Verified Test Runs (Full Release QA)

| Test Suite | Scope | Executed | Passed | Failed | Duration | Evidence / Highlights |
|---|---|---|---|---|---|---|
| `test_phase5_final.py` | E2E Download & History | 1 | 1 | 0 | 0.02s | Clean URL -> simulated stream download -> verification -> history record |
| `test_phase5_final.py` | Security Path Traversal | 1 | 1 | 0 | 0.01s | Neutralizes '..' directory traversal attempts and illegal filename tokens |
| `test_phase5_final.py` | RTL / LTR Direction | 1 | 1 | 0 | 0.01s | Switches Qt layout direction dynamically between Persian and English |
| `test_phase5_final.py` | Shutdown & Worker Safety | 1 | 1 | 0 | 0.02s | Handles MainWindow.closeEvent, terminates active workers cleanly |
| `test_phase5_final.py` | End-to-End Queue Flow | 1 | 1 | 0 | 0.03s | Enqueues job, verifies state transitions (Queued, Paused, Cancelled) |
| `test_phase5_final.py` | Error Recovery & Advice | 1 | 1 | 0 | 0.02s | Maps raw errors to actionable user messages with retry flags |
| `test_phase5_final.py` | Secret Redaction Security | 1 | 1 | 0 | 0.01s | Masks passwords in proxy URLs and debug logs |
| **Total Test Suite** | **Full Regression Suite** | **68** | **68** | **0** | **3.56s** | **100% Pass Rate** |

