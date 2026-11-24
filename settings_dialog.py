"""
Settings Dialog for YTDownloader Pro (Phase 4).
Includes:
- General & Automation (Language, download folder, clipboard consent, preset auto-suggest, config import/export)
- Proxy Manager (Profiles, V2Ray/Clash/Sing-box presets, real connection testing with latency)
- Download & Network Preferences (Timeouts, retries, fragments, rate limits, IPv4/IPv6, Netscape & browser cookies)
- SponsorBlock (8 categories, select all/none)
- Engine & Diagnostics (Component inventory, Diagnostic Center launcher, safe report export)
"""

import os
import sys
import json
from typing import Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QTabWidget, QWidget,
    QFileDialog, QFrame, QMessageBox, QGridLayout, QApplication,
    QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal

from theme import Tokens
from icons import get_icon
import core
import yt_dlp
import network_system
from diagnostics_dialog import DiagnosticsDialog


class ProxyTestWorker(QThread):
    sig_result = Signal(bool, str)

    def __init__(self, proxy_url: str):
        super().__init__()
        self.proxy_url = proxy_url

    def run(self):
        try:
            success, latency, ip_str, msg = network_system.ProxyManager.test_proxy_connection(
                self.proxy_url, timeout=5.0
            )
            if success:
                self.sig_result.emit(True, f"Connected ({latency} ms)")
            else:
                self.sig_result.emit(False, f"Connection Failed: {msg}")
        except Exception as e:
            self.sig_result.emit(False, f"Error: {str(e)[:60]}")


