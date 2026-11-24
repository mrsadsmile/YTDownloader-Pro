"""
Phase 3 Advanced Media Tools Tests:
- Audio pipeline with custom sample rates and channels
- Educational lossless re-encoding warning
- Subtitle parsing separating manual from auto-generated captions
- SponsorBlock category mapping and API query parsing
- PresetManager full lifecycle (duplicate, export, import, sanitization)
- Filename template formatting with token substitution and directory traversal prevention
- SubtitlesDialog and PresetsDialog GUI tests
"""
import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

# Ensure single QApplication
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import core
import media_tools
from presets_dialog import PresetsDialog
from subtitles_dialog import SubtitlesDialog


class TestPhase3Advanced(unittest.TestCase):
    def test_lossless_warning(self):
        """Verify warning when converting lossy source to FLAC or WAV."""
        warn_flac = media_tools.get_lossless_warning("aac", "FLAC")
        self.assertIsNotNone(warn_flac)
        self.assertIn("does not restore", warn_flac)

        warn_wav = media_tools.get_lossless_warning("opus", "WAV")
        self.assertIsNotNone(warn_wav)

        # Lossy to lossy should not warn
        warn_mp3 = media_tools.get_lossless_warning("aac", "MP3")
        self.assertIsNone(warn_mp3)

    def test_audio_ffmpeg_args_builder(self):
        """Verify FFmpeg arguments for format, bitrate, sample rate, and channels."""
        # 1. MP3 with 320k, 48kHz, Mono
        args, ext = media_tools.build_audio_ffmpeg_args("MP3", "320 kbps", "48 kHz", "Mono (1ch)")
        self.assertEqual(ext, "mp3")
        self.assertIn("-c:a", args)
        self.assertIn("libmp3lame", args)
        self.assertIn("-b:a", args)
        self.assertIn("320k", args)
        self.assertIn("-ar", args)
        self.assertIn("48000", args)
        self.assertIn("-ac", args)
        self.assertIn("1", args)

        # 2. FLAC (lossless) - should omit bitrate flag
        flac_args, flac_ext = media_tools.build_audio_ffmpeg_args("FLAC", "Best Available", "44.1 kHz", "Stereo (2ch)")
        self.assertEqual(flac_ext, "flac")
        self.assertIn("flac", flac_args)
        self.assertNotIn("-b:a", flac_args)
        self.assertIn("44100", flac_args)
        self.assertIn("2", flac_args)

    def test_subtitle_parsing_manual_vs_auto(self):
        """Verify parsing of subtitles into manual vs auto-generated categories."""
        fake_info = {
            "subtitles": {
                "en": [{"ext": "vtt", "name": "English"}],
                "fa": [{"ext": "srt", "name": "Persian"}]
            },
            "automatic_captions": {
                "es": [{"ext": "vtt", "name": "Spanish"}],
                "fr": [{"ext": "vtt", "name": "French"}]
            }
        }
        parsed = media_tools.parse_media_subtitles(fake_info)
        self.assertEqual(len(parsed["manual"]), 2)
        self.assertEqual(len(parsed["auto"]), 2)

        manual_langs = [s["lang"] for s in parsed["manual"]]
        self.assertIn("en", manual_langs)
        self.assertIn("fa", manual_langs)

        auto_langs = [s["lang"] for s in parsed["auto"]]
        self.assertIn("es", auto_langs)
        self.assertIn("fr", auto_langs)

    def test_sponsorblock_api_and_youtube_id(self):
        """Verify YouTube ID extraction and SponsorBlock segment parsing."""
        # Test ID extraction
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "dQw4w9WgXcQ"
        ]
        for u in urls:
            self.assertEqual(media_tools.extract_youtube_id(u), "dQw4w9WgXcQ")

        # Non-youtube
        self.assertIsNone(media_tools.extract_youtube_id("https://soundcloud.com/artist/track"))

        # Test Mocked API response
        mock_response = MagicMock()
        mock_enter = MagicMock()
        mock_enter.status = 200
        mock_enter.read.return_value = json.dumps([
            {
                "category": "sponsor",
                "segment": [15.2, 45.8],
                "UUID": "test-uuid-1234"
            },
            {
                "category": "intro",
                "segment": [0.0, 10.5],
                "UUID": "test-uuid-5678"
            }
        ]).encode("utf-8")
        mock_response.__enter__.return_value = mock_enter

        with patch("urllib.request.urlopen", return_value=mock_response):
            ok, segments, msg = media_tools.fetch_sponsorblock_segments("dQw4w9WgXcQ")
            self.assertTrue(ok)
            self.assertEqual(len(segments), 2)
            self.assertEqual(segments[0]["category"], "sponsor")
            self.assertEqual(segments[0]["start"], 15.2)
            self.assertEqual(segments[0]["end"], 45.8)

    def test_preset_manager_lifecycle_and_sanitization(self):
        """Verify PresetManager creation, duplication, export, and security sanitization."""
        # 1. Save
        test_data = {
            "download_type": "Video",
            "video_quality": "1080p",
            "video_format": "MP4",
            "audio_format": "MP3",
            "audio_quality": "320 kbps",
            "embed_metadata": True,
            "malicious_shell_cmd": "rm -rf /",  # Should be stripped
        }
        ok, msg = media_tools.PresetManager.save_preset("Test Preset Alpha", test_data)
        self.assertTrue(ok)

        all_p = media_tools.PresetManager.get_all_presets()
        self.assertIn("Test Preset Alpha", all_p)
        # Verify malicious key was stripped
        self.assertNotIn("malicious_shell_cmd", all_p["Test Preset Alpha"])

        # 2. Duplicate
        ok_dup, _ = media_tools.PresetManager.duplicate_preset("Test Preset Alpha", "Test Preset Beta")
        self.assertTrue(ok_dup)
        all_p2 = media_tools.PresetManager.get_all_presets()
        self.assertIn("Test Preset Beta", all_p2)

        # 3. Export to JSON
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "exported_presets.json"
            ok_exp, _ = media_tools.PresetManager.export_presets(str(export_file))
            self.assertTrue(ok_exp)
            self.assertTrue(export_file.exists())

            # 4. Import from JSON
            # Delete one preset first
            media_tools.PresetManager.delete_preset("Test Preset Alpha")
            self.assertNotIn("Test Preset Alpha", media_tools.PresetManager.get_all_presets())

            ok_imp, count, _ = media_tools.PresetManager.import_presets(str(export_file))
            self.assertTrue(ok_imp)
            self.assertGreaterEqual(count, 1)
            self.assertIn("Test Preset Alpha", media_tools.PresetManager.get_all_presets())

        # Cleanup
        media_tools.PresetManager.delete_preset("Test Preset Alpha")
        media_tools.PresetManager.delete_preset("Test Preset Beta")

    def test_filename_template_formatting_and_traversal(self):
        """Verify filename template variables and path traversal prevention."""
        meta = {
            "title": "My Favorite Song",
            "uploader": "Cool Artist",
            "upload_date": "20261124",
            "id": "abc123xyz",
            "playlist_index": 5
        }

        # 1. Custom template with variables
        tmpl = "{uploader} - {title} [{id}]"
        out = media_tools.apply_filename_template(tmpl, meta, ext="mp3")
        self.assertEqual(out, "Cool Artist - My Favorite Song [abc123xyz].mp3")

        # 2. yt-dlp syntax %(uploader)s
        tmpl_ytdlp = "%(uploader)s - %(title)s"
        out_ytdlp = media_tools.apply_filename_template(tmpl_ytdlp, meta, ext="mp4")
        self.assertEqual(out_ytdlp, "Cool Artist - My Favorite Song.mp4")

        # 3. Path traversal attack attempt
        evil_meta = {
            "title": "../../../../etc/passwd",
            "uploader": "..\\Windows\\System32"
        }
        evil_out = media_tools.apply_filename_template("{uploader}_{title}", evil_meta, ext="mp4")
        self.assertNotIn("..", evil_out)
        self.assertNotIn("/", evil_out)
        self.assertNotIn("\\", evil_out)

    def test_subtitles_dialog_gui(self):
        """Verify SubtitlesDialog creates cleanly and populates language items."""
        fake_info = {
            "title": "Test Video with Subs",
            "subtitles": {"en": [{"name": "English", "ext": "vtt"}]},
            "automatic_captions": {"fa": [{"name": "Persian", "ext": "vtt"}]}
        }
        dlg = SubtitlesDialog(fake_info)
        self.assertEqual(dlg.list_manual.count(), 1)
        self.assertEqual(dlg.list_auto.count(), 1)
        self.assertIn("English", dlg.list_manual.item(0).text())
        dlg.close()
        dlg.deleteLater()

    def test_presets_dialog_gui(self):
        """Verify PresetsDialog creates cleanly and lists built-in presets."""
        dlg = PresetsDialog()
        self.assertGreater(dlg.list_presets.count(), 3)
        dlg.close()
        dlg.deleteLater()

    def test_pipeline_missing_file_safety(self):
        """Verify audio extraction and subtitle embedding fail safely on missing input without crash."""
        ok_audio, msg_audio = media_tools.extract_audio_pipeline("non_existent_input.mp4", "output.mp3")
        self.assertFalse(ok_audio)
        self.assertIn("not found", msg_audio.lower())

        ok_sub, msg_sub = media_tools.embed_subtitles_safely("non_existent_video.mp4", "non_existent_sub.srt", "output.mp4")
        self.assertFalse(ok_sub)
        self.assertIn("not found", msg_sub.lower())


if __name__ == "__main__":
    unittest.main()
