"""
Subtitles Manager Dialog for YTDownloader Pro (Phase 3).
Allows users to discover available manual vs auto-generated subtitles,
select target languages, choose subtitle format (SRT, VTT, ASS),
and specify embedding vs separate file vs subtitle-only download.
"""
from typing import Dict, List, Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QComboBox, QCheckBox,
    QRadioButton, QButtonGroup, QMessageBox, QTabWidget, QWidget
)

from theme import Tokens
from icons import get_icon
from media_tools import parse_media_subtitles


class SubtitlesDialog(QDialog):
    sig_subtitles_configured = Signal(dict)

    def __init__(self, media_metadata: Optional[Dict[str, Any]] = None, current_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Subtitle Manager & Language Selection")
        self.resize(650, 500)
        self.setStyleSheet(f"background-color: {Tokens.BG_MAIN}; color: {Tokens.TEXT_PRIMARY};")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.metadata = media_metadata or {}
        self.config = current_config or {}
        self.parsed_subs = parse_media_subtitles(self.metadata)

        self.init_ui()
        self.populate_subtitles()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title & Media Title
        top_row = QHBoxLayout()
        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_icon("film", Tokens.ACCENT, 20).pixmap(20, 20))
        top_row.addWidget(lbl_icon)

        title_col = QVBoxLayout()
        lbl_title = QLabel("Available Subtitles & Closed Captions")
        lbl_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        title_col.addWidget(lbl_title)

        media_name = self.metadata.get("title", "Active Media")
        self.lbl_media = QLabel(f"Source: {media_name[:60]}..." if len(media_name) > 60 else f"Source: {media_name}")
        self.lbl_media.setProperty("secondary", True)
        title_col.addWidget(self.lbl_media)

        top_row.addLayout(title_col)
        top_row.addStretch()
        main_layout.addLayout(top_row)

        # Subtitle Languages Tab Widget (Manual vs Auto-Generated)
        self.tabs_subs = QTabWidget()
        self.tabs_subs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {Tokens.BORDER}; border-radius: 6px; background-color: {Tokens.SURFACE_ELEVATED}; }}"
            f"QTabBar::tab {{ background: {Tokens.BG_INPUT}; color: {Tokens.TEXT_SECONDARY}; padding: 6px 14px; margin-right: 4px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}"
            f"QTabBar::tab:selected {{ background: {Tokens.SURFACE_ELEVATED}; color: {Tokens.TEXT_PRIMARY}; font-weight: 600; }}"
        )

        # Tab 1: Manual Subtitles
        tab_manual = QWidget()
        tm_layout = QVBoxLayout(tab_manual)
        tm_layout.setContentsMargins(10, 10, 10, 10)
        self.list_manual = QListWidget()
        self.list_manual.setStyleSheet(f"background-color: {Tokens.BG_INPUT}; border: none; font-size: 13px;")
        tm_layout.addWidget(self.list_manual)
        self.tabs_subs.addTab(tab_manual, "Manual Subtitles (Creator Verified)")

        # Tab 2: Auto-Generated Subtitles
        tab_auto = QWidget()
        ta_layout = QVBoxLayout(tab_auto)
        ta_layout.setContentsMargins(10, 10, 10, 10)
        self.list_auto = QListWidget()
        self.list_auto.setStyleSheet(f"background-color: {Tokens.BG_INPUT}; border: none; font-size: 13px;")
        ta_layout.addWidget(self.list_auto)
        self.tabs_subs.addTab(tab_auto, "Auto-Generated Captions")

        main_layout.addWidget(self.tabs_subs)

        # Quick Selection Bar
        quick_row = QHBoxLayout()
        self.lbl_selected_count = QLabel("Selected: 0 languages")
        self.lbl_selected_count.setStyleSheet(f"font-weight: 600; color: {Tokens.ACCENT};")
        quick_row.addWidget(self.lbl_selected_count)
        quick_row.addStretch()

        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self.select_all_languages)
        quick_row.addWidget(btn_select_all)

        btn_deselect = QPushButton("Deselect All")
        btn_deselect.clicked.connect(self.deselect_all_languages)
        quick_row.addWidget(btn_deselect)

        main_layout.addLayout(quick_row)

        # Subtitle Output Configuration Card
        conf_card = QFrame()
        conf_card.setProperty("card", "elevated")
        c_layout = QVBoxLayout(conf_card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(10)

        # Mode Selection
        lbl_mode = QLabel("Subtitle Delivery Mode:")
        lbl_mode.setStyleSheet(f"font-weight: 600; color: {Tokens.TEXT_PRIMARY}; font-size: 13px;")
        c_layout.addWidget(lbl_mode)

        self.btn_group_mode = QButtonGroup(self)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(16)

        self.rb_separate = QRadioButton("Separate File (.srt/.vtt alongside video)")
        self.rb_separate.setChecked(True)
        self.btn_group_mode.addButton(self.rb_separate, 1)
        mode_row.addWidget(self.rb_separate)

        self.rb_embed = QRadioButton("Embed into Video Container (MP4 / MKV via FFmpeg)")
        self.btn_group_mode.addButton(self.rb_embed, 2)
        mode_row.addWidget(self.rb_embed)

        self.rb_sub_only = QRadioButton("Subtitle Only (Skip video download)")
        self.btn_group_mode.addButton(self.rb_sub_only, 3)
        mode_row.addWidget(self.rb_sub_only)

        c_layout.addLayout(mode_row)

        # Format Row
        fmt_row = QHBoxLayout()
        lbl_fmt = QLabel("Preferred Subtitle Format:")
        lbl_fmt.setProperty("secondary", True)
        fmt_row.addWidget(lbl_fmt)

        self.cmb_sub_format = QComboBox()
        self.cmb_sub_format.addItems(["SRT (SubRip - Universal)", "VTT (WebVTT - Modern)", "ASS (Advanced SubStation Alpha)"])
        fmt_row.addWidget(self.cmb_sub_format)
        fmt_row.addStretch()
        c_layout.addLayout(fmt_row)

        main_layout.addWidget(conf_card)

        # Bottom Buttons
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        btn_apply = QPushButton("Apply Subtitle Settings")
        btn_apply.setIcon(get_icon("check", "#FFFFFF", 14))
        btn_apply.setStyleSheet(f"background-color: {Tokens.ACCENT}; color: #FFFFFF; font-weight: 700; padding: 7px 18px;")
        btn_apply.clicked.connect(self.save_and_apply)
        bottom_row.addWidget(btn_apply)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(btn_cancel)

        main_layout.addLayout(bottom_row)

    def populate_subtitles(self):
        self.list_manual.clear()
        self.list_auto.clear()

        manual_subs = self.parsed_subs.get("manual", [])
        auto_subs = self.parsed_subs.get("auto", [])

        # Add manual
        for sub in manual_subs:
            item = QListWidgetItem(f"✓  {sub['name']} ({sub['lang']})")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, sub["lang"])
            self.list_manual.addItem(item)

        if not manual_subs:
            empty_item = QListWidgetItem("No verified manual subtitles available for this media.")
            empty_item.setFlags(Qt.NoItemFlags)
            empty_item.setForeground(Qt.GlobalColor.darkGray)
            self.list_manual.addItem(empty_item)

        # Add auto
        for sub in auto_subs:
            item = QListWidgetItem(f"⚡  {sub['name']} ({sub['lang']}) [Auto]")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, sub["lang"])
            self.list_auto.addItem(item)

        if not auto_subs:
            empty_item = QListWidgetItem("No auto-generated captions discovered.")
            empty_item.setFlags(Qt.NoItemFlags)
            empty_item.setForeground(Qt.GlobalColor.darkGray)
            self.list_auto.addItem(empty_item)

        # Connect check state changes to counter
        self.list_manual.itemChanged.connect(self.update_selection_counter)
        self.list_auto.itemChanged.connect(self.update_selection_counter)

        # If previous config had languages selected, pre-check them
        prev_langs = str(self.config.get("subtitle_lang", "")).split(",")
        prev_langs = [p.strip().lower() for p in prev_langs if p.strip()]

        for i in range(self.list_manual.count()):
            it = self.list_manual.item(i)
            lang = it.data(Qt.UserRole)
            if lang and lang.lower() in prev_langs:
                it.setCheckState(Qt.Checked)

        for i in range(self.list_auto.count()):
            it = self.list_auto.item(i)
            lang = it.data(Qt.UserRole)
            if lang and lang.lower() in prev_langs:
                it.setCheckState(Qt.Checked)

        self.update_selection_counter()

    def update_selection_counter(self):
        selected = self.get_selected_language_codes()
        self.lbl_selected_count.setText(f"Selected: {len(selected)} languages")

    def get_selected_language_codes(self) -> List[str]:
        langs = []
        for i in range(self.list_manual.count()):
            it = self.list_manual.item(i)
            if it.checkState() == Qt.Checked:
                code = it.data(Qt.UserRole)
                if code and code not in langs:
                    langs.append(code)

        for i in range(self.list_auto.count()):
            it = self.list_auto.item(i)
            if it.checkState() == Qt.Checked:
                code = it.data(Qt.UserRole)
                if code and code not in langs:
                    langs.append(code)
        return langs

    def select_all_languages(self):
        current_list = self.list_manual if self.tabs_subs.currentIndex() == 0 else self.list_auto
        for i in range(current_list.count()):
            it = current_list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Checked)
        self.update_selection_counter()

    def deselect_all_languages(self):
        for i in range(self.list_manual.count()):
            it = self.list_manual.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Unchecked)
        for i in range(self.list_auto.count()):
            it = self.list_auto.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Unchecked)
        self.update_selection_counter()

    def save_and_apply(self):
        langs = self.get_selected_language_codes()
        if not langs:
            res = QMessageBox.question(
                self, "No Languages Selected",
                "No subtitle languages were selected. Do you want to disable subtitle download?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res == QMessageBox.Yes:
                self.sig_subtitles_configured.emit({
                    "download_subtitles": False,
                    "subtitle_lang": "",
                    "embed_subtitles": False,
                    "sub_only": False,
                    "subtitle_format": "srt"
                })
                self.accept()
            return

        fmt = "srt"
        if "vtt" in self.cmb_sub_format.currentText().lower():
            fmt = "vtt"
        elif "ass" in self.cmb_sub_format.currentText().lower():
            fmt = "ass"

        payload = {
            "download_subtitles": True,
            "subtitle_lang": ",".join(langs),
            "embed_subtitles": self.rb_embed.isChecked(),
            "sub_only": self.rb_sub_only.isChecked(),
            "subtitle_format": fmt
        }
        self.sig_subtitles_configured.emit(payload)
        self.accept()
