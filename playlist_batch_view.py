"""
Playlists & Batch URL Ingestion View for YTDownloader Pro
Supports analyzing full playlists with selectable items and multi-URL batch queues.
"""
import os
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QCheckBox, QFileDialog, QMessageBox, QFrame,
    QTabWidget, QLineEdit
)
from PySide6.QtCore import Qt

from theme import Tokens
from icons import get_icon
import core
from queue_manager import QueueManager
import playlist_batch


class PlaylistBatchView(QWidget):
    def __init__(self, queue_mgr: QueueManager, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.queue_mgr = queue_mgr
        self.config = config
        self.playlist_data: Optional[Dict[str, Any]] = None
        self.playlist_worker: Optional[playlist_batch.PlaylistInspectWorker] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Tab Widget: Playlist Explorer vs Batch URL Importer
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {Tokens.BORDER};
                background: {Tokens.BG_MAIN};
                border-radius: {Tokens.RADIUS_MD};
            }}
            QTabBar::tab {{
                background: {Tokens.BG_SECONDARY};
                color: {Tokens.TEXT_SECONDARY};
                padding: 8px 16px;
                border-top-left-radius: {Tokens.RADIUS_SM};
                border-top-right-radius: {Tokens.RADIUS_SM};
                margin-right: 4px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {Tokens.SURFACE_ELEVATED};
                color: {Tokens.TEXT_PRIMARY};
                border-bottom: 2px solid {Tokens.ACCENT};
            }}
        """)

        # Tab 1: Playlist Explorer
        tab_playlist = QWidget()
        self.setup_playlist_tab(tab_playlist)
        self.tabs.addTab(tab_playlist, "Playlist Explorer")

        # Tab 2: Batch URL Importer
        tab_batch = QWidget()
        self.setup_batch_tab(tab_batch)
        self.tabs.addTab(tab_batch, "Batch URL Importer")

        layout.addWidget(self.tabs)

    # --- 1. PLAYLIST EXPLORER ---
    def setup_playlist_tab(self, parent: QWidget):
        p_layout = QVBoxLayout(parent)
        p_layout.setContentsMargins(16, 14, 16, 14)
        p_layout.setSpacing(10)

        # Input Row
        input_card = QFrame()
        input_card.setProperty("card", "true")
        i_layout = QHBoxLayout(input_card)
        i_layout.setContentsMargins(12, 10, 12, 10)
        i_layout.setSpacing(8)

        self.txt_playlist_url = QLineEdit()
        self.txt_playlist_url.setPlaceholderText("Paste YouTube Playlist URL...")
        i_layout.addWidget(self.txt_playlist_url)

        self.btn_inspect_playlist = QPushButton("Analyze Playlist")
        self.btn_inspect_playlist.setIcon(get_icon("search", "#FFFFFF", 15))
        self.btn_inspect_playlist.setProperty("primary", True)
        self.btn_inspect_playlist.clicked.connect(self.on_inspect_playlist)
        i_layout.addWidget(self.btn_inspect_playlist)

        p_layout.addWidget(input_card)

        # Playlist Info & Options Header
        self.p_info_card = QFrame()
        self.p_info_card.setProperty("card", "elevated")
        self.p_info_card.setVisible(False)
        pi_layout = QVBoxLayout(self.p_info_card)
        pi_layout.setContentsMargins(14, 10, 14, 10)
        pi_layout.setSpacing(8)

        self.lbl_p_title = QLabel("Playlist: --")
        self.lbl_p_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        pi_layout.addWidget(self.lbl_p_title)

        options_row = QHBoxLayout()
        options_row.setSpacing(16)

        self.chk_subfolder = QCheckBox("Create dedicated playlist folder")
        self.chk_subfolder.setChecked(True)
        options_row.addWidget(self.chk_subfolder)

        self.chk_numbering = QCheckBox("Preserve playlist numbering (01, 02...)")
        self.chk_numbering.setChecked(True)
        options_row.addWidget(self.chk_numbering)

        options_row.addStretch()

        self.btn_sel_all = QPushButton("Select All")
        self.btn_sel_all.clicked.connect(lambda: self.toggle_playlist_selection(True))
        options_row.addWidget(self.btn_sel_all)

        self.btn_desel_all = QPushButton("Deselect All")
        self.btn_desel_all.clicked.connect(lambda: self.toggle_playlist_selection(False))
        options_row.addWidget(self.btn_desel_all)

        pi_layout.addLayout(options_row)
        p_layout.addWidget(self.p_info_card)

        # Playlist Items Table
        self.tbl_playlist = QTableWidget()
        self.tbl_playlist.setColumnCount(5)
        self.tbl_playlist.setHorizontalHeaderLabels(["Select", "#", "Title", "Duration", "Creator"])
        self.tbl_playlist.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_playlist.verticalHeader().setVisible(False)
        p_layout.addWidget(self.tbl_playlist)

        # Enqueue Bar
        eq_row = QHBoxLayout()
        eq_row.setSpacing(10)

        self.lbl_p_summary = QLabel("Enter playlist URL to view videos.")
        self.lbl_p_summary.setProperty("muted", True)
        eq_row.addWidget(self.lbl_p_summary)

        eq_row.addStretch()

        self.cmb_p_mode = QComboBox()
        self.cmb_p_mode.addItems(["Video (MP4)", "Audio (MP3 320k)", "Dual Mode"])
        eq_row.addWidget(self.cmb_p_mode)

        self.btn_enqueue_playlist = QPushButton("Add Selected to Queue")
        self.btn_enqueue_playlist.setIcon(get_icon("download", "#FFFFFF", 15))
        self.btn_enqueue_playlist.setProperty("primary", True)
        self.btn_enqueue_playlist.setEnabled(False)
        self.btn_enqueue_playlist.clicked.connect(self.enqueue_selected_playlist)
        eq_row.addWidget(self.btn_enqueue_playlist)

        p_layout.addLayout(eq_row)

    # --- 2. BATCH URL IMPORTER ---
    def setup_batch_tab(self, parent: QWidget):
        b_layout = QVBoxLayout(parent)
        b_layout.setContentsMargins(16, 14, 16, 14)
        b_layout.setSpacing(10)

        # Text Area for pasted URLs
        lbl = QLabel("Paste URLs (one per line) or import from a TXT file:")
        lbl.setProperty("secondary", True)
        b_layout.addWidget(lbl)

        self.txt_batch = QPlainTextEdit()
        self.txt_batch.setPlaceholderText("https://www.youtube.com/watch?v=...\nhttps://youtu.be/...\nhttps://vimeo.com/...")
        self.txt_batch.setFixedHeight(120)
        b_layout.addWidget(self.txt_batch)

        # Control Row
        c_row = QHBoxLayout()
        c_row.setSpacing(10)

        self.btn_import_txt = QPushButton("Import TXT File...")
        self.btn_import_txt.setIcon(get_icon("folder", Tokens.TEXT_PRIMARY, 14))
        self.btn_import_txt.clicked.connect(self.import_txt_file)
        c_row.addWidget(self.btn_import_txt)

        self.btn_validate_batch = QPushButton("Validate & Parse")
        self.btn_validate_batch.setIcon(get_icon("search", Tokens.TEXT_PRIMARY, 14))
        self.btn_validate_batch.clicked.connect(self.validate_batch_urls)
        c_row.addWidget(self.btn_validate_batch)

        self.lbl_batch_status = QLabel("")
        self.lbl_batch_status.setProperty("secondary", True)
        c_row.addWidget(self.lbl_batch_status)

        c_row.addStretch()
        b_layout.addLayout(c_row)

        # Batch Table
        self.tbl_batch = QTableWidget()
        self.tbl_batch.setColumnCount(3)
        self.tbl_batch.setHorizontalHeaderLabels(["Select", "URL", "Validation Status"])
        self.tbl_batch.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_batch.verticalHeader().setVisible(False)
        b_layout.addWidget(self.tbl_batch)

        # Enqueue Bar
        eq_row = QHBoxLayout()
        eq_row.setSpacing(10)

        lbl_set = QLabel("Shared Profile:")
        lbl_set.setProperty("secondary", True)
        eq_row.addWidget(lbl_set)

        self.cmb_b_mode = QComboBox()
        self.cmb_b_mode.addItems(["Video (MP4)", "Audio (MP3 320k)", "Dual Mode"])
        eq_row.addWidget(self.cmb_b_mode)

        eq_row.addStretch()

        self.btn_enqueue_batch = QPushButton("Add Valid to Queue")
        self.btn_enqueue_batch.setIcon(get_icon("download", "#FFFFFF", 15))
        self.btn_enqueue_batch.setProperty("primary", True)
        self.btn_enqueue_batch.setEnabled(False)
        self.btn_enqueue_batch.clicked.connect(self.enqueue_selected_batch)
        eq_row.addWidget(self.btn_enqueue_batch)

        b_layout.addLayout(eq_row)

    # --- PLAYLIST ACTIONS ---
    def on_inspect_playlist(self):
        url = self.txt_playlist_url.text().strip()
        is_valid, reason = core.validate_url(url)
        if not is_valid:
            QMessageBox.warning(self, "Invalid URL", reason)
            return

        self.btn_inspect_playlist.setEnabled(False)
        self.btn_inspect_playlist.setText("Analyzing...")
        self.lbl_p_summary.setText("Fetching playlist index...")

        proxy = self.config.get("proxy_url") if self.config.get("proxy_enabled") else None
        self.playlist_worker = playlist_batch.PlaylistInspectWorker(url, proxy)
        self.playlist_worker.sig_completed.connect(self.on_playlist_loaded)
        self.playlist_worker.sig_failed.connect(self.on_playlist_failed)
        self.playlist_worker.start()

    def on_playlist_loaded(self, data: Dict[str, Any]):
        self.btn_inspect_playlist.setEnabled(True)
        self.btn_inspect_playlist.setText("Analyze Playlist")
        self.playlist_data = data

        self.lbl_p_title.setText(f"{data.get('title', 'Playlist')} • {data.get('uploader')} ({data.get('count', 0)} videos)")
        self.p_info_card.setVisible(True)

        items = data.get("items", [])
        self.tbl_playlist.setRowCount(len(items))

        for row, item in enumerate(items):
            # Checkbox
            chk = QCheckBox()
            chk.setChecked(True)
            chk_widget = QWidget()
            ch_layout = QHBoxLayout(chk_widget)
            ch_layout.addWidget(chk)
            ch_layout.setAlignment(Qt.AlignCenter)
            ch_layout.setContentsMargins(0, 0, 0, 0)
            self.tbl_playlist.setCellWidget(row, 0, chk_widget)

            # Index
            idx_item = QTableWidgetItem(str(item.get("index", row + 1)))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.tbl_playlist.setItem(row, 1, idx_item)

            # Title
            t_item = QTableWidgetItem(item.get("title", ""))
            self.tbl_playlist.setItem(row, 2, t_item)

            # Duration
            d_item = QTableWidgetItem(item.get("duration", "--:--"))
            d_item.setTextAlignment(Qt.AlignCenter)
            self.tbl_playlist.setItem(row, 3, d_item)

            # Creator
            u_item = QTableWidgetItem(item.get("uploader", ""))
            self.tbl_playlist.setItem(row, 4, u_item)

        self.btn_enqueue_playlist.setEnabled(len(items) > 0)
        self.lbl_p_summary.setText(f"Loaded {len(items)} videos. Ready to enqueue.")

    def on_playlist_failed(self, error: str):
        self.btn_inspect_playlist.setEnabled(True)
        self.btn_inspect_playlist.setText("Analyze Playlist")
        self.lbl_p_summary.setText(f"Analysis failed: {error[:60]}")
        QMessageBox.critical(self, "Playlist Error", f"Could not analyze playlist:\n\n{error}")

    def toggle_playlist_selection(self, select_all: bool):
        for row in range(self.tbl_playlist.rowCount()):
            w = self.tbl_playlist.cellWidget(row, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk:
                    chk.setChecked(select_all)

    def enqueue_selected_playlist(self):
        if not self.playlist_data:
            return

        base_dest = self.config.get("download_path", core.DEFAULT_DOWNLOAD_PATH)
        if self.chk_subfolder.isChecked():
            clean_title = core.sanitize_filename(self.playlist_data.get("title", "Playlist"))
            dest_folder = os.path.join(base_dest, clean_title)
        else:
            dest_folder = base_dest

        # Determine download profile
        mode_text = self.cmb_p_mode.currentText()
        if "Audio" in mode_text:
            m_type, v_q, v_f, a_f, a_q = "Audio", "Best Available", "MP4", "MP3", "320 kbps"
        elif "Dual" in mode_text:
            m_type, v_q, v_f, a_f, a_q = "Dual Mode", "Best Available", "MP4", "MP3", "320 kbps"
        else:
            m_type, v_q, v_f, a_f, a_q = "Video", "Best Available", "MP4", "MP3", "320 kbps"

        items = self.playlist_data.get("items", [])
        enqueued_count = 0

        for row in range(self.tbl_playlist.rowCount()):
            w = self.tbl_playlist.cellWidget(row, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk and chk.isChecked() and row < len(items):
                    item = items[row]
                    idx = item.get("index", row + 1)
                    title = item.get("title", "Untitled")
                    if self.chk_numbering.isChecked():
                        tmpl = f"{idx:02d} - %(title)s.%(ext)s"
                    else:
                        tmpl = "%(title)s.%(ext)s"

                    job_params = {
                        "url": item["url"],
                        "title": f"{idx:02d} - {title}" if self.chk_numbering.isChecked() else title,
                        "download_path": dest_folder,
                        "download_type": m_type,
                        "video_quality": v_q,
                        "video_format": v_f,
                        "audio_format": a_f,
                        "audio_quality": a_q,
                        "filename_template": tmpl,
                        "proxy_enabled": self.config.get("proxy_enabled", False),
                        "proxy_url": self.config.get("proxy_url"),
                        "embed_metadata": self.config.get("embed_metadata", True)
                    }
                    self.queue_mgr.enqueue_job(job_params, auto_start=False)
                    enqueued_count += 1

        self.queue_mgr.process_queue()
        QMessageBox.information(
            self,
            "Playlist Enqueued",
            f"Successfully added {enqueued_count} videos from the playlist to the download queue."
        )

    # --- BATCH ACTIONS ---
    def import_txt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open URLs File", "", "Text Files (*.txt);;All Files (*.*)")
        if file_path:
            urls = playlist_batch.parse_urls_from_file(file_path)
            self.txt_batch.setPlainText("\n".join(urls))
            self.validate_batch_urls()

    def validate_batch_urls(self):
        text = self.txt_batch.toPlainText()
        raw_urls = playlist_batch.parse_urls_from_text(text)

        seen = set()
        valid_items = []
        rejected = 0
        duplicates = 0

        for u in raw_urls:
            is_valid, _ = core.validate_url(u)
            if not is_valid:
                rejected += 1
                continue
            clean = core.clean_url(u)
            if clean in seen:
                duplicates += 1
                continue
            seen.add(clean)
            valid_items.append(clean)

        self.tbl_batch.setRowCount(len(valid_items))
        for row, u in enumerate(valid_items):
            chk = QCheckBox()
            chk.setChecked(True)
            chk_widget = QWidget()
            ch_layout = QHBoxLayout(chk_widget)
            ch_layout.addWidget(chk)
            ch_layout.setAlignment(Qt.AlignCenter)
            ch_layout.setContentsMargins(0, 0, 0, 0)
            self.tbl_batch.setCellWidget(row, 0, chk_widget)

            u_item = QTableWidgetItem(u)
            self.tbl_batch.setItem(row, 1, u_item)

            st_item = QTableWidgetItem("✓ Ready to Enqueue")
            st_item.setForeground(Qt.green)
            self.tbl_batch.setItem(row, 2, st_item)

        self.lbl_batch_status.setText(f"Accepted: {len(valid_items)} | Duplicate: {duplicates} | Invalid: {rejected}")
        self.btn_enqueue_batch.setEnabled(len(valid_items) > 0)

    def enqueue_selected_batch(self):
        mode_text = self.cmb_b_mode.currentText()
        if "Audio" in mode_text:
            m_type, v_q, v_f, a_f, a_q = "Audio", "Best Available", "MP4", "MP3", "320 kbps"
        elif "Dual" in mode_text:
            m_type, v_q, v_f, a_f, a_q = "Dual Mode", "Best Available", "MP4", "MP3", "320 kbps"
        else:
            m_type, v_q, v_f, a_f, a_q = "Video", "Best Available", "MP4", "MP3", "320 kbps"

        dest_folder = self.config.get("download_path", core.DEFAULT_DOWNLOAD_PATH)
        enqueued_count = 0

        for row in range(self.tbl_batch.rowCount()):
            w = self.tbl_batch.cellWidget(row, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    url_item = self.tbl_batch.item(row, 1)
                    if url_item:
                        u = url_item.text().strip()
                        job_params = {
                            "url": u,
                            "title": "Batch Download Media",
                            "download_path": dest_folder,
                            "download_type": m_type,
                            "video_quality": v_q,
                            "video_format": v_f,
                            "audio_format": a_f,
                            "audio_quality": a_q,
                            "proxy_enabled": self.config.get("proxy_enabled", False),
                            "proxy_url": self.config.get("proxy_url"),
                            "embed_metadata": self.config.get("embed_metadata", True)
                        }
                        self.queue_mgr.enqueue_job(job_params, auto_start=False)
                        enqueued_count += 1

        self.queue_mgr.process_queue()
        QMessageBox.information(
            self,
            "Batch Enqueued",
            f"Successfully added {enqueued_count} URLs to the download queue."
        )
