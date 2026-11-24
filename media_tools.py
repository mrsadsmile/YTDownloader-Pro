"""
Media Tools Service for YTDownloader Pro (Phase 3).
Provides:
- Advanced audio extraction & conversion pipeline (MP3, M4A, OPUS, WAV, FLAC).
- Lossless source fidelity verification & re-encoding warning detection.
- Subtitle manager: manual vs automatic subtitle discovery, multi-language extraction & embedding.
- SponsorBlock integration: official API client & categories filter.
- Smart download presets manager (built-in + custom CRUD + secure JSON import/export).
- Safe filename template formatter with OS path traversal protection.
- Atomic file operations and FFmpeg error recovery preserving original media.
"""
import os
import sys
import re
import json
import uuid
import shutil
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import core

# --- SponsorBlock Categories ---
SPONSORBLOCK_CATEGORIES = {
    "sponsor": "Sponsor Segments (Paid promotional content)",
    "selfpromo": "Self-Promotion (Merch, channel promo, other videos)",
    "interaction": "Interaction Reminders (Subscribe, like, bell)",
    "intro": "Intro / Intermission (Title cards, opening animations)",
    "outro": "Outro / End Cards (Credits, end screens)",
    "preview": "Preview / Recap (Teasers, previous episode recaps)",
    "filler": "Filler / Tangent (Unrelated banter, slow pauses)",
    "music_offtopic": "Music Video: Off-topic Section (Non-music intro/skit)"
}

DEFAULT_SPONSOR_CATEGORIES = ["sponsor", "selfpromo", "interaction", "intro", "outro"]

# --- Built-in Smart Presets ---
BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "Best Available (Auto)": {
        "download_type": "Video",
        "video_quality": "Best Available",
        "video_format": "MP4",
        "audio_format": "Best Available (Original)",
        "audio_quality": "Best Available",
        "embed_metadata": True,
        "sponsorblock_enabled": False,
        "download_subtitles": False,
        "builtin": True
    },
    "1080p Full HD (MP4)": {
        "download_type": "Video",
        "video_quality": "1080p",
        "video_format": "MP4",
        "audio_format": "MP3",
        "audio_quality": "320 kbps",
        "embed_metadata": True,
        "sponsorblock_enabled": False,
        "download_subtitles": False,
        "builtin": True
    },
    "4K Ultra HD (MKV)": {
        "download_type": "Video",
        "video_quality": "2160p (4K)",
        "video_format": "MKV",
        "audio_format": "MP3",
        "audio_quality": "320 kbps",
        "embed_metadata": True,
        "sponsorblock_enabled": False,
        "download_subtitles": False,
        "builtin": True
    },
    "Social Media (720p MP4)": {
        "download_type": "Video",
        "video_quality": "720p",
        "video_format": "MP4",
        "audio_format": "MP3",
        "audio_quality": "192 kbps",
        "embed_metadata": True,
        "sponsorblock_enabled": True,
        "download_subtitles": False,
        "builtin": True
    },
    "High Quality Audio (320k MP3)": {
        "download_type": "Audio",
        "video_quality": "Best Available",
        "video_format": "MP4",
        "audio_format": "MP3",
        "audio_quality": "320 kbps",
        "audio_sample_rate": "Auto",
        "audio_channels": "Auto",
        "embed_metadata": True,
        "download_thumbnail": True,
        "sponsorblock_enabled": False,
        "builtin": True
    },
    "Voice & Podcast (128k MP3)": {
        "download_type": "Audio",
        "video_quality": "Best Available",
        "video_format": "MP4",
        "audio_format": "MP3",
        "audio_quality": "128 kbps",
        "audio_sample_rate": "44.1 kHz",
        "audio_channels": "Mono (1ch)",
        "embed_metadata": True,
        "download_thumbnail": False,
        "sponsorblock_enabled": True,
        "builtin": True
    },
    "Lossless Master (FLAC)": {
        "download_type": "Audio",
        "video_quality": "Best Available",
        "video_format": "MP4",
        "audio_format": "FLAC",
        "audio_quality": "Best Available",
        "audio_sample_rate": "Auto",
        "audio_channels": "Auto",
        "embed_metadata": True,
        "download_thumbnail": True,
        "sponsorblock_enabled": False,
        "builtin": True
    },
    "Archive (Original Stream)": {
        "download_type": "Video",
        "video_quality": "Best Available",
        "video_format": "MKV",
        "audio_format": "Best Available (Original)",
        "audio_quality": "Best Available",
        "embed_metadata": True,
        "download_subtitles": True,
        "embed_subtitles": True,
        "sponsorblock_enabled": False,
        "builtin": True
    }
}


