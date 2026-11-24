# YTDownloader Pro --- Bug Fix Log & Remediation History

This log records all defects identified, diagnosed, remediated, and verified during autonomous acceptance testing and QA review.

---

### BUG-001: Qt C++ Static Destructor Conflict on Python 3.14 Exit
- **Discovery:** Automated test runner crashed or hung intermittently on Python 3.14 during `tearDown` of GUI widgets.
- **Severity:** Medium (Test Reliability / Developer Experience).
- **Affected Feature:** Test runner lifecycle in `tests/test_baseline_gui.py`.
- **Root Cause:** C++ Qt objects created in Python tests were collected by Python's GC after QApplication began destruction.
- **Files Changed:** `tests/test_baseline_gui.py`.
- **Fix:** Added explicit `widget.close()`, `widget.deleteLater()`, and `QApplication.processEvents()` inside `tearDown`.
- **Tests Added/Run:** `test_main_window_components`, `test_settings_dialog_tabs`.
- **Retest Result:** PASSED (Clean exit on Python 3.14.7).
- **Caveat:** None.

---

### BUG-002: Insufficient Consecutive Dot Sanitization in Path Traversal Defense
- **Discovery:** Security audit identified that filenames containing `..` (e.g. `../../etc/passwd`) were partially stripped but could form traversal tokens if nested.
- **Severity:** High (Security / Filesystem Traversal).
- **Affected Feature:** `core.sanitize_filename()`.
- **Root Cause:** Slashes were replaced with `_`, but consecutive dots `..` were not explicitly normalized into non-traversing underscores.
- **Files Changed:** `core.py`.
- **Fix:** Added regex `re.sub(r'\.{2,}', '_', name)` before stripping trailing periods.
- **Tests Added/Run:** `tests/test_phase1_core.py::test_filename_sanitization`, `tests/test_phase5_final.py::test_security_path_traversal_and_injection`.
- **Retest Result:** PASSED (All `..` replaced with `_`).
- **Caveat:** None.

---

### BUG-003: PySide6 Framework Version Omitted in System Diagnostic Report
- **Discovery:** Initial diagnostic output listed Python, OS, yt-dlp, and FFmpeg, but lacked Qt framework version.
- **Severity:** Low (Diagnostics / Observability).
- **Affected Feature:** `core.generate_diagnostic_report()`.
- **Root Cause:** PySide6 version string was not queried in the report formatter.
- **Files Changed:** `core.py`.
- **Fix:** Added `PySide6 Framework Version: {getattr(sys.modules.get('PySide6'), '__version__', '6.12.0')}`.
- **Tests Added/Run:** `tests/test_phase4_system.py::test_diagnostic_report_generation`.
- **Retest Result:** PASSED.
- **Caveat:** None.

---

### BUG-004: IP Protocol Matching Failed on Human-Readable Dropdown Labels
- **Discovery:** Settings dropdown uses `"IPv4 only"` and `"IPv6 only"`, while `network_system.NetworkConfig.apply_network_options` checked `if ip_mode == "ipv4"`.
- **Severity:** Medium (Network Settings Integration).
- **Affected Feature:** `network_system.NetworkConfig.apply_network_options()`.
- **Root Cause:** Strict equality test on lowercase string failed when label contained `"only"`.
- **Files Changed:** `network_system.py`.
- **Fix:** Changed check to `if "ipv4" in ip_mode: ydl_opts["source_address"] = "0.0.0.0"` and `elif "ipv6" in ip_mode: ydl_opts["source_address"] = "::"`.
- **Tests Added/Run:** `tests/test_phase4_system.py::test_network_config_apply_options`.
- **Retest Result:** PASSED.
- **Caveat:** None.

---

### BUG-005: Queue Manager Rejected Keyword Argument Ingestion
- **Discovery:** `QueueManager.enqueue_job` only accepted a dictionary `params` argument, failing with `TypeError` when called with kwargs from UI views.
- **Severity:** Medium (Queue Dispatching & API Ergonomics).
- **Affected Feature:** `queue_manager.QueueManager.enqueue_job()`.
- **Root Cause:** Signature lacked `**kwargs` support.
- **Files Changed:** `queue_manager.py`.
- **Fix:** Updated signature to `enqueue_job(self, params=None, auto_start=True, **kwargs)`, supporting both dictionary and keyword arguments seamlessly.
- **Tests Added/Run:** `tests/test_phase5_final.py::test_end_to_end_queue_workflow`.
- **Retest Result:** PASSED.
- **Caveat:** None.

---

### BUG-006: Inconsistent Destination Field Key Mapping Across Database & Queue
- **Discovery:** Callers used varied parameter names (`destination`, `download_path`, `output_path`). `database.py` only saved `data.get("output_path")`, causing recovered or restarted jobs to lose their destination directory.
- **Severity:** High (Data Integrity & Crash Recovery).
- **Affected Feature:** `database.JobRepository.add_job()`, `queue_manager.QueueManager._start_worker()`.
- **Root Cause:** No normalization across the three equivalent parameter keys.
- **Files Changed:** `database.py`, `queue_manager.py`.
- **Fix:** Normalized destination fallback in `database.py`: `data.get("output_path") or data.get("destination") or data.get("download_path") or str(Path.home() / "Downloads")`, and updated `_start_worker()` in `queue_manager.py`.
- **Tests Added/Run:** `tests/test_phase2_db.py::test_destination_field_mapping`.
- **Retest Result:** PASSED.
- **Caveat:** None.

---

### BUG-007: Unguarded Application Shutdown and Worker Lifecycle
- **Discovery:** Closing the main window during an active download abruptly terminated the process, leaving temporary files and orphaned sub-workers.
- **Severity:** High (Process Lifecycle & Reliability).
- **Affected Feature:** `main_window.MainWindow.closeEvent()`.
- **Root Cause:** `closeEvent` was not implemented on `MainWindow`.
- **Files Changed:** `main_window.py`.
- **Fix:** Implemented `closeEvent` with active job confirmation dialog, graceful cancellation of `InspectWorker`, `DownloadWorker`, and queue tasks, and bounded wait timeouts.
- **Tests Added/Run:** `tests/test_phase5_final.py::test_safe_shutdown_close_event`.
- **Retest Result:** PASSED.
- **Caveat:** None.

---

### BUG-008: Missing Visual Empty State Indicators Across Tables
- **Discovery:** Queue, History, and Files tables rendered completely blank when empty, providing no onboarding guidance to new users.
- **Severity:** Low (Usability & First Impression).
- **Affected Feature:** `queue_view.py`, `history_view.py`, `files_view.py`.
- **Root Cause:** No placeholder widgets toggled when item counts reached zero.
- **Files Changed:** `queue_view.py`, `history_view.py`, `files_view.py`.
- **Fix:** Added centered, styled `lbl_empty` guidance labels that toggle dynamically based on row count.
- **Tests Added/Run:** Full GUI test suite.
- **Retest Result:** PASSED.
- **Caveat:** None.
