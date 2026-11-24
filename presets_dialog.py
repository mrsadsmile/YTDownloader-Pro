"""
Presets Management Dialog for YTDownloader Pro (Phase 3).
Allows users to view, apply, create, duplicate, rename, delete,
import, and export download presets with instant validation.
"""
from typing import Dict, Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QLineEdit, QComboBox,
    QCheckBox, QMessageBox, QFileDialog, QGroupBox, QGridLayout,
    QInputDialog
)

import core
from theme import Tokens
from icons import get_icon
from media_tools import PresetManager, BUILTIN_PRESETS


class PresetsDialog(QDialog):
    sig_preset_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Presets Manager")
        self.resize(720, 520)
        self.setStyleSheet(f"background-color: {Tokens.BG_MAIN}; color: {Tokens.TEXT_PRIMARY};")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.presets: Dict[str, Dict[str, Any]] = {}
        self.current_preset_name: Optional[str] = None

        self.init_ui()
        self.refresh_preset_list()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title & Subtitle
        header_row = QHBoxLayout()
        lbl_title = QLabel("Smart Download Presets")
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        header_row.addWidget(lbl_title)
        header_row.addStretch()

        btn_import = QPushButton("Import JSON")
        btn_import.setIcon(get_icon("download", Tokens.TEXT_PRIMARY, 14))
        btn_import.clicked.connect(self.import_presets)
        header_row.addWidget(btn_import)

        btn_export = QPushButton("Export JSON")
        btn_export.setIcon(get_icon("external_link", Tokens.TEXT_PRIMARY, 14))
        btn_export.clicked.connect(self.export_presets)
        header_row.addWidget(btn_export)

        main_layout.addLayout(header_row)

        # Split Content Layout: Left = List, Right = Details / Editor
        content_row = QHBoxLayout()
        content_row.setSpacing(14)

        # Left Column: List of Presets
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        lbl_list = QLabel("Available Presets:")
        lbl_list.setProperty("secondary", True)
        left_col.addWidget(lbl_list)

        self.list_presets = QListWidget()
        self.list_presets.setStyleSheet(
            f"background-color: {Tokens.BG_INPUT}; border: 1px solid {Tokens.BORDER}; "
            f"border-radius: 6px; padding: 4px; font-size: 13px;"
        )
        self.list_presets.currentItemChanged.connect(self.on_selection_changed)
        left_col.addWidget(self.list_presets)

        # Preset Actions Row
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self.btn_new = QPushButton("New")
        self.btn_new.setIcon(get_icon("plus", Tokens.TEXT_PRIMARY, 13))
        self.btn_new.clicked.connect(self.create_new_preset)
        action_row.addWidget(self.btn_new)

        self.btn_dup = QPushButton("Duplicate")
        self.btn_dup.setIcon(get_icon("copy", Tokens.TEXT_PRIMARY, 13))
        self.btn_dup.clicked.connect(self.duplicate_preset)
        action_row.addWidget(self.btn_dup)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(get_icon("trash", Tokens.ERROR, 13))
        self.btn_delete.setStyleSheet(f"color: {Tokens.ERROR};")
        self.btn_delete.clicked.connect(self.delete_preset)
        action_row.addWidget(self.btn_delete)

        left_col.addLayout(action_row)
        content_row.addLayout(left_col, 2)

        # Right Column: Details & Editing
        right_frame = QFrame()
        right_frame.setProperty("card", "elevated")
        r_layout = QVBoxLayout(right_frame)
        r_layout.setContentsMargins(14, 14, 14, 14)
        r_layout.setSpacing(10)

        lbl_edit_title = QLabel("Preset Configuration:")
        lbl_edit_title.setStyleSheet(f"font-weight: 700; color: {Tokens.TEXT_PRIMARY}; font-size: 14px;")
        r_layout.addWidget(lbl_edit_title)

        grid = QGridLayout()
        grid.setSpacing(8)

        # Name
        grid.addWidget(QLabel("Preset Name:"), 0, 0)
        self.txt_name = QLineEdit()
        grid.addWidget(self.txt_name, 0, 1)

        # Download Type
        grid.addWidget(QLabel("Download Mode:"), 1, 0)
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Video", "Audio", "Dual Mode"])
        grid.addWidget(self.cmb_type, 1, 1)

        # Video Quality
        grid.addWidget(QLabel("Video Resolution:"), 2, 0)
        self.cmb_v_quality = QComboBox()
        self.cmb_v_quality.addItems(["Best Available", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"])
        grid.addWidget(self.cmb_v_quality, 2, 1)

        # Video Format
        grid.addWidget(QLabel("Video Container:"), 3, 0)
        self.cmb_v_format = QComboBox()
        self.cmb_v_format.addItems(["MP4", "MKV", "WEBM"])
        grid.addWidget(self.cmb_v_format, 3, 1)

        # Audio Format
        grid.addWidget(QLabel("Audio Format:"), 4, 0)
        self.cmb_a_format = QComboBox()
        self.cmb_a_format.addItems(["Best Available (Original)", "MP3", "M4A", "OPUS", "WAV", "FLAC"])
        grid.addWidget(self.cmb_a_format, 4, 1)

        # Audio Quality
        grid.addWidget(QLabel("Audio Bitrate:"), 5, 0)
        self.cmb_a_quality = QComboBox()
        self.cmb_a_quality.addItems(["Best Available", "320 kbps", "256 kbps", "192 kbps", "128 kbps"])
        grid.addWidget(self.cmb_a_quality, 5, 1)

        # Sample Rate
        grid.addWidget(QLabel("Sample Rate:"), 6, 0)
        self.cmb_sample_rate = QComboBox()
        self.cmb_sample_rate.addItems(["Auto", "44.1 kHz", "48 kHz", "96 kHz"])
        grid.addWidget(self.cmb_sample_rate, 6, 1)

        # Audio Channels
        grid.addWidget(QLabel("Channels:"), 7, 0)
        self.cmb_channels = QComboBox()
        self.cmb_channels.addItems(["Auto", "Stereo (2ch)", "Mono (1ch)"])
        grid.addWidget(self.cmb_channels, 7, 1)

        r_layout.addLayout(grid)

        # Checkbox Toggles
        self.chk_metadata = QCheckBox("Embed ID3 / media metadata tags")
        r_layout.addWidget(self.chk_metadata)

        self.chk_thumbnail = QCheckBox("Embed video thumbnail as cover art")
        r_layout.addWidget(self.chk_thumbnail)

        self.chk_sponsor = QCheckBox("Enable SponsorBlock segment skipping")
        r_layout.addWidget(self.chk_sponsor)

        self.chk_subtitles = QCheckBox("Download subtitles if available")
        r_layout.addWidget(self.chk_subtitles)

        r_layout.addStretch()

        # Save Preset Button
        self.btn_save = QPushButton("Save Preset Changes")
        self.btn_save.setIcon(get_icon("check", "#FFFFFF", 14))
        self.btn_save.clicked.connect(self.save_current_preset)
        r_layout.addWidget(self.btn_save)

        content_row.addWidget(right_frame, 3)
        main_layout.addLayout(content_row)

        # Bottom Bar: Apply Preset or Close
        bottom_row = QHBoxLayout()
        self.lbl_builtin_badge = QLabel("")
        self.lbl_builtin_badge.setProperty("muted", True)
        bottom_row.addWidget(self.lbl_builtin_badge)
        bottom_row.addStretch()

        self.btn_apply = QPushButton("Apply to Downloader")
        self.btn_apply.setIcon(get_icon("download", "#FFFFFF", 15))
        self.btn_apply.setStyleSheet(f"background-color: {Tokens.ACCENT}; color: #FFFFFF; font-weight: 700; padding: 7px 18px;")
        self.btn_apply.clicked.connect(self.apply_preset)
        bottom_row.addWidget(self.btn_apply)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)

        main_layout.addLayout(bottom_row)

    def refresh_preset_list(self):
        self.presets = PresetManager.get_all_presets()
        self.list_presets.clear()

        for name, conf in self.presets.items():
            is_builtin = conf.get("builtin", False)
            tag = " [Built-in]" if is_builtin else ""
            item = QListWidgetItem(f"{name}{tag}")
            item.setData(Qt.UserRole, name)
            if is_builtin:
                item.setForeground(Qt.GlobalColor.darkGray)
            self.list_presets.addItem(item)

        if self.list_presets.count() > 0:
            self.list_presets.setCurrentRow(0)

    def on_selection_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem] = None):
        if not current:
            return
        name = current.data(Qt.UserRole)
        self.current_preset_name = name
        conf = self.presets.get(name, {})
        is_builtin = conf.get("builtin", False)

        self.txt_name.setText(name)
        self.txt_name.setEnabled(not is_builtin)
        self.btn_delete.setEnabled(not is_builtin)
        self.btn_save.setEnabled(not is_builtin)

        if is_builtin:
            self.lbl_builtin_badge.setText("ℹ Built-in preset (read-only). Click 'Duplicate' to customize.")
        else:
            self.lbl_builtin_badge.setText("Custom user preset (editable).")

        # Load values into controls
        idx_type = self.cmb_type.findText(conf.get("download_type", "Video"))
        if idx_type >= 0:
            self.cmb_type.setCurrentIndex(idx_type)

        idx_vq = self.cmb_v_quality.findText(conf.get("video_quality", "Best Available"))
        if idx_vq >= 0:
            self.cmb_v_quality.setCurrentIndex(idx_vq)

        idx_vf = self.cmb_v_format.findText(conf.get("video_format", "MP4"))
        if idx_vf >= 0:
            self.cmb_v_format.setCurrentIndex(idx_vf)

        idx_af = self.cmb_a_format.findText(conf.get("audio_format", "MP3"))
        if idx_af >= 0:
            self.cmb_a_format.setCurrentIndex(idx_af)

        idx_aq = self.cmb_a_quality.findText(conf.get("audio_quality", "320 kbps"))
        if idx_aq >= 0:
            self.cmb_a_quality.setCurrentIndex(idx_aq)

        idx_sr = self.cmb_sample_rate.findText(conf.get("audio_sample_rate", "Auto"))
        if idx_sr >= 0:
            self.cmb_sample_rate.setCurrentIndex(idx_sr)

        idx_ch = self.cmb_channels.findText(conf.get("audio_channels", "Auto"))
        if idx_ch >= 0:
            self.cmb_channels.setCurrentIndex(idx_ch)

        self.chk_metadata.setChecked(conf.get("embed_metadata", True))
        self.chk_thumbnail.setChecked(conf.get("download_thumbnail", False))
        self.chk_sponsor.setChecked(conf.get("sponsorblock_enabled", False))
        self.chk_subtitles.setChecked(conf.get("download_subtitles", False))

    def save_current_preset(self):
        if not self.current_preset_name or self.current_preset_name in BUILTIN_PRESETS:
            QMessageBox.warning(self, "Invalid Action", "Cannot modify built-in presets. Click Duplicate to create a copy.")
            return

        new_name = self.txt_name.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Invalid Name", "Preset name cannot be empty.")
            return

        conf = {
            "download_type": self.cmb_type.currentText(),
            "video_quality": self.cmb_v_quality.currentText(),
            "video_format": self.cmb_v_format.currentText(),
            "audio_format": self.cmb_a_format.currentText(),
            "audio_quality": self.cmb_a_quality.currentText(),
            "audio_sample_rate": self.cmb_sample_rate.currentText(),
            "audio_channels": self.cmb_channels.currentText(),
            "embed_metadata": self.chk_metadata.isChecked(),
            "download_thumbnail": self.chk_thumbnail.isChecked(),
            "sponsorblock_enabled": self.chk_sponsor.isChecked(),
            "download_subtitles": self.chk_subtitles.isChecked()
        }

        # If name was changed, delete old one
        if new_name != self.current_preset_name:
            PresetManager.delete_preset(self.current_preset_name)

        ok, msg = PresetManager.save_preset(new_name, conf)
        if ok:
            self.refresh_preset_list()
            # Select the newly named preset
            for i in range(self.list_presets.count()):
                if self.list_presets.item(i).data(Qt.UserRole) == new_name:
                    self.list_presets.setCurrentRow(i)
                    break
            QMessageBox.information(self, "Preset Saved", msg)
        else:
            QMessageBox.critical(self, "Error", msg)

    def create_new_preset(self):
        name, ok = QInputDialog.getText(self, "New Preset", "Enter a name for the new preset:")
        if ok and name.strip():
            clean_name = name.strip()
            if clean_name in self.presets:
                QMessageBox.warning(self, "Duplicate Name", "A preset with this name already exists.")
                return
            default_conf = {
                "download_type": "Video",
                "video_quality": "1080p",
                "video_format": "MP4",
                "audio_format": "MP3",
                "audio_quality": "320 kbps",
                "embed_metadata": True
            }
            succ, msg = PresetManager.save_preset(clean_name, default_conf)
            if succ:
                self.refresh_preset_list()
                for i in range(self.list_presets.count()):
                    if self.list_presets.item(i).data(Qt.UserRole) == clean_name:
                        self.list_presets.setCurrentRow(i)
                        break

    def duplicate_preset(self):
        if not self.current_preset_name:
            return
        base_name = self.current_preset_name.replace(" [Built-in]", "")
        new_name, ok = QInputDialog.getText(self, "Duplicate Preset", "Enter name for the copy:", text=f"{base_name} (Copy)")
        if ok and new_name.strip():
            succ, msg = PresetManager.duplicate_preset(self.current_preset_name, new_name.strip())
            if succ:
                self.refresh_preset_list()
                for i in range(self.list_presets.count()):
                    if self.list_presets.item(i).data(Qt.UserRole) == new_name.strip():
                        self.list_presets.setCurrentRow(i)
                        break
            else:
                QMessageBox.warning(self, "Error", msg)

    def delete_preset(self):
        if not self.current_preset_name:
            return
        if self.current_preset_name in BUILTIN_PRESETS:
            QMessageBox.warning(self, "Cannot Delete", "Built-in presets cannot be deleted.")
            return

        res = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete preset '{self.current_preset_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            PresetManager.delete_preset(self.current_preset_name)
            self.refresh_preset_list()

    def export_presets(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Presets JSON", "ytdownloader_presets.json", "JSON Files (*.json)")
        if path:
            ok, msg = PresetManager.export_presets(path)
            if ok:
                QMessageBox.information(self, "Export Presets", msg)
            else:
                QMessageBox.critical(self, "Export Failed", msg)

    def import_presets(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Presets JSON", "", "JSON Files (*.json)")
        if path:
            ok, count, msg = PresetManager.import_presets(path)
            if ok:
                self.refresh_preset_list()
                QMessageBox.information(self, "Import Presets", msg)
            else:
                QMessageBox.critical(self, "Import Failed", msg)

    def apply_preset(self):
        if not self.current_preset_name:
            return
        conf = self.presets.get(self.current_preset_name, {})
        self.sig_preset_selected.emit(conf)
        self.accept()
