"""
Visual Backtest Application — MT5 Style
=========================================
Entry point. Launches the PyQt5 GUI with dark theme.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor, QFont, QIcon
from PyQt5.QtCore import Qt


def create_dark_palette() -> QPalette:
    """Create professional trading terminal palette."""
    palette = QPalette()

    # Base colors — deeper, more contrast
    palette.setColor(QPalette.Window, QColor('#0F1019'))
    palette.setColor(QPalette.WindowText, QColor('#C0C0D0'))
    palette.setColor(QPalette.Base, QColor('#12131F'))
    palette.setColor(QPalette.AlternateBase, QColor('#1A1B2E'))
    palette.setColor(QPalette.ToolTipBase, QColor('#1E1F2E'))
    palette.setColor(QPalette.ToolTipText, QColor('#D0D0DC'))
    palette.setColor(QPalette.Text, QColor('#D0D0DC'))
    palette.setColor(QPalette.Button, QColor('#1E1F32'))
    palette.setColor(QPalette.ButtonText, QColor('#C0C0D0'))
    palette.setColor(QPalette.BrightText, QColor('#FFFFFF'))
    palette.setColor(QPalette.Link, QColor('#2563EB'))
    palette.setColor(QPalette.Highlight, QColor('#2563EB'))
    palette.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))

    # Disabled colors
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor('#3B3D56'))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor('#3B3D56'))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor('#3B3D56'))

    return palette


GLOBAL_STYLESHEET = """
    /* ══════════════════════════════════════════════
       PROFESSIONAL TRADING TERMINAL THEME
       ══════════════════════════════════════════════ */

    * {
        font-family: 'Segoe UI', 'Inter', 'Roboto', 'SF Pro Display', sans-serif;
        outline: none;
    }

    QMainWindow {
        background-color: #0F1019;
    }

    /* ── Tooltips ─────────────────────────────── */
    QToolTip {
        background-color: #1E1F2E;
        color: #D0D0DC;
        border: 1px solid #2D2E42;
        border-radius: 3px;
        padding: 5px 8px;
        font-size: 11px;
    }

    /* ── Menu Bar ─────────────────────────────── */
    QMenuBar {
        background-color: #0F1019;
        color: #8E8EA0;
        border-bottom: 1px solid #1C1D2E;
        padding: 2px;
        font-size: 12px;
    }
    QMenuBar::item:selected {
        background-color: #252638;
        color: #E0E0EC;
        border-radius: 3px;
    }

    QMenu {
        background-color: #1A1B2E;
        color: #C0C0D0;
        border: 1px solid #2D2E42;
        border-radius: 4px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 24px 6px 12px;
        border-radius: 3px;
    }
    QMenu::item:selected {
        background-color: #2563EB;
        color: #FFFFFF;
    }
    QMenu::separator {
        height: 1px;
        background-color: #2D2E42;
        margin: 4px 8px;
    }

    /* ── Status Bar ───────────────────────────── */
    QStatusBar {
        background-color: #0D0E16;
        color: #6B6B80;
        font-size: 11px;
        font-weight: 500;
        border-top: 1px solid #1C1D2E;
        padding: 2px 8px;
    }

    /* ── Splitter ─────────────────────────────── */
    QSplitter::handle {
        background-color: #1C1D2E;
        width: 2px;
        height: 2px;
    }
    QSplitter::handle:hover {
        background-color: #2563EB;
    }

    /* ── Scroll Bars ──────────────────────────── */
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #2D2E42;
        border-radius: 4px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover {
        background: #3B3D56;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        height: 0; background: none;
    }

    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background: #2D2E42;
        border-radius: 4px;
        min-width: 24px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #3B3D56;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        width: 0; background: none;
    }

    /* ── Buttons (global default) ─────────────── */
    QPushButton {
        background-color: #1E1F32;
        color: #C0C0D0;
        border: 1px solid #2D2E42;
        border-radius: 4px;
        padding: 6px 14px;
        font-size: 11px;
        font-weight: 600;
        min-height: 18px;
    }
    QPushButton:hover {
        background-color: #282A40;
        border-color: #3B3D56;
        color: #E0E0EC;
    }
    QPushButton:pressed {
        background-color: #15162A;
    }
    QPushButton:disabled {
        background-color: #151626;
        color: #3B3D56;
        border-color: #1C1D2E;
    }

    /* ── Inputs ───────────────────────────────── */
    QLineEdit {
        background-color: #12131F;
        color: #E0E0EC;
        border: 1px solid #2D2E42;
        border-radius: 4px;
        padding: 5px 10px;
        font-size: 12px;
        selection-background-color: #2563EB;
    }
    QLineEdit:focus {
        border-color: #2563EB;
    }

    QSpinBox, QDoubleSpinBox {
        background-color: #12131F;
        color: #E0E0EC;
        border: 1px solid #2D2E42;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border-color: #2563EB;
    }
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
        width: 16px;
        border: none;
        background: #1E1F32;
    }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: none; width: 0; height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid #6B6B80;
    }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: none; width: 0; height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #6B6B80;
    }

    QComboBox {
        background-color: #12131F;
        color: #E0E0EC;
        border: 1px solid #2D2E42;
        border-radius: 4px;
        padding: 5px 10px;
        font-size: 11px;
        min-width: 60px;
    }
    QComboBox:hover {
        border-color: #3B3D56;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: none; width: 0; height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #6B6B80;
    }
    QComboBox QAbstractItemView {
        background-color: #1A1B2E;
        color: #D0D0DC;
        border: 1px solid #2D2E42;
        selection-background-color: #2563EB;
        selection-color: #FFF;
        padding: 4px;
    }

    /* ── Tables ───────────────────────────────── */
    QTableWidget {
        background-color: #0F1019;
        alternate-background-color: #13141F;
        color: #C0C0D0;
        border: 1px solid #1C1D2E;
        border-radius: 4px;
        gridline-color: #1C1D2E;
        font-size: 11px;
    }
    QTableWidget::item {
        padding: 4px 8px;
        border-bottom: 1px solid #1C1D2E;
    }
    QTableWidget::item:selected {
        background-color: #1E3A5F;
        color: #FFFFFF;
    }
    QHeaderView::section {
        background-color: #141520;
        color: #6B6B80;
        border: none;
        border-bottom: 2px solid #1C1D2E;
        border-right: 1px solid #1C1D2E;
        padding: 6px 8px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
    }

    /* ── Tabs ─────────────────────────────────── */
    QTabWidget::pane {
        border: 1px solid #1C1D2E;
        background-color: #0F1019;
        border-radius: 0 0 4px 4px;
    }
    QTabBar::tab {
        background-color: #141520;
        color: #6B6B80;
        padding: 7px 16px;
        border: 1px solid #1C1D2E;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #0F1019;
        color: #E0E0EC;
        border-bottom: 2px solid #2563EB;
    }
    QTabBar::tab:hover:!selected {
        background-color: #1E1F32;
        color: #C0C0D0;
    }

    /* ── Group Boxes ──────────────────────────── */
    QGroupBox {
        color: #8E8EA0;
        font-size: 12px;
        font-weight: 700;
        border: 1px solid #1C1D2E;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 16px;
        background-color: #12131F;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: #8E8EA0;
    }

    /* ── Progress Bar ─────────────────────────── */
    QProgressBar {
        background-color: #12131F;
        border: 1px solid #1C1D2E;
        border-radius: 4px;
        text-align: center;
        color: #8E8EA0;
        font-size: 10px;
        max-height: 12px;
    }
    QProgressBar::chunk {
        background-color: #2563EB;
        border-radius: 3px;
    }

    /* ── Slider ───────────────────────────────── */
    QSlider::groove:horizontal {
        height: 4px;
        background: #1C1D2E;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        width: 14px;
        height: 14px;
        margin: -5px 0;
        background: #2563EB;
        border-radius: 7px;
    }
    QSlider::handle:horizontal:hover {
        background: #3B82F6;
    }

    /* ── Text Editors ─────────────────────────── */
    QPlainTextEdit {
        background-color: #0D0E16;
        color: #D0D0DC;
        border: 1px solid #1C1D2E;
        border-radius: 4px;
        padding: 8px;
        selection-background-color: #2563EB40;
        font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    }
    QTextEdit {
        background-color: #0D0E16;
        color: #D0D0DC;
        border: 1px solid #1C1D2E;
        border-radius: 4px;
        padding: 6px;
        font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    }

    /* ── Scroll Area ──────────────────────────── */
    QScrollArea {
        background-color: #0F1019;
        border: 1px solid #1C1D2E;
        border-radius: 4px;
    }

    /* ── Check Box ────────────────────────────── */
    QCheckBox {
        color: #C0C0D0;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 14px;
        height: 14px;
        border: 1px solid #2D2E42;
        border-radius: 3px;
        background-color: #12131F;
    }
    QCheckBox::indicator:checked {
        background-color: #2563EB;
        border-color: #2563EB;
    }

    /* ── Labels ───────────────────────────────── */
    QLabel {
        color: #C0C0D0;
    }
"""


def main():
    """Launch the application."""
    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Visual Backtest")
    app.setStyle('Fusion')

    # Apply dark theme
    app.setPalette(create_dark_palette())
    app.setStyleSheet(GLOBAL_STYLESHEET)

    # Main window
    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
