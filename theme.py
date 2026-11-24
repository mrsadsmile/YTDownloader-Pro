"""
Theme and Design Tokens for YTDownloader Pro
Refined Graphite & Slate system following UI/UX Pro Max guidelines.
"""

class Tokens:
    # Color System
    BG_MAIN = "#11151B"
    BG_SECONDARY = "#171D25"
    SURFACE_ELEVATED = "#1D2530"
    BG_INPUT = "#151B23"
    BORDER = "#2A3442"
    BORDER_HOVER = "#3B4A5E"
    BORDER_FOCUS = "#718CF5"

    # Typography Colors
    TEXT_PRIMARY = "#EDF1F7"
    TEXT_SECONDARY = "#929DAC"
    TEXT_MUTED = "#687586"

    # Accent & States
    ACCENT = "#718CF5"
    ACCENT_HOVER = "#5E7BF0"
    ACCENT_PRESSED = "#4B68E0"
    ACCENT_SUBTLE = "#1C2438"

    SUCCESS = "#55AE89"
    WARNING = "#D5A451"
    ERROR = "#D76F75"
    DANGER = "#D76F75"
    DANGER_HOVER = "#C55B61"

    # Radius
    RADIUS_SM = "4px"
    RADIUS_MD = "6px"
    RADIUS_LG = "10px"

    # Typography
    FONT_FAMILY = "Vazirmatn, Peyda, Inter, -apple-system, 'Segoe UI', Roboto, sans-serif"
    FONT_MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"


