"""
Trades Panel Widget
--------------------
Shows open trades with floating P/L and closed trades history.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QTabWidget, QLabel, QHeaderView, QSizePolicy, QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QBrush
from typing import List, Dict


class TradesPanel(QWidget):
    """
    Tabbed panel showing open trades and trade history.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header = QLabel("TRADES")
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

        # Tab widget (styled by global stylesheet)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Open Trades table
        self.open_table = QTableWidget()
        self.open_table.setColumnCount(6)
        self.open_table.setHorizontalHeaderLabels([
            'Time', 'Type', 'Size', 'Entry', 'Current', 'P/L'
        ])
        self._setup_table(self.open_table)
        self.tabs.addTab(self.open_table, "Open Trades")

        # Closed Trades table
        self.closed_table = QTableWidget()
        self.closed_table.setColumnCount(7)
        self.closed_table.setHorizontalHeaderLabels([
            'Entry', 'Exit', 'Type', 'Size', 'Entry$', 'Exit$', 'P/L'
        ])
        self._setup_table(self.closed_table)
        self.tabs.addTab(self.closed_table, "History")

    def _setup_table(self, table: QTableWidget):
        """Apply common table config."""
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setDefaultSectionSize(75)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        font = QFont("Consolas", 10)
        table.setFont(font)

    def update_open_trades(self, trades: List[Dict]):
        """Update the open trades table."""
        self.open_table.setRowCount(len(trades))

        for row, trade in enumerate(trades):
            entry_time = str(trade.get('entry_time', ''))
            if len(entry_time) > 10:
                entry_time = entry_time[:10]

            is_long = trade.get('is_long', True)
            type_str = "BUY" if is_long else "SELL"
            type_color = QColor('#00E676') if is_long else QColor('#FF5252')

            size = abs(trade.get('size', 0))
            entry_price = trade.get('entry_price', 0)
            current_price = trade.get('current_price', 0)
            pnl = trade.get('floating_pnl', 0)
            pnl_color = QColor('#00E676') if pnl >= 0 else QColor('#FF5252')

            items = [
                (entry_time, None),
                (type_str, type_color),
                (f"{size:.2f}", None),
                (f"{entry_price:.2f}", None),
                (f"{current_price:.2f}", None),
                (f"${pnl:+,.2f}", pnl_color),
            ]

            for col, (text, color) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if color:
                    item.setForeground(QBrush(color))
                self.open_table.setItem(row, col, item)

        # Update tab label
        self.tabs.setTabText(0, f"Open Trades ({len(trades)})")

    def update_closed_trades(self, trades: list):
        """Update closed trades history."""
        # Show most recent trades first, limit to 100
        recent = trades[-100:] if len(trades) > 100 else trades
        recent = list(reversed(recent))

        self.closed_table.setRowCount(len(recent))

        for row, trade in enumerate(recent):
            entry_time = str(getattr(trade, 'entry_time', ''))
            exit_time = str(getattr(trade, 'exit_time', ''))
            if len(entry_time) > 10:
                entry_time = entry_time[:10]
            if len(exit_time) > 10:
                exit_time = exit_time[:10]

            is_long = trade.is_long
            type_str = "BUY" if is_long else "SELL"
            type_color = QColor('#00E676') if is_long else QColor('#FF5252')

            pnl = trade.pnl
            pnl_color = QColor('#00E676') if pnl >= 0 else QColor('#FF5252')

            items = [
                (entry_time, None),
                (exit_time, None),
                (type_str, type_color),
                (f"{abs(trade.size):.2f}", None),
                (f"{trade.entry_price:.2f}", None),
                (f"{trade.exit_price:.2f}", None),
                (f"${pnl:+,.2f}", pnl_color),
            ]

            for col, (text, color) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if color:
                    item.setForeground(QBrush(color))
                self.closed_table.setItem(row, col, item)

        # Update tab label
        total = len(trades)
        self.tabs.setTabText(1, f"History ({total})")