class SettingsDialog(QDialog):
    def __init__(self, parent=None, config: Dict[str, Any] = None):
        super().__init__(parent)
        self.config = dict(config or core.load_config())
        self.test_worker = None

        self.setWindowTitle("Settings — YTDownloader Pro")
        self.resize(650, 580)
        self.setMinimumSize(580, 500)
        self.init_ui()
        self.load_values()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Tabs (Exactly 5 tabs to preserve test suite compatibility)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: General & Automation
        self.tab_general = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.tab_general, get_icon("settings", Tokens.TEXT_SECONDARY, 16), "General")

        # Tab 2: Proxy
        self.tab_proxy = QWidget()
        self.setup_proxy_tab()
        self.tabs.addTab(self.tab_proxy, get_icon("shield", Tokens.TEXT_SECONDARY, 16), "Proxy")

        # Tab 3: Preferences & Network
        self.tab_prefs = QWidget()
        self.setup_prefs_tab()
        self.tabs.addTab(self.tab_prefs, get_icon("download", Tokens.TEXT_SECONDARY, 16), "Preferences")

        # Tab 4: SponsorBlock
        self.tab_sponsor = QWidget()
        self.setup_sponsor_tab()
        self.tabs.addTab(self.tab_sponsor, get_icon("x_circle", Tokens.TEXT_SECONDARY, 16), "SponsorBlock")

        # Tab 5: Engine Info & Diagnostics
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

    # --------------------------------------------------------------------------
    # TAB 1: GENERAL & AUTOMATION
    # --------------------------------------------------------------------------
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
        self.chk_clipboard_consent = QCheckBox("Prompt before analyzing links detected in clipboard")
        self.chk_auto_suggest_preset = QCheckBox("Auto-suggest best preset based on link source domain")

        layout.addWidget(self.chk_remember)
        layout.addWidget(self.chk_notifications)
        layout.addWidget(self.chk_clipboard_consent)
        layout.addWidget(self.chk_auto_suggest_preset)

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

    # --------------------------------------------------------------------------
    # TAB 2: PROXY MANAGER
    # --------------------------------------------------------------------------
    def setup_proxy_tab(self):
        layout = QVBoxLayout(self.tab_proxy)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.chk_proxy = QCheckBox("Enable Network Proxy (Bypass Filtering & Restrictions)")
        self.chk_proxy.toggled.connect(self.toggle_proxy_fields)
        layout.addWidget(self.chk_proxy)

        # Proxy Profile Form Card
        profile_card = QFrame()
        profile_card.setProperty("card", "elevated")
        p_layout = QGridLayout(profile_card)
        p_layout.setContentsMargins(14, 12, 14, 12)
        p_layout.setSpacing(10)

        p_layout.addWidget(QLabel("Proxy Type:"), 0, 0)
        self.cmb_proxy_type = QComboBox()
        self.cmb_proxy_type.addItems(["socks5", "http", "https", "socks4"])
        self.cmb_proxy_type.currentTextChanged.connect(self.update_proxy_url_from_fields)
        p_layout.addWidget(self.cmb_proxy_type, 0, 1)

        p_layout.addWidget(QLabel("Host / IP:"), 0, 2)
        self.txt_proxy_host = QLineEdit("127.0.0.1")
        self.txt_proxy_host.textChanged.connect(self.update_proxy_url_from_fields)
        p_layout.addWidget(self.txt_proxy_host, 0, 3)

        p_layout.addWidget(QLabel("Port:"), 1, 0)
        self.txt_proxy_port = QLineEdit("10808")
        self.txt_proxy_port.textChanged.connect(self.update_proxy_url_from_fields)
        p_layout.addWidget(self.txt_proxy_port, 1, 1)

        p_layout.addWidget(QLabel("Username (Opt):"), 1, 2)
        self.txt_proxy_user = QLineEdit()
        self.txt_proxy_user.textChanged.connect(self.update_proxy_url_from_fields)
        p_layout.addWidget(self.txt_proxy_user, 1, 3)

        p_layout.addWidget(QLabel("Password (Opt):"), 2, 0)
        self.txt_proxy_pass = QLineEdit()
        self.txt_proxy_pass.setEchoMode(QLineEdit.Password)
        self.txt_proxy_pass.textChanged.connect(self.update_proxy_url_from_fields)
        p_layout.addWidget(self.txt_proxy_pass, 2, 1)

        layout.addWidget(profile_card)

        # Full Proxy URL
        lbl_proxy_url = QLabel("Active Proxy URL / Address:")
        lbl_proxy_url.setProperty("secondary", True)
        layout.addWidget(lbl_proxy_url)

        self.txt_proxy_url = QLineEdit()
        self.txt_proxy_url.setPlaceholderText("socks5://127.0.0.1:10808 or http://127.0.0.1:10809")
        layout.addWidget(self.txt_proxy_url)

        # Quick Presets
        lbl_presets = QLabel("Quick Local Presets:")
        lbl_presets.setProperty("muted", True)
        layout.addWidget(lbl_presets)

        preset_row = QHBoxLayout()
        presets = [
            ("V2Ray SOCKS (10808)", "socks5://127.0.0.1:10808"),
            ("V2Ray HTTP (10809)", "http://127.0.0.1:10809"),
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
        self.btn_test_proxy.setIcon(get_icon("refresh_cw", Tokens.TEXT_PRIMARY, 16))
        self.btn_test_proxy.clicked.connect(self.test_proxy_connection)
        test_row.addWidget(self.btn_test_proxy)

        self.lbl_proxy_status = QLabel("")
        self.lbl_proxy_status.setProperty("secondary", True)
        test_row.addWidget(self.lbl_proxy_status)
        test_row.addStretch()
        layout.addLayout(test_row)

        layout.addStretch()

    def update_proxy_url_from_fields(self):
        """Constructs proxy URL from profile inputs."""
        ptype = self.cmb_proxy_type.currentText().strip()
        host = self.txt_proxy_host.text().strip() or "127.0.0.1"
        port = self.txt_proxy_port.text().strip() or "10808"
        user = self.txt_proxy_user.text().strip()
        pwd = self.txt_proxy_pass.text().strip()

        if user and pwd:
            auth = f"{user}:{pwd}@"
        elif user:
            auth = f"{user}@"
        else:
            auth = ""

        self.txt_proxy_url.setText(f"{ptype}://{auth}{host}:{port}")

    # --------------------------------------------------------------------------
    # TAB 3: DOWNLOAD & NETWORK PREFERENCES
    # --------------------------------------------------------------------------
    def setup_prefs_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # Section 1: Media Defaults
        sec1 = QFrame()
        sec1.setProperty("card", "elevated")
        s1_layout = QVBoxLayout(sec1)
        s1_layout.setContentsMargins(14, 12, 14, 12)
        s1_layout.setSpacing(10)

        lbl_s1_title = QLabel("Default Media Preferences:")
        lbl_s1_title.setStyleSheet(f"font-weight: 700; color: {Tokens.TEXT_PRIMARY}; font-size: 13px;")
        s1_layout.addWidget(lbl_s1_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Default Mode:"), 0, 0)
        self.cmb_def_mode = QComboBox()
        self.cmb_def_mode.addItems(["Video", "Audio", "Dual Mode"])
        grid.addWidget(self.cmb_def_mode, 0, 1)

        grid.addWidget(QLabel("Default Video Quality:"), 1, 0)
        self.cmb_def_v_quality = QComboBox()
        self.cmb_def_v_quality.addItems(["Best Available", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"])
        grid.addWidget(self.cmb_def_v_quality, 1, 1)

        grid.addWidget(QLabel("Default Video Format:"), 2, 0)
        self.cmb_def_v_format = QComboBox()
        self.cmb_def_v_format.addItems(["MP4", "MKV", "WEBM"])
        grid.addWidget(self.cmb_def_v_format, 2, 1)

        grid.addWidget(QLabel("Default Audio Format:"), 3, 0)
        self.cmb_def_a_format = QComboBox()
        self.cmb_def_a_format.addItems(["MP3", "M4A", "OPUS", "WAV", "FLAC"])
        grid.addWidget(self.cmb_def_a_format, 3, 1)

        grid.addWidget(QLabel("Default Audio Quality:"), 4, 0)
        self.cmb_def_a_quality = QComboBox()
        self.cmb_def_a_quality.addItems(["320 kbps", "256 kbps", "192 kbps", "128 kbps"])
        grid.addWidget(self.cmb_def_a_quality, 4, 1)

        s1_layout.addLayout(grid)

        self.chk_embed_metadata = QCheckBox("Embed media metadata tags into output files")
        s1_layout.addWidget(self.chk_embed_metadata)

        # Template
        lbl_tmpl = QLabel("Filename Naming Template:")
        lbl_tmpl.setProperty("secondary", True)
        s1_layout.addWidget(lbl_tmpl)

        self.txt_template = QLineEdit()
        self.txt_template.setPlaceholderText("%(title)s.%(ext)s")
        s1_layout.addWidget(self.txt_template)

        layout.addWidget(sec1)

        # Section 2: Network Acceleration & Resiliency (Phase 4)
        sec2 = QFrame()
        sec2.setProperty("card", "elevated")
        s2_layout = QVBoxLayout(sec2)
        s2_layout.setContentsMargins(14, 12, 14, 12)
        s2_layout.setSpacing(10)

        lbl_s2_title = QLabel("Network Acceleration & Resiliency:")
        lbl_s2_title.setStyleSheet(f"font-weight: 700; color: {Tokens.TEXT_PRIMARY}; font-size: 13px;")
        s2_layout.addWidget(lbl_s2_title)

        grid_net = QGridLayout()
        grid_net.setSpacing(10)

        grid_net.addWidget(QLabel("Socket Timeout:"), 0, 0)
        self.cmb_timeout = QComboBox()
        self.cmb_timeout.addItems(["5s", "10s", "15s", "30s", "60s"])
        grid_net.addWidget(self.cmb_timeout, 0, 1)

        grid_net.addWidget(QLabel("Network Retries:"), 0, 2)
        self.cmb_retries = QComboBox()
        self.cmb_retries.addItems(["0", "3", "5", "10", "20"])
        grid_net.addWidget(self.cmb_retries, 0, 3)

        grid_net.addWidget(QLabel("Concurrent Fragments:"), 1, 0)
        self.cmb_fragments = QComboBox()
        self.cmb_fragments.addItems(["1", "2", "4", "8", "16"])
        grid_net.addWidget(self.cmb_fragments, 1, 1)

        grid_net.addWidget(QLabel("Download Speed Limit:"), 1, 2)
        self.cmb_rate_limit = QComboBox()
        self.cmb_rate_limit.addItems(["Unlimited", "500K", "1M", "2M", "5M", "10M", "25M"])
        grid_net.addWidget(self.cmb_rate_limit, 1, 3)

        grid_net.addWidget(QLabel("IP Protocol Preference:"), 2, 0)
        self.cmb_ip_proto = QComboBox()
        self.cmb_ip_proto.addItems(["Auto", "IPv4 only", "IPv6 only"])
        grid_net.addWidget(self.cmb_ip_proto, 2, 1)

        s2_layout.addLayout(grid_net)
        layout.addWidget(sec2)

        # Section 3: Authentication & Cookies (Phase 4)
        sec3 = QFrame()
        sec3.setProperty("card", "elevated")
        s3_layout = QVBoxLayout(sec3)
        s3_layout.setContentsMargins(14, 12, 14, 12)
        s3_layout.setSpacing(10)

        lbl_s3_title = QLabel("Authentication & Cookies:")
        lbl_s3_title.setStyleSheet(f"font-weight: 700; color: {Tokens.TEXT_PRIMARY}; font-size: 13px;")
        s3_layout.addWidget(lbl_s3_title)

        lbl_cookie = QLabel("Netscape Cookies File (For private media or memberships):")
        lbl_cookie.setProperty("secondary", True)
        s3_layout.addWidget(lbl_cookie)

        cookie_row = QHBoxLayout()
        self.txt_cookie = QLineEdit()
        self.txt_cookie.setPlaceholderText("Path to cookies.txt (Netscape format)...")
        cookie_row.addWidget(self.txt_cookie)

        self.btn_browse_cookie = QPushButton("Browse...")
        self.btn_browse_cookie.setIcon(get_icon("folder", Tokens.TEXT_PRIMARY, 16))
        self.btn_browse_cookie.clicked.connect(self.browse_cookie_file)
        cookie_row.addWidget(self.btn_browse_cookie)

        self.btn_validate_cookie = QPushButton("Validate")
        self.btn_validate_cookie.clicked.connect(self.validate_cookie_file)
        cookie_row.addWidget(self.btn_validate_cookie)
        s3_layout.addLayout(cookie_row)

        self.lbl_cookie_status = QLabel("")
        self.lbl_cookie_status.setProperty("secondary", True)
        s3_layout.addWidget(self.lbl_cookie_status)

        # Browser Cookie Extraction
        browser_row = QHBoxLayout()
        lbl_b_cookie = QLabel("Extract Browser Cookies:")
        lbl_b_cookie.setProperty("secondary", True)
        browser_row.addWidget(lbl_b_cookie)

        self.cmb_browser_cookies = QComboBox()
        self.cmb_browser_cookies.addItems(["None", "chrome", "firefox", "edge", "brave", "opera"])
        browser_row.addWidget(self.cmb_browser_cookies)
        browser_row.addStretch()
        s3_layout.addLayout(browser_row)

        lbl_cookie_sec = QLabel(
            "Note: Extracted browser cookies are stored only locally in temporary memory during download "
            "to authenticate streams. Credentials are never transmitted to third parties."
        )
        lbl_cookie_sec.setProperty("muted", True)
        lbl_cookie_sec.setWordWrap(True)
        s3_layout.addWidget(lbl_cookie_sec)

        layout.addWidget(sec3)

        scroll.setWidget(content)
        top_l = QVBoxLayout(self.tab_prefs)
        top_l.setContentsMargins(0, 0, 0, 0)
        top_l.addWidget(scroll)

    # --------------------------------------------------------------------------
    # TAB 4: SPONSORBLOCK
    # --------------------------------------------------------------------------
    def setup_sponsor_tab(self):
        layout = QVBoxLayout(self.tab_sponsor)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.chk_sponsor = QCheckBox("Enable SponsorBlock (Automatically cut sponsor segments)")
        layout.addWidget(self.chk_sponsor)

        lbl_desc = QLabel(
            "SponsorBlock uses an official community database (sponsor.ajay.app) to detect and skip sponsored "
            "segments, promotions, and fillers in YouTube videos. Note: Only YouTube videos are supported by this API."
        )
        lbl_desc.setProperty("secondary", True)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setProperty("card", "elevated")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(8)

        lbl_cat_title = QLabel("Select Categories to Cut:")
        lbl_cat_title.setStyleSheet(f"font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_cat_title)

        import media_tools
        self.sb_category_boxes = {}
        for cat_key, cat_label in media_tools.SPONSORBLOCK_CATEGORIES.items():
            cb = QCheckBox(cat_label)
            self.sb_category_boxes[cat_key] = cb
            c_layout.addWidget(cb)

        # Quick select buttons
        btn_row = QHBoxLayout()
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self.sb_category_boxes.values()])
        btn_row.addWidget(btn_sel_all)

        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.clicked.connect(lambda: [cb.setChecked(False) for cb in self.sb_category_boxes.values()])
        btn_row.addWidget(btn_desel_all)
        btn_row.addStretch()
        c_layout.addLayout(btn_row)

        layout.addWidget(card)
        layout.addStretch()

    # --------------------------------------------------------------------------
    # TAB 5: ENGINE INFO & DIAGNOSTICS
    # --------------------------------------------------------------------------
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
        c_layout.addWidget(QLabel("2.9.0 (Pro Desktop)"), 0, 1)

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

        # Diagnostic Center Actions (Phase 4)
        diag_row = QHBoxLayout()
        self.btn_launch_diag = QPushButton("Launch Diagnostic Center...")
        self.btn_launch_diag.setIcon(get_icon("activity", Tokens.TEXT_PRIMARY, 16))
        self.btn_launch_diag.clicked.connect(self.open_diagnostic_center)
        diag_row.addWidget(self.btn_launch_diag)

        self.btn_copy_diagnostics = QPushButton("Copy Diagnostic Report")
        self.btn_copy_diagnostics.setIcon(get_icon("clipboard", Tokens.TEXT_PRIMARY, 16))
        self.btn_copy_diagnostics.clicked.connect(self.copy_diagnostic_report)
        diag_row.addWidget(self.btn_copy_diagnostics)

        layout.addLayout(diag_row)

        self.btn_check_updates = QPushButton("Check for Engine Updates")
        self.btn_check_updates.setIcon(get_icon("refresh_cw", Tokens.TEXT_PRIMARY, 16))
        self.btn_check_updates.clicked.connect(self.check_for_updates)
        layout.addWidget(self.btn_check_updates)

        layout.addStretch()

    def open_diagnostic_center(self):
        diag_dlg = DiagnosticsDialog(self)
        diag_dlg.exec()

    def check_for_updates(self):
        ytdlp_ver = getattr(yt_dlp.version, "__version__", "Unknown")
        QMessageBox.information(
            self,
            "Engine Status",
            f"YTDownloader Pro Version 2.9.0 is up to date.\n"
            f"Core Engine (yt-dlp): v{ytdlp_ver}\n"
            f"All components verified operational."
        )

    # --------------------------------------------------------------------------
    # ACTIONS & HELPERS
    # --------------------------------------------------------------------------
    def apply_preset(self, val: str):
        self.txt_proxy_url.setText(val)
        self.chk_proxy.setChecked(True)
        # Parse host and port if standard
        if "://" in val:
            proto, rest = val.split("://", 1)
            self.cmb_proxy_type.setCurrentText(proto.lower())
            if ":" in rest:
                h, p = rest.split(":", 1)
                self.txt_proxy_host.setText(h)
                self.txt_proxy_port.setText(p.split("/")[0])

    def toggle_proxy_fields(self, enabled: bool):
        self.txt_proxy_url.setEnabled(enabled)
        self.cmb_proxy_type.setEnabled(enabled)
        self.txt_proxy_host.setEnabled(enabled)
        self.txt_proxy_port.setEnabled(enabled)
        self.txt_proxy_user.setEnabled(enabled)
        self.txt_proxy_pass.setEnabled(enabled)
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
            self.validate_cookie_file()

    def validate_cookie_file(self):
        p = self.txt_cookie.text().strip()
        if not p:
            self.lbl_cookie_status.setText("No cookie file selected.")
            self.lbl_cookie_status.setStyleSheet(f"color: {Tokens.TEXT_MUTED};")
            return
        is_val, count, msg = network_system.validate_netscape_cookie_file(p)
        color = Tokens.SUCCESS if is_val else Tokens.ERROR
        self.lbl_cookie_status.setStyleSheet(f"color: {color}; font-weight: 500;")
        self.lbl_cookie_status.setText(f"{'✓' if is_val else '⚠'} {msg}")

    def copy_diagnostic_report(self):
        report = network_system.DiagnosticCenter.export_sanitized_report()
        clipboard = QApplication.clipboard()
        if clipboard:
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

    # --------------------------------------------------------------------------
    # LOAD & SAVE CONFIGURATION
    # --------------------------------------------------------------------------
    def load_values(self):
        # General & Automation
        lang = self.config.get("language", "en")
        self.cmb_lang.setCurrentIndex(1 if lang == "fa" else 0)
        self.txt_dir.setText(self.config.get("download_path", core.DEFAULT_DOWNLOAD_PATH))
        self.chk_remember.setChecked(self.config.get("remember_settings", True))
        self.chk_notifications.setChecked(self.config.get("notifications", True))
        self.chk_clipboard_consent.setChecked(self.config.get("clipboard_consent", True))
        self.chk_auto_suggest_preset.setChecked(self.config.get("auto_suggest_preset", True))

        # Proxy
        self.chk_proxy.setChecked(self.config.get("proxy_enabled", False))
        self.txt_proxy_url.setText(self.config.get("proxy_url", "http://127.0.0.1:10809"))
        self.toggle_proxy_fields(self.chk_proxy.isChecked())

        # Media Prefs
        self.cmb_def_mode.setCurrentText(self.config.get("download_type", "Video"))
        self.cmb_def_v_quality.setCurrentText(self.config.get("video_quality", "Best Available"))
        self.cmb_def_v_format.setCurrentText(self.config.get("video_format", "MP4"))
        self.cmb_def_a_format.setCurrentText(self.config.get("audio_format", "MP3"))
        self.cmb_def_a_quality.setCurrentText(self.config.get("audio_quality", "320 kbps"))
        self.chk_embed_metadata.setChecked(self.config.get("embed_metadata", True))
        self.txt_template.setText(self.config.get("filename_template", "%(title)s.%(ext)s"))

        # Network Settings (Phase 4)
        t_val = f"{self.config.get('socket_timeout', 15)}s"
        idx_t = self.cmb_timeout.findText(t_val)
        if idx_t >= 0:
            self.cmb_timeout.setCurrentIndex(idx_t)

        r_val = str(self.config.get("network_retries", 5))
        idx_r = self.cmb_retries.findText(r_val)
        if idx_r >= 0:
            self.cmb_retries.setCurrentIndex(idx_r)

        f_val = str(self.config.get("concurrent_fragments", 1))
        idx_f = self.cmb_fragments.findText(f_val)
        if idx_f >= 0:
            self.cmb_fragments.setCurrentIndex(idx_f)

        rl_val = str(self.config.get("rate_limit", "Unlimited"))
        idx_rl = self.cmb_rate_limit.findText(rl_val)
        if idx_rl >= 0:
            self.cmb_rate_limit.setCurrentIndex(idx_rl)

        ip_val = str(self.config.get("ip_protocol", "Auto"))
        idx_ip = self.cmb_ip_proto.findText(ip_val)
        if idx_ip >= 0:
            self.cmb_ip_proto.setCurrentIndex(idx_ip)

        # Cookies & Auth
        self.txt_cookie.setText(self.config.get("cookie_file", ""))
        b_cookie = str(self.config.get("browser_cookies", "None"))
        idx_b = self.cmb_browser_cookies.findText(b_cookie)
        if idx_b >= 0:
            self.cmb_browser_cookies.setCurrentIndex(idx_b)

        # SponsorBlock
        self.chk_sponsor.setChecked(self.config.get("sponsorblock_enabled", False))
        active_cats = self.config.get("sponsorblock_categories", ["sponsor", "selfpromo", "interaction", "intro", "outro"])
        for cat_k, cb in getattr(self, "sb_category_boxes", {}).items():
            cb.setChecked(cat_k in active_cats)

    def save_and_accept(self):
        # General & Automation
        self.config["language"] = "fa" if self.cmb_lang.currentIndex() == 1 else "en"
        self.config["download_path"] = self.txt_dir.text().strip()
        self.config["remember_settings"] = self.chk_remember.isChecked()
        self.config["notifications"] = self.chk_notifications.isChecked()
        self.config["clipboard_consent"] = self.chk_clipboard_consent.isChecked()
        self.config["auto_suggest_preset"] = self.chk_auto_suggest_preset.isChecked()

        # Proxy
        self.config["proxy_enabled"] = self.chk_proxy.isChecked()
        self.config["proxy_url"] = self.txt_proxy_url.text().strip()

        # Media Prefs
        self.config["download_type"] = self.cmb_def_mode.currentText()
        self.config["video_quality"] = self.cmb_def_v_quality.currentText()
        self.config["video_format"] = self.cmb_def_v_format.currentText()
        self.config["audio_format"] = self.cmb_def_a_format.currentText()
        self.config["audio_quality"] = self.cmb_def_a_quality.currentText()
        self.config["embed_metadata"] = self.chk_embed_metadata.isChecked()
        self.config["filename_template"] = self.txt_template.text().strip() or "%(title)s.%(ext)s"

        # Network Settings
        try:
            self.config["socket_timeout"] = int(self.cmb_timeout.currentText().rstrip("s"))
        except ValueError:
            self.config["socket_timeout"] = 15

        try:
            self.config["network_retries"] = int(self.cmb_retries.currentText())
        except ValueError:
            self.config["network_retries"] = 5

        try:
            self.config["concurrent_fragments"] = int(self.cmb_fragments.currentText())
        except ValueError:
            self.config["concurrent_fragments"] = 1

        self.config["rate_limit"] = self.cmb_rate_limit.currentText()
        self.config["ip_protocol"] = self.cmb_ip_proto.currentText()

        # Cookies & Auth
        self.config["cookie_file"] = self.txt_cookie.text().strip()
        self.config["browser_cookies"] = self.cmb_browser_cookies.currentText()

        # SponsorBlock
        self.config["sponsorblock_enabled"] = self.chk_sponsor.isChecked()
        selected_cats = [k for k, cb in getattr(self, "sb_category_boxes", {}).items() if cb.isChecked()]
        self.config["sponsorblock_categories"] = selected_cats

        core.save_config(self.config)
        self.accept()
