"""
Settings Dialog for YTDownloader Pro
Minimal, focused settings: General, Proxy, Download Preferences, SponsorBlock, Engine Info.
"""

import os
import sys
import urllib.request
from typing import Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QTabWidget, QWidget,
    QFileDialog, QFrame, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, QThread, Signal

from theme import Tokens
from icons import get_icon
import core
import yt_dlp


class ProxyTestWorker(QThread):
    sig_result = Signal(bool, str)

    def __init__(self, proxy_url: str):
        super().__init__()
        self.proxy_url = proxy_url

    def run(self):
        try:
            proxy_handler = urllib.request.ProxyHandler({
                'http': self.proxy_url,
                'https': self.proxy_url
            })
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(
                "https://www.youtube.com",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with opener.open(req, timeout=4) as response:
                if response.status == 200:
                    self.sig_result.emit(True, "Connected successfully (HTTP 200)")
                else:
                    self.sig_result.emit(True, f"Connected (HTTP {response.status})")
        except urllib.error.URLError as e:
            self.sig_result.emit(False, f"Connection Failed: {e.reason}")
        except Exception as e:
            self.sig_result.emit(False, f"Error: {str(e)[:60]}")


class SettingsDialog(QDialog):
    def __init__(self, parent=None, config: Dict[str, Any] = None):
        super().__init__(parent)
        self.config = dict(config or core.load_config())
        self.test_worker = None

        self.setWindowTitle("Settings — YTDownloader Pro")
        self.resize(580, 520)
        self.setMinimumSize(520, 480)
        self.init_ui()
        self.load_values()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: General
        self.tab_general = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.tab_general, get_icon("settings", Tokens.TEXT_SECONDARY, 16), "General")

        # Tab 2: Proxy
        self.tab_proxy = QWidget()
        self.setup_proxy_tab()
        self.tabs.addTab(self.tab_proxy, get_icon("shield", Tokens.TEXT_SECONDARY, 16), "Proxy")

        # Tab 3: Download Preferences
        self.tab_prefs = QWidget()
        self.setup_prefs_tab()
        self.tabs.addTab(self.tab_prefs, get_icon("download", Tokens.TEXT_SECONDARY, 16), "Preferences")

        # Tab 4: SponsorBlock
        self.tab_sponsor = QWidget()
        self.setup_sponsor_tab()
        self.tabs.addTab(self.tab_sponsor, get_icon("x_circle", Tokens.TEXT_SECONDARY, 16), "SponsorBlock")

        # Tab 5: Engine Info
        self.tab_engine = QWidget()
        self.setup_engine_tab()
        self.tabs.addTab(self.tab_engine, get_icon("info", Tokens.TEXT_SECONDARY, 16), "Engine Info")

        # Footer Actions
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        footer_layout.addStretch()

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setProperty("primary", True)
        self.btn_save.clicked.connect(self.save_and_accept)
        footer_layout.addWidget(self.btn_save)

        main_layout.addLayout(footer_layout)

    def setup_general_tab(self):
        layout = QVBoxLayout(self.tab_general)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Language
        lbl_lang = QLabel("Interface Language:")
        lbl_lang.setProperty("secondary", True)
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["English", "فارسی (Persian)"])
        layout.addWidget(lbl_lang)
        layout.addWidget(self.cmb_lang)

        # Default Download Directory
        lbl_dir = QLabel("Default Download Location:")
        lbl_dir.setProperty("secondary", True)
        layout.addWidget(lbl_dir)

        dir_row = QHBoxLayout()
        self.txt_dir = QLineEdit()
        self.txt_dir.setReadOnly(True)
        dir_row.addWidget(self.txt_dir)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setIcon(get_icon("folder", Tokens.TEXT_PRIMARY, 16))
        self.btn_browse.clicked.connect(self.browse_directory)
        dir_row.addWidget(self.btn_browse)
        layout.addLayout(dir_row)

        # Toggles
        self.chk_remember = QCheckBox("Remember last selected media options")
        self.chk_notifications = QCheckBox("Show desktop notifications on download completion")
        layout.addWidget(self.chk_remember)
        layout.addWidget(self.chk_notifications)

        # Settings Management Row
        mgmt_row = QHBoxLayout()
        self.btn_export_settings = QPushButton("Export Settings...")
        self.btn_export_settings.clicked.connect(self.export_settings)
        mgmt_row.addWidget(self.btn_export_settings)

        self.btn_import_settings = QPushButton("Import Settings...")
        self.btn_import_settings.clicked.connect(self.import_settings)
        mgmt_row.addWidget(self.btn_import_settings)

        self.btn_reset_defaults = QPushButton("Reset Defaults")
        self.btn_reset_defaults.setProperty("danger", True)
        self.btn_reset_defaults.clicked.connect(self.reset_to_defaults)
        mgmt_row.addWidget(self.btn_reset_defaults)
        layout.addLayout(mgmt_row)

        layout.addStretch()

    def setup_proxy_tab(self):
        layout = QVBoxLayout(self.tab_proxy)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.chk_proxy = QCheckBox("Enable Network Proxy (Bypass Filtering & Restrictions)")
        self.chk_proxy.toggled.connect(self.toggle_proxy_fields)
        layout.addWidget(self.chk_proxy)

        lbl_proxy_url = QLabel("Proxy URL / Address (HTTP or SOCKS5):")
        lbl_proxy_url.setProperty("secondary", True)
        layout.addWidget(lbl_proxy_url)

        self.txt_proxy_url = QLineEdit()
        self.txt_proxy_url.setPlaceholderText("http://127.0.0.1:10809 or socks5://127.0.0.1:10808")
        layout.addWidget(self.txt_proxy_url)

        # Quick Presets
        lbl_presets = QLabel("Quick Presets (Common Local Ports):")
        lbl_presets.setProperty("muted", True)
        layout.addWidget(lbl_presets)

        preset_row = QHBoxLayout()
        presets = [
            ("V2Ray HTTP (10809)", "http://127.0.0.1:10809"),
            ("V2Ray SOCKS (10808)", "socks5://127.0.0.1:10808"),
            ("Clash (7890)", "http://127.0.0.1:7890"),
            ("Sing-Box (2080)", "socks5://127.0.0.1:2080"),
        ]
        for name, val in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, v=val: self.apply_preset(v))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

        # Test Connection Button
        test_row = QHBoxLayout()
        self.btn_test_proxy = QPushButton("Test Connection")
        self.btn_test_proxy.setIcon(get_icon("refresh", Tokens.TEXT_PRIMARY, 16))
        self.btn_test_proxy.clicked.connect(self.test_proxy_connection)
        test_row.addWidget(self.btn_test_proxy)

        self.lbl_proxy_status = QLabel("")
        self.lbl_proxy_status.setProperty("secondary", True)
        test_row.addWidget(self.lbl_proxy_status)
        test_row.addStretch()
        layout.addLayout(test_row)

        layout.addStretch()

    def setup_prefs_tab(self):
        layout = QVBoxLayout(self.tab_prefs)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Default Mode
        grid.addWidget(QLabel("Default Download Mode:"), 0, 0)
        self.cmb_def_mode = QComboBox()
        self.cmb_def_mode.addItems(["Video", "Audio", "Dual Mode"])
        grid.addWidget(self.cmb_def_mode, 0, 1)

        # Default Video Quality
        grid.addWidget(QLabel("Default Video Quality:"), 1, 0)
        self.cmb_def_v_quality = QComboBox()
        self.cmb_def_v_quality.addItems(["Best Available", "1080p", "720p", "480p"])
        grid.addWidget(self.cmb_def_v_quality, 1, 1)

        # Default Video Format
        grid.addWidget(QLabel("Default Video Format:"), 2, 0)
        self.cmb_def_v_format = QComboBox()
        self.cmb_def_v_format.addItems(["MP4", "MKV", "WEBM"])
        grid.addWidget(self.cmb_def_v_format, 2, 1)

        # Default Audio Format
        grid.addWidget(QLabel("Default Audio Format:"), 3, 0)
        self.cmb_def_a_format = QComboBox()
        self.cmb_def_a_format.addItems(["MP3", "M4A", "OPUS", "WAV", "FLAC"])
        grid.addWidget(self.cmb_def_a_format, 3, 1)

        # Default Audio Quality
        grid.addWidget(QLabel("Default Audio Quality:"), 4, 0)
        self.cmb_def_a_quality = QComboBox()
        self.cmb_def_a_quality.addItems(["320 kbps", "256 kbps", "192 kbps", "128 kbps"])
        grid.addWidget(self.cmb_def_a_quality, 4, 1)

        layout.addLayout(grid)

        # Embed metadata toggle
        self.chk_embed_metadata = QCheckBox("Embed media metadata tags into output files")
        layout.addWidget(self.chk_embed_metadata)

        # Cookie File Selector
        lbl_cookie = QLabel("Netscape Cookies File (Optional, for private media/memberships):")
        lbl_cookie.setProperty("secondary", True)
        layout.addWidget(lbl_cookie)

        cookie_row = QHBoxLayout()
        self.txt_cookie = QLineEdit()
        self.txt_cookie.setPlaceholderText("Path to cookies.txt (Netscape format)...")
        cookie_row.addWidget(self.txt_cookie)

        self.btn_browse_cookie = QPushButton("Browse...")
        self.btn_browse_cookie.setIcon(get_icon("folder", Tokens.TEXT_PRIMARY, 16))
        self.btn_browse_cookie.clicked.connect(self.browse_cookie_file)
        cookie_row.addWidget(self.btn_browse_cookie)
        layout.addLayout(cookie_row)

        layout.addStretch()

    def setup_sponsor_tab(self):
        layout = QVBoxLayout(self.tab_sponsor)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.chk_sponsor = QCheckBox("Enable SponsorBlock (Automatically cut sponsor segments)")
        layout.addWidget(self.chk_sponsor)

        lbl_desc = QLabel(
            "SponsorBlock uses a community database to detect and skip sponsored segments, "
            "self-promotions, and intermission fillers in YouTube videos."
        )
        lbl_desc.setProperty("secondary", True)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setProperty("card", "elevated")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 12, 12, 12)
        c_layout.addWidget(QLabel("Active Categories:"))
        c_layout.addWidget(QLabel("• Sponsored Segments"))
        c_layout.addWidget(QLabel("• Self-Promotion / Channel Ads"))
        c_layout.addWidget(QLabel("• Interaction Reminders (Subscribe / Like)"))
        c_layout.addWidget(QLabel("• Intro / Outro Cards"))
        layout.addWidget(card)

        layout.addStretch()

    def setup_engine_tab(self):
        layout = QVBoxLayout(self.tab_engine)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("card", "elevated")
        c_layout = QGridLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(10)

        # Versions
        ytdlp_ver = getattr(yt_dlp.version, "__version__", "Unknown")
        ffmpeg_bin = core.get_ffmpeg_path()
        ffmpeg_stat = "Available" if ffmpeg_bin else "Missing"

        c_layout.addWidget(QLabel("Application Version:"), 0, 0)
        c_layout.addWidget(QLabel("2.6.0 (Pro Desktop)"), 0, 1)

        c_layout.addWidget(QLabel("yt-dlp Engine:"), 1, 0)
        c_layout.addWidget(QLabel(f"v{ytdlp_ver}"), 1, 1)

        c_layout.addWidget(QLabel("FFmpeg Processing Core:"), 2, 0)
        c_layout.addWidget(QLabel(f"{ffmpeg_stat} ({ffmpeg_bin or 'None'})"), 2, 1)

        c_layout.addWidget(QLabel("Python Runtime:"), 3, 0)
        c_layout.addWidget(QLabel(f"{sys.version.split()[0]} (64-bit)"), 3, 1)

        layout.addWidget(card)

        # Note
        lbl_note = QLabel("The core download engine and FFmpeg utilities operate locally without external telemetry.")
        lbl_note.setProperty("muted", True)
        layout.addWidget(lbl_note)

        # Diagnostic Report Actions
        self.btn_copy_diagnostics = QPushButton("Copy Diagnostic Report to Clipboard")
        self.btn_copy_diagnostics.setIcon(get_icon("clipboard", Tokens.TEXT_PRIMARY, 16))
        self.btn_copy_diagnostics.clicked.connect(self.copy_diagnostic_report)
        layout.addWidget(self.btn_copy_diagnostics)

        layout.addStretch()

    def apply_preset(self, val: str):
        self.txt_proxy_url.setText(val)
        self.chk_proxy.setChecked(True)

    def toggle_proxy_fields(self, enabled: bool):
        self.txt_proxy_url.setEnabled(enabled)
        self.btn_test_proxy.setEnabled(enabled)

    def test_proxy_connection(self):
        url = self.txt_proxy_url.text().strip()
        if not url:
            self.lbl_proxy_status.setText("Please enter a proxy URL first.")
            return

        self.lbl_proxy_status.setText("Testing connection...")
        self.btn_test_proxy.setEnabled(False)

        self.test_worker = ProxyTestWorker(url)
        self.test_worker.sig_result.connect(self.on_proxy_test_result)
        self.test_worker.start()

    def on_proxy_test_result(self, success: bool, msg: str):
        self.btn_test_proxy.setEnabled(True)
        color = Tokens.SUCCESS if success else Tokens.ERROR
        self.lbl_proxy_status.setStyleSheet(f"color: {color}; font-weight: 500;")
        self.lbl_proxy_status.setText(msg)

    def browse_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select Default Download Location", self.txt_dir.text())
        if path:
            self.txt_dir.setText(path)

    def browse_cookie_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Netscape Cookies File", self.txt_dir.text(), "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.txt_cookie.setText(file_path)

    def copy_diagnostic_report(self):
        report = core.generate_diagnostic_report()
        clipboard = QApplication.clipboard()
        clipboard.setText(report)
        QMessageBox.information(
            self,
            "Diagnostics Copied",
            "Safe system diagnostic report has been copied to your clipboard."
        )

    def reset_to_defaults(self):
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all preferences to default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.config = core.reset_config()
            self.load_values()

    def export_settings(self):
        target, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", "ytdownloader_config.json", "JSON Files (*.json)"
        )
        if target:
            try:
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Export Complete", f"Settings exported to:\n{target}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))

    def import_settings(self):
        src, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "JSON Files (*.json);;All Files (*)"
        )
        if src:
            try:
                with open(src, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.config.update(data)
                        self.load_values()
                        QMessageBox.information(self, "Import Complete", "Settings imported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", f"Could not parse configuration file:\n{e}")

    def load_values(self):
        lang = self.config.get("language", "en")
        self.cmb_lang.setCurrentIndex(1 if lang == "fa" else 0)

        self.txt_dir.setText(self.config.get("download_path", core.DEFAULT_DOWNLOAD_PATH))
        self.chk_remember.setChecked(self.config.get("remember_settings", True))
        self.chk_notifications.setChecked(self.config.get("notifications", True))

        # Proxy
        self.chk_proxy.setChecked(self.config.get("proxy_enabled", False))
        self.txt_proxy_url.setText(self.config.get("proxy_url", "http://127.0.0.1:10809"))
        self.toggle_proxy_fields(self.chk_proxy.isChecked())

        # Prefs
        self.cmb_def_mode.setCurrentText(self.config.get("download_type", "Video"))
        self.cmb_def_v_quality.setCurrentText(self.config.get("video_quality", "Best Available"))
        self.cmb_def_v_format.setCurrentText(self.config.get("video_format", "MP4"))
        self.cmb_def_a_format.setCurrentText(self.config.get("audio_format", "MP3"))
        self.cmb_def_a_quality.setCurrentText(self.config.get("audio_quality", "320 kbps"))
        self.chk_embed_metadata.setChecked(self.config.get("embed_metadata", True))
        self.txt_cookie.setText(self.config.get("cookie_file", ""))

        # Sponsor
        self.chk_sponsor.setChecked(self.config.get("sponsorblock_enabled", False))

    def save_and_accept(self):
        self.config["language"] = "fa" if self.cmb_lang.currentIndex() == 1 else "en"
        self.config["download_path"] = self.txt_dir.text().strip()
        self.config["remember_settings"] = self.chk_remember.isChecked()
        self.config["notifications"] = self.chk_notifications.isChecked()

        # Proxy
        self.config["proxy_enabled"] = self.chk_proxy.isChecked()
        self.config["proxy_url"] = self.txt_proxy_url.text().strip()

        # Prefs
        self.config["download_type"] = self.cmb_def_mode.currentText()
        self.config["video_quality"] = self.cmb_def_v_quality.currentText()
        self.config["video_format"] = self.cmb_def_v_format.currentText()
        self.config["audio_format"] = self.cmb_def_a_format.currentText()
        self.config["audio_quality"] = self.cmb_def_a_quality.currentText()
        self.config["embed_metadata"] = self.chk_embed_metadata.isChecked()
        self.config["cookie_file"] = self.txt_cookie.text().strip()

        # Sponsor
        self.config["sponsorblock_enabled"] = self.chk_sponsor.isChecked()

        core.save_config(self.config)
        self.accept()
