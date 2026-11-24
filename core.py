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
from pathlib import Path
from typing import Optional, Dict, Any, List

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

    def run(self):
        self.sig_started.emit()
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
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    self.sig_failed.emit("No media metadata found for this URL.")
                    return

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

                duration = info.get("duration", 0)
                mins, secs = divmod(duration, 60)
                hrs, mins = divmod(mins, 60)
                dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

                payload = {
                    "url": self.url,
                    "title": info.get("title", "Untitled Media"),
                    "uploader": info.get("uploader") or info.get("channel") or "Unknown Creator",
                    "duration": dur_str,
                    "thumbnail": info.get("thumbnail"),
                    "resolutions": clean_res,
                    "has_audio": has_audio,
                    "ext": info.get("ext", "mp4"),
                    "is_live": info.get("is_live", False)
                }
                self.sig_completed.emit(payload)

        except Exception as e:
            err_msg = str(e)
            clean_err = re.sub(r"ERROR:\s*", "", err_msg)
            self.sig_failed.emit(clean_err)


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
        save_path = self.params["download_path"]
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
            self.sig_log.emit(f"[PROXY] Traffic routed via: {proxy}")

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

                cmd = [
                    ffmpeg_bin or "ffmpeg",
                    "-y",
                    "-i", candidate_file,
                    "-vn",
                    "-c:a", "libmp3lame" if a_format == "mp3" else "aac",
                    "-b:a", bitrate_flag,
                    extracted_audio_file
                ]
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
            clean_err = re.sub(r"ERROR:\s*", "", str(e))
            self.sig_status.emit("Failed")
            self.sig_error.emit(clean_err)
            self.sig_log.emit(f"[CRITICAL ERROR] {clean_err}")