# ==============================================================================
# 1. AUDIO EXTRACTION & CONVERSION UTILITIES
# ==============================================================================

def get_lossless_warning(source_acodec: Optional[str], target_format: str) -> Optional[str]:
    """
    Checks if a lossy source codec (AAC, Opus, Vorbis, MP3) is being converted to
    a lossless format (FLAC or WAV). Returns an educational warning or None.
    """
    target = (target_format or "").upper().strip()
    if target not in ("FLAC", "WAV"):
        return None

    src = (source_acodec or "").lower().strip()
    if any(k in src for k in ["aac", "opus", "mp3", "vorbis", "webm", "m4a", "lossy"]):
        return (
            f"Converting lossy web audio ({source_acodec}) to {target} does not restore "
            "original studio fidelity and only increases file size."
        )
    return None


def build_audio_ffmpeg_args(
    target_format: str,
    bitrate: str = "320 kbps",
    sample_rate: str = "Auto",
    channels: str = "Auto"
) -> Tuple[List[str], str]:
    """
    Constructs FFmpeg argument flags for audio conversion.
    Returns: (args_list, output_extension)
    """
    fmt = (target_format or "mp3").lower().strip()
    if fmt == "best available (original)":
        return ["-c:a", "copy"], "aac"

    codec_info = {
        "mp3": ("libmp3lame", True, "mp3"),
        "m4a": ("aac", True, "m4a"),
        "opus": ("libopus", True, "opus"),
        "wav": ("pcm_s16le", False, "wav"),
        "flac": ("flac", False, "flac"),
    }
    codec, uses_bitrate, ext = codec_info.get(fmt, ("libmp3lame", True, "mp3"))

    args = ["-vn", "-c:a", codec]

    if uses_bitrate:
        b_str = "320k"
        if "256" in bitrate:
            b_str = "256k"
        elif "192" in bitrate:
            b_str = "192k"
        elif "128" in bitrate:
            b_str = "128k"
        args.extend(["-b:a", b_str])

    # Sample rate handling
    if "44.1" in sample_rate or "44100" in sample_rate:
        args.extend(["-ar", "44100"])
    elif "48" in sample_rate or "48000" in sample_rate:
        args.extend(["-ar", "48000"])
    elif "96" in sample_rate or "96000" in sample_rate:
        args.extend(["-ar", "96000"])

    # Channel handling
    if "mono" in channels.lower() or "1ch" in channels.lower():
        args.extend(["-ac", "1"])
    elif "stereo" in channels.lower() or "2ch" in channels.lower():
        args.extend(["-ac", "2"])

    return args, ext


def extract_audio_pipeline(
    input_file: str,
    output_path: str,
    target_format: str = "MP3",
    bitrate: str = "320 kbps",
    sample_rate: str = "Auto",
    channels: str = "Auto",
    embed_metadata: bool = True
) -> Tuple[bool, str]:
    """
    Safely extracts audio from input_file into output_path using FFmpeg.
    Uses an atomic temporary file so the original input is untouched if FFmpeg fails.
    Returns: (success: bool, message: str)
    """
    if not os.path.exists(input_file):
        return False, f"Input media file not found: {input_file}"

    ffmpeg_bin = core.get_ffmpeg_path()
    if not ffmpeg_bin:
        return False, "FFmpeg binary is missing. Please verify FFmpeg in Settings."

    out_dir = os.path.dirname(os.path.abspath(output_path))
    temp_name = f".tmp_{uuid.uuid4().hex[:8]}_{os.path.basename(output_path)}"
    temp_path = os.path.join(out_dir, temp_name)

    args, _ = build_audio_ffmpeg_args(target_format, bitrate, sample_rate, channels)

    cmd = [ffmpeg_bin, "-y", "-i", input_file] + args
    if embed_metadata:
        cmd.extend(["-map_metadata", "0"])
    cmd.append(temp_path)

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(temp_path, output_path)
            return True, output_path
        else:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            err_msg = res.stderr.decode("utf-8", errors="ignore")[-250:].strip()
            return False, f"FFmpeg error: {err_msg or 'Extraction failed'}"
    except Exception as ex:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False, str(ex)


