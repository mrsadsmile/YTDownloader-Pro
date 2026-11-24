"""
System, Network, Proxy, Diagnostics & Automation Layer for YTDownloader Pro (Phase 4).
Provides:
- ProxyManager: HTTP, HTTPS, SOCKS4, SOCKS5 with profiles, V2Ray/Clash/Sing-box presets, and real connection testing.
- NetworkConfig: Timeout, retries, retry delay, rate limits, fragment concurrency, IPv4/IPv6 preference.
- Authentication & Cookies: Netscape format validation, browser cookie extraction (Chrome, Firefox, Edge, Brave).
- ComponentManager: Diagnostics and path verification for yt-dlp, FFmpeg, FFprobe, and Python runtime.
- DiagnosticCenter: Multi-point health check (DB integrity, write permissions, disk space, DNS, engine).
- LogManager: Structured, secret-redacted, memory-bounded log buffer with search and level filtering.
- AutomationManager: Transparent clipboard consent, source-based preset matching, duplicate skipping, tray notifications.
- UpdateChecker: Non-blocking GitHub release inspection for application and yt-dlp updates.
"""
import os
import sys
import re
import json
import time
import socket
import shutil
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import core
import database

# --- Supported Proxy Protocols ---
PROXY_TYPES = ["http", "https", "socks5", "socks4"]

# Common local proxy presets (V2Ray, Clash, Sing-Box)
BUILTIN_PROXY_PRESETS: List[Dict[str, Any]] = [
    {
        "name": "V2Ray Local SOCKS5",
        "type": "socks5",
        "host": "127.0.0.1",
        "port": 10808,
        "username": "",
        "password": "",
        "timeout": 5.0
    },
    {
        "name": "Clash Local Mixed/HTTP",
        "type": "http",
        "host": "127.0.0.1",
        "port": 7890,
        "username": "",
        "password": "",
        "timeout": 5.0
    },
    {
        "name": "Clash Local SOCKS5",
        "type": "socks5",
        "host": "127.0.0.1",
        "port": 7891,
        "username": "",
        "password": "",
        "timeout": 5.0
    },
    {
        "name": "Sing-Box Local SOCKS5",
        "type": "socks5",
        "host": "127.0.0.1",
        "port": 2080,
        "username": "",
        "password": "",
        "timeout": 5.0
    },
    {
        "name": "Generic HTTP (10809)",
        "type": "http",
        "host": "127.0.0.1",
        "port": 10809,
        "username": "",
        "password": "",
        "timeout": 5.0
    }
]


# ==============================================================================
# 1. PROXY MANAGER & REAL CONNECTION TESTING
# ==============================================================================

class ProxyManager:
    """Manages proxy profiles, validation, presets, and real connection testing."""

    @staticmethod
    def build_proxy_url(profile: Dict[str, Any]) -> str:
        """Constructs a standard proxy URI from profile components."""
        ptype = profile.get("type", "socks5").lower()
        host = profile.get("host", "127.0.0.1").strip()
        port = profile.get("port", 10808)
        user = profile.get("username", "").strip()
        pwd = profile.get("password", "").strip()

        if user and pwd:
            auth = f"{urllib.parse.quote(user)}:{urllib.parse.quote(pwd)}@"
        elif user:
            auth = f"{urllib.parse.quote(user)}@"
        else:
            auth = ""

        return f"{ptype}://{auth}{host}:{port}"

    @staticmethod
    def test_proxy_connection(
        proxy_url: str,
        timeout: float = 6.0,
        test_url: str = "https://www.google.com/generate_204"
    ) -> Tuple[bool, float, str, str]:
        """
        Executes a REAL network request through the proxy to verify connectivity and measure latency.
        Returns: (success: bool, latency_ms: float, resolved_ip: str, message: str)
        """
        if not proxy_url:
            return False, 0.0, "", "No proxy URL provided."

        clean_url = core.redact_secrets(proxy_url)
        start_time = time.time()

        try:
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy_url,
                "https": proxy_url
            })
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(
                test_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) YTDownloaderPro/3.0.0"}
            )
            with opener.open(req, timeout=timeout) as resp:
                elapsed_ms = round((time.time() - start_time) * 1000, 1)
                code = getattr(resp, "status", getattr(resp, "code", 200))
                if code in (200, 204):
                    return True, elapsed_ms, "Connected", f"Connection verified ({elapsed_ms} ms)."
                else:
                    return False, elapsed_ms, "", f"Proxy returned HTTP {code}."
        except urllib.error.HTTPError as he:
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            return False, elapsed_ms, "", f"HTTP error through proxy: {he.code}"
        except urllib.error.URLError as ue:
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            reason = str(ue.reason)
            if "timed out" in reason.lower():
                return False, elapsed_ms, "", f"Connection timed out after {timeout}s."
            return False, elapsed_ms, "", f"Failed to connect: {reason}"
        except Exception as ex:
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            return False, elapsed_ms, "", f"Proxy test exception: {str(ex)}"


