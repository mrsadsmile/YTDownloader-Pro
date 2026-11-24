"""
Diagnostic Center Dialog for YTDownloader Pro (Phase 4).
Runs multi-point health audits on configuration, database, storage,
network, proxy, and media components with copy/export capabilities.
"""
from typing import List, Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QFileDialog, QApplication, QTextEdit
)

from theme import Tokens
from icons import get_icon
from network_system import DiagnosticCenter, ComponentManager


class DiagnosticsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diagnostic Center & System Health")
        self.resize(760, 560)
        self.setStyleSheet(f"background-color: {Tokens.BG_MAIN}; color: {Tokens.TEXT_PRIMARY};")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.init_ui()
        self.run_diagnostics()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title Row
        top_row = QHBoxLayout()
        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_icon("activity", Tokens.ACCENT, 20).pixmap(20, 20))
        top_row.addWidget(lbl_icon)

        title_col = QVBoxLayout()
        lbl_title = QLabel("System Diagnostics & Health Audit")
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Tokens.TEXT_PRIMARY};")
        title_col.addWidget(lbl_title)

        lbl_desc = QLabel("Verifies environment health, storage permissions, database WAL mode, and network routing.")
        lbl_desc.setProperty("secondary", True)
        title_col.addWidget(lbl_desc)
        top_row.addLayout(title_col)
        top_row.addStretch()

        self.btn_refresh = QPushButton("Run Tests")
        self.btn_refresh.setIcon(get_icon("refresh_cw", Tokens.TEXT_PRIMARY, 14))
        self.btn_refresh.clicked.connect(self.run_diagnostics)
        top_row.addWidget(self.btn_refresh)

        main_layout.addLayout(top_row)

        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Test Component", "Status", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {Tokens.BG_INPUT}; border: 1px solid {Tokens.BORDER}; border-radius: 6px; gridline-color: {Tokens.BORDER}; }}"
            f"QHeaderView::section {{ background-color: {Tokens.SURFACE_ELEVATED}; color: {Tokens.TEXT_PRIMARY}; padding: 6px; border: none; font-weight: 600; }}"
        )
        main_layout.addWidget(self.table)

        # Component Inventory Summary Card
        card = QFrame()
        card.setProperty("card", "elevated")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(6)

        lbl_c_title = QLabel("Runtime Component Status:")
        lbl_c_title.setStyleSheet(f"font-weight: 700; color: {Tokens.TEXT_PRIMARY}; font-size: 13px;")
        c_layout.addWidget(lbl_c_title)

        self.lbl_comp_summary = QLabel("Loading component data...")
        self.lbl_comp_summary.setProperty("secondary", True)
        self.lbl_comp_summary.setWordWrap(True)
        c_layout.addWidget(self.lbl_comp_summary)

        main_layout.addWidget(card)

        # Bottom Actions: Copy Report, Export Report, Close
        bottom_row = QHBoxLayout()
        btn_copy = QPushButton("Copy Report")
        btn_copy.setIcon(get_icon("copy", Tokens.TEXT_PRIMARY, 14))
        btn_copy.clicked.connect(self.copy_report)
        bottom_row.addWidget(btn_copy)

        btn_export = QPushButton("Export Report...")
        btn_export.setIcon(get_icon("external_link", Tokens.TEXT_PRIMARY, 14))
        btn_export.clicked.connect(self.export_report)
        bottom_row.addWidget(btn_export)

        bottom_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)

        main_layout.addLayout(bottom_row)

    def run_diagnostics(self):
        tests = DiagnosticCenter.run_full_diagnostics()
        self.table.setRowCount(len(tests))

        for row, t in enumerate(tests):
            item_name = QTableWidgetItem(t["test"])
            item_status = QTableWidgetItem(t["status"])
            item_detail = QTableWidgetItem(t["detail"])

            if t["status"] == "Passed":
                item_status.setForeground(Qt.GlobalColor.green)
            elif t["status"] == "Warning":
                item_status.setForeground(Qt.GlobalColor.yellow)
            else:
                item_status.setForeground(Qt.GlobalColor.red)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_status)
            self.table.setItem(row, 2, item_detail)

        # Refresh components
        comps = ComponentManager.get_component_inventory()
        lines = []
        for c in comps:
            mark = "✓" if c["healthy"] else "⚠"
            lines.append(f"{mark} {c['name']} ({c['version']})")
        self.lbl_comp_summary.setText("   •   ".join(lines))

    def copy_report(self):
        report = DiagnosticCenter.export_sanitized_report()
        QApplication.clipboard().setText(report)
        QMessageBox.information(self, "Report Copied", "Sanitized diagnostic report copied to clipboard.")

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Diagnostic Report", "ytdownloader_diagnostic_report.txt", "Text Files (*.txt)"
        )
        if path:
            try:
                report = DiagnosticCenter.export_sanitized_report()
                with open(path, "w", encoding="utf-8") as f:
                    f.write(report)
                QMessageBox.information(self, "Export Complete", f"Diagnostic report saved to:\n{path}")
            except Exception as ex:
                QMessageBox.critical(self, "Export Failed", f"Could not write file: {ex}")