# ==============================================================================
# 2. SUBTITLE MANAGER UTILITIES
# ==============================================================================

def parse_media_subtitles(info: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """
    Parses media metadata dictionary and returns discovered subtitles categorized
    into 'manual' and 'auto' lists with language code, name, and available formats.
    """
    result = {"manual": [], "auto": []}
    if not isinstance(info, dict):
        return result

    # 1. Manual Subtitles
    subs = info.get("subtitles") or {}
    for code, tracks in subs.items():
        name = code
        formats = []
        if isinstance(tracks, list) and len(tracks) > 0:
            name = tracks[0].get("name") or code
            formats = [t.get("ext", "vtt") for t in tracks if isinstance(t, dict)]
        result["manual"].append({
            "lang": code,
            "name": name,
            "formats": sorted(list(set(formats))) if formats else ["vtt", "srt"],
            "type": "Manual"
        })

    # 2. Automatic Captions
    auto_subs = info.get("automatic_captions") or {}
    for code, tracks in auto_subs.items():
        name = code
        formats = []
        if isinstance(tracks, list) and len(tracks) > 0:
            name = tracks[0].get("name") or code
            formats = [t.get("ext", "vtt") for t in tracks if isinstance(t, dict)]
        result["auto"].append({
            "lang": code,
            "name": name,
            "formats": sorted(list(set(formats))) if formats else ["vtt"],
            "type": "Auto-Generated"
        })

    # Sort alphabetically by language name
    result["manual"].sort(key=lambda x: x["name"].lower())
    result["auto"].sort(key=lambda x: x["name"].lower())
    return result


def embed_subtitles_safely(video_file: str, subtitle_file: str, output_file: str) -> Tuple[bool, str]:
    """
    Embeds a subtitle file (.srt/.vtt) into a video container using FFmpeg without re-encoding video.
    Safely writes to a temporary file first; if it fails, the original video is untouched.
    """
    if not os.path.exists(video_file):
        return False, f"Video file not found: {video_file}"
    if not os.path.exists(subtitle_file):
        return False, f"Subtitle file not found: {subtitle_file}"

    ffmpeg_bin = core.get_ffmpeg_path()
    if not ffmpeg_bin:
        return False, "FFmpeg binary is required for embedding subtitles."

    out_dir = os.path.dirname(os.path.abspath(output_file))
    temp_output = os.path.join(out_dir, f".sub_embed_{uuid.uuid4().hex[:8]}_{os.path.basename(output_file)}")

    # MP4 uses mov_text, MKV uses srt/ass/copy
    ext = os.path.splitext(output_file)[1].lower()
    sub_codec = "mov_text" if ext == ".mp4" else "srt"

    cmd = [
        ffmpeg_bin, "-y",
        "-i", video_file,
        "-i", subtitle_file,
        "-c:v", "copy",
        "-c:a", "copy",
        "-c:s", sub_codec,
        "-map", "0:v",
        "-map", "0:a?",
        "-map", "1:s?",
        temp_output
    ]

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0 and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            if os.path.exists(output_file):
                os.remove(output_file)
            shutil.move(temp_output, output_file)
            return True, output_file
        else:
            if os.path.exists(temp_output):
                os.remove(temp_output)
            err = res.stderr.decode("utf-8", errors="ignore")[-200:].strip()
            return False, f"Subtitle embedding failed: {err}"
    except Exception as ex:
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except Exception:
                pass
        return False, str(ex)


# ==============================================================================
# 3. SPONSORBLOCK API & CATEGORY FILTER
# ==============================================================================

def extract_youtube_id(url: str) -> Optional[str]:
    """Extracts YouTube 11-character video ID from varied URL formats."""
    if not url:
        return None
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$"
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def fetch_sponsorblock_segments(
    video_id_or_url: str,
    categories: Optional[List[str]] = None,
    timeout_seconds: float = 3.5
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Queries the official SponsorBlock API (https://sponsor.ajay.app) for segments.
    Returns: (success: bool, segments: list, message: str)
    Handles 404 (no segments found), network timeouts, or invalid video IDs safely.
    """
    vid = extract_youtube_id(video_id_or_url)
    if not vid:
        return False, [], "SponsorBlock only supports YouTube video IDs."

    cats = categories or DEFAULT_SPONSOR_CATEGORIES
    valid_cats = [c for c in cats if c in SPONSORBLOCK_CATEGORIES]
    cats_json = json.dumps(valid_cats)

    api_url = f"https://sponsor.ajay.app/api/skipSegments?videoID={vid}&categories={urllib.parse.quote(cats_json)}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "YTDownloader-Pro/2.7.0"})

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                segments = []
                for item in data:
                    cat = item.get("category", "unknown")
                    seg = item.get("segment", [0, 0])
                    segments.append({
                        "category": cat,
                        "category_name": SPONSORBLOCK_CATEGORIES.get(cat, cat.title()),
                        "start": round(seg[0], 2) if len(seg) > 0 else 0.0,
                        "end": round(seg[1], 2) if len(seg) > 1 else 0.0,
                        "uuid": item.get("UUID", "")
                    })
                return True, segments, f"Discovered {len(segments)} SponsorBlock segments."
    except urllib.error.HTTPError as he:
        if he.code == 404:
            return True, [], "No SponsorBlock segments found for this video."
        return False, [], f"SponsorBlock API returned HTTP {he.code}"
    except urllib.error.URLError as ue:
        return False, [], f"Network error connecting to SponsorBlock API: {ue.reason}"
    except Exception as ex:
        return False, [], f"SponsorBlock lookup failed: {str(ex)}"

    return False, [], "Unknown response from SponsorBlock API."


# ==============================================================================
# 4. PRESETS MANAGER (BUILT-IN + USER CUSTOM)
# ==============================================================================

class PresetManager:
    """Manages built-in and user download presets with safe JSON import/export."""

    ALLOWED_KEYS = {
        "download_type", "video_quality", "video_format",
        "audio_format", "audio_quality", "audio_sample_rate", "audio_channels",
        "embed_metadata", "download_thumbnail", "sponsorblock_enabled",
        "download_subtitles", "embed_subtitles", "subtitle_format"
    }

    @classmethod
    def get_all_presets(cls) -> Dict[str, Dict[str, Any]]:
        """Returns all built-in presets merged with user presets from config."""
        cfg = core.load_config()
        all_p = dict(BUILTIN_PRESETS)
        user_p = cfg.get("user_presets", {})
        if isinstance(user_p, dict):
            for k, v in user_p.items():
                if isinstance(v, dict):
                    v_clean = dict(v)
                    v_clean["builtin"] = False
                    all_p[k] = v_clean
        return all_p

    @classmethod
    def save_preset(cls, name: str, preset_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """Saves or updates a custom user preset."""
        clean_name = name.strip()
        if not clean_name:
            return False, "Preset name cannot be empty."
        if clean_name in BUILTIN_PRESETS:
            return False, "Cannot overwrite built-in presets. Choose a custom name."

        # Filter allowed keys only
        filtered = {k: v for k, v in preset_dict.items() if k in cls.ALLOWED_KEYS}
        filtered["builtin"] = False

        cfg = core.load_config()
        if "user_presets" not in cfg or not isinstance(cfg["user_presets"], dict):
            cfg["user_presets"] = {}
        cfg["user_presets"][clean_name] = filtered
        core.save_config(cfg)
        return True, f"Preset '{clean_name}' saved successfully."

    @classmethod
    def delete_preset(cls, name: str) -> Tuple[bool, str]:
        """Deletes a custom user preset."""
        if name in BUILTIN_PRESETS:
            return False, "Built-in presets cannot be deleted."
        cfg = core.load_config()
        user_p = cfg.get("user_presets", {})
        if isinstance(user_p, dict) and name in user_p:
            del user_p[name]
            cfg["user_presets"] = user_p
            core.save_config(cfg)
            return True, f"Preset '{name}' removed."
        return False, f"Preset '{name}' not found."

    @classmethod
    def duplicate_preset(cls, src_name: str, new_name: str) -> Tuple[bool, str]:
        """Duplicates an existing preset under a new name."""
        all_p = cls.get_all_presets()
        if src_name not in all_p:
            return False, f"Source preset '{src_name}' does not exist."
        data = dict(all_p[src_name])
        return cls.save_preset(new_name, data)

    @classmethod
    def export_presets(cls, target_json_path: str) -> Tuple[bool, str]:
        """Exports all custom presets to a JSON file."""
        cfg = core.load_config()
        user_p = cfg.get("user_presets", {})
        try:
            with open(target_json_path, "w", encoding="utf-8") as f:
                json.dump({"ytdownloader_presets_v1": user_p}, f, indent=2, ensure_ascii=False)
            return True, f"Exported {len(user_p)} custom presets to {os.path.basename(target_json_path)}."
        except Exception as ex:
            return False, f"Failed to export presets: {str(ex)}"

    @classmethod
    def import_presets(cls, source_json_path: str) -> Tuple[bool, int, str]:
        """
        Safely imports custom presets from a JSON file.
        Strictly sanitizes keys to prevent command injection or tampering.
        Returns: (success: bool, imported_count: int, message: str)
        """
        if not os.path.exists(source_json_path):
            return False, 0, "Preset file not found."

        try:
            with open(source_json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as ex:
            return False, 0, f"Malformed JSON file: {str(ex)}"

        raw_dict = payload.get("ytdownloader_presets_v1") if isinstance(payload, dict) else None
        if not isinstance(raw_dict, dict):
            # Fallback to direct dict
            if isinstance(payload, dict):
                raw_dict = payload
            else:
                return False, 0, "Invalid preset file structure."

        cfg = core.load_config()
        if "user_presets" not in cfg or not isinstance(cfg["user_presets"], dict):
            cfg["user_presets"] = {}

        count = 0
        for name, conf in raw_dict.items():
            if not isinstance(name, str) or not isinstance(conf, dict):
                continue
            clean_name = name.strip()
            if not clean_name or clean_name in BUILTIN_PRESETS:
                continue
            # Sanitize keys
            safe_conf = {k: v for k, v in conf.items() if k in cls.ALLOWED_KEYS}
            safe_conf["builtin"] = False
            cfg["user_presets"][clean_name] = safe_conf
            count += 1

        core.save_config(cfg)
        return True, count, f"Successfully imported {count} presets."


# ==============================================================================
# 5. FILENAME TEMPLATE FORMATTER & PATH SAFETY
# ==============================================================================

def apply_filename_template(
    template: str,
    meta: Dict[str, Any],
    ext: str = "mp4"
) -> str:
    """
    Formats a filename using configurable variables:
    {title}, {uploader}, {upload_date}, {id}, {playlist_title}, {playlist_index}, {resolution}.
    Neutralizes path traversal tokens (..) and invalid OS characters.
    """
    clean_ext = ext.lstrip(".").strip() or "mp4"
    tmpl = template or "%(title)s.%(ext)s"

    # Convert yt-dlp %(var)s syntax to python {var} format
    norm_tmpl = re.sub(r"%\((.*?)\)s", r"{\1}", tmpl)

    title = meta.get("title") or "Untitled Media"
    uploader = meta.get("uploader") or meta.get("channel") or "Unknown Creator"
    upload_date = meta.get("upload_date") or ""
    video_id = meta.get("id") or meta.get("video_id") or "media"
    playlist_title = meta.get("playlist_title") or "Playlist"
    playlist_index = str(meta.get("playlist_index") or meta.get("n_entries") or "01").zfill(2)
    resolution = meta.get("resolution") or meta.get("video_quality") or "Best"

    replacements = {
        "title": title,
        "uploader": uploader,
        "channel": uploader,
        "artist": uploader,
        "upload_date": upload_date,
        "date": upload_date,
        "id": video_id,
        "playlist_title": playlist_title,
        "playlist": playlist_title,
        "playlist_index": playlist_index,
        "resolution": resolution,
        "ext": clean_ext
    }

    try:
        formatted = norm_tmpl.format_map(replacements)
    except KeyError:
        # Fallback if unknown tokens exist
        formatted = f"{title}.{clean_ext}"

    # Remove any existing extension from template expansion to avoid double extension
    base, f_ext = os.path.splitext(formatted)
    if f_ext.lstrip(".").lower() == clean_ext.lower():
        formatted_base = base
    else:
        formatted_base = formatted

    safe_base = core.sanitize_filename(formatted_base)
    # Ensure traversal is strictly neutralized
    safe_base = re.sub(r"\.{2,}", "_", safe_base)
    return f"{safe_base}.{clean_ext}"
