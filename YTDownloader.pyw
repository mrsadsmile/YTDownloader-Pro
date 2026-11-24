"""
YTDownloader Pro — Modern Professional Desktop Downloader
Entry Point
"""

import sys
import os
from pathlib import Path

# Ensure local module directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

import core
import theme
from main_window import MainWindow


def main():
    # Configure high-DPI behavior
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("YTDownloader Pro")
    app.setOrganizationName("YTDownloader")
    app.setApplicationVersion("2.6.0")

    # Set Application Window Icon
    icon_path = core.APP_DIR / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Set Modern Default Typography
    default_font = QFont()
    default_font.setFamilies(["Vazirmatn", "Peyda", "Inter", "Segoe UI", "Tahoma", "sans-serif"])
    default_font.setPointSize(10)
    app.setFont(default_font)

    # Apply Design System QSS
    app.setStyleSheet(theme.get_stylesheet())

    # Initialize and display Main Window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
