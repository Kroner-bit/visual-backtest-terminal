"""
Strategy Editor Widget
-----------------------
Python code editor with syntax highlighting for writing
backtesting.py strategies.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QLabel, QTextEdit, QComboBox,
    QFileDialog, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QRegExp
from PyQt5.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QPalette, QFontMetrics,
)
import os

# Default strategy template
DEFAULT_STRATEGY = '''"""
SMA Crossover Strategy
"""

from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd


def SMA(values, n):
    """Simple Moving Average."""
    return pd.Series(values).rolling(n).mean()


class SmaCross(Strategy):
    # Strategy parameters
    n1 = 10   # Fast SMA period
    n2 = 20   # Slow SMA period

    def init(self):
        self.sma1 = self.I(SMA, self.data.Close, self.n1, name='SMA_fast')
        self.sma2 = self.I(SMA, self.data.Close, self.n2, name='SMA_slow')

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.sell()
'''


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code."""

    def __init__(self, document):
        super().__init__(document)

        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor('#C792EA'))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'and', 'as', 'assert', 'async', 'await', 'break', 'class',
            'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
            'while', 'with', 'yield', 'True', 'False', 'None',
        ]
        for word in keywords:
            pattern = QRegExp(f'\\b{word}\\b')
            self.highlighting_rules.append((pattern, keyword_format))

        # Built-in functions
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor('#82AAFF'))
        builtins = [
            'print', 'len', 'range', 'int', 'float', 'str', 'list',
            'dict', 'set', 'tuple', 'bool', 'abs', 'max', 'min',
            'sum', 'round', 'enumerate', 'zip', 'map', 'filter',
            'isinstance', 'type', 'super', 'self',
        ]
        for word in builtins:
            pattern = QRegExp(f'\\b{word}\\b')
            self.highlighting_rules.append((pattern, builtin_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#F78C6C'))
        self.highlighting_rules.append(
            (QRegExp(r'\b[0-9]+\.?[0-9]*\b'), number_format)
        )

        # Strings (single and double quotes)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#C3E88D'))
        self.highlighting_rules.append(
            (QRegExp(r"'[^']*'"), string_format)
        )
        self.highlighting_rules.append(
            (QRegExp(r'"[^"]*"'), string_format)
        )

        # Decorators
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor('#FFCB6B'))
        self.highlighting_rules.append(
            (QRegExp(r'@\w+'), decorator_format)
        )

        # Comments
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor('#546E7A'))
        self.comment_format.setFontItalic(True)
        self.highlighting_rules.append(
            (QRegExp(r'#[^\n]*'), self.comment_format)
        )

        # Docstrings (triple quotes)
        self.docstring_format = QTextCharFormat()
        self.docstring_format.setForeground(QColor('#546E7A'))
        self.docstring_format.setFontItalic(True)

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)


