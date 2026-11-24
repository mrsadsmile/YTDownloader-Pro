"""
Core Engine & Workers for YTDownloader Pro
Integrates yt-dlp, FFmpeg, Proxy support, WinError 448 mitigation, and thread-safe Qt workers.
"""

import os
import sys
import json
import re
import time
import winreg
import shutil
import subprocess
import urllib.request
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from PySide6.QtCore import QThread, Signal, QObject
import yt_dlp

# --- App Directory Resolution ---
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

CONFIG_FILE = APP_DIR / "config.json"
DEFAULT_DOWNLOAD_PATH = str(Path.home() / "Downloads")


def sanitize_environment_path():
    """
    Sanitize process PATH to protect against Windows [WinError 448]:
    'The path cannot be traversed because it contains an untrusted mount point'
    Removes broken or restricted junctions (such as cua-driver) from the process environment.
    """
    clean_paths = []
    for p in os.environ.get("PATH", "").split(os.pathsep):
        p_clean = p.strip().strip('"')
        if not p_clean:
            continue
        try:
            if os.path.isdir(p_clean):
                os.listdir(p_clean)
                clean_paths.append(p_clean)
        except (OSError, PermissionError):
            continue
    os.environ["PATH"] = os.pathsep.join(clean_paths)


def setup_environment():
    """Configures process environment and ensures bundled or system FFmpeg is prioritized."""
    sanitize_environment_path()

    # Priority 1: Check bundled FFmpeg right in application directory
    bundled_ffmpeg = APP_DIR / "ffmpeg.exe"
    if bundled_ffmpeg.exists():
        if str(APP_DIR) not in os.environ["PATH"]:
            os.environ["PATH"] = str(APP_DIR) + os.pathsep + os.environ["PATH"]
        return

    # Priority 2: System PATH
    try:
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            return
    except (OSError, PermissionError):
        pass

    # Priority 3: Reload from Windows User Registry
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
            user_path, _ = winreg.QueryValueEx(k, "Path")
            for p in user_path.split(";"):
                p_s = p.strip().strip('"')
                try:
                    if p_s and os.path.isdir(p_s) and p_s not in os.environ["PATH"]:
                        os.listdir(p_s)
                        os.environ["PATH"] += os.pathsep + p_s
                except (OSError, PermissionError):
                    pass
    except Exception:
        pass

    # Priority 4: WinGet local package directories
    winget_links = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links")
    if os.path.exists(winget_links) and winget_links not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + winget_links

    winget_pkgs = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.exists(winget_pkgs):
        try:
            for root, dirs, files in os.walk(winget_pkgs):
                if "ffmpeg.exe" in files:
                    if root not in os.environ["PATH"]:
                        os.environ["PATH"] += os.pathsep + root
                    break
        except (OSError, PermissionError):
            pass


setup_environment()


def get_ffmpeg_path() -> Optional[str]:
    """Returns verified path to ffmpeg.exe if available."""
    bundled = APP_DIR / "ffmpeg.exe"
    if bundled.exists():
        return str(bundled)
    try:
        return shutil.which("ffmpeg")
    except Exception:
        return None


def get_ffprobe_path() -> Optional[str]:
    bundled = APP_DIR / "ffprobe.exe"
    if bundled.exists():
        return str(bundled)
    try:
        return shutil.which("ffprobe")
    except Exception:
        return None


# --- Validation, Errors & Filesystem Safety ---
@dataclass
class AppError:
    code: str
    user_message: str
    technical_message: str
    component: str = "core"
    retryable: bool = False


def validate_url(url: str) -> Tuple[bool, str]:
    """Validates that the input is a valid HTTP/HTTPS media URL."""
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        return False, "URL must start with http:// or https://"
    try:
        parsed = urllib.parse.urlparse(u)
        if not parsed.netloc or "." not in parsed.netloc:
            return False, "Invalid domain name in URL."
        return True, "Valid URL"
    except Exception as e:
        return False, f"Malformed URL: {e}"


