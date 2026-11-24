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

Final QA must distinguish Passed, Failed, Not Run, Blocked, and
UNVERIFIED.