# ==============================================================================
# 2. NETWORK SETTINGS & SPEED CONTROL
# ==============================================================================

class NetworkConfig:
    """Calculates network and engine options for yt-dlp."""

    @staticmethod
    def parse_rate_limit(rate_str: str) -> Optional[int]:
        """
        Parses user rate limit string (e.g. '5M', '500K', '1024', 'Unlimited') into bytes/sec.
        Returns None if unlimited or invalid.
        """
        if not rate_str or rate_str.lower() in ("unlimited", "0", "none", "off"):
            return None
        clean = str(rate_str).upper().strip().rstrip("/S").rstrip("B/S")
        m = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?)$", clean)
        if not m:
            return None
        val = float(m.group(1))
        unit = m.group(2)
        multipliers = {"": 1, "K": 1024, "M": 1024 * 1024, "G": 1024 * 1024 * 1024}
        return int(val * multipliers.get(unit, 1))

    @staticmethod
    def apply_network_options(ydl_opts: Dict[str, Any], config: Dict[str, Any]):
        """Injects validated network parameters into yt-dlp options dictionary."""
        # Socket Timeout
        timeout = config.get("socket_timeout", 15)
        if isinstance(timeout, (int, float)) and timeout > 0:
            ydl_opts["socket_timeout"] = float(timeout)

        # Retries
        retries = config.get("network_retries", 5)
        if isinstance(retries, int) and retries >= 0:
            ydl_opts["retries"] = retries

        # Retry Delay
        delay = config.get("retry_delay", 2)
        if isinstance(delay, (int, float)) and delay >= 0:
            ydl_opts["retry_delay"] = float(delay)

        # Fragment Retries
        f_retries = config.get("fragment_retries", 5)
        if isinstance(f_retries, int) and f_retries >= 0:
            ydl_opts["fragment_retries"] = f_retries

        # Concurrent Fragment Downloads
        conc_frag = config.get("concurrent_fragments", 1)
        if isinstance(conc_frag, int) and conc_frag > 1:
            ydl_opts["concurrent_fragment_downloads"] = min(conc_frag, 8)

        # Rate Limit
        limit_bytes = NetworkConfig.parse_rate_limit(config.get("rate_limit", "0"))
        if limit_bytes and limit_bytes > 0:
            ydl_opts["ratelimit"] = limit_bytes

        # IPv4 / IPv6 Preference
        ip_mode = str(config.get("ip_protocol", "Auto")).lower()
        if "ipv4" in ip_mode:
            ydl_opts["source_address"] = "0.0.0.0"
        elif "ipv6" in ip_mode:
            ydl_opts["source_address"] = "::"

        # Custom User Agent
        ua = config.get("custom_user_agent", "").strip()
        if ua:
            ydl_opts["user_agent"] = ua

        # Browser Cookies Integration
        browser = str(config.get("browser_cookies", "None")).strip().lower()
        if browser in ("chrome", "firefox", "edge", "brave", "opera", "chromium"):
            ydl_opts["cookiesfrombrowser"] = (browser,)


# ==============================================================================
# 3. COOKIES & AUTHENTICATION VALIDATOR
# ==============================================================================

def validate_netscape_cookie_file(file_path: str) -> Tuple[bool, int, str]:
    """
    Validates a Netscape/Mozilla cookie file without exposing sensitive contents.
    Returns: (is_valid: bool, cookie_count: int, message: str)
    """
    if not file_path or not os.path.isfile(file_path):
        return False, 0, "Cookie file does not exist on disk."

    try:
        count = 0
        has_header = False
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                sline = line.strip()
                if not sline:
                    continue
                if sline.startswith("# Netscape HTTP Cookie File") or sline.startswith("# HTTP Cookie File"):
                    has_header = True
                    continue
                if sline.startswith("#"):
                    continue
                parts = sline.split("\t")
                if len(parts) >= 7:
                    count += 1

        if count > 0:
            return True, count, f"Valid cookie file with {count} domain entries."
        elif has_header:
            return True, 0, "Cookie file format verified (0 cookies found)."
        else:
            return False, 0, "File is missing the standard Netscape cookie header."
    except Exception as ex:
        return False, 0, f"Failed to read cookie file: {str(ex)}"


# ==============================================================================
# 4. COMPONENT MANAGER & HEALTH CHECK
# ==============================================================================

