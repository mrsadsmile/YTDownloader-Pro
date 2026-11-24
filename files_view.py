"""
Files & Media Library View for YTDownloader Pro
Dedicated view for managing downloaded media on disk with safe Rename, Move, and Delete operations.
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QFileDialog, QInputDialog, QFrame,
    QApplication
)
from PySide6.QtCore import Qt

from theme import Tokens
from icons import get_icon, get_pixmap
import database
import core


class FilesView(QWidget):
    def __init__(self, db: database.Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Controls Card
        ctrl_card = QFrame()
        ctrl_card.setProperty("card", "true")
        c_layout = QHBoxLayout(ctrl_card)
        c_layout.setContentsMargins(14, 10, 14, 10)
        c_layout.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search downloaded files...")
        self.txt_search.textChanged.connect(self.refresh_files)
        c_layout.addWidget(self.txt_search)

        lbl_filter = QLabel("Filter:")
        lbl_filter.setProperty("secondary", True)
        c_layout.addWidget(lbl_filter)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["All Files", "Video", "Audio"])
        self.cmb_filter.currentTextChanged.connect(self.refresh_files)
        c_layout.addWidget(self.cmb_filter)

        c_layout.addStretch()

        self.btn_refresh = QPushButton("Refresh Library")
        self.btn_refresh.setIcon(get_icon("refresh_cw", Tokens.TEXT_PRIMARY, 14))
        self.btn_refresh.clicked.connect(self.refresh_files)
        c_layout.addWidget(self.btn_refresh)

        layout.addWidget(ctrl_card)

        # Files Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Filename", "Type", "Format", "Size", "Duration", "Date", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
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

        self.refresh_files()

    def refresh_files(self):
        search = self.txt_search.text().strip().lower()
        filter_type = self.cmb_filter.currentText()

        records = self.db.history.get_history()
        existing_files = []

        for rec in records:
            p = rec.get("file_path", "")
            if p and os.path.exists(p):
                fname = os.path.basename(p)
                m_type = rec.get("media_type", "Video")

                if filter_type == "Video" and m_type not in ("Video", "Dual Mode"):
                    continue
                if filter_type == "Audio" and m_type != "Audio":
                    continue

                if search and (search not in fname.lower() and search not in rec.get("title", "").lower()):
                    continue

                existing_files.append((rec, p, fname))

        self.table.setRowCount(len(existing_files))

        for row, (rec, file_path, fname) in enumerate(existing_files):
            rec_id = rec["id"]
            ext = os.path.splitext(fname)[1].lstrip(".").upper() or "FILE"

            try:
                sz = os.path.getsize(file_path)
                sz_str = f"{sz / (1024 * 1024):.1f} MB"
            except Exception:
                sz_str = "--"

            # 0. Filename
            f_item = QTableWidgetItem(fname)
            f_item.setToolTip(f"Path: {file_path}")
            self.table.setItem(row, 0, f_item)

            # 1. Type
            t_item = QTableWidgetItem(rec.get("media_type", "Video"))
            t_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, t_item)

            # 2. Format
            fmt_item = QTableWidgetItem(ext)
            fmt_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, fmt_item)

            # 3. Size
            sz_item = QTableWidgetItem(sz_str)
            sz_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, sz_item)

            # 4. Duration
            dur_item = QTableWidgetItem(rec.get("duration", "--:--"))
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, dur_item)

            # 5. Date
            dt_item = QTableWidgetItem(rec.get("completed_at", "")[:10])
            dt_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, dt_item)

            # 6. Action Buttons Widget
            actions_widget = QWidget()
            a_layout = QHBoxLayout(actions_widget)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            # Play / Open
            btn_play = QPushButton()
            btn_play.setIcon(get_icon("play", Tokens.TEXT_PRIMARY, 13))
            btn_play.setToolTip("Open File")
            btn_play.setFixedSize(26, 26)
            btn_play.clicked.connect(lambda _, p=file_path: self.open_file(p))
            a_layout.addWidget(btn_play)

            # Reveal in Folder
            btn_reveal = QPushButton()
            btn_reveal.setIcon(get_icon("folder_open", Tokens.TEXT_PRIMARY, 13))
            btn_reveal.setToolTip("Show in Explorer")
            btn_reveal.setFixedSize(26, 26)
            btn_reveal.clicked.connect(lambda _, p=file_path: self.reveal_file(p))
            a_layout.addWidget(btn_reveal)

            # Rename
            btn_rename = QPushButton()
            btn_rename.setIcon(get_icon("settings", Tokens.TEXT_SECONDARY, 13))
            btn_rename.setToolTip("Rename File")
            btn_rename.setFixedSize(26, 26)
            btn_rename.clicked.connect(lambda _, rid=rec_id, p=file_path: self.rename_file(rid, p))
            a_layout.addWidget(btn_rename)

            # Move
            btn_move = QPushButton()
            btn_move.setIcon(get_icon("folder", Tokens.TEXT_SECONDARY, 13))
            btn_move.setToolTip("Move File to Another Folder")
            btn_move.setFixedSize(26, 26)
            btn_move.clicked.connect(lambda _, rid=rec_id, p=file_path: self.move_file(rid, p))
            a_layout.addWidget(btn_move)

            # Delete
            btn_del = QPushButton()
            btn_del.setIcon(get_icon("trash_2", Tokens.DANGER, 13))
            btn_del.setToolTip("Delete File from Disk")
            btn_del.setFixedSize(26, 26)
            btn_del.clicked.connect(lambda _, rid=rec_id, p=file_path: self.delete_file(rid, p))
            a_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 6, actions_widget)

    def open_file(self, path: str):
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.warning(self, "Open File", f"Could not launch file: {e}")

    def reveal_file(self, path: str):
        if path and os.path.exists(path):
            subprocess.Popen(f'explorer /select,"{path}"')

    def rename_file(self, record_id: int, old_path: str):
        if not os.path.exists(old_path):
            QMessageBox.warning(self, "Error", "File does not exist on disk.")
            return

        old_dir = os.path.dirname(old_path)
        old_name, ext = os.path.splitext(os.path.basename(old_path))

        new_name, ok = QInputDialog.getText(self, "Rename File", "Enter new filename (without extension):", text=old_name)
        if ok and new_name.strip():
            safe_stem = core.sanitize_filename(new_name.strip())
            new_path = os.path.join(old_dir, f"{safe_stem}{ext}")

            if os.path.exists(new_path) and new_path != old_path:
                QMessageBox.warning(self, "Conflict", "A file with this name already exists in this directory.")
                return

            try:
                os.rename(old_path, new_path)
                self.db.history.update_file_path(record_id, new_path)
                self.refresh_files()
                QMessageBox.information(self, "Renamed", "File renamed successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Rename Failed", f"Could not rename file:\n\n{e}")

    def move_file(self, record_id: int, current_path: str):
        if not os.path.exists(current_path):
            QMessageBox.warning(self, "Error", "File does not exist on disk.")
            return

        target_dir = QFileDialog.getExistingDirectory(self, "Select Target Directory", os.path.dirname(current_path))
        if target_dir:
            fname = os.path.basename(current_path)
            target_file = os.path.join(target_dir, fname)

            if os.path.exists(target_file):
                unique_path = core.get_unique_path(target_dir, fname)
                target_file = str(unique_path)

            try:
                shutil.move(current_path, target_file)
                self.db.history.update_file_path(record_id, target_file)
                self.refresh_files()
                QMessageBox.information(self, "Moved", f"File moved to:\n{target_file}")
            except Exception as e:
                QMessageBox.critical(self, "Move Failed", f"Could not move file:\n\n{e}")

    def delete_file(self, record_id: int, file_path: str):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete this file from disk?\n\n{os.path.basename(file_path)}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                self.db.history.delete_record(record_id)
                self.refresh_files()
                QMessageBox.information(self, "Deleted", "File was deleted from disk and library.")
            except Exception as e:
                QMessageBox.critical(self, "Delete Failed", f"Could not delete file:\n\n{e}")
