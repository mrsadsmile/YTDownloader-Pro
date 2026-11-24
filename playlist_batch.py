"""
Playlist & Batch Download Processing Service for YTDownloader Pro
Provides background extraction of playlists, batch URL validation, and queue ingestion.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QThread, Signal
import yt_dlp

import core


def parse_urls_from_text(text: str) -> List[str]:
    """Extracts non-empty URL strings from multi-line text input."""
    if not text:
        return []
    urls = []
    for line in text.strip().splitlines():
        clean = line.strip()
        if clean and not clean.startswith("#"):
            urls.append(clean)
    return urls


def parse_urls_from_file(file_path: str) -> List[str]:
    """Reads URLs from a UTF-8 text file, ignoring empty lines and comments."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return parse_urls_from_text(f.read())


class PlaylistInspectWorker(QThread):
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
        self.requestInterruption()

    def run(self):
        self.sig_started.emit()
        cleaned = core.clean_url(self.url)
        opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "no_warnings": True,
            "windowsfilenames": True,
        }
        ffmpeg_bin = core.get_ffmpeg_path()
        if ffmpeg_bin:
            opts["ffmpeg_location"] = ffmpeg_bin
        if self.proxy:
            opts["proxy"] = self.proxy

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(cleaned, download=False)
                if self.cancel_requested or self.isInterruptionRequested():
                    return
                if not info:
                    self.sig_failed.emit("Could not fetch playlist metadata.")
                    return

                entries_raw = info.get("entries") or []
                playlist_title = info.get("title") or "Untitled Playlist"
                uploader = info.get("uploader") or info.get("channel") or "Unknown Creator"
                thumbnail = info.get("thumbnail")

                parsed_items = []
                for idx, entry in enumerate(entries_raw):
                    if not entry:
                        continue
                    item_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
                    if item_url and not item_url.startswith("http"):
                        item_url = f"https://www.youtube.com/watch?v={item_url}"

                    dur = entry.get("duration") or 0
                    if dur > 0:
                        mins, secs = divmod(dur, 60)
                        dur_str = f"{mins:02d}:{secs:02d}"
                    else:
                        dur_str = "--:--"

                    parsed_items.append({
                        "index": idx + 1,
                        "id": entry.get("id"),
                        "title": entry.get("title") or f"Item {idx + 1}",
                        "url": item_url,
                        "duration": dur_str,
                        "duration_sec": dur,
                        "uploader": entry.get("uploader") or uploader,
                        "selected": True,
                        "status": "Available"
                    })

                payload = {
                    "url": cleaned,
                    "title": playlist_title,
                    "uploader": uploader,
                    "count": len(parsed_items),
                    "thumbnail": thumbnail,
                    "items": parsed_items
                }
                if not (self.cancel_requested or self.isInterruptionRequested()):
                    self.sig_completed.emit(payload)

        except Exception as e:
            if not (self.cancel_requested or self.isInterruptionRequested()):
                err_obj = core.classify_error(e)
                self.sig_failed.emit(err_obj.user_message)