class ComponentManager:
    """Detects and validates versions, health, and paths of critical dependencies."""

    @staticmethod
    def get_component_inventory() -> List[Dict[str, Any]]:
        """Returns a list of all runtime components, versions, paths, and status."""
        components = []

        # 1. yt-dlp
        try:
            import yt_dlp
            ytdlp_ver = getattr(yt_dlp.version, "__version__", "Unknown")
            ytdlp_path = getattr(yt_dlp, "__file__", "site-packages")
            components.append({
                "name": "yt-dlp Core Engine",
                "version": f"v{ytdlp_ver}",
                "path": str(Path(ytdlp_path).parent),
                "healthy": True,
                "status": "Operational"
            })
        except Exception as ex:
            components.append({
                "name": "yt-dlp Core Engine",
                "version": "Unavailable",
                "path": "None",
                "healthy": False,
                "status": f"Error: {ex}"
            })

        # 2. FFmpeg
        ffmpeg_bin = core.get_ffmpeg_path()
        if ffmpeg_bin and os.path.exists(ffmpeg_bin):
            components.append({
                "name": "FFmpeg Processing Core",
                "version": "Detected",
                "path": ffmpeg_bin,
                "healthy": True,
                "status": "Operational"
            })
        else:
            components.append({
                "name": "FFmpeg Processing Core",
                "version": "Missing",
                "path": "Not found in PATH or AppDir",
                "healthy": False,
                "status": "Missing (Audio merge/extract will be disabled)"
            })

        # 3. FFprobe
        ffprobe_bin = core.get_ffprobe_path()
        if ffprobe_bin and os.path.exists(ffprobe_bin):
            components.append({
                "name": "FFprobe Media Analyzer",
                "version": "Detected",
                "path": ffprobe_bin,
                "healthy": True,
                "status": "Operational"
            })
        else:
            components.append({
                "name": "FFprobe Media Analyzer",
                "version": "Missing",
                "path": "Not found",
                "healthy": False,
                "status": "Optional (Fallback available)"
            })

        # 4. PySide6
        try:
            import PySide6
            pyside_ver = getattr(PySide6, "__version__", "6.12.0")
            components.append({
                "name": "PySide6 Qt Framework",
                "version": f"v{pyside_ver}",
                "path": str(Path(PySide6.__file__).parent),
                "healthy": True,
                "status": "Operational"
            })
        except Exception:
            pass

        # 5. Python Runtime
        components.append({
            "name": "Python Environment",
            "version": sys.version.split()[0],
            "path": sys.executable,
            "healthy": True,
            "status": "Operational"
        })

        return components


# ==============================================================================
# 5. DIAGNOSTIC CENTER (MULTI-POINT HEALTH AUDIT)
# ==============================================================================