class StrategyEditor(QWidget):
    """
    Strategy code editor with syntax highlighting.
    Emits signals when user wants to run a backtest.
    """

    run_backtest_requested = pyqtSignal(str)  # code string
    optimize_requested = pyqtSignal(str)       # code string for optimizer
    walkforward_requested = pyqtSignal(str)    # code string for walk-forward

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(350)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header = QLabel("STRATEGY EDITOR")
        header.setStyleSheet("""
            QLabel {
                color: #6B6B80;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.2px;
                padding: 6px 4px 2px 4px;
            }
        """)
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self.btn_load = QPushButton("Load")
        self.btn_save = QPushButton("Save")
        self.btn_run = QPushButton("▶  Run Backtest")

        # Default buttons use global style (no override needed)

        # Primary action: Run
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 7px 18px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #15803D; }
            QPushButton:pressed { background-color: #166534; }
        """)

        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        toolbar.addStretch()

        self.btn_optimize = QPushButton("Optimize")
        self.btn_optimize.setStyleSheet("""
            QPushButton {
                background-color: #B45309;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 7px 14px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #A16207; }
        """)
        toolbar.addWidget(self.btn_optimize)

        self.btn_walkforward = QPushButton("Walk-Forward")
        self.btn_walkforward.setStyleSheet("""
            QPushButton {
                background-color: #1D4ED8;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 7px 14px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1E40AF; }
        """)
        toolbar.addWidget(self.btn_walkforward)
        toolbar.addWidget(self.btn_run)
        layout.addLayout(toolbar)

        # Code editor
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(DEFAULT_STRATEGY)
        font = QFont("Consolas", 11)
        if not QFontMetrics(font).averageCharWidth():
            font = QFont("Courier New", 11)
        self.editor.setFont(font)
        self.editor.setTabStopDistance(
            QFontMetrics(font).horizontalAdvance(' ') * 4
        )
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1A1A2E;
                color: #EEFFFF;
                border: 1px solid #2A2A45;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #3A3A6A;
            }
        """)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.editor, stretch=3)

        # Syntax highlighter
        self.highlighter = PythonHighlighter(self.editor.document())

        # Error output
        error_label = QLabel("Output:")
        error_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(error_label)

        self.error_output = QTextEdit()
        self.error_output.setReadOnly(True)
        self.error_output.setMaximumHeight(100)
        self.error_output.setFont(QFont("Consolas", 9))
        self.error_output.setStyleSheet("""
            QTextEdit {
                background-color: #0D0D1A;
                color: #FF8A80;
                border: 1px solid #2A2A45;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.error_output, stretch=0)

        # Connections
        self.btn_load.clicked.connect(self._load_file)
        self.btn_save.clicked.connect(self._save_file)
        self.btn_run.clicked.connect(self._run_clicked)
        self.btn_optimize.clicked.connect(self._optimize_clicked)
        self.btn_walkforward.clicked.connect(self._walkforward_clicked)

    def _load_file(self):
        """Open a .py file and load its content."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Strategy", "",
            "Python Files (*.py);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
                self.show_message(f"Loaded: {os.path.basename(filepath)}", success=True)
            except Exception as e:
                self.show_error(str(e))

    def _save_file(self):
        """Save editor content to a .py file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Strategy", "",
            "Python Files (*.py);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
                self.show_message(f"Saved: {os.path.basename(filepath)}", success=True)
            except Exception as e:
                self.show_error(str(e))

    def _run_clicked(self):
        """Emit signal to run backtest with current code."""
        code = self.editor.toPlainText()
        self.run_backtest_requested.emit(code)

    def get_code(self) -> str:
        """Return the current strategy code."""
        return self.editor.toPlainText()

    def set_code(self, code: str):
        """Set the editor content."""
        self.editor.setPlainText(code)

    def _optimize_clicked(self):
        """Emit signal to open optimizer with current code."""
        code = self.editor.toPlainText()
        self.optimize_requested.emit(code)

    def _walkforward_clicked(self):
        """Emit signal to open walk-forward dialog with current code."""
        code = self.editor.toPlainText()
        self.walkforward_requested.emit(code)

    def show_error(self, msg: str):
        """Display error message."""
        self.error_output.setStyleSheet("""
            QTextEdit {
                background-color: #1A0A0A;
                color: #FF8A80;
                border: 1px solid #4A1A1A;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.error_output.setPlainText(f"❌ {msg}")

    def show_message(self, msg: str, success=False):
        """Display a status message."""
        if success:
            self.error_output.setStyleSheet("""
                QTextEdit {
                    background-color: #0A1A0A;
                    color: #A5D6A7;
                    border: 1px solid #1A4A1A;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            self.error_output.setPlainText(f"✅ {msg}")
        else:
            self.error_output.setStyleSheet("""
                QTextEdit {
                    background-color: #0D0D1A;
                    color: #C8C8D4;
                    border: 1px solid #2A2A45;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            self.error_output.setPlainText(msg)
