"""
History & Media Library Dialog for YTDownloader Pro
Displays completed downloads, search filter, file verification, and explorer actions.
"""
import os
import sys
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QWidget,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from theme import Tokens
from icons import get_icon
import database


class HistoryDialog(QDialog):
    def __init__(self, parent=None, db: Optional[database.Database] = None):
        super().__init__(parent)
        self.db = db or database.get_db()

        self.setWindowTitle("Download History — YTDownloader Pro")
        self.resize(680, 520)
        self.setMinimumSize(600, 440)

        self.init_ui()
        self.load_history()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header & Search Row
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        lbl_title = QLabel("Download History")
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        header_row.addWidget(lbl_title)

        header_row.addStretch()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search history...")
        self.txt_search.setFixedWidth(220)
        self.txt_search.textChanged.connect(self.load_history)
        header_row.addWidget(self.txt_search)

        self.btn_clear_all = QPushButton("Clear All")
        self.btn_clear_all.setIcon(get_icon("x_circle", Tokens.TEXT_MUTED, 14))
        self.btn_clear_all.clicked.connect(self.clear_all_history)
        header_row.addWidget(self.btn_clear_all)

        main_layout.addLayout(header_row)

        # History List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {Tokens.BG_SECONDARY};
                border: 1px solid {Tokens.BORDER};
                border-radius: {Tokens.RADIUS_MD};
                padding: 6px;
            }}
            QListWidget::item {{
                background-color: {Tokens.SURFACE_ELEVATED};
                border: 1px solid {Tokens.BORDER};
                border-radius: {Tokens.RADIUS_SM};
                margin-bottom: 6px;
                padding: 10px;
            }}
            QListWidget::item:hover {{
                border-color: {Tokens.BORDER_HOVER};
            }}
        """)
        main_layout.addWidget(self.list_widget)

        # Empty State Label
        self.lbl_empty = QLabel("No download history yet.")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setProperty("muted", True)
        self.lbl_empty.setStyleSheet("font-size: 13px; padding: 40px;")
        main_layout.addWidget(self.lbl_empty)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_close)
        main_layout.addLayout(footer)

    def load_history(self):
        search_query = self.txt_search.text().strip()
        records = self.db.history.get_history(search=search_query)

        self.list_widget.clear()

        if not records:
            self.list_widget.setVisible(False)
            self.lbl_empty.setVisible(True)
            self.lbl_empty.setText("No matching downloads found." if search_query else "No download history yet.")
            return

        self.list_widget.setVisible(True)
        self.lbl_empty.setVisible(False)

        for rec in records:
            item = QListWidgetItem(self.list_widget)
            widget = self._create_item_widget(rec)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)

    def _create_item_widget(self, rec: Dict[str, Any]) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(12)

        # Icon based on type
        media_type = rec.get("media_type", "Video")
        icon_name = "music" if media_type == "Audio" else "video"
        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_icon(icon_name, Tokens.ACCENT, 22).pixmap(22, 22))
        layout.addWidget(lbl_icon)

        # Info Box
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        title = rec.get("title", "Untitled")
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-weight: 600; color: {Tokens.TEXT_PRIMARY}; font-size: 13px;")
        info_col.addWidget(lbl_title)

        file_path = rec.get("file_path", "")
        file_exists = os.path.exists(file_path) if file_path else False

        size_mb = rec.get("file_size", 0) / (1024 * 1024)
        size_str = f"{size_mb:.1f} MB" if size_mb > 0 else "Unknown size"
        date_str = rec.get("completed_at", "")[:16].replace("T", " ")

        status_text = "On Disk" if file_exists else "File Moved or Deleted"
        status_color = Tokens.SUCCESS if file_exists else Tokens.WARNING

        meta_lbl = QLabel(f"{date_str} • {size_str} • <span style='color: {status_color};'>{status_text}</span>")
        meta_lbl.setProperty("muted", True)
        info_col.addWidget(meta_lbl)

        layout.addLayout(info_col)
        layout.addStretch()

        # Action Buttons
        btn_open = QPushButton("Open")
        btn_open.setIcon(get_icon("play", Tokens.TEXT_PRIMARY, 13))
        btn_open.setEnabled(file_exists)
        btn_open.clicked.connect(lambda _, p=file_path: self._open_file(p))
        layout.addWidget(btn_open)

        btn_folder = QPushButton("Folder")
        btn_folder.setIcon(get_icon("folder_open", Tokens.TEXT_PRIMARY, 13))
        btn_folder.clicked.connect(lambda _, p=file_path: self._open_folder(p))
        layout.addWidget(btn_folder)

        btn_delete = QPushButton()
        btn_delete.setIcon(get_icon("x", Tokens.TEXT_SECONDARY, 14))
        btn_delete.setToolTip("Remove from history")
        btn_delete.setFixedWidth(30)
        btn_delete.clicked.connect(lambda _, r_id=rec["id"]: self._delete_record(r_id))
        layout.addWidget(btn_delete)

        return widget

    def _open_file(self, path: str):
        if path and os.path.exists(path):
            os.startfile(path)

    def _open_folder(self, path: str):
        if path and os.path.exists(path):
            subprocess.Popen(f'explorer /select,"{path}"')
        elif path and os.path.exists(os.path.dirname(path)):
            subprocess.Popen(f'explorer "{os.path.dirname(path)}"')

    def _delete_record(self, record_id: int):
        self.db.history.delete_record(record_id)
        self.load_history()

    def _delete_record(self, record_id: int):
        self.db.history.delete_record(record_id)
        self.load_history()

    def clear_all_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all download history records? (Files on disk will not be deleted)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.history.clear_history()
            self.load_history()