def get_stylesheet() -> str:
    return f"""
    /* Global Window & Base Styles */
    QMainWindow, QDialog, QWidget#centralWidget {{
        background-color: {Tokens.BG_MAIN};
        color: {Tokens.TEXT_PRIMARY};
        font-family: {Tokens.FONT_FAMILY};
        font-size: 13px;
    }}

    /* Global ScrollBars */
    QScrollBar:vertical {{
        background: {Tokens.BG_MAIN};
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {Tokens.BORDER};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {Tokens.BORDER_HOVER};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* Cards and Surface Containers */
    QFrame[card="true"] {{
        background-color: {Tokens.BG_SECONDARY};
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_LG};
    }}
    QFrame[card="elevated"] {{
        background-color: {Tokens.SURFACE_ELEVATED};
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_LG};
    }}

    /* Labels */
    QLabel {{
        color: {Tokens.TEXT_PRIMARY};
        background: transparent;
    }}
    QLabel[secondary="true"] {{
        color: {Tokens.TEXT_SECONDARY};
    }}
    QLabel[muted="true"] {{
        color: {Tokens.TEXT_MUTED};
        font-size: 11px;
    }}
    QLabel[heading="true"] {{
        font-size: 15px;
        font-weight: 600;
        color: {Tokens.TEXT_PRIMARY};
    }}

    /* Text Inputs */
    QLineEdit {{
        background-color: {Tokens.BG_INPUT};
        color: {Tokens.TEXT_PRIMARY};
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_MD};
        padding: 8px 12px;
        selection-background-color: {Tokens.ACCENT};
        selection-color: #FFFFFF;
        font-size: 13px;
    }}
    QLineEdit:hover {{
        border: 1px solid {Tokens.BORDER_HOVER};
    }}
    QLineEdit:focus {{
        border: 1px solid {Tokens.BORDER_FOCUS};
        background-color: #171F2A;
    }}
    QLineEdit[readOnly="true"] {{
        color: {Tokens.TEXT_SECONDARY};
        background-color: {Tokens.BG_SECONDARY};
    }}

    /* Buttons */
    QPushButton {{
        background-color: {Tokens.SURFACE_ELEVATED};
        color: {Tokens.TEXT_PRIMARY};
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_MD};
        padding: 7px 14px;
        font-weight: 500;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: #242E3C;
        border: 1px solid {Tokens.BORDER_HOVER};
    }}
    QPushButton:pressed {{
        background-color: #18202A;
    }}
    QPushButton:disabled {{
        background-color: {Tokens.BG_SECONDARY};
        color: {Tokens.TEXT_MUTED};
        border: 1px solid {Tokens.BORDER};
    }}

    /* Primary CTA Button */
    QPushButton[primary="true"] {{
        background-color: {Tokens.ACCENT};
        color: #FFFFFF;
        border: 1px solid {Tokens.ACCENT};
        font-weight: 600;
    }}
    QPushButton[primary="true"]:hover {{
        background-color: {Tokens.ACCENT_HOVER};
        border: 1px solid {Tokens.ACCENT_HOVER};
    }}
    QPushButton[primary="true"]:pressed {{
        background-color: {Tokens.ACCENT_PRESSED};
    }}
    QPushButton[primary="true"]:disabled {{
        background-color: #2D3748;
        color: {Tokens.TEXT_MUTED};
        border: 1px solid #2D3748;
    }}

    /* Danger / Cancel Button */
    QPushButton[danger="true"] {{
        background-color: #2A1A1E;
        color: {Tokens.ERROR};
        border: 1px solid #4D262A;
    }}
    QPushButton[danger="true"]:hover {{
        background-color: #381E24;
        border: 1px solid {Tokens.ERROR};
    }}
    QPushButton[danger="true"]:pressed {{
        background-color: #201317;
    }}
    QPushButton[danger="true"]:disabled {{
        background-color: {Tokens.BG_SECONDARY};
        color: {Tokens.TEXT_MUTED};
        border: 1px solid {Tokens.BORDER};
    }}

    /* Segmented Controls */
    QFrame[segmented="true"] {{
        background-color: {Tokens.BG_INPUT};
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_MD};
        padding: 2px;
    }}
    QPushButton[segmentBtn="true"] {{
        background-color: transparent;
        color: {Tokens.TEXT_SECONDARY};
        border: none;
        border-radius: {Tokens.RADIUS_SM};
        padding: 6px 14px;
        font-weight: 500;
    }}
    QPushButton[segmentBtn="true"]:hover {{
        color: {Tokens.TEXT_PRIMARY};
        background-color: rgba(255, 255, 255, 0.04);
    }}
    QPushButton[segmentBtn="true"][checked="true"] {{
        background-color: {Tokens.SURFACE_ELEVATED};
        color: {Tokens.TEXT_PRIMARY};
        border: 1px solid {Tokens.BORDER};
        font-weight: 600;
    }}

    /* ComboBox */
    QComboBox {{
        background-color: {Tokens.BG_INPUT};
        color: {Tokens.TEXT_PRIMARY};
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_MD};
        padding: 6px 12px;
        font-size: 13px;
        min-height: 20px;
    }}
    QComboBox:hover {{
        border: 1px solid {Tokens.BORDER_HOVER};
    }}
    QComboBox:focus {{
        border: 1px solid {Tokens.BORDER_FOCUS};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {Tokens.SURFACE_ELEVATED};
        color: {Tokens.TEXT_PRIMARY};
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_MD};
        selection-background-color: {Tokens.ACCENT_SUBTLE};
        selection-color: {Tokens.ACCENT};
        padding: 4px;
        outline: none;
    }}

    /* CheckBoxes & RadioButtons */
    QCheckBox {{
        color: {Tokens.TEXT_PRIMARY};
        spacing: 8px;
        font-size: 13px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {Tokens.BORDER};
        background-color: {Tokens.BG_INPUT};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {Tokens.BORDER_HOVER};
    }}
    QCheckBox::indicator:checked {{
        background-color: {Tokens.ACCENT};
        border: 1px solid {Tokens.ACCENT};
    }}

    /* Progress Bar */
    QProgressBar {{
        background-color: {Tokens.BG_INPUT};
        border: 1px solid {Tokens.BORDER};
        border-radius: 4px;
        text-align: center;
        color: transparent;
        height: 8px;
    }}
    QProgressBar::chunk {{
        background-color: {Tokens.ACCENT};
        border-radius: 3px;
    }}

    /* Tabs */
    QTabWidget::pane {{
        border: none;
        background: transparent;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {Tokens.TEXT_SECONDARY};
        padding: 8px 16px;
        font-weight: 500;
        font-size: 13px;
        border-bottom: 2px solid transparent;
        margin-right: 4px;
    }}
    QTabBar::tab:hover {{
        color: {Tokens.TEXT_PRIMARY};
    }}
    QTabBar::tab:selected {{
        color: {Tokens.ACCENT};
        border-bottom: 2px solid {Tokens.ACCENT};
        font-weight: 600;
    }}

    /* Technical Log / PlainTextEdit */
    QPlainTextEdit {{
        background-color: #0A0D11;
        color: {Tokens.TEXT_SECONDARY};
        font-family: {Tokens.FONT_MONO};
        font-size: 11px;
        border: 1px solid {Tokens.BORDER};
        border-radius: {Tokens.RADIUS_MD};
        padding: 8px;
    }}

    /* Tooltips */
    QToolTip {{
        background-color: {Tokens.SURFACE_ELEVATED};
        color: {Tokens.TEXT_PRIMARY};
        border: 1px solid {Tokens.BORDER};
        border-radius: 4px;
        padding: 5px 8px;
        font-size: 11px;
    }}
    """
