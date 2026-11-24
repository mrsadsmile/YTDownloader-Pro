"""
History View for YTDownloader Pro
Filterable and searchable record of downloaded items with file relinking, retrying, and disk status.
"""
import os
import subprocess
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QFileDialog, QFrame, QApplication
)
from PySide6.QtCore import Qt

from theme import Tokens
from icons import get_icon
import database
from queue_manager import QueueManager


class HistoryView(QWidget):
    def __init__(self, db: database.Database, queue_mgr: Optional[QueueManager] = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.queue_mgr = queue_mgr
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Filter & Search Card
        filter_card = QFrame()
        filter_card.setProperty("card", "true")
        f_layout = QVBoxLayout(filter_card)
        f_layout.setContentsMargins(14, 12, 14, 12)
        f_layout.setSpacing(10)

        # Top row: Search input
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search download history by title, URL, or path...")
        self.txt_search.textChanged.connect(self.refresh_table)
        top_row.addWidget(self.txt_search)

        self.btn_clear_search = QPushButton()
        self.btn_clear_search.setIcon(get_icon("x", Tokens.TEXT_MUTED, 14))
        self.btn_clear_search.setToolTip("Clear Search")
        self.btn_clear_search.setFixedWidth(32)
        self.btn_clear_search.clicked.connect(lambda: self.txt_search.clear())
        top_row.addWidget(self.btn_clear_search)

        f_layout.addLayout(top_row)

        # Second row: Filter dropdowns
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        # Media Type Filter
        lbl_type = QLabel("Type:")
        lbl_type.setProperty("secondary", True)
        filter_row.addWidget(lbl_type)
        self.cmb_filter_type = QComboBox()
        self.cmb_filter_type.addItems(["All", "Video", "Audio", "Dual Mode"])
        self.cmb_filter_type.currentTextChanged.connect(self.refresh_table)
        filter_row.addWidget(self.cmb_filter_type)

        # Platform Filter
        lbl_plat = QLabel("Platform:")
        lbl_plat.setProperty("secondary", True)
        filter_row.addWidget(lbl_plat)
        self.cmb_filter_plat = QComboBox()
        self.cmb_filter_plat.addItems(["All", "YouTube", "SoundCloud", "Vimeo", "Web"])
        self.cmb_filter_plat.currentTextChanged.connect(self.refresh_table)
        filter_row.addWidget(self.cmb_filter_plat)

        # Sort Dropdown
        lbl_sort = QLabel("Sort:")
        lbl_sort.setProperty("secondary", True)
        filter_row.addWidget(lbl_sort)
        self.cmb_sort = QComboBox()
        self.cmb_sort.addItems(["Newest First", "Oldest First", "Title (A-Z)", "Size (Largest)"])
        self.cmb_sort.currentTextChanged.connect(self.refresh_table)
        filter_row.addWidget(self.cmb_sort)

        filter_row.addStretch()

        self.btn_clear_all_history = QPushButton("Clear History")
        self.btn_clear_all_history.setIcon(get_icon("trash_2", Tokens.DANGER, 14))
        self.btn_clear_all_history.setProperty("danger", True)
        self.btn_clear_all_history.clicked.connect(self.on_clear_all_history)
        filter_row.addWidget(self.btn_clear_all_history)

        f_layout.addLayout(filter_row)
        layout.addWidget(filter_card)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Date", "Title", "Type", "Size", "Duration", "Disk Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Tokens.BG_MAIN};
                gridline-color: {Tokens.BORDER};
                border: 1px solid {Tokens.BORDER};
                border-radius: {Tokens.RADIUS_MD};
            }}
            QHeaderView::section {{
                background-color: {Tokens.BG_SECONDARY};
                color: {Tokens.TEXT_SECONDARY};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {Tokens.BORDER};
                font-weight: 600;
            }}
        """)
        layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        search = self.txt_search.text().strip()
        type_filter = self.cmb_filter_type.currentText()
        plat_filter = self.cmb_filter_plat.currentText()
        sort_choice = self.cmb_sort.currentText()

        sort_key = "completed_at_desc"
        if sort_choice == "Oldest First":
            sort_key = "completed_at_asc"
        elif sort_choice == "Title (A-Z)":
            sort_key = "title_asc"
        elif sort_choice == "Size (Largest)":
            sort_key = "size_desc"

        records = self.db.history.get_history(
            search=search,
            platform=plat_filter,
            media_type=type_filter,
            sort_by=sort_key
        )

        self.table.setRowCount(len(records))

        for row, rec in enumerate(records):
            rec_id = rec["id"]
            file_path = rec.get("file_path", "")
            exists = os.path.exists(file_path) if file_path else False

            # 0. Date
            date_str = rec.get("completed_at", "")[:10]
            d_item = QTableWidgetItem(date_str)
            d_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, d_item)

            # 1. Title
            t_item = QTableWidgetItem(rec.get("title", "Untitled"))
            t_item.setToolTip(f"{rec.get('title')}\nURL: {rec.get('url')}\nPath: {file_path}")
            self.table.setItem(row, 1, t_item)

            # 2. Type
            m_item = QTableWidgetItem(rec.get("media_type", "Video"))
            m_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, m_item)

            # 3. Size
            sz = rec.get("file_size", 0)
            sz_str = f"{sz / (1024 * 1024):.1f} MB" if sz > 0 else "--"
            sz_item = QTableWidgetItem(sz_str)
            sz_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, sz_item)

            # 4. Duration
            dur_item = QTableWidgetItem(rec.get("duration", "--:--"))
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, dur_item)

            # 5. Disk Status badge
            if exists:
                st_item = QTableWidgetItem("● On Disk")
                st_item.setForeground(Qt.green)
            else:
                st_item = QTableWidgetItem("○ Moved/Deleted")
                st_item.setForeground(Qt.red)
            st_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, st_item)

            # 6. Action Buttons Widget
            actions_widget = QWidget()
            a_layout = QHBoxLayout(actions_widget)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            # Open File
            btn_play = QPushButton()
            btn_play.setIcon(get_icon("play", Tokens.TEXT_PRIMARY, 13))
            btn_play.setToolTip("Open in Media Player")
            btn_play.setFixedSize(26, 26)
            btn_play.setEnabled(exists)
            btn_play.clicked.connect(lambda _, p=file_path: self.open_file(p))
            a_layout.addWidget(btn_play)

            # Open Containing Folder
            btn_folder = QPushButton()
            btn_folder.setIcon(get_icon("folder_open", Tokens.TEXT_PRIMARY, 13))
            btn_folder.setToolTip("Open Containing Folder")
            btn_folder.setFixedSize(26, 26)
            btn_folder.setEnabled(exists)
            btn_folder.clicked.connect(lambda _, p=file_path: self.open_folder(p))
            a_layout.addWidget(btn_folder)

            # Copy URL
            btn_copy = QPushButton()
            btn_copy.setIcon(get_icon("clipboard", Tokens.TEXT_SECONDARY, 13))
            btn_copy.setToolTip("Copy Source URL")
            btn_copy.setFixedSize(26, 26)
            btn_copy.clicked.connect(lambda _, u=rec.get("url", ""): self.copy_url(u))
            a_layout.addWidget(btn_copy)

            # Locate / Relink Moved File
            if not exists:
                btn_relink = QPushButton()
                btn_relink.setIcon(get_icon("folder", Tokens.WARNING, 13))
                btn_relink.setToolTip("Locate Moved File on Disk")
                btn_relink.setFixedSize(26, 26)
                btn_relink.clicked.connect(lambda _, rid=rec_id, old_p=file_path: self.relink_file(rid, old_p))
                a_layout.addWidget(btn_relink)

            # Retry Download (if queue_mgr available)
            if self.queue_mgr and rec.get("url"):
                btn_retry = QPushButton()
                btn_retry.setIcon(get_icon("refresh_cw", Tokens.TEXT_MUTED, 13))
                btn_retry.setToolTip("Download Again (Add to Queue)")
                btn_retry.setFixedSize(26, 26)
                btn_retry.clicked.connect(lambda _, r=rec: self.retry_download(r))
                a_layout.addWidget(btn_retry)

            # Delete Record (does not delete file)
            btn_del = QPushButton()
            btn_del.setIcon(get_icon("x", Tokens.DANGER, 13))
            btn_del.setToolTip("Remove History Record")
            btn_del.setFixedSize(26, 26)
            btn_del.clicked.connect(lambda _, rid=rec_id: self.delete_record(rid))
            a_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 6, actions_widget)

    def open_file(self, path: str):
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.warning(self, "Open File", f"Could not launch file: {e}")

    def open_folder(self, path: str):
        if path and os.path.exists(path):
            subprocess.Popen(f'explorer /select,"{path}"')
        elif path and os.path.exists(os.path.dirname(path)):
            subprocess.Popen(f'explorer "{os.path.dirname(path)}"')

    def copy_url(self, url: str):
        if url:
            QApplication.clipboard().setText(url)
            QMessageBox.information(self, "Copied", "Media URL copied to clipboard.")

    def relink_file(self, record_id: int, old_path: str):
        base_dir = os.path.dirname(old_path) if old_path else ""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Moved File", base_dir, "All Files (*.*)")
        if file_path and os.path.exists(file_path):
            self.db.history.update_file_path(record_id, file_path)
            self.refresh_table()
            QMessageBox.information(self, "Relinked", "File path updated successfully in history.")

    def retry_download(self, rec: Dict[str, Any]):
        if self.queue_mgr:
            job_params = {
                "url": rec.get("url", ""),
                "title": rec.get("title", "Retried Download"),
                "download_type": rec.get("media_type", "Video"),
                "download_path": os.path.dirname(rec.get("file_path")) if rec.get("file_path") else "",
                "video_quality": rec.get("quality", "Best Available"),
                "video_format": rec.get("format", "MP4"),
                "audio_format": "MP3",
                "audio_quality": "320 kbps",
            }
            self.queue_mgr.enqueue_job(job_params)
            QMessageBox.information(self, "Job Enqueued", "Media added back to download queue.")

    def delete_record(self, record_id: int):
        self.db.history.delete_record(record_id)
        self.refresh_table()

    def on_clear_all_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to delete all history records?\n\n(Note: Your downloaded media files on disk will NOT be deleted.)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.history.clear_history()
            self.refresh_table()
