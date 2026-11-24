"""
Main Window for YTDownloader Pro
Production-grade desktop application matching UI/UX Pro Max standards.
"""

import os
import sys
import uuid
import subprocess
import urllib.request
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QProgressBar,
    QFileDialog, QFrame, QScrollArea, QSizePolicy, QPlainTextEdit,
    QMessageBox, QApplication, QStackedWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QClipboard

from theme import Tokens
from icons import get_icon, get_pixmap
from settings_dialog import SettingsDialog
from history_dialog import HistoryDialog
from queue_manager import QueueManager
from queue_view import QueueView
from playlist_batch_view import PlaylistBatchView
from history_view import HistoryView
from files_view import FilesView
from presets_dialog import PresetsDialog
from subtitles_dialog import SubtitlesDialog
import media_tools
import core
import database


class ThumbnailLoader(QThread):
    sig_loaded = Signal(QPixmap)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = resp.read()
            image = QImage.fromData(data)
            if not image.isNull():
                pix = QPixmap.fromImage(image).scaled(
                    170, 96,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.sig_loaded.emit(pix)
        except Exception:
            pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.config = core.load_config()
        self.inspect_worker: Optional[core.InspectWorker] = None
        self.download_worker: Optional[core.DownloadWorker] = None
        self.thumb_worker: Optional[ThumbnailLoader] = None

        self.active_media_info: Optional[Dict[str, Any]] = None
        self.last_download_result: Optional[Dict[str, Any]] = None
        self.subtitles_config: Dict[str, Any] = {}
        self.current_source_acodec: str = "aac"

        self.setWindowTitle("YTDownloader Pro")
        self.resize(960, 740)
        self.setMinimumSize(900, 660)

        # Apply Window Icon
        icon_path = core.APP_DIR / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(get_icon("download", Tokens.ACCENT, 32))

        # Initialize persistence & reconcile interrupted jobs
        self.db = database.get_db()
        self.db.jobs.recover_interrupted_jobs()
        self.queue_mgr = QueueManager(self.db)

        self.init_ui()
        self.check_clipboard_for_url()

        # Connect clipboard monitoring if active
        clip = QApplication.clipboard()
        if clip:
            clip.dataChanged.connect(self.on_clipboard_data_changed)

    def on_clipboard_data_changed(self):
        if self.config.get("clipboard_monitor", False):
            self.check_clipboard_for_url()

    def init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(12)

        # 1. Header Bar
        self.create_header(root_layout)

        # 2. Navigation Bar (Segmented Control)
        self.create_navbar(root_layout)

        # 3. Stacked Widget for Views
        self.stack = QStackedWidget()

        # View 0: Downloader
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setContentsMargins(0, 4, 0, 8)
        self.content_layout.setSpacing(14)

        # Downloader Cards
        self.create_url_card(self.content_layout)
        self.create_preview_card(self.content_layout)
        self.create_configuration_card(self.content_layout)
        self.create_advanced_card(self.content_layout)
        self.create_progress_hud(self.content_layout)
        self.create_technical_logs(self.content_layout)

        scroll.setWidget(scroll_content)
        self.view_downloader = scroll
        self.stack.addWidget(self.view_downloader)

        # View 1: Queue
        self.view_queue = QueueView(self.queue_mgr)
        self.stack.addWidget(self.view_queue)

        # View 2: Playlists & Batch
        self.view_batch = PlaylistBatchView(self.queue_mgr, self.config)
        self.stack.addWidget(self.view_batch)

        # View 3: History
        self.view_history = HistoryView(self.db, self.queue_mgr)
        self.stack.addWidget(self.view_history)

        # View 4: Files Library
        self.view_files = FilesView(self.db)
        self.stack.addWidget(self.view_files)

        root_layout.addWidget(self.stack)
        self.switch_nav(0)

    def create_navbar(self, parent_layout: QVBoxLayout):
        nav_frame = QFrame()
        nav_frame.setProperty("segmented", True)
        n_layout = QHBoxLayout(nav_frame)
        n_layout.setContentsMargins(4, 4, 4, 4)
        n_layout.setSpacing(4)

        self.btn_nav_down = QPushButton("Downloader")
        self.btn_nav_down.setIcon(get_icon("download", Tokens.TEXT_PRIMARY, 15))
        self.btn_nav_down.setProperty("segmentBtn", True)
        self.btn_nav_down.clicked.connect(lambda: self.switch_nav(0))
        n_layout.addWidget(self.btn_nav_down)

        self.btn_nav_queue = QPushButton("Queue")
        self.btn_nav_queue.setIcon(get_icon("layers", Tokens.TEXT_PRIMARY, 15))
        self.btn_nav_queue.setProperty("segmentBtn", True)
        self.btn_nav_queue.clicked.connect(lambda: self.switch_nav(1))
        n_layout.addWidget(self.btn_nav_queue)

        self.btn_nav_batch = QPushButton("Playlists & Batch")
        self.btn_nav_batch.setIcon(get_icon("search", Tokens.TEXT_PRIMARY, 15))
        self.btn_nav_batch.setProperty("segmentBtn", True)
        self.btn_nav_batch.clicked.connect(lambda: self.switch_nav(2))
        n_layout.addWidget(self.btn_nav_batch)

        self.btn_nav_hist = QPushButton("History")
        self.btn_nav_hist.setIcon(get_icon("clock", Tokens.TEXT_PRIMARY, 15))
        self.btn_nav_hist.setProperty("segmentBtn", True)
        self.btn_nav_hist.clicked.connect(lambda: self.switch_nav(3))
        n_layout.addWidget(self.btn_nav_hist)

        self.btn_nav_files = QPushButton("Files")
        self.btn_nav_files.setIcon(get_icon("folder", Tokens.TEXT_PRIMARY, 15))
        self.btn_nav_files.setProperty("segmentBtn", True)
        self.btn_nav_files.clicked.connect(lambda: self.switch_nav(4))
        n_layout.addWidget(self.btn_nav_files)

        parent_layout.addWidget(nav_frame)
        self.nav_buttons = [
            self.btn_nav_down, self.btn_nav_queue, self.btn_nav_batch,
            self.btn_nav_hist, self.btn_nav_files
        ]

    def switch_nav(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("checked", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if index == 1:
            self.view_queue.refresh_table()
        elif index == 3:
            self.view_history.refresh_table()
        elif index == 4:
            self.view_files.refresh_files()

    # --- 1. HEADER ---
    def create_header(self, parent_layout: QVBoxLayout):
        header = QFrame()
        header.setFixedHeight(44)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)

        # Logo & App Title
        lbl_logo = QLabel()
        lbl_logo.setPixmap(get_pixmap("download", Tokens.ACCENT, 22))
        h_layout.addWidget(lbl_logo)

        lbl_title = QLabel("YTDownloader Pro")
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        h_layout.addWidget(lbl_title)

        lbl_ver = QLabel("v2.8.0")
        lbl_ver.setProperty("muted", True)
        h_layout.addWidget(lbl_ver)

        h_layout.addStretch()

        # Engine Status Pill
        ffmpeg_ready = core.get_ffmpeg_path() is not None
        status_color = Tokens.SUCCESS if ffmpeg_ready else Tokens.WARNING
        status_text = "Engine Ready" if ffmpeg_ready else "FFmpeg Missing"

        self.lbl_engine_status = QLabel(f"● {status_text}")
        self.lbl_engine_status.setStyleSheet(f"""
            color: {status_color};
            background-color: {Tokens.SURFACE_ELEVATED};
            border: 1px solid {Tokens.BORDER};
            border-radius: 12px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        h_layout.addWidget(self.lbl_engine_status)

        # History Button
        self.btn_history = QPushButton()
        self.btn_history.setIcon(get_icon("clock", Tokens.TEXT_PRIMARY, 16))
        self.btn_history.setToolTip("View Download History")
        self.btn_history.setFixedSize(36, 36)
        self.btn_history.clicked.connect(self.open_history)
        h_layout.addWidget(self.btn_history)

        # Settings Button
        self.btn_settings = QPushButton()
        self.btn_settings.setIcon(get_icon("settings", Tokens.TEXT_PRIMARY, 17))
        self.btn_settings.setToolTip("Open Settings")
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.clicked.connect(self.open_settings)
        h_layout.addWidget(self.btn_settings)

        parent_layout.addWidget(header)

    # --- 2. URL INPUT CARD ---
    def create_url_card(self, parent_layout: QVBoxLayout):
        card = QFrame()
        card.setProperty("card", "true")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(10)

        lbl = QLabel("Media URL")
        lbl.setProperty("heading", True)
        c_layout.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Paste YouTube video, music, or playlist URL...")
        self.txt_url.returnPressed.connect(self.on_analyze_clicked)
        self.txt_url.textChanged.connect(self.on_url_text_changed)
        row.addWidget(self.txt_url)

        self.btn_paste = QPushButton("Paste")
        self.btn_paste.setIcon(get_icon("clipboard", Tokens.TEXT_PRIMARY, 16))
        self.btn_paste.clicked.connect(self.paste_from_clipboard)
        row.addWidget(self.btn_paste)

        self.btn_clear = QPushButton()
        self.btn_clear.setIcon(get_icon("x", Tokens.TEXT_SECONDARY, 15))
        self.btn_clear.setToolTip("Clear URL")
        self.btn_clear.setFixedWidth(34)
        self.btn_clear.clicked.connect(self.clear_url)
        row.addWidget(self.btn_clear)

        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setIcon(get_icon("search", "#FFFFFF", 16))
        self.btn_analyze.setProperty("primary", True)
        self.btn_analyze.clicked.connect(self.on_analyze_clicked)
        row.addWidget(self.btn_analyze)

        c_layout.addLayout(row)

        # Validation feedback label
        self.lbl_url_feedback = QLabel("")
        self.lbl_url_feedback.setProperty("muted", True)
        c_layout.addWidget(self.lbl_url_feedback)

        parent_layout.addWidget(card)

    # --- 3. MEDIA PREVIEW CARD ---
    def create_preview_card(self, parent_layout: QVBoxLayout):
        self.preview_card = QFrame()
        self.preview_card.setProperty("card", "elevated")
        self.preview_card.setVisible(False)

        p_layout = QHBoxLayout(self.preview_card)
        p_layout.setContentsMargins(16, 16, 16, 16)
        p_layout.setSpacing(16)

        # Thumbnail Box
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(170, 96)
        self.lbl_thumb.setStyleSheet(f"""
            background-color: {Tokens.BG_INPUT};
            border: 1px solid {Tokens.BORDER};
            border-radius: {Tokens.RADIUS_MD};
        """)
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setPixmap(get_pixmap("video", Tokens.TEXT_MUTED, 32))
        p_layout.addWidget(self.lbl_thumb)

        # Details
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        self.lbl_prev_title = QLabel("Media Title")
        self.lbl_prev_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Tokens.TEXT_PRIMARY};")
        self.lbl_prev_title.setWordWrap(True)
        info_layout.addWidget(self.lbl_prev_title)

        # Meta Row 1: Platform, Creator, Duration, Upload Date
        meta_row_1 = QHBoxLayout()
        meta_row_1.setSpacing(14)

        self.lbl_prev_platform = QLabel("Platform: --")
        self.lbl_prev_platform.setProperty("secondary", True)
        meta_row_1.addWidget(self.lbl_prev_platform)

        self.lbl_prev_channel = QLabel("Creator: --")
        self.lbl_prev_channel.setProperty("secondary", True)
        meta_row_1.addWidget(self.lbl_prev_channel)

        self.lbl_prev_duration = QLabel("Duration: --:--")
        self.lbl_prev_duration.setProperty("secondary", True)
        meta_row_1.addWidget(self.lbl_prev_duration)

        self.lbl_prev_date = QLabel("Uploaded: --")
        self.lbl_prev_date.setProperty("secondary", True)
        meta_row_1.addWidget(self.lbl_prev_date)

        meta_row_1.addStretch()
        info_layout.addLayout(meta_row_1)

        # Meta Row 2: Resolutions, Codecs/FPS, Subtitles, Est Size
        meta_row_2 = QHBoxLayout()
        meta_row_2.setSpacing(14)

        self.lbl_prev_res = QLabel("Resolutions: Auto")
        self.lbl_prev_res.setProperty("muted", True)
        meta_row_2.addWidget(self.lbl_prev_res)

        self.lbl_prev_codecs = QLabel("Codecs: Auto")
        self.lbl_prev_codecs.setProperty("muted", True)
        meta_row_2.addWidget(self.lbl_prev_codecs)

        self.lbl_prev_subs = QLabel("Subtitles: None")
        self.lbl_prev_subs.setProperty("muted", True)
        meta_row_2.addWidget(self.lbl_prev_subs)

        self.btn_quick_subs = QPushButton("Subtitles...")
        self.btn_quick_subs.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_quick_subs.clicked.connect(self.open_subtitles_dialog)
        meta_row_2.addWidget(self.btn_quick_subs)

        self.lbl_prev_size = QLabel("Est. Size: --")
        self.lbl_prev_size.setProperty("muted", True)
        meta_row_2.addWidget(self.lbl_prev_size)

        meta_row_2.addStretch()
        info_layout.addLayout(meta_row_2)

        p_layout.addLayout(info_layout)
        parent_layout.addWidget(self.preview_card)

    # --- 4. CONFIGURATION CARD ---
    def create_configuration_card(self, parent_layout: QVBoxLayout):
        card = QFrame()
        card.setProperty("card", "true")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        # Quick Presets Bar
        preset_bar = QHBoxLayout()
        preset_bar.setSpacing(8)

        lbl_preset = QLabel("Preset Profile:")
        lbl_preset.setProperty("secondary", True)
        preset_bar.addWidget(lbl_preset)

        self.cmb_presets = QComboBox()
        self.refresh_presets_combo()
        self.cmb_presets.currentIndexChanged.connect(self.on_preset_dropdown_changed)
        preset_bar.addWidget(self.cmb_presets, 3)

        self.btn_save_preset = QPushButton("Save Preset")
        self.btn_save_preset.setIcon(get_icon("plus", Tokens.TEXT_PRIMARY, 13))
        self.btn_save_preset.clicked.connect(self.save_as_preset)
        preset_bar.addWidget(self.btn_save_preset)

        self.btn_manage_presets = QPushButton("Presets...")
        self.btn_manage_presets.setIcon(get_icon("sliders", Tokens.TEXT_PRIMARY, 13))
        self.btn_manage_presets.clicked.connect(self.open_presets_dialog)
        preset_bar.addWidget(self.btn_manage_presets)

        c_layout.addLayout(preset_bar)

        # Mode Selection (Segmented Control)
        mode_header = QHBoxLayout()
        lbl_mode = QLabel("Download Type")
        lbl_mode.setProperty("heading", True)
        mode_header.addWidget(lbl_mode)
        mode_header.addStretch()

        seg_frame = QFrame()
        seg_frame.setProperty("segmented", True)
        s_layout = QHBoxLayout(seg_frame)
        s_layout.setContentsMargins(2, 2, 2, 2)
        s_layout.setSpacing(2)

        self.btn_mode_video = QPushButton("Video")
        self.btn_mode_video.setIcon(get_icon("video", Tokens.TEXT_PRIMARY, 15))
        self.btn_mode_video.setProperty("segmentBtn", True)
        self.btn_mode_video.clicked.connect(lambda: self.set_download_mode("Video"))

        self.btn_mode_audio = QPushButton("Audio Only")
        self.btn_mode_audio.setIcon(get_icon("music", Tokens.TEXT_PRIMARY, 15))
        self.btn_mode_audio.setProperty("segmentBtn", True)
        self.btn_mode_audio.clicked.connect(lambda: self.set_download_mode("Audio"))

        self.btn_mode_dual = QPushButton("Dual Mode (Video + Audio)")
        self.btn_mode_dual.setIcon(get_icon("layers", Tokens.TEXT_PRIMARY, 15))
        self.btn_mode_dual.setProperty("segmentBtn", True)
        self.btn_mode_dual.clicked.connect(lambda: self.set_download_mode("Dual Mode"))

        s_layout.addWidget(self.btn_mode_video)
        s_layout.addWidget(self.btn_mode_audio)
        s_layout.addWidget(self.btn_mode_dual)
        mode_header.addWidget(seg_frame)
        c_layout.addLayout(mode_header)

        # Dynamic Quality & Format Settings Container
        self.settings_grid_frame = QFrame()
        grid_layout = QHBoxLayout(self.settings_grid_frame)
        grid_layout.setContentsMargins(0, 4, 0, 4)
        grid_layout.setSpacing(12)

        # Video Quality Column
        self.col_video_quality = QVBoxLayout()
        self.lbl_v_quality = QLabel("Video Resolution:")
        self.lbl_v_quality.setProperty("secondary", True)
        self.cmb_video_quality = QComboBox()
        self.cmb_video_quality.addItems(["Best Available", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"])
        self.col_video_quality.addWidget(self.lbl_v_quality)
        self.col_video_quality.addWidget(self.cmb_video_quality)
        grid_layout.addLayout(self.col_video_quality)

        # Video Format Column
        self.col_video_format = QVBoxLayout()
        self.lbl_v_format = QLabel("Video Container:")
        self.lbl_v_format.setProperty("secondary", True)
        self.cmb_video_format = QComboBox()
        self.cmb_video_format.addItems(["MP4", "MKV", "WEBM"])
        self.col_video_format.addWidget(self.lbl_v_format)
        self.col_video_format.addWidget(self.cmb_video_format)
        grid_layout.addLayout(self.col_video_format)

        # Audio Format Column
        self.col_audio_format = QVBoxLayout()
        self.lbl_a_format = QLabel("Audio Format:")
        self.lbl_a_format.setProperty("secondary", True)
        self.cmb_audio_format = QComboBox()
        self.cmb_audio_format.addItems(["Best Available (Original)", "MP3", "M4A", "OPUS", "WAV", "FLAC"])
        self.cmb_audio_format.currentTextChanged.connect(self.on_audio_format_changed)
        self.col_audio_format.addWidget(self.lbl_a_format)
        self.col_audio_format.addWidget(self.cmb_audio_format)
        grid_layout.addLayout(self.col_audio_format)

        # Audio Quality Column
        self.col_audio_quality = QVBoxLayout()
        self.lbl_a_quality = QLabel("Audio Bitrate:")
        self.lbl_a_quality.setProperty("secondary", True)
        self.cmb_audio_quality = QComboBox()
        self.cmb_audio_quality.addItems(["Best Available", "320 kbps", "256 kbps", "192 kbps", "128 kbps"])
        self.col_audio_quality.addWidget(self.lbl_a_quality)
        self.col_audio_quality.addWidget(self.cmb_audio_quality)
        grid_layout.addLayout(self.col_audio_quality)

        # Audio Sample Rate Column
        self.col_audio_sample_rate = QVBoxLayout()
        self.lbl_a_sample_rate = QLabel("Sample Rate:")
        self.lbl_a_sample_rate.setProperty("secondary", True)
        self.cmb_audio_sample_rate = QComboBox()
        self.cmb_audio_sample_rate.addItems(["Auto", "44.1 kHz", "48 kHz", "96 kHz"])
        self.col_audio_sample_rate.addWidget(self.lbl_a_sample_rate)
        self.col_audio_sample_rate.addWidget(self.cmb_audio_sample_rate)
        grid_layout.addLayout(self.col_audio_sample_rate)

        # Audio Channels Column
        self.col_audio_channels = QVBoxLayout()
        self.lbl_a_channels = QLabel("Channels:")
        self.lbl_a_channels.setProperty("secondary", True)
        self.cmb_audio_channels = QComboBox()
        self.cmb_audio_channels.addItems(["Auto", "Stereo (2ch)", "Mono (1ch)"])
        self.col_audio_channels.addWidget(self.lbl_a_channels)
        self.col_audio_channels.addWidget(self.cmb_audio_channels)
        grid_layout.addLayout(self.col_audio_channels)

        c_layout.addWidget(self.settings_grid_frame)

        self.lbl_lossless_warning = QLabel("")
        self.lbl_lossless_warning.setStyleSheet(f"color: {Tokens.WARNING}; font-size: 12px; padding: 2px 4px;")
        self.lbl_lossless_warning.setWordWrap(True)
        self.lbl_lossless_warning.setVisible(False)
        c_layout.addWidget(self.lbl_lossless_warning)

        # Save Directory Row
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(8)

        lbl_dir = QLabel("Save To:")
        lbl_dir.setProperty("secondary", True)
        dir_layout.addWidget(lbl_dir)

        self.txt_path = QLineEdit()
        self.txt_path.setText(self.config.get("download_path", core.DEFAULT_DOWNLOAD_PATH))
        self.txt_path.setReadOnly(True)
        dir_layout.addWidget(self.txt_path)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setIcon(get_icon("folder", Tokens.TEXT_PRIMARY, 15))
        self.btn_browse.clicked.connect(self.browse_folder)
        dir_layout.addWidget(self.btn_browse)

        self.btn_open_folder = QPushButton("Open Folder")
        self.btn_open_folder.setIcon(get_icon("folder_open", Tokens.TEXT_PRIMARY, 15))
        self.btn_open_folder.clicked.connect(self.open_download_folder)
        dir_layout.addWidget(self.btn_open_folder)

        c_layout.addLayout(dir_layout)

        parent_layout.addWidget(card)

        # Set initial mode from config
        initial_mode = self.config.get("download_type", "Video")
        self.set_download_mode(initial_mode)

    # --- 5. ADVANCED COLLAPSIBLE OPTIONS ---
    def create_advanced_card(self, parent_layout: QVBoxLayout):
        self.advanced_card = QFrame()
        self.advanced_card.setProperty("card", "true")
        a_layout = QVBoxLayout(self.advanced_card)
        a_layout.setContentsMargins(18, 12, 18, 12)
        a_layout.setSpacing(10)

        # Header Toggle
        header_row = QHBoxLayout()
        self.btn_toggle_adv = QPushButton("Advanced Options")
        self.btn_toggle_adv.setIcon(get_icon("chevron_down", Tokens.TEXT_SECONDARY, 16))
        self.btn_toggle_adv.setStyleSheet("background: transparent; border: none; font-weight: 600; text-align: left;")
        self.btn_toggle_adv.clicked.connect(self.toggle_advanced)
        header_row.addWidget(self.btn_toggle_adv)
        header_row.addStretch()
        a_layout.addLayout(header_row)

        # Collapsible Body
        self.adv_body = QWidget()
        b_layout = QVBoxLayout(self.adv_body)
        b_layout.setContentsMargins(0, 4, 0, 4)
        b_layout.setSpacing(8)

        self.chk_adv_metadata = QCheckBox("Embed metadata tags into output file")
        self.chk_adv_metadata.setChecked(self.config.get("embed_metadata", True))
        b_layout.addWidget(self.chk_adv_metadata)

        self.chk_adv_thumbnail = QCheckBox("Embed video thumbnail as cover art")
        self.chk_adv_thumbnail.setChecked(self.config.get("download_thumbnail", False))
        b_layout.addWidget(self.chk_adv_thumbnail)

        self.chk_adv_sponsor = QCheckBox("SponsorBlock: Automatically remove sponsored segments")
        self.chk_adv_sponsor.setChecked(self.config.get("sponsorblock_enabled", False))
        b_layout.addWidget(self.chk_adv_sponsor)

        sub_row = QHBoxLayout()
        self.lbl_adv_subs_status = QLabel("Subtitles: Default settings (en, fa)")
        self.lbl_adv_subs_status.setProperty("secondary", True)
        sub_row.addWidget(self.lbl_adv_subs_status)
        sub_row.addStretch()

        self.btn_manage_subs = QPushButton("Subtitle Manager...")
        self.btn_manage_subs.setIcon(get_icon("film", Tokens.TEXT_PRIMARY, 14))
        self.btn_manage_subs.clicked.connect(self.open_subtitles_dialog)
        sub_row.addWidget(self.btn_manage_subs)
        b_layout.addLayout(sub_row)

        self.adv_body.setVisible(False)
        a_layout.addWidget(self.adv_body)

        parent_layout.addWidget(self.advanced_card)

    # --- 6. PROGRESS HUD & ACTIONS ---
    def create_progress_hud(self, parent_layout: QVBoxLayout):
        card = QFrame()
        card.setProperty("card", "elevated")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(10)

        # Status & Percentage Header
        top_row = QHBoxLayout()
        self.lbl_task_status = QLabel("Ready")
        self.lbl_task_status.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {Tokens.TEXT_PRIMARY};")
        top_row.addWidget(self.lbl_task_status)

        top_row.addStretch()

        self.lbl_percent = QLabel("0.0%")
        self.lbl_percent.setStyleSheet(f"font-family: {Tokens.FONT_MONO}; font-weight: 700; font-size: 14px; color: {Tokens.ACCENT};")
        top_row.addWidget(self.lbl_percent)
        c_layout.addLayout(top_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        c_layout.addWidget(self.progress_bar)

        # Details: Speed, ETA, Size
        meta_row = QHBoxLayout()
        self.lbl_speed = QLabel("Speed: --")
        self.lbl_speed.setProperty("muted", True)
        meta_row.addWidget(self.lbl_speed)

        meta_row.addStretch()

        self.lbl_eta = QLabel("ETA: --")
        self.lbl_eta.setProperty("muted", True)
        meta_row.addWidget(self.lbl_eta)

        meta_row.addStretch()

        self.lbl_size = QLabel("Size: --")
        self.lbl_size.setProperty("muted", True)
        meta_row.addWidget(self.lbl_size)

        c_layout.addLayout(meta_row)

        # Actions Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.btn_download = QPushButton("Start Download")
        self.btn_download.setIcon(get_icon("download", "#FFFFFF", 16))
        self.btn_download.setProperty("primary", True)
        self.btn_download.setFixedHeight(40)
        self.btn_download.clicked.connect(self.start_download)
        actions_row.addWidget(self.btn_download, 3)

        self.btn_enqueue = QPushButton("Add to Queue")
        self.btn_enqueue.setIcon(get_icon("layers", Tokens.TEXT_PRIMARY, 15))
        self.btn_enqueue.setFixedHeight(40)
        self.btn_enqueue.clicked.connect(self.enqueue_from_downloader)
        actions_row.addWidget(self.btn_enqueue, 2)

        self.btn_open_file = QPushButton("Open File")
        self.btn_open_file.setIcon(get_icon("play", Tokens.TEXT_PRIMARY, 16))
        self.btn_open_file.setFixedHeight(40)
        self.btn_open_file.setEnabled(False)
        self.btn_open_file.setToolTip("Open downloaded media file in default system player")
        self.btn_open_file.clicked.connect(self.open_downloaded_file)
        actions_row.addWidget(self.btn_open_file, 1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setIcon(get_icon("x_circle", Tokens.DANGER, 16))
        self.btn_cancel.setProperty("danger", True)
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_download)
        actions_row.addWidget(self.btn_cancel, 1)

        c_layout.addLayout(actions_row)

        parent_layout.addWidget(card)

    # --- 7. COLLAPSIBLE TECHNICAL LOGS ---
    def create_technical_logs(self, parent_layout: QVBoxLayout):
        log_frame = QFrame()
        l_layout = QVBoxLayout(log_frame)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(6)

        toggle_row = QHBoxLayout()
        self.btn_toggle_logs = QPushButton("Technical Details (Diagnostics)")
        self.btn_toggle_logs.setIcon(get_icon("chevron_down", Tokens.TEXT_MUTED, 14))
        self.btn_toggle_logs.setStyleSheet("background: transparent; border: none; font-size: 11px; color: #687586; text-align: left;")
        self.btn_toggle_logs.clicked.connect(self.toggle_logs)
        toggle_row.addWidget(self.btn_toggle_logs)
        toggle_row.addStretch()
        l_layout.addLayout(toggle_row)

        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFixedHeight(110)
        self.log_edit.setVisible(False)
        l_layout.addWidget(self.log_edit)

        parent_layout.addWidget(log_frame)

    # --- UI INTERACTIONS ---
    def set_download_mode(self, mode: str):
        self.btn_mode_video.setProperty("checked", mode == "Video")
        self.btn_mode_audio.setProperty("checked", mode == "Audio")
        self.btn_mode_dual.setProperty("checked", mode == "Dual Mode")

        for btn in [self.btn_mode_video, self.btn_mode_audio, self.btn_mode_dual]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Show/Hide dynamic options
        show_video = (mode in ["Video", "Dual Mode"])
        show_audio = (mode in ["Audio", "Dual Mode"])

        for i in range(self.col_video_quality.count()):
            w = self.col_video_quality.itemAt(i).widget()
            if w:
                w.setVisible(show_video)
        for i in range(self.col_video_format.count()):
            w = self.col_video_format.itemAt(i).widget()
            if w:
                w.setVisible(show_video)

        for i in range(self.col_audio_format.count()):
            w = self.col_audio_format.itemAt(i).widget()
            if w:
                w.setVisible(show_audio)
        for i in range(self.col_audio_quality.count()):
            w = self.col_audio_quality.itemAt(i).widget()
            if w:
                w.setVisible(show_audio)
        for i in range(self.col_audio_sample_rate.count()):
            w = self.col_audio_sample_rate.itemAt(i).widget()
            if w:
                w.setVisible(show_audio)
        for i in range(self.col_audio_channels.count()):
            w = self.col_audio_channels.itemAt(i).widget()
            if w:
                w.setVisible(show_audio)

        self.config["download_type"] = mode
        core.save_config(self.config)

    def toggle_advanced(self):
        visible = not self.adv_body.isVisible()
        self.adv_body.setVisible(visible)
        icon_name = "chevron_up" if visible else "chevron_down"
        self.btn_toggle_adv.setIcon(get_icon(icon_name, Tokens.TEXT_SECONDARY, 16))

    def toggle_logs(self):
        visible = not self.log_edit.isVisible()
        self.log_edit.setVisible(visible)
        icon_name = "chevron_up" if visible else "chevron_down"
        self.btn_toggle_logs.setIcon(get_icon(icon_name, Tokens.TEXT_MUTED, 14))

    def check_clipboard_for_url(self):
        clipboard = QApplication.clipboard()
        if not clipboard:
            return
        text = clipboard.text().strip()
        if text.startswith("http://") or text.startswith("https://"):
            is_valid, _ = core.validate_url(text)
            if is_valid and text != self.txt_url.text().strip():
                self.txt_url.setText(text)
                if self.config.get("clipboard_consent", True):
                    self.lbl_url_feedback.setText("Media link detected in clipboard. Ready for analysis.")
                else:
                    self.lbl_url_feedback.setText("URL detected from clipboard.")
                self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.ACCENT};")

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.txt_url.setText(text)
            self.on_analyze_clicked()

    def clear_url(self):
        if self.inspect_worker and self.inspect_worker.isRunning():
            self.inspect_worker.cancel()
        self.txt_url.clear()
        self.preview_card.setVisible(False)
        self.active_media_info = None
        self.lbl_url_feedback.setText("")
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Analyze")
        self.btn_analyze.setIcon(get_icon("search", "#FFFFFF", 16))
        self.btn_open_file.setEnabled(False)
        self.reset_hud()

    def on_url_text_changed(self, text: str):
        t = text.strip()
        if not t:
            self.lbl_url_feedback.setText("")
            self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.TEXT_MUTED};")
        else:
            is_valid, reason = core.validate_url(t)
            if is_valid:
                self.lbl_url_feedback.setText("✓ Valid media URL format")
                self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.SUCCESS};")
            else:
                self.lbl_url_feedback.setText(reason)
                self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.WARNING};")

    def on_audio_format_changed(self, fmt: str):
        is_lossless_or_source = (fmt in ["Best Available (Original)", "WAV", "FLAC"])
        self.cmb_audio_quality.setEnabled(not is_lossless_or_source)
        if is_lossless_or_source:
            self.lbl_a_quality.setText("Audio Bitrate: (Lossless / Source)")
        else:
            self.lbl_a_quality.setText("Audio Bitrate:")

        # Lossless conversion warning
        warn = media_tools.get_lossless_warning(self.current_source_acodec, fmt)
        if warn:
            self.lbl_lossless_warning.setText(f"⚠ {warn}")
            self.lbl_lossless_warning.setVisible(True)
        else:
            self.lbl_lossless_warning.setVisible(False)

    def refresh_presets_combo(self):
        self.cmb_presets.blockSignals(True)
        self.cmb_presets.clear()
        self.cmb_presets.addItem("Manual Configuration", None)
        all_p = media_tools.PresetManager.get_all_presets()
        for name, conf in all_p.items():
            tag = " [Built-in]" if conf.get("builtin") else ""
            self.cmb_presets.addItem(f"{name}{tag}", conf)
        self.cmb_presets.blockSignals(False)

    def on_preset_dropdown_changed(self, idx: int):
        conf = self.cmb_presets.currentData()
        if conf and isinstance(conf, dict):
            self.apply_preset_dict(conf)

    def apply_preset_dict(self, conf: Dict[str, Any]):
        m = conf.get("download_type", "Video")
        self.set_download_mode(m)

        idx_vq = self.cmb_video_quality.findText(conf.get("video_quality", "Best Available"))
        if idx_vq >= 0:
            self.cmb_video_quality.setCurrentIndex(idx_vq)
        idx_vf = self.cmb_video_format.findText(conf.get("video_format", "MP4"))
        if idx_vf >= 0:
            self.cmb_video_format.setCurrentIndex(idx_vf)

        idx_af = self.cmb_audio_format.findText(conf.get("audio_format", "MP3"))
        if idx_af >= 0:
            self.cmb_audio_format.setCurrentIndex(idx_af)
        idx_aq = self.cmb_audio_quality.findText(conf.get("audio_quality", "320 kbps"))
        if idx_aq >= 0:
            self.cmb_audio_quality.setCurrentIndex(idx_aq)
        idx_sr = self.cmb_audio_sample_rate.findText(conf.get("audio_sample_rate", "Auto"))
        if idx_sr >= 0:
            self.cmb_audio_sample_rate.setCurrentIndex(idx_sr)
        idx_ch = self.cmb_audio_channels.findText(conf.get("audio_channels", "Auto"))
        if idx_ch >= 0:
            self.cmb_audio_channels.setCurrentIndex(idx_ch)

        if "embed_metadata" in conf:
            self.chk_adv_metadata.setChecked(bool(conf["embed_metadata"]))
        if "download_thumbnail" in conf and hasattr(self, "chk_adv_thumbnail"):
            self.chk_adv_thumbnail.setChecked(bool(conf["download_thumbnail"]))
        if "sponsorblock_enabled" in conf:
            self.chk_adv_sponsor.setChecked(bool(conf["sponsorblock_enabled"]))
        if "download_subtitles" in conf:
            self.subtitles_config["download_subtitles"] = bool(conf["download_subtitles"])
            if "embed_subtitles" in conf:
                self.subtitles_config["embed_subtitles"] = bool(conf["embed_subtitles"])

    def save_as_preset(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter a name for this custom preset:")
        if ok and name.strip():
            conf = {
                "download_type": "Audio" if self.btn_mode_audio.property("checked") else ("Dual Mode" if self.btn_mode_dual.property("checked") else "Video"),
                "video_quality": self.cmb_video_quality.currentText(),
                "video_format": self.cmb_video_format.currentText(),
                "audio_format": self.cmb_audio_format.currentText(),
                "audio_quality": self.cmb_audio_quality.currentText(),
                "audio_sample_rate": self.cmb_audio_sample_rate.currentText(),
                "audio_channels": self.cmb_audio_channels.currentText(),
                "embed_metadata": self.chk_adv_metadata.isChecked(),
                "download_thumbnail": self.chk_adv_thumbnail.isChecked() if hasattr(self, "chk_adv_thumbnail") else False,
                "sponsorblock_enabled": self.chk_adv_sponsor.isChecked(),
                "download_subtitles": self.subtitles_config.get("download_subtitles", False)
            }
            succ, msg = media_tools.PresetManager.save_preset(name.strip(), conf)
            if succ:
                self.refresh_presets_combo()
                for i in range(self.cmb_presets.count()):
                    if name.strip() in self.cmb_presets.itemText(i):
                        self.cmb_presets.setCurrentIndex(i)
                        break
                QMessageBox.information(self, "Preset Saved", msg)
            else:
                QMessageBox.warning(self, "Error", msg)

    def open_presets_dialog(self):
        dlg = PresetsDialog(self)
        dlg.sig_preset_selected.connect(self.apply_preset_dict)
        if dlg.exec():
            self.refresh_presets_combo()

    def open_subtitles_dialog(self):
        dlg = SubtitlesDialog(self.active_media_info or {}, self.subtitles_config, self)
        dlg.sig_subtitles_configured.connect(self.on_subtitles_configured)
        dlg.exec()

    def on_subtitles_configured(self, cfg: Dict[str, Any]):
        self.subtitles_config.update(cfg)
        langs = cfg.get("subtitle_lang", "")
        if not cfg.get("download_subtitles") or not langs:
            self.lbl_prev_subs.setText("Subtitles: Disabled")
            self.lbl_adv_subs_status.setText("Subtitles: Disabled")
        else:
            mode_desc = "Embed" if cfg.get("embed_subtitles") else ("Sub-only" if cfg.get("sub_only") else "Separate")
            self.lbl_prev_subs.setText(f"Subtitles: {langs} ({mode_desc})")
            self.lbl_adv_subs_status.setText(f"Subtitles: {langs} ({mode_desc})")

    def enqueue_from_downloader(self):
        url = self.txt_url.text().strip()
        is_valid, _ = core.validate_url(url)
        if not is_valid:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid media URL before adding to queue.")
            return

        mode = "Video"
        if self.btn_mode_audio.property("checked"):
            mode = "Audio"
        elif self.btn_mode_dual.property("checked"):
            mode = "Dual Mode"

        title = self.active_media_info.get("title", "Untitled Media") if self.active_media_info else "Queued Media"
        thumb = self.active_media_info.get("thumbnail") if self.active_media_info else None
        platform = self.active_media_info.get("platform", "Web") if self.active_media_info else "Web"

        job_id = self.queue_mgr.enqueue_job(
            url=url,
            title=title,
            download_type=mode,
            video_quality=self.cmb_video_quality.currentText(),
            video_format=self.cmb_video_format.currentText(),
            audio_format=self.cmb_audio_format.currentText(),
            audio_quality=self.cmb_audio_quality.currentText(),
            destination=self.txt_path.text().strip(),
            thumbnail=thumb,
            platform=platform,
            extra_params={
                "audio_sample_rate": self.cmb_audio_sample_rate.currentText(),
                "audio_channels": self.cmb_audio_channels.currentText(),
                "embed_metadata": self.chk_adv_metadata.isChecked(),
                "download_thumbnail": self.chk_adv_thumbnail.isChecked() if hasattr(self, "chk_adv_thumbnail") else True,
                "sponsorblock_enabled": self.chk_adv_sponsor.isChecked(),
                "sponsorblock_categories": self.config.get("sponsorblock_categories"),
                "filename_template": self.config.get("filename_template"),
                "download_subtitles": self.subtitles_config.get("download_subtitles", False),
                "subtitle_lang": self.subtitles_config.get("subtitle_lang"),
                "embed_subtitles": self.subtitles_config.get("embed_subtitles", False),
                "sub_only": self.subtitles_config.get("sub_only", False),
                "subtitle_format": self.subtitles_config.get("subtitle_format", "srt")
            }
        )
        QMessageBox.information(self, "Added to Queue", f"Job '{title[:50]}' was added to the download queue.")

    def open_downloaded_file(self):
        if not self.last_download_result:
            return
        target = self.last_download_result.get("video_file") or self.last_download_result.get("audio_file")
        if target and os.path.exists(target):
            try:
                os.startfile(target)
            except Exception as e:
                QMessageBox.warning(self, "Open File", f"Could not launch media player: {e}")
        else:
            QMessageBox.information(self, "Open File", "Media file not found on disk.")

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.txt_path.text())
        if path:
            self.txt_path.setText(path)
            self.config["download_path"] = path
            core.save_config(self.config)

    def open_download_folder(self):
        target = self.txt_path.text().strip()
        if os.path.exists(target):
            if self.last_download_result and self.last_download_result.get("video_file"):
                v_file = self.last_download_result["video_file"]
                if os.path.exists(v_file):
                    subprocess.Popen(f'explorer /select,"{v_file}"')
                    return
            subprocess.Popen(f'explorer "{target}"')

    def open_settings(self):
        dlg = SettingsDialog(self, self.config)
        if dlg.exec():
            self.config = core.load_config()
            self.txt_path.setText(self.config.get("download_path", core.DEFAULT_DOWNLOAD_PATH))
            app_inst = QApplication.instance()
            if app_inst:
                if self.config.get("language") == "fa":
                    app_inst.setLayoutDirection(Qt.RightToLeft)
                else:
                    app_inst.setLayoutDirection(Qt.LeftToRight)

    def open_history(self):
        self.switch_nav(3)

    def reset_hud(self):
        self.progress_bar.setValue(0)
        self.lbl_percent.setText("0.0%")
        self.lbl_task_status.setText("Ready")
        self.lbl_speed.setText("Speed: --")
        self.lbl_eta.setText("ETA: --")
        self.lbl_size.setText("Size: --")

    # --- ANALYSIS FLOW ---
    def on_analyze_clicked(self):
        if self.inspect_worker and self.inspect_worker.isRunning():
            self.inspect_worker.cancel()
            self.btn_analyze.setText("Analyze")
            self.btn_analyze.setIcon(get_icon("search", "#FFFFFF", 16))
            self.lbl_task_status.setText("Analysis cancelled.")
            self.lbl_url_feedback.setText("Metadata analysis cancelled by operator.")
            self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.TEXT_MUTED};")
            return

        url = self.txt_url.text().strip()
        is_valid, reason = core.validate_url(url)
        if not is_valid:
            self.lbl_url_feedback.setText(reason)
            self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.ERROR};")
            return

        self.btn_analyze.setText("Cancel Analysis")
        self.btn_analyze.setIcon(get_icon("x_circle", "#FFFFFF", 16))
        self.lbl_task_status.setText("Analyzing media metadata...")
        self.lbl_url_feedback.setText("Fetching metadata from source...")
        self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.TEXT_MUTED};")

        proxy = self.config.get("proxy_url") if self.config.get("proxy_enabled") else None

        self.inspect_worker = core.InspectWorker(url, proxy)
        self.inspect_worker.sig_completed.connect(self.on_inspect_completed)
        self.inspect_worker.sig_failed.connect(self.on_inspect_failed)
        self.inspect_worker.start()

    def on_inspect_completed(self, data: Dict[str, Any]):
        self.btn_analyze.setText("Analyze")
        self.btn_analyze.setIcon(get_icon("search", "#FFFFFF", 16))
        self.active_media_info = data

        # Populate Preview Card
        self.lbl_prev_title.setText(data.get("title", "Untitled Media"))
        if data.get("is_playlist"):
            self.lbl_prev_channel.setText(f"Playlist ({data.get('playlist_count')} items) • {data.get('uploader')}")
        else:
            self.lbl_prev_channel.setText(f"Creator: {data.get('uploader')}")
        self.lbl_prev_duration.setText(f"Duration: {data.get('duration')}")
        self.lbl_prev_platform.setText(f"Platform: {data.get('platform', 'Web')}")
        self.lbl_prev_date.setText(f"Uploaded: {data.get('upload_date', '--')}")

        res_list = data.get("resolutions", [])
        self.lbl_prev_res.setText(f"Resolutions: {', '.join(res_list[:5])}")

        # Codecs & FPS
        v_c = "/".join(data.get("vcodecs", ["Auto"]))
        a_c = "/".join(data.get("acodecs", ["Auto"]))
        self.current_source_acodec = a_c
        fps_info = f" • {data['fps']}fps" if data.get("fps") else ""
        self.lbl_prev_codecs.setText(f"Codecs: {v_c} / {a_c}{fps_info}")
        self.on_audio_format_changed(self.cmb_audio_format.currentText())

        # Subtitles
        subs = data.get("subtitles", [])
        self.lbl_prev_subs.setText(f"Subtitles: {', '.join(subs) if subs else 'None'}")

        # File size estimation
        est_bytes = data.get("estimated_size", 0)
        if est_bytes and est_bytes > 0:
            if est_bytes > 1024 * 1024 * 1024:
                self.lbl_prev_size.setText(f"Est. Size: {est_bytes / (1024*1024*1024):.2f} GB")
            else:
                self.lbl_prev_size.setText(f"Est. Size: {est_bytes / (1024*1024):.1f} MB")
        else:
            self.lbl_prev_size.setText("Est. Size: Dynamic")

        # Update Quality ComboBox
        self.cmb_video_quality.clear()
        self.cmb_video_quality.addItems(res_list)

        self.preview_card.setVisible(True)
        self.lbl_task_status.setText("Media verified. Ready to download.")
        self.lbl_url_feedback.setText("Analysis successful.")
        self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.SUCCESS};")

        # Auto-suggest preset based on source URL domain (Phase 4 Automation)
        if self.config.get("auto_suggest_preset", True):
            try:
                import network_system
                suggested_preset = network_system.AutomationManager.match_preset_for_url(data.get("url", ""))
                if suggested_preset:
                    idx = self.cmb_presets.findText(suggested_preset, Qt.MatchContains)
                    if idx >= 0:
                        self.cmb_presets.setCurrentIndex(idx)
                        self.lbl_task_status.setText(f"Preset auto-matched: {suggested_preset}")
                        self.log_edit.appendPlainText(f"[AUTOMATION] Applied matched preset '{suggested_preset}' for media domain.")
            except Exception:
                pass

        # Load Thumbnail
        thumb_url = data.get("thumbnail")
        if thumb_url:
            self.thumb_worker = ThumbnailLoader(thumb_url)
            self.thumb_worker.sig_loaded.connect(self.lbl_thumb.setPixmap)
            self.thumb_worker.start()

    def on_inspect_failed(self, error: str):
        self.btn_analyze.setText("Analyze")
        self.btn_analyze.setIcon(get_icon("search", "#FFFFFF", 16))
        self.lbl_task_status.setText("Analysis failed.")
        self.lbl_url_feedback.setText(f"Error: {error[:90]}")
        self.lbl_url_feedback.setStyleSheet(f"color: {Tokens.ERROR};")
        self.log_edit.appendPlainText(f"[ANALYSIS ERROR] {error}")

    # --- DOWNLOAD FLOW ---
    def start_download(self):
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid Input", "Please provide a valid media URL.")
            return

        save_path = self.txt_path.text().strip()
        if not os.path.isdir(save_path):
            QMessageBox.critical(self, "Invalid Path", "Selected download directory does not exist.")
            return

        # Prepare parameters
        mode = "Video"
        if self.btn_mode_audio.property("checked"):
            mode = "Audio"
        elif self.btn_mode_dual.property("checked"):
            mode = "Dual Mode"

        subs_cfg = self.subtitles_config
        params = {
            "url": url,
            "download_path": save_path,
            "download_type": mode,
            "video_quality": self.cmb_video_quality.currentText(),
            "video_format": self.cmb_video_format.currentText(),
            "audio_format": self.cmb_audio_format.currentText(),
            "audio_quality": self.cmb_audio_quality.currentText(),
            "audio_sample_rate": self.cmb_audio_sample_rate.currentText(),
            "audio_channels": self.cmb_audio_channels.currentText(),
            "proxy_enabled": self.config.get("proxy_enabled", False),
            "proxy_url": self.config.get("proxy_url"),
            "embed_metadata": self.chk_adv_metadata.isChecked(),
            "download_thumbnail": self.chk_adv_thumbnail.isChecked() if hasattr(self, "chk_adv_thumbnail") else True,
            "sponsorblock_enabled": self.chk_adv_sponsor.isChecked(),
            "sponsorblock_categories": self.config.get("sponsorblock_categories", ["sponsor", "selfpromo", "interaction", "intro", "outro"]),
            "filename_template": self.config.get("filename_template", "%(title)s.%(ext)s"),
            "download_subtitles": subs_cfg.get("download_subtitles", self.config.get("download_subtitles", False)),
            "subtitle_lang": subs_cfg.get("subtitle_lang", self.config.get("subtitle_lang", "en,fa")),
            "embed_subtitles": subs_cfg.get("embed_subtitles", self.config.get("embed_subtitles", False)),
            "sub_only": subs_cfg.get("sub_only", False),
            "subtitle_format": subs_cfg.get("subtitle_format", "srt"),
            "socket_timeout": self.config.get("socket_timeout", 15),
            "network_retries": self.config.get("network_retries", 5),
            "retry_delay": self.config.get("retry_delay", 2),
            "fragment_retries": self.config.get("fragment_retries", 5),
            "concurrent_fragments": self.config.get("concurrent_fragments", 1),
            "rate_limit": self.config.get("rate_limit", "Unlimited"),
            "ip_protocol": self.config.get("ip_protocol", "Auto"),
            "custom_user_agent": self.config.get("custom_user_agent", ""),
            "browser_cookies": self.config.get("browser_cookies", "None"),
            "cookie_file": self.config.get("cookie_file", "")
        }

        self.btn_download.setText("Start Download")
        self.btn_download.setIcon(get_icon("download", "#FFFFFF", 16))
        self.btn_download.setEnabled(False)
        self.btn_open_file.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_analyze.setEnabled(False)
        self.reset_hud()

        self.download_worker = core.DownloadWorker(params)
        self.download_worker.sig_status.connect(self.on_download_status)
        self.download_worker.sig_progress.connect(self.on_download_progress)
        self.download_worker.sig_finished.connect(self.on_download_finished)
        self.download_worker.sig_error.connect(self.on_download_error)
        self.download_worker.sig_log.connect(self.log_edit.appendPlainText)
        self.download_worker.start()

    def cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.btn_cancel.setEnabled(False)

    def on_download_status(self, status: str):
        self.lbl_task_status.setText(status)

    def on_download_progress(self, prog: Dict[str, Any]):
        frac = prog.get("fraction", 0.0)
        self.progress_bar.setValue(int(frac * 1000))
        self.lbl_percent.setText(prog.get("percent_str", "0.0%"))
        self.lbl_speed.setText(f"Speed: {prog.get('speed', '--')}")
        self.lbl_eta.setText(f"ETA: {prog.get('eta', '--')}")

        downloaded = prog.get("downloaded_bytes", 0) / (1024 * 1024)
        total = prog.get("total_bytes", 0) / (1024 * 1024)
        if total > 0:
            self.lbl_size.setText(f"Size: {downloaded:.1f} MB / {total:.1f} MB")
        else:
            self.lbl_size.setText(f"Size: {downloaded:.1f} MB")

    def on_download_finished(self, result: Dict[str, Any]):
        self.btn_download.setText("Start Download")
        self.btn_download.setIcon(get_icon("download", "#FFFFFF", 16))
        self.btn_download.setEnabled(True)
        self.btn_open_file.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_analyze.setEnabled(True)
        self.progress_bar.setValue(1000)
        self.lbl_percent.setText("100%")
        self.lbl_task_status.setText("Completed")
        self.last_download_result = result

        # Persist completed download to history database
        out_file = result.get("video_file") or result.get("audio_file") or ""
        file_size = 0
        if out_file and os.path.exists(out_file):
            try:
                file_size = os.path.getsize(out_file)
            except Exception:
                pass

        title = self.active_media_info.get("title", "Untitled Media") if self.active_media_info else "Downloaded Media"
        url = self.txt_url.text().strip()
        mode = "Video"
        if self.btn_mode_audio.property("checked"):
            mode = "Audio"
        elif self.btn_mode_dual.property("checked"):
            mode = "Dual Mode"

        self.db.history.add_record(
            job_id=str(uuid.uuid4()),
            title=title,
            url=url,
            file_path=out_file,
            media_type=mode,
            file_size=file_size,
            duration=self.active_media_info.get("duration", "--:--") if self.active_media_info else "--:--"
        )

        QMessageBox.information(
            self,
            "Download Complete",
            "Media has been successfully downloaded and saved to disk."
        )

    def on_download_error(self, err_msg: str):
        self.btn_download.setText("Retry Download")
        self.btn_download.setIcon(get_icon("refresh_cw", "#FFFFFF", 16))
        self.btn_download.setEnabled(True)
        self.btn_open_file.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_analyze.setEnabled(True)
        self.lbl_task_status.setText("Failed")
        self.lbl_url_feedback.setText(f"Error: {err_msg[:80]}")

        QMessageBox.critical(
            self,
            "Download Error",
            f"An error occurred while downloading:\n\n{err_msg}\n\n"
            "Tip: If connections are filtered, check proxy configuration in Settings."
        )