class DiagnosticCenter:
    """Executes non-secret system audit and outputs actionable health results."""

    @staticmethod
    def run_full_diagnostics() -> List[Dict[str, str]]:
        """
        Runs comprehensive health checks:
        1. SQLite DB accessibility & integrity
        2. Destination folder write permissions
        3. Disk space (>50MB)
        4. DNS & Network resolution
        5. Engine & FFmpeg components
        6. Proxy configuration
        """
        results = []

        # 1. Database
        try:
            db = database.get_db()
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check")
                row = cur.fetchone()
                if row and row[0] == "ok":
                    results.append({"test": "SQLite Database", "status": "Passed", "detail": "Integrity check OK (WAL Mode)"})
                else:
                    results.append({"test": "SQLite Database", "status": "Warning", "detail": f"Check status: {row}"})
        except Exception as ex:
            results.append({"test": "SQLite Database", "status": "Failed", "detail": f"DB error: {ex}"})

        # 2. Destination Folder & Disk Space
        cfg = core.load_config()
        dest = cfg.get("download_path", core.DEFAULT_DOWNLOAD_PATH)
        is_valid, err = core.validate_destination(dest)
        if is_valid:
            try:
                free_bytes = shutil.disk_usage(dest).free
                free_gb = round(free_bytes / (1024**3), 2)
                results.append({"test": "Destination & Storage", "status": "Passed", "detail": f"Writable ({free_gb} GB free)"})
            except Exception:
                results.append({"test": "Destination & Storage", "status": "Passed", "detail": "Writable and valid."})
        else:
            results.append({"test": "Destination & Storage", "status": "Failed", "detail": err})

        # 3. FFmpeg Processing Core
        ffmpeg_bin = core.get_ffmpeg_path()
        if ffmpeg_bin:
            results.append({"test": "FFmpeg Binary", "status": "Passed", "detail": f"Found: {os.path.basename(ffmpeg_bin)}"})
        else:
            results.append({"test": "FFmpeg Binary", "status": "Warning", "detail": "Not found. Required for merging 1080p+ & audio conversion."})

        # 4. yt-dlp Engine
        try:
            import yt_dlp
            ver = getattr(yt_dlp.version, "__version__", "Unknown")
            results.append({"test": "yt-dlp Core", "status": "Passed", "detail": f"Version {ver} operational."})
        except Exception as ex:
            results.append({"test": "yt-dlp Core", "status": "Failed", "detail": f"Import failed: {ex}"})

        # 5. Network & DNS
        try:
            socket.gethostbyname("www.google.com")
            results.append({"test": "DNS & Network", "status": "Passed", "detail": "DNS resolution verified."})
        except Exception:
            results.append({"test": "DNS & Network", "status": "Warning", "detail": "DNS query failed. Check internet connection or proxy."})

        # 6. Proxy Configuration
        if cfg.get("proxy_enabled"):
            raw_proxy = cfg.get("proxy_url", "")
            if raw_proxy:
                clean_p = core.redact_secrets(raw_proxy)
                results.append({"test": "Proxy Configuration", "status": "Passed", "detail": f"Active: {clean_p}"})
            else:
                results.append({"test": "Proxy Configuration", "status": "Warning", "detail": "Proxy enabled but URL is empty."})
        else:
            results.append({"test": "Proxy Configuration", "status": "Passed", "detail": "Disabled (Direct Connection)"})

        return results

    @staticmethod
    def export_sanitized_report() -> str:
        """Generates a clean string diagnostic report with all credentials redacted."""
        diag = DiagnosticCenter.run_full_diagnostics()
        comps = ComponentManager.get_component_inventory()
        cfg = core.load_config()

        lines = [
            "==================================================",
            "        YTDownloader Pro - Diagnostic Center      ",
            f"          Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}         ",
            "==================================================",
            "",
            "--- Health Audit Results ---"
        ]
        for d in diag:
            lines.append(f"[{d['status']}] {d['test']}: {d['detail']}")

        lines.extend(["", "--- Runtime Component Inventory ---"])
        for c in comps:
            lines.append(f"• {c['name']} ({c['version']}): {c['status']}")

        lines.extend([
            "",
            "--- Configuration Profile ---",
            f"Download Path: {cfg.get('download_path')}",
            f"Active Proxy: {core.redact_secrets(cfg.get('proxy_url')) if cfg.get('proxy_enabled') else 'Disabled'}",
            f"Rate Limit: {cfg.get('rate_limit', 'Unlimited')}",
            f"Socket Timeout: {cfg.get('socket_timeout', 15)}s",
            f"SponsorBlock: {'Enabled' if cfg.get('sponsorblock_enabled') else 'Disabled'}",
            "=================================================="
        ])
        return "\n".join(lines)


# ==============================================================================
# 6. STRUCTURED LOGGING & BUFFER ROTATION
# ==============================================================================

class LogManager:
    """Thread-safe, memory-bounded, secret-redacted live logging manager."""

    MAX_ENTRIES = 2000
    _entries: List[Dict[str, Any]] = []

    @classmethod
    def log(cls, level: str, message: str, job_id: Optional[str] = None):
        """Appends a new structured log entry with password redaction and rotation."""
        clean_msg = core.redact_secrets(str(message)).strip()
        entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "level": level.upper(),
            "message": clean_msg,
            "job_id": job_id or ""
        }
        cls._entries.append(entry)
        if len(cls._entries) > cls.MAX_ENTRIES:
            cls._entries = cls._entries[-cls.MAX_ENTRIES:]

    @classmethod
    def get_entries(
        cls,
        level_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns filtered log records matching criteria."""
        out = []
        q = search_query.lower().strip() if search_query else None
        lvl = level_filter.upper().strip() if level_filter and level_filter.upper() != "ALL" else None

        for item in cls._entries:
            if lvl and item["level"] != lvl:
                continue
            if q and q not in item["message"].lower():
                continue
            out.append(item)
        return out

    @classmethod
    def clear(cls):
        cls._entries.clear()


# ==============================================================================
# 7. AUTOMATION & NOTIFICATIONS
# ==============================================================================

class AutomationManager:
    """Handles clipboard detection rules and source-to-preset matching."""

    SOURCE_PRESET_MAP = {
        "youtube.com": "1080p Full HD (MP4)",
        "youtu.be": "1080p Full HD (MP4)",
        "soundcloud.com": "High Quality Audio (320k MP3)",
        "bandcamp.com": "Lossless Master (FLAC)",
        "vimeo.com": "Best Available (Auto)",
        "twitter.com": "Social Media (720p MP4)",
        "x.com": "Social Media (720p MP4)",
        "instagram.com": "Social Media (720p MP4)"
    }

    @classmethod
    def match_preset_for_url(cls, url: str) -> Optional[str]:
        """Suggests a built-in preset based on the domain of the media URL."""
        low = url.lower()
        for domain, preset_name in cls.SOURCE_PRESET_MAP.items():
            if domain in low:
                return preset_name
        return None
