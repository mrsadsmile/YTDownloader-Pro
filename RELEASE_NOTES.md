# YTDownloader Pro v2.6.0 --- Official Release Notes

**Release Date:** November 24, 2026  
**Architecture:** Windows 10/11 x64  
**Packaging:** Standalone Installer (`YTDownloader_Setup_v2.6.0.exe`)  
**Core Technologies:** Python 3.14, PySide6 6.12, yt-dlp 2026.10.26, FFmpeg N-128251  

---

## 🌟 Highlights & Overview

YTDownloader Pro v2.6.0 is a modern, lightweight desktop media utility engineered according to strict UI/UX and architectural guidelines. It delivers a refined dark Graphite & Slate aesthetic, responsive controls, thread-safe background workers, and crash-safe SQLite persistence.

---

## 🚀 Key Features by Phase

### 1. Core Engine & Download Experience
- **Smart URL Analysis & Cleaning:** Automatically strips social tracking and referrer parameters (`si`, `feature`, etc.) before analysis.
- **Dynamic Resolution Discovery:** Dynamically detects actual available media resolutions from 360p up to 4K (2160p) without offering fake or unavailable formats.
- **Three Core Download Modes:**
  - **Video Mode:** Merges best available video with optimal audio stream into MP4, MKV, or WEBM.
  - **Audio Only Mode:** Extracts audio tracks directly into MP3, M4A, OPUS, WAV, or FLAC with user-selectable bitrates.
  - **Dual Mode:** Downloads the pristine full-resolution video AND extracts an independent standalone high-bitrate MP3 in one operation.
- **Strict Output Verification:** Guarantees media files exist and have non-zero file sizes on disk before reporting success.
- **Structured Error Model:** Maps low-level exceptions into clear, actionable user messages with retryability flags.

### 2. Download Management & Persistence
- **Crash-Safe SQLite Database:** Operates with Write-Ahead Logging (WAL) and automatic versioned schema migrations (`app_data.db`).
- **Crash & Interruption Recovery:** Automatically reconciles and recovers active jobs if the system is restarted or terminated unexpectedly.
- **Searchable Download History:** Real-time search by title, URL, or path with live disk file verification (detects if files have been moved or deleted).
- **Concurrency & Queue Scheduler:** Enqueues multiple media downloads with configurable worker limits (`max_concurrent`).
- **Batch Ingestion:** Ingests and sanitizes multiline URL batches.

### 3. Media Tools & Post-Processing
- **Comprehensive Codec Support:** Lossless (`flac`, `pcm_s16le`) and lossy (`libmp3lame`, `aac`, `libopus`) audio encoding.
- **Subtitles & Captions:** Discovers available manual and automated subtitles with custom language selection and embedding options.
- **SponsorBlock Integration:** Skips sponsor segments, self-promotions, and intros based on community data.
- **Built-in Presets:** High Quality 1080p, Maximum 4K, Podcast MP3 320k, Lossless FLAC, and Mobile 480p, plus custom user presets CRUD.

### 4. System & Advanced Capabilities
- **Proxy Management:** Presets for V2Ray (HTTP/SOCKS), Clash, and Sing-Box with live latency connection testing.
- **Credential Protection:** Automatic redaction of sensitive credentials and passwords from URLs, diagnostic logs, and terminal outputs.
- **Diagnostic Center:** Generates a sanitized, one-click copyable diagnostic report for rapid troubleshooting.
- **Cookie Support:** Netscape-format cookie file importer for downloading authorized or age-restricted content.
- **Settings Portability:** Export settings to JSON, import configuration, or reset to factory defaults.
- **Internationalization:** Full layout direction switching between English (LTR) and Persian (RTL).

---

## 🛡️ Security & Reliability Fixes
- **Path Traversal Defense:** Sanitizes filenames to eliminate directory traversal sequences (`..`, slashes, illegal Windows characters).
- **Command Injection Prevention:** All FFmpeg invocations use explicit argument lists without raw shell execution.
- **WinError 448 Junction Mitigation:** Sanitizes process `PATH` to eliminate unverified junctions before invoking yt-dlp.

---

## 📋 Quality Assurance Summary
- **Total Automated Tests:** 29 automated unit, GUI, integration, and E2E regression tests.
- **Pass Rate:** 100% (29 passed, 0 failed in 1.17s).
- **Tested Environment:** Windows 11 x64, Python 3.14.7, PySide6 6.12.0.

---

## 📥 Installation

Download `YTDownloader_Setup_v2.6.0.exe` from the [Releases](https://github.com/mrsadsmile/YTDownloader-Pro/releases) page. The installer is completely standalone and bundles all Python, Qt, yt-dlp, and FFmpeg dependencies.