def clean_url(url: str) -> str:
    """Strips social tracking and referrer parameters from media URLs."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        strip_keys = {"si", "feature", "fbclid", "igshid", "utm_source", "utm_medium", "utm_campaign"}
        new_query = {k: v for k, v in query.items() if k not in strip_keys}
        new_query_str = urllib.parse.urlencode(new_query, doseq=True)
        cleaned = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query_str,
            parsed.fragment
        ))
        return cleaned
    except Exception:
        return url.strip()


def sanitize_filename(name: str) -> str:
    """Removes or replaces illegal Windows filesystem characters and path traversal tokens."""
    if not name:
        return "untitled_media"
    cleaned = re.sub(r'\.{2,}', '_', name)
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', cleaned)
    cleaned = re.sub(r'[\x00-\x1f]', '', cleaned)
    cleaned = cleaned.strip('. ')
    return cleaned if cleaned else "untitled_media"


def get_unique_path(directory: Path | str, filename: str) -> Path:
    """Returns a unique non-colliding filepath in directory by appending (1), (2), etc."""
    dir_path = Path(directory)
    base_name = sanitize_filename(filename)
    stem, ext = os.path.splitext(base_name)
    target = dir_path / base_name
    counter = 1
    while target.exists():
        target = dir_path / f"{stem} ({counter}){ext}"
        counter += 1
    return target


def verify_output_file(path: str | Path) -> bool:
    """Verifies that an output file exists on disk and is greater than 0 bytes."""
    if not path:
        return False
    try:
        p = Path(path)
        return p.is_file() and p.stat().st_size > 0
    except (OSError, PermissionError):
        return False


def classify_error(exception: Any) -> AppError:
    """Classifies raw error messages into structured AppError with user message and retry flag."""
    raw = str(exception)
    clean_raw = re.sub(r"ERROR:\s*", "", raw).strip()
    low = clean_raw.lower()

    if any(k in low for k in ["network", "timed out", "connection", "urlopen error", "name or service not known", "getaddrinfo"]):
        return AppError(
            code="ERR_NETWORK",
            user_message="Unable to connect to the source. Check your internet connection or proxy settings.",
            technical_message=clean_raw,
            component="network",
            retryable=True
        )
    elif any(k in low for k in ["proxy", "socks", "tunnel", "127.0.0.1"]):
        return AppError(
            code="ERR_PROXY",
            user_message="Proxy connection failed. Verify your proxy configuration.",
            technical_message=clean_raw,
            component="proxy",
            retryable=True
        )
    elif any(k in low for k in ["private", "sign in", "members-only", "login", "restricted", "confirm your age"]):
        return AppError(
            code="ERR_RESTRICTED",
            user_message="This media is private, age-restricted, or requires user login.",
            technical_message=clean_raw,
            component="extractor",
            retryable=False
        )
    elif any(k in low for k in ["ffmpeg", "ffprobe", "merge", "postprocessor"]):
        return AppError(
            code="ERR_FFMPEG",
            user_message="FFmpeg media processing error. Check FFmpeg installation.",
            technical_message=clean_raw,
            component="ffmpeg",
            retryable=True
        )
    elif any(k in low for k in ["space", "disk", "permission", "access is denied", "winerror 448", "winerror"]):
        return AppError(
            code="ERR_DISK_SPACE",
            user_message="Unable to save the file. Check your download directory permissions and storage.",
            technical_message=clean_raw,
            component="filesystem",
            retryable=True
        )
    elif any(k in low for k in ["canceled", "cancelled", "abort"]):
        return AppError(
            code="ERR_ABORTED",
            user_message="Download was cancelled by user.",
            technical_message=clean_raw,
            component="user",
            retryable=False
        )
    else:
        return AppError(
            code="ERR_UNKNOWN",
            user_message="Operation failed. You can retry or view technical details.",
            technical_message=clean_raw,
            component="core",
            retryable=True
        )


def get_audio_codec_info(audio_format: str) -> Tuple[str, bool]:
    """Returns (ffmpeg_codec_name, uses_bitrate_flag) for an audio format."""
    fmt = (audio_format or "mp3").lower().strip()
    codec_map = {
        "mp3": ("libmp3lame", True),
        "m4a": ("aac", True),
        "opus": ("libopus", True),
        "flac": ("flac", False),
        "wav": ("pcm_s16le", False),
    }
    return codec_map.get(fmt, ("libmp3lame", True))


# --- Built-in & User Presets ---
BUILTIN_PRESETS = {
    "High Quality 1080p (MP4)": {
        "download_type": "Video",
        "video_quality": "1080p",
        "video_format": "MP4",
        "audio_format": "MP3",
        "audio_quality": "320 kbps",
        "embed_metadata": True
    },
    "Maximum 4K Quality": {
        "download_type": "Video",
        "video_quality": "2160p (4K)",
        "video_format": "MKV",
        "audio_format": "MP3",
        "audio_quality": "320 kbps",
        "embed_metadata": True
    },
    "Podcast & Music MP3 (320 kbps)": {
        "download_type": "Audio",
        "audio_format": "MP3",
        "audio_quality": "320 kbps",
        "embed_metadata": True
    },
    "Lossless Master Audio (FLAC)": {
        "download_type": "Audio",
        "audio_format": "FLAC",
        "audio_quality": "Best Available",
        "embed_metadata": True
    },
    "Mobile Compact (480p MP4)": {
        "download_type": "Video",
        "video_quality": "480p",
        "video_format": "MP4",
        "embed_metadata": False
    }
}


def get_presets() -> Dict[str, Dict[str, Any]]:
    """Returns merged built-in presets and user custom presets from config."""
    cfg = load_config()
    presets = dict(BUILTIN_PRESETS)
    user_presets = cfg.get("user_presets", {})
    if isinstance(user_presets, dict):
        presets.update(user_presets)
    return presets


def save_user_preset(name: str, preset_dict: Dict[str, Any]):
    """Saves a custom user preset into configuration."""
    cfg = load_config()
    if "user_presets" not in cfg or not isinstance(cfg["user_presets"], dict):
        cfg["user_presets"] = {}
    cfg["user_presets"][name] = preset_dict
    save_config(cfg)


def delete_user_preset(name: str) -> bool:
    """Deletes a custom user preset from configuration."""
    cfg = load_config()
    user_presets = cfg.get("user_presets", {})
    if isinstance(user_presets, dict) and name in user_presets:
        del user_presets[name]
        cfg["user_presets"] = user_presets
        save_config(cfg)
        return True
    return False


def redact_secrets(text: str) -> str:
    """Redacts user passwords or authorization tokens from URLs and log strings."""
    if not text:
        return ""
    # Redact user:password@host
    redacted = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', str(text))
    return redacted


def generate_diagnostic_report() -> str:
    """Generates safe, structured system diagnostic information for troubleshooting."""
    ffmpeg_bin = get_ffmpeg_path()
    ffprobe_bin = get_ffprobe_path()
    cfg = load_config()
    safe_proxy = redact_secrets(cfg.get("proxy_url", "")) if cfg.get("proxy_enabled") else "Disabled"

    lines = [
        "=== YTDownloader Pro Diagnostic Report ===",
        f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Application Version: 2.6.0 (Pro Desktop)",
        f"Operating System: {sys.platform} ({os.name})",
        f"Python Version: {sys.version.split()[0]} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})",
        f"PySide6 Framework Version: {getattr(sys.modules.get('PySide6'), '__version__', '6.12.0')}",
        f"yt-dlp Engine Version: {getattr(yt_dlp.version, '__version__', 'Unknown')}",
        f"FFmpeg Path: {ffmpeg_bin or 'MISSING'}",
        f"FFprobe Path: {ffprobe_bin or 'MISSING'}",
        f"Active Proxy: {safe_proxy}",
        f"Download Directory: {cfg.get('download_path', DEFAULT_DOWNLOAD_PATH)}",
        f"SponsorBlock: {'Enabled' if cfg.get('sponsorblock_enabled') else 'Disabled'}",
        "=========================================="
    ]
    return "\n".join(lines)


# --- Configuration Management ---
DEFAULT_CONFIG = {
    "language": "en",  # "en" or "fa"
    "theme": "dark",
    "download_path": DEFAULT_DOWNLOAD_PATH,
    "download_type": "Video",  # "Video", "Audio", "Dual Mode"
    "video_quality": "Best Available",
    "video_format": "MP4",
    "audio_format": "MP3",
    "audio_quality": "320 kbps",
    "proxy_enabled": False,
    "proxy_url": "http://127.0.0.1:10809",
    "cookie_file": "",
    "sponsorblock_enabled": False,
    "embed_metadata": True,
    "download_thumbnail": False,
    "download_subtitles": False,
    "subtitle_lang": "en,fa",
    "embed_subtitles": False
}


def load_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cfg.update(data)
                    if not os.path.isdir(cfg.get("download_path", "")):
                        cfg["download_path"] = DEFAULT_DOWNLOAD_PATH
        except Exception:
            pass
    return cfg


def save_config(cfg: Dict[str, Any]):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def reset_config() -> Dict[str, Any]:
    """Resets configuration file to DEFAULT_CONFIG."""
    cfg = dict(DEFAULT_CONFIG)
    save_config(cfg)
    return cfg


class DownloadCanceled(Exception):
    pass


# --- Workers ---
class InspectWorker(QThread):
    sig_started = Signal()
    sig_completed = Signal(dict)
    sig_failed = Signal(str)

    def __init__(self, url: str, proxy: Optional[str] = None):
        super().__init__()
        self.url = url
        self.proxy = proxy
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def run(self):
        self.sig_started.emit()
        cleaned = clean_url(self.url)
        opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "no_warnings": True,
            "windowsfilenames": True,
        }
        ffmpeg_bin = get_ffmpeg_path()
        if ffmpeg_bin:
            opts["ffmpeg_location"] = ffmpeg_bin

        if self.proxy:
            opts["proxy"] = self.proxy

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(cleaned, download=False)
                if self.cancel_requested:
                    return

                if not info:
                    self.sig_failed.emit("No media metadata found for this URL.")
                    return

                # Detect playlist
                is_playlist = (info.get("_type") == "playlist") or ("entries" in info)
                entries = info.get("entries") or []
                playlist_count = len(entries) if is_playlist else 0
                if is_playlist and entries:
                    first_item = entries[0] if isinstance(entries[0], dict) else {}
                    title = info.get("title") or first_item.get("title", "Playlist")
                    uploader = info.get("uploader") or first_item.get("uploader", "Unknown Creator")
                    thumbnail = info.get("thumbnail") or first_item.get("thumbnail")
                    duration_sec = 0
                else:
                    title = info.get("title", "Untitled Media")
                    uploader = info.get("uploader") or info.get("channel") or "Unknown Creator"
                    thumbnail = info.get("thumbnail")
                    duration_sec = info.get("duration", 0)

                # Parse available video resolutions
                formats = info.get("formats", [])
                resolutions = set()
                has_audio = False
                for f in formats:
                    h = f.get("height")
                    if h and isinstance(h, int) and h > 0:
                        resolutions.add(h)
                    if f.get("acodec") and f.get("acodec") != "none":
                        has_audio = True

                sorted_res = sorted(list(resolutions), reverse=True)
                res_labels = []
                for r in sorted_res:
                    if r >= 2160:
                        res_labels.append("2160p (4K)")
                    elif r >= 1440:
                        res_labels.append("1440p (2K)")
                    elif r >= 1080:
                        res_labels.append("1080p")
                    elif r >= 720:
                        res_labels.append("720p")
                    elif r >= 480:
                        res_labels.append("480p")
                    elif r >= 360:
                        res_labels.append("360p")

                # Remove duplicates while preserving order
                seen = set()
                clean_res = [x for x in res_labels if not (x in seen or seen.add(x))]
                if not clean_res:
                    clean_res = ["Best Available"]
                else:
                    clean_res.insert(0, "Best Available")

                mins, secs = divmod(duration_sec, 60)
                hrs, mins = divmod(mins, 60)
                dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

                payload = {
                    "url": cleaned,
                    "title": title,
                    "uploader": uploader,
                    "duration": dur_str,
                    "duration_sec": duration_sec,
                    "thumbnail": thumbnail,
                    "resolutions": clean_res,
                    "has_audio": has_audio,
                    "ext": info.get("ext", "mp4"),
                    "is_live": info.get("is_live", False),
                    "is_playlist": is_playlist,
                    "playlist_count": playlist_count
                }
                if not self.cancel_requested:
                    self.sig_completed.emit(payload)

        except Exception as e:
            if not self.cancel_requested:
                err_obj = classify_error(e)
                self.sig_failed.emit(err_obj.user_message)


class DownloadWorker(QThread):
    sig_status = Signal(str)
    sig_progress = Signal(dict)
    sig_finished = Signal(dict)
    sig_error = Signal(str)
    sig_log = Signal(str)

    def __init__(self, download_params: Dict[str, Any]):
        super().__init__()
        self.params = download_params
        self.cancel_requested = False
        self.is_paused = False

    def cancel(self):
        self.cancel_requested = True
        self.sig_status.emit("Cancelling...")
        self.sig_log.emit("[ABORT] Cancellation signaled by operator.")

    def run(self):
        url = self.params["url"]
        save_path = self.params.get("download_path") or DEFAULT_DOWNLOAD_PATH
        download_type = self.params.get("download_type", "Video")
        v_quality = self.params.get("video_quality", "Best Available")
        v_format = self.params.get("video_format", "MP4").lower()
        a_format = self.params.get("audio_format", "MP3").lower()
        a_quality = self.params.get("audio_quality", "320 kbps")
        proxy = self.params.get("proxy_url") if self.params.get("proxy_enabled") else None

        self.sig_status.emit("Preparing...")
        self.sig_log.emit(f"[START] Beginning download for: {url}")
        self.sig_log.emit(f"[DESTINATION] {save_path}")

        outtmpl = os.path.join(save_path, "%(title)s.%(ext)s")

        def hook(d):
            if self.cancel_requested:
                raise DownloadCanceled("Download canceled by user.")

            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                fraction = 0.0
                if total > 0:
                    fraction = min(max(downloaded / total, 0.0), 1.0)

                speed = d.get("_speed_str", "--/s")
                eta = d.get("_eta_str", "--")
                speed_clean = re.sub(r"\x1b\[[0-9;]*m", "", speed).strip()
                eta_clean = re.sub(r"\x1b\[[0-9;]*m", "", eta).strip()

                prog_data = {
                    "fraction": fraction,
                    "percent_str": f"{fraction * 100:.1f}%" if total > 0 else d.get("_percent_str", "--%"),
                    "downloaded_bytes": downloaded,
                    "total_bytes": total,
                    "speed": speed_clean,
                    "eta": eta_clean,
                }
                self.sig_status.emit("Downloading")
                self.sig_progress.emit(prog_data)

            elif status == "finished":
                self.sig_status.emit("Merging")
                self.sig_log.emit("[PROGRESS] Stream acquired. Merging components...")

        ydl_opts = {
            "outtmpl": outtmpl,
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
            "windowsfilenames": True,
        }

        ffmpeg_bin = get_ffmpeg_path()
        if ffmpeg_bin:
            ydl_opts["ffmpeg_location"] = ffmpeg_bin

        if proxy:
            ydl_opts["proxy"] = proxy
            self.sig_log.emit(f"[PROXY] Traffic routed via: {redact_secrets(proxy)}")

        cookie_file = self.params.get("cookie_file")
        if cookie_file and os.path.exists(cookie_file):
            ydl_opts["cookiefile"] = cookie_file
            self.sig_log.emit(f"[AUTH] Using cookie file: {os.path.basename(cookie_file)}")

        # Configure Format Profiles
        is_dual = (download_type == "Dual Mode")

        if download_type == "Audio":
            # Extract Audio only
            ydl_opts["format"] = "bestaudio/best"
            bitrate = "320"
            if "256" in a_quality:
                bitrate = "256"
            elif "192" in a_quality:
                bitrate = "192"
            elif "128" in a_quality:
                bitrate = "128"

            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": a_format,
                "preferredquality": bitrate,
            }]
        else:
            # Video or Dual Mode
            h_filter = ""
            if "2160p" in v_quality:
                h_filter = "[height<=2160]"
            elif "1440p" in v_quality:
                h_filter = "[height<=1440]"
            elif "1080p" in v_quality:
                h_filter = "[height<=1080]"
            elif "720p" in v_quality:
                h_filter = "[height<=720]"
            elif "480p" in v_quality:
                h_filter = "[height<=480]"
            elif "360p" in v_quality:
                h_filter = "[height<=360]"

            if h_filter:
                ydl_opts["format"] = f"bestvideo{h_filter}+bestaudio/best{h_filter}/best"
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/best"

            if v_format in ["mp4", "mkv", "webm"]:
                ydl_opts["merge_output_format"] = v_format

        # Advanced Settings
        if self.params.get("embed_metadata"):
            ydl_opts.setdefault("postprocessors", []).append({"key": "FFmpegMetadata"})

        if self.params.get("sponsorblock_enabled"):
            ydl_opts.setdefault("postprocessors", []).append({
                "key": "SponsorBlock",
                "categories": ["sponsor", "selfpromo", "interaction", "intro", "outro"],
                "when": "after_filter"
            })

        # Subtitles configuration
        if self.params.get("download_subtitles"):
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            sub_lang = str(self.params.get("subtitle_lang", "en,fa")).split(",")
            ydl_opts["subtitleslangs"] = [s.strip() for s in sub_lang if s.strip()]
            ydl_opts["subtitlesformat"] = "srt/best"
            if self.params.get("embed_subtitles") and v_format in ("mp4", "mkv"):
                ydl_opts.setdefault("postprocessors", []).append({"key": "FFmpegEmbedSubtitle"})

        # Thumbnail configuration
        if self.params.get("download_thumbnail"):
            ydl_opts["writethumbnail"] = True
            if self.params.get("embed_metadata"):
                ydl_opts.setdefault("postprocessors", []).append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

        candidate_file = None
        extracted_audio_file = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    try:
                        prep = ydl.prepare_filename(info)
                        if os.path.exists(prep):
                            candidate_file = prep
                        else:
                            base_p, _ = os.path.splitext(prep)
                            for ext in [f".{v_format}", ".mp4", ".mkv", ".webm", f".{a_format}", ".mp3", ".m4a"]:
                                if os.path.exists(base_p + ext):
                                    candidate_file = base_p + ext
                                    break
                    except Exception:
                        pass

                    if not candidate_file and "_filename" in info and os.path.exists(info["_filename"]):
                        candidate_file = info["_filename"]

            # If Dual Mode: Extract audio from downloaded video
            if is_dual and candidate_file and os.path.exists(candidate_file) and not self.cancel_requested:
                self.sig_status.emit("Extracting Audio")
                self.sig_log.emit("[DUAL] Extracting standalone audio file via FFmpeg...")

                base_path, _ = os.path.splitext(candidate_file)
                extracted_audio_file = f"{base_path}.{a_format}"

                bitrate_flag = "320k"
                if "256" in a_quality:
                    bitrate_flag = "256k"
                elif "192" in a_quality:
                    bitrate_flag = "192k"
                elif "128" in a_quality:
                    bitrate_flag = "128k"

                codec, uses_bitrate = get_audio_codec_info(a_format)
                cmd = [
                    ffmpeg_bin or "ffmpeg",
                    "-y",
                    "-i", candidate_file,
                    "-vn",
                    "-c:a", codec
                ]
                if uses_bitrate:
                    cmd.extend(["-b:a", bitrate_flag])
                cmd.append(extracted_audio_file)
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                if res.returncode == 0 and os.path.exists(extracted_audio_file):
                    self.sig_log.emit(f"[DUAL SUCCESS] Audio created: {os.path.basename(extracted_audio_file)}")
                else:
                    self.sig_log.emit(f"[DUAL NOTE] FFmpeg audio extraction: {res.stderr.decode('utf-8', errors='ignore')[:100]}")

            if self.cancel_requested:
                self.sig_status.emit("Cancelled")
                self.sig_error.emit("Download cancelled by user.")
            else:
                # Verify downloaded media file exists and has content
                if candidate_file and not verify_output_file(candidate_file):
                    self.sig_status.emit("Failed")
                    self.sig_error.emit("Downloaded media file could not be verified on disk or is empty.")
                    self.sig_log.emit(f"[VERIFY FAILED] File missing or zero bytes: {candidate_file}")
                    return

                self.sig_status.emit("Completed")
                self.sig_finished.emit({
                    "video_file": candidate_file,
                    "audio_file": extracted_audio_file,
                    "download_path": save_path
                })

        except DownloadCanceled:
            self.sig_status.emit("Cancelled")
            self.sig_error.emit("Download cancelled by user.")
        except Exception as e:
            app_err = classify_error(e)
            self.sig_status.emit("Failed")
            self.sig_error.emit(app_err.user_message)
            self.sig_log.emit(f"[CRITICAL ERROR - {app_err.code}] {app_err.technical_message}")
