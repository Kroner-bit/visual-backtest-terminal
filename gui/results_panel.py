"""
Results Panel Widget
---------------------
Shows final backtest statistics in a clean summary view.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import Dict, Any


class ResultsPanel(QWidget):
    """
    Displays final backtest results in a styled summary panel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header = QLabel("BACKTEST RESULTS")
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

        # Scroll area for stats (styled by global stylesheet)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.stats_container = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_container)
        self.stats_layout.setContentsMargins(8, 8, 8, 8)
        self.stats_layout.setSpacing(2)
        self.stats_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.stats_container)
        layout.addWidget(scroll)

        # Status label
        self.status_label = QLabel("Run a backtest to see results")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 20px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.stats_layout.addWidget(self.status_label)

    def update_results(self, stats: Dict[str, Any]):
        """Display backtest statistics."""
        # Clear existing
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not stats:
            self.status_label = QLabel("No results available")
            self.status_label.setStyleSheet("color: #666; font-size: 12px; padding: 20px;")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.stats_layout.addWidget(self.status_label)
            return

        # Group stats into sections
        sections = {
            'Performance': [
                'Return [%]', 'Buy & Hold Return [%]',
                'Return (Ann.) [%]', 'Volatility (Ann.) [%]',
            ],
            'Risk Metrics': [
                'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio',
                'Max. Drawdown [%]', 'Avg. Drawdown [%]',
                'Max. Drawdown Duration', 'Avg. Drawdown Duration',
            ],
            'Trade Statistics': [
                '# Trades', 'Win Rate [%]',
                'Best Trade [%]', 'Worst Trade [%]',
                'Avg. Trade [%]', 'Profit Factor',
                'Expectancy [%]', 'SQN',
            ],
            'Account': [
                'Equity Final [$]', 'Equity Peak [$]',
                'Exposure Time [%]',
            ],
            'Duration': [
                'Start', 'End', 'Duration',
                'Max. Trade Duration', 'Avg. Trade Duration',
            ],
        }

        for section_name, keys in sections.items():
            # Section header
            section_items = [(k, stats[k]) for k in keys if k in stats]
            if not section_items:
                continue

            header = QLabel(section_name)
            header.setStyleSheet("""
                QLabel {
                    color: #2563EB;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 8px 0 4px 0;
                    border-bottom: 1px solid #1C1D2E;
                }
            """)
            self.stats_layout.addWidget(header)

            for key, value in section_items:
                row = self._create_stat_row(key, value)
                self.stats_layout.addWidget(row)

        # Spacer at bottom
        self.stats_layout.addStretch()

    def _create_stat_row(self, key: str, value: Any) -> QWidget:
        """Create a single stat row widget."""
        row = QFrame()
        row.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-bottom: 1px solid #1A1A2E;
                padding: 0px;
            }
        """)

        layout = QVBoxLayout(row)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)

        # Determine value color
        value_color = '#FFFFFF'
        value_str = str(value)

        if isinstance(value, (int, float)):
            if 'Return' in key or 'P/L' in key or key in ('Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio', 'Profit Factor', 'SQN', 'Win Rate [%]', 'Best Trade [%]'):
                if value > 0:
                    value_color = '#00E676'
                elif value < 0:
                    value_color = '#FF5252'
            if 'Drawdown' in key and isinstance(value, float):
                value_color = '#FF5252' if value < 0 else '#FF9800'
            if '$' in key:
                value_str = f"${value:,.2f}"
            elif '%' in key:
                value_str = f"{value:.2f}%"
            else:
                value_str = f"{value:.4f}" if isinstance(value, float) else str(value)

        label = QLabel(
            f'<span style="color:#888;font-size:10px;">{key}</span>'
            f'<br/>'
            f'<span style="color:{value_color};font-size:12px;font-weight:bold;">{value_str}</span>'
        )
        label.setStyleSheet("background: transparent;")
        layout.addWidget(label)

        return row

    def show_running(self):
        """Show 'running' status."""
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        lbl = QLabel("⏳ Running backtest...")
        lbl.setStyleSheet("""
            QLabel {
                color: #42A5F5;
                font-size: 13px;
                padding: 20px;
            }
        """)
        lbl.setAlignment(Qt.AlignCenter)
        self.stats_layout.addWidget(lbl)
