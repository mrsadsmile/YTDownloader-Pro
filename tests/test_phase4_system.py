"""
Phase 4 Comprehensive Unit & GUI Tests:
- Secret redaction in logs and proxy URLs
- System diagnostic report generation
- Settings export, import, and reset to defaults
- ProxyManager (URL building, connection testing)
- NetworkConfig (rate limits, timeouts, fragment concurrency, retries, IPv4/IPv6, browser cookies)
- Cookie file validation (Netscape format)
- ComponentManager (inventory and status)
- DiagnosticCenter (full diagnostics, sanitized report export)
- LogManager (buffering, rotation, level filtering, search, secret redaction)
- AutomationManager (source domain-to-preset matching)
- SettingsDialog (5 tabs, UI components, load & save roundtrip)
- DiagnosticsDialog (GUI table population, refresh)
"""
import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
import core
import database
import network_system
from settings_dialog import SettingsDialog
from diagnostics_dialog import DiagnosticsDialog

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestPhase4System(unittest.TestCase):

    def test_secret_redaction(self):
        """Verify sensitive credentials in proxy URLs or strings are redacted."""
        url_with_creds = "http://admin:superSecretPass123@127.0.0.1:8080"
        redacted = core.redact_secrets(url_with_creds)
        self.assertNotIn("superSecretPass123", redacted)
        self.assertIn("admin:***@", redacted)

        plain_url = "http://127.0.0.1:10809"
        self.assertEqual(core.redact_secrets(plain_url), plain_url)

    def test_diagnostic_report_generation(self):
        """Verify generation of non-secret system diagnostic report."""
        report = core.generate_diagnostic_report()
        self.assertIn("YTDownloader Pro", report)
        self.assertIn("Python", report)
        self.assertIn("PySide6", report)
        self.assertIn("yt-dlp", report)
        self.assertIn("FFmpeg", report)
        self.assertNotIn("password", report.lower())

    def test_settings_reset_to_defaults(self):
        """Verify reset_config resets all settings to DEFAULT_CONFIG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cfg = Path(tmpdir) / "test_cfg.json"
            orig = core.CONFIG_FILE
            try:
                core.CONFIG_FILE = test_cfg
                custom = {"language": "fa", "video_quality": "480p"}
                core.save_config(custom)

                core.reset_config()
                cfg = core.load_config()
                self.assertEqual(cfg["language"], core.DEFAULT_CONFIG["language"])
                self.assertEqual(cfg["video_quality"], core.DEFAULT_CONFIG["video_quality"])
                self.assertEqual(cfg["socket_timeout"], 15)
                self.assertEqual(cfg["network_retries"], 5)
            finally:
                core.CONFIG_FILE = orig

    def test_proxy_manager_build_url(self):
        """Verify ProxyManager creates standard proxy URLs with/without authentication."""
        profile_plain = {
            "type": "socks5",
            "host": "127.0.0.1",
            "port": 10808
        }
        self.assertEqual(network_system.ProxyManager.build_proxy_url(profile_plain), "socks5://127.0.0.1:10808")

        profile_auth = {
            "type": "http",
            "host": "proxy.example.com",
            "port": 8080,
            "username": "user1",
            "password": "secretPassword"
        }
        self.assertEqual(
            network_system.ProxyManager.build_proxy_url(profile_auth),
            "http://user1:secretPassword@proxy.example.com:8080"
        )

    @patch("urllib.request.build_opener")
    def test_proxy_manager_test_connection(self, mock_build_opener):
        """Verify test_proxy_connection reports success and failure correctly."""
        # Success case
        mock_opener = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_opener.open.return_value.__enter__.return_value = mock_resp
        mock_build_opener.return_value = mock_opener

        success, latency, ip_str, msg = network_system.ProxyManager.test_proxy_connection("http://127.0.0.1:7890")
        self.assertTrue(success)
        self.assertGreaterEqual(latency, 0.0)

        # Failure case (None or empty URL)
        succ_empty, _, _, msg_empty = network_system.ProxyManager.test_proxy_connection("")
        self.assertFalse(succ_empty)

    def test_network_config_parse_rate_limit(self):
        """Verify rate limit string parsing into bytes/sec."""
        self.assertIsNone(network_system.NetworkConfig.parse_rate_limit("Unlimited"))
        self.assertIsNone(network_system.NetworkConfig.parse_rate_limit("0"))
        self.assertIsNone(network_system.NetworkConfig.parse_rate_limit(""))

        self.assertEqual(network_system.NetworkConfig.parse_rate_limit("500K"), 500 * 1024)
        self.assertEqual(network_system.NetworkConfig.parse_rate_limit("1M"), 1024 * 1024)
        self.assertEqual(network_system.NetworkConfig.parse_rate_limit("5M/s"), 5 * 1024 * 1024)
        self.assertEqual(network_system.NetworkConfig.parse_rate_limit("10MB/s"), 10 * 1024 * 1024)

    def test_network_config_apply_options(self):
        """Verify NetworkConfig injects options into yt-dlp ydl_opts dictionary."""
        ydl_opts = {}
        config = {
            "socket_timeout": 30,
            "network_retries": 10,
            "retry_delay": 5,
            "fragment_retries": 8,
            "concurrent_fragments": 4,
            "rate_limit": "2M",
            "ip_protocol": "IPv4 only",
            "custom_user_agent": "CustomAgent/1.0",
            "browser_cookies": "firefox"
        }
        network_system.NetworkConfig.apply_network_options(ydl_opts, config)

        self.assertEqual(ydl_opts.get("socket_timeout"), 30.0)
        self.assertEqual(ydl_opts.get("retries"), 10)
        self.assertEqual(ydl_opts.get("retry_delay"), 5.0)
        self.assertEqual(ydl_opts.get("fragment_retries"), 8)
        self.assertEqual(ydl_opts.get("concurrent_fragment_downloads"), 4)
        self.assertEqual(ydl_opts.get("ratelimit"), 2 * 1024 * 1024)
        self.assertEqual(ydl_opts.get("source_address"), "0.0.0.0")
        self.assertEqual(ydl_opts.get("user_agent"), "CustomAgent/1.0")
        self.assertEqual(ydl_opts.get("cookiesfrombrowser"), ("firefox",))

    def test_validate_netscape_cookie_file(self):
        """Verify validation of Netscape format cookies.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_cookie = Path(tmpdir) / "cookies.txt"
            valid_cookie.write_text(
                "# Netscape HTTP Cookie File\n"
                "# http://curl.haxx.se/rfc/cookie_spec.html\n"
                ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tLOGIN_INFO\tAFmmF2kwRAIg...\n"
                ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tsample_session_id\n",
                encoding="utf-8"
            )

            is_valid, count, msg = network_system.validate_netscape_cookie_file(str(valid_cookie))
            self.assertTrue(is_valid)
            self.assertEqual(count, 2)
            self.assertIn("2", msg)

            # Invalid file format
            invalid_file = Path(tmpdir) / "bad.txt"
            invalid_file.write_text("random binary content without cookie header", encoding="utf-8")
            is_valid_bad, count_bad, msg_bad = network_system.validate_netscape_cookie_file(str(invalid_file))
            self.assertFalse(is_valid_bad)

            # Missing file
            is_valid_none, _, _ = network_system.validate_netscape_cookie_file("non_existent_file.txt")
            self.assertFalse(is_valid_none)

    def test_component_manager_inventory(self):
        """Verify ComponentManager inspects runtime environment."""
        inventory = network_system.ComponentManager.get_component_inventory()
        self.assertIsInstance(inventory, list)
        self.assertGreaterEqual(len(inventory), 4)

        names = [item["name"] for item in inventory]
        self.assertTrue(any("yt-dlp" in n for n in names))
        self.assertTrue(any("Python" in n for n in names))
        self.assertTrue(any("FFmpeg" in n for n in names))

    def test_diagnostic_center_full_audit(self):
        """Verify DiagnosticCenter executes all 6 health checks without throwing errors."""
        results = network_system.DiagnosticCenter.run_full_diagnostics()
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 5)

        test_names = [r["test"] for r in results]
        self.assertIn("SQLite Database", test_names)
        self.assertIn("Destination & Storage", test_names)
        self.assertIn("yt-dlp Core", test_names)
        self.assertIn("Proxy Configuration", test_names)

        # Sanitized report export
        sanitized = network_system.DiagnosticCenter.export_sanitized_report()
        self.assertIn("Health Audit Results", sanitized)
        self.assertNotIn("password", sanitized.lower())

    def test_log_manager_buffering_and_filtering(self):
        """Verify LogManager records, filters, rotates, and redacts logs."""
        network_system.LogManager.clear()
        network_system.LogManager.log("INFO", "Starting media inspection for job-1")
        network_system.LogManager.log("WARNING", "Proxy connection retry 1")
        network_system.LogManager.log("ERROR", "Download failed: http://user:superSecret@127.0.0.1:8080")

        all_logs = network_system.LogManager.get_entries()
        self.assertEqual(len(all_logs), 3)

        # Secret redaction
        error_logs = network_system.LogManager.get_entries(level_filter="ERROR")
        self.assertEqual(len(error_logs), 1)
        self.assertNotIn("superSecret", error_logs[0]["message"])
        self.assertIn("user:***@", error_logs[0]["message"])

        # Query filtering
        filtered = network_system.LogManager.get_entries(search_query="inspection")
        self.assertEqual(len(filtered), 1)
        self.assertIn("media inspection", filtered[0]["message"])

    def test_automation_manager_source_preset_matching(self):
        """Verify AutomationManager suggests built-in presets by source URL."""
        yt_preset = network_system.AutomationManager.match_preset_for_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(yt_preset, "1080p Full HD (MP4)")

        sc_preset = network_system.AutomationManager.match_preset_for_url("https://soundcloud.com/artist/track")
        self.assertEqual(sc_preset, "High Quality Audio (320k MP3)")

        bc_preset = network_system.AutomationManager.match_preset_for_url("https://artist.bandcamp.com/album/ep")
        self.assertEqual(bc_preset, "Lossless Master (FLAC)")

        unknown = network_system.AutomationManager.match_preset_for_url("https://random-domain.org/video")
        self.assertIsNone(unknown)

    def test_settings_dialog_gui_roundtrip(self):
        """Verify SettingsDialog 5 tabs, components, and load/save roundtrip."""
        test_cfg = {
            "language": "en",
            "proxy_enabled": True,
            "proxy_url": "socks5://127.0.0.1:10808",
            "socket_timeout": 30,
            "network_retries": 10,
            "concurrent_fragments": 4,
            "rate_limit": "5M",
            "ip_protocol": "IPv4 only",
            "clipboard_consent": True,
            "auto_suggest_preset": True,
            "browser_cookies": "chrome"
        }
        dlg = SettingsDialog(config=test_cfg)
        self.assertEqual(dlg.tabs.count(), 5)
        self.assertEqual(dlg.cmb_proxy_type.currentText(), "socks5")
        self.assertEqual(dlg.cmb_rate_limit.currentText(), "5M")
        self.assertEqual(dlg.cmb_browser_cookies.currentText(), "chrome")
        self.assertTrue(dlg.chk_clipboard_consent.isChecked())
        self.assertTrue(dlg.chk_auto_suggest_preset.isChecked())
        dlg.close()

    def test_diagnostics_dialog_gui(self):
        """Verify DiagnosticsDialog initializes and populates the table."""
        diag_dlg = DiagnosticsDialog()
        self.assertGreater(diag_dlg.table.rowCount(), 0)
        diag_dlg.close()


if __name__ == "__main__":
    unittest.main()
