"""
Queue Management View for YTDownloader Pro
Displays active, pending, paused, completed, and failed jobs with full lifecycle control.
"""
import os
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QProgressBar, QMessageBox, QFrame, QMenu
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction

from theme import Tokens
from icons import get_icon, get_pixmap
import database
from queue_manager import QueueManager


class QueueView(QWidget):
    def __init__(self, queue_mgr: QueueManager, parent=None):
        super().__init__(parent)
        self.queue_mgr = queue_mgr
        self.db = queue_mgr.db
        self.init_ui()

        # Connect queue manager signals
        self.queue_mgr.sig_queue_updated.connect(self.refresh_table)
        self.queue_mgr.sig_job_status.connect(self.on_job_status)
        self.queue_mgr.sig_job_progress.connect(self.on_job_progress)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header Bar with Controls
        header_card = QFrame()
        header_card.setProperty("card", "true")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(10)

        lbl_title = QLabel("Download Queue")
        lbl_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        h_layout.addWidget(lbl_title)

        h_layout.addStretch()

        # Concurrency selector
        lbl_conc = QLabel("Max Concurrent:")
        lbl_conc.setProperty("secondary", True)
        h_layout.addWidget(lbl_conc)

        self.cmb_concurrent = QComboBox()
        self.cmb_concurrent.addItems(["1", "2", "3", "4", "5"])
        self.cmb_concurrent.setCurrentText(str(self.queue_mgr.max_concurrent))
        self.cmb_concurrent.currentTextChanged.connect(self.on_concurrency_changed)
        h_layout.addWidget(self.cmb_concurrent)

        # Bulk Actions
        self.btn_pause_all = QPushButton("Pause All")
        self.btn_pause_all.setIcon(get_icon("pause", Tokens.TEXT_PRIMARY, 14))
        self.btn_pause_all.clicked.connect(self.queue_mgr.pause_all)
        h_layout.addWidget(self.btn_pause_all)

        self.btn_resume_all = QPushButton("Resume All")
        self.btn_resume_all.setIcon(get_icon("play", Tokens.TEXT_PRIMARY, 14))
        self.btn_resume_all.clicked.connect(self.queue_mgr.resume_all)
        h_layout.addWidget(self.btn_resume_all)

        self.btn_cancel_all = QPushButton("Cancel All")
        self.btn_cancel_all.setIcon(get_icon("x_circle", Tokens.DANGER, 14))
        self.btn_cancel_all.setProperty("danger", True)
        self.btn_cancel_all.clicked.connect(self.on_cancel_all_clicked)
        h_layout.addWidget(self.btn_cancel_all)

        self.btn_clear_done = QPushButton("Clear Finished")
        self.btn_clear_done.setIcon(get_icon("trash_2", Tokens.TEXT_MUTED, 14))
        self.btn_clear_done.clicked.connect(self.queue_mgr.clear_completed)
        h_layout.addWidget(self.btn_clear_done)

        layout.addWidget(header_card)

        # Queue Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Prio", "Title", "Mode", "Quality", "Status", "Speed", "ETA", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
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

    def on_concurrency_changed(self, text: str):
        try:
            val = int(text)
            self.queue_mgr.set_max_concurrent(val)
        except ValueError:
            pass

    def on_cancel_all_clicked(self):
        reply = QMessageBox.question(
            self,
            "Confirm Cancel All",
            "Are you sure you want to cancel all active and pending downloads in the queue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.queue_mgr.cancel_all()

    def refresh_table(self):
        jobs = self.db.jobs.get_all_jobs()
        self.table.setRowCount(len(jobs))

        for row, job in enumerate(jobs):
            job_id = job["id"]
            status = job.get("status", "Queued")
            prio = job.get("priority", 0)

            # 0. Priority
            item_prio = QTableWidgetItem(f"{prio:+d}" if prio != 0 else "0")
            item_prio.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_prio)

            # 1. Title
            title_text = job.get("title", "Untitled Media")
            item_title = QTableWidgetItem(title_text)
            item_title.setToolTip(f"{title_text}\nURL: {job.get('url', '')}")
            self.table.setItem(row, 1, item_title)

            # 2. Mode
            item_mode = QTableWidgetItem(job.get("download_type", "Video"))
            item_mode.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_mode)

            # 3. Quality
            q_info = job.get("video_quality") if job.get("download_type") != "Audio" else job.get("audio_quality", "")
            item_q = QTableWidgetItem(str(q_info))
            item_q.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_q)

            # 4. Status Badge
            item_status = QTableWidgetItem(f"● {status}")
            if status == "Downloading":
                item_status.setForeground(Qt.cyan)
            elif status == "Completed":
                item_status.setForeground(Qt.green)
            elif status in ("Failed", "Cancelled", "Interrupted"):
                item_status.setForeground(Qt.red)
            elif status == "Paused":
                item_status.setForeground(Qt.yellow)
            else:
                item_status.setForeground(Qt.gray)
            item_status.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_status)

            # 5. Speed
            speed_val = job.get("speed") or "--"
            item_speed = QTableWidgetItem(str(speed_val))
            item_speed.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, item_speed)

            # 6. ETA
            eta_val = job.get("eta") or "--"
            item_eta = QTableWidgetItem(str(eta_val))
            item_eta.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, item_eta)

            # 7. Action Buttons Widget
            actions_widget = QWidget()
            a_layout = QHBoxLayout(actions_widget)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            # Up / Down buttons
            btn_up = QPushButton()
            btn_up.setIcon(get_icon("chevron_up", Tokens.TEXT_SECONDARY, 13))
            btn_up.setToolTip("Increase Priority (Move Up)")
            btn_up.setFixedSize(26, 26)
            btn_up.clicked.connect(lambda _, j=job_id: self.queue_mgr.reorder_job(j, "up"))
            a_layout.addWidget(btn_up)

            btn_down = QPushButton()
            btn_down.setIcon(get_icon("chevron_down", Tokens.TEXT_SECONDARY, 13))
            btn_down.setToolTip("Decrease Priority (Move Down)")
            btn_down.setFixedSize(26, 26)
            btn_down.clicked.connect(lambda _, j=job_id: self.queue_mgr.reorder_job(j, "down"))
            a_layout.addWidget(btn_down)

            # Status action button (Pause / Resume / Retry)
            if status in ("Downloading", "Queued", "Pending"):
                btn_state = QPushButton()
                btn_state.setIcon(get_icon("pause", Tokens.TEXT_PRIMARY, 13))
                btn_state.setToolTip("Pause")
                btn_state.setFixedSize(26, 26)
                btn_state.clicked.connect(lambda _, j=job_id: self.queue_mgr.pause_job(j))
                a_layout.addWidget(btn_state)
            elif status == "Paused":
                btn_state = QPushButton()
                btn_state.setIcon(get_icon("play", Tokens.SUCCESS, 13))
                btn_state.setToolTip("Resume")
                btn_state.setFixedSize(26, 26)
                btn_state.clicked.connect(lambda _, j=job_id: self.queue_mgr.resume_job(j))
                a_layout.addWidget(btn_state)
            elif status in ("Failed", "Cancelled", "Interrupted"):
                btn_state = QPushButton()
                btn_state.setIcon(get_icon("refresh_cw", Tokens.WARNING, 13))
                btn_state.setToolTip("Retry")
                btn_state.setFixedSize(26, 26)
                btn_state.clicked.connect(lambda _, j=job_id: self.queue_mgr.retry_job(j))
                a_layout.addWidget(btn_state)

            # Delete / Remove from queue
            btn_del = QPushButton()
            btn_del.setIcon(get_icon("x", Tokens.DANGER, 13))
            btn_del.setToolTip("Remove from Queue")
            btn_del.setFixedSize(26, 26)
            btn_del.clicked.connect(lambda _, j=job_id: self.queue_mgr.remove_job(j))
            a_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 7, actions_widget)

    def on_job_status(self, job_id: str, status: str):
        self.refresh_table()

    def on_job_progress(self, job_id: str, prog: Dict[str, Any]):
        # Update active row speed / eta without full redraw for efficiency
        for row in range(self.table.rowCount()):
            pass
