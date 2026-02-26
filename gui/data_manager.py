"""
Data Manager Dialog
--------------------
Separate window for browsing cached datasets and
downloading new market data. Uses SQLite via data_cache.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QApplication, QSpinBox, QGroupBox,
    QAbstractItemView, QWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

import pandas as pd
import data_fetcher
import data_cache


class DataManagerDialog(QDialog):
    """
    Dialog for managing cached market data.
    Allows browsing existing datasets and downloading new ones.
    """

    # Emitted when user selects a dataset: (dataset_id, ticker, df)
    dataset_selected = pyqtSignal(int, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Data Manager")
        self.setMinimumSize(800, 650)
        self.resize(900, 720)
        self.setStyleSheet("""
            QDialog {
                background-color: #1C1C2E;
                color: #C8C8D4;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # === Download Section ===
        dl_group = QGroupBox("⬇ Download New Data")
        dl_group.setStyleSheet("""
            QGroupBox {
                color: #42A5F5;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #2A2A45;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        dl_layout = QHBoxLayout(dl_group)
        dl_layout.setSpacing(8)

        lbl_style = "color: #888; font-size: 11px;"
        input_style = """
            QLineEdit, QComboBox, QSpinBox {
                background-color: #1A1A2E;
                color: #FFF;
                border: 1px solid #3A3A5A;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 12px;
            }
        """

        # Ticker
        lbl_t = QLabel("Symbol:")
        lbl_t.setStyleSheet(lbl_style)
        self.txt_ticker = QLineEdit("AAPL")
        self.txt_ticker.setMaximumWidth(100)
        self.txt_ticker.setStyleSheet(input_style)

        # Period
        lbl_p = QLabel("Period:")
        lbl_p.setStyleSheet(lbl_style)
        self.cmb_period = QComboBox()
        self.cmb_period.addItems(["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"])
        self.cmb_period.setCurrentText("1y")
        self.cmb_period.setMaximumWidth(80)
        self.cmb_period.setStyleSheet(input_style)

        # Interval
        lbl_i = QLabel("Interval:")
        lbl_i.setStyleSheet(lbl_style)
        self.cmb_interval = QComboBox()
        self.cmb_interval.addItems(["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"])
        self.cmb_interval.setCurrentText("1d")
        self.cmb_interval.setMaximumWidth(80)
        self.cmb_interval.setStyleSheet(input_style)

        # Download button
        self.btn_download = QPushButton("⬇ Download")
        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: #1565C0;
                color: #FFF;
                border: 1px solid #1976D2;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_download.clicked.connect(self._on_download)

        dl_layout.addWidget(lbl_t)
        dl_layout.addWidget(self.txt_ticker)
        dl_layout.addWidget(lbl_p)
        dl_layout.addWidget(self.cmb_period)
        dl_layout.addWidget(lbl_i)
        dl_layout.addWidget(self.cmb_interval)
        dl_layout.addStretch()
        dl_layout.addWidget(self.btn_download)

        main_layout.addWidget(dl_group)

        # === Ticker Search Section ===
        search_group = QGroupBox("🔍 Search Ticker")
        search_group.setStyleSheet("""
            QGroupBox {
                color: #FF9800;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #2A2A45;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        search_layout = QVBoxLayout(search_group)
        search_layout.setSpacing(6)

        # Search input row
        search_input_layout = QHBoxLayout()
        search_input_layout.setSpacing(8)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by company name or ticker (e.g. Apple, TSLA, Bitcoin)...")
        self.txt_search.setStyleSheet(input_style)
        self.txt_search.returnPressed.connect(self._on_search)

        self.btn_search = QPushButton("🔍 Search")
        self.btn_search.setStyleSheet("""
            QPushButton {
                background-color: #E65100;
                color: #FFF;
                border: 1px solid #F57C00;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F57C00; }
        """)
        self.btn_search.clicked.connect(self._on_search)

        search_input_layout.addWidget(self.txt_search, stretch=1)
        search_input_layout.addWidget(self.btn_search)
        search_layout.addLayout(search_input_layout)

        # Search results table
        self.search_table = QTableWidget()
        self.search_table.setColumnCount(4)
        self.search_table.setHorizontalHeaderLabels(["Symbol", "Name", "Type", "Exchange"])
        self.search_table.horizontalHeader().setStretchLastSection(True)
        self.search_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.search_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.search_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.search_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.search_table.verticalHeader().setVisible(False)
        self.search_table.setMaximumHeight(130)
        self.search_table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A2E;
                color: #C8C8D4;
                border: 1px solid #2A2A45;
                border-radius: 4px;
                gridline-color: #2A2A45;
                font-size: 11px;
            }
            QTableWidget::item { padding: 3px 6px; }
            QTableWidget::item:selected {
                background-color: #E65100;
                color: #FFF;
            }
            QHeaderView::section {
                background-color: #252540;
                color: #FF9800;
                font-weight: bold;
                font-size: 11px;
                padding: 4px;
                border: 1px solid #2A2A45;
            }
        """)
        self.search_table.doubleClicked.connect(self._on_search_select)
        search_layout.addWidget(self.search_table)

        self.lbl_search_hint = QLabel("💡 Double-click a result to fill the Symbol field above")
        self.lbl_search_hint.setStyleSheet("color: #666; font-size: 10px;")
        search_layout.addWidget(self.lbl_search_hint)

        main_layout.addWidget(search_group)

        # === Status label ===
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #888; font-size: 11px; padding: 2px 4px;")
        main_layout.addWidget(self.lbl_status)

        # === Cached Data Table ===
        lbl_cached = QLabel("📁 Cached Datasets")
        lbl_cached.setStyleSheet("color: #42A5F5; font-size: 13px; font-weight: bold;")
        main_layout.addWidget(lbl_cached)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Ticker", "Period", "Interval", "Bars", "Start", "End", "Downloaded"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A2E;
                color: #C8C8D4;
                border: 1px solid #2A2A45;
                border-radius: 4px;
                gridline-color: #2A2A45;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QTableWidget::item:selected {
                background-color: #1565C0;
                color: #FFF;
            }
            QTableWidget::item:alternate {
                background-color: #22223A;
            }
            QHeaderView::section {
                background-color: #252540;
                color: #42A5F5;
                font-weight: bold;
                font-size: 11px;
                padding: 5px;
                border: 1px solid #2A2A45;
            }
        """)
        self.table.doubleClicked.connect(self._on_double_click)
        main_layout.addWidget(self.table, stretch=1)

        # === Bottom buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_load = QPushButton("✅ Load Selected")
        self.btn_load.setStyleSheet("""
            QPushButton {
                background-color: #1B5E20;
                color: #FFF;
                border: 1px solid #2E7D32;
                border-radius: 4px;
                padding: 7px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2E7D32; }
        """)
        self.btn_load.clicked.connect(self._on_load)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #B71C1C;
                color: #FFF;
                border: 1px solid #D32F2F;
                border-radius: 4px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D32F2F; }
        """)
        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #2A2A45;
                color: #C8C8D4;
                border: 1px solid #3A3A5A;
                border-radius: 4px;
                padding: 7px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #3A3A5A; }
        """)
        self.btn_refresh.clicked.connect(self._refresh_table)

        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(btn_layout)

        # Internal state
        self._datasets = []

        # Load data
        self._refresh_table()

    def _refresh_table(self):
        """Reload the table from the database."""
        self._datasets = data_cache.list_datasets()
        self.table.setRowCount(len(self._datasets))

        for i, ds in enumerate(self._datasets):
            self.table.setItem(i, 0, QTableWidgetItem(ds['ticker']))
            self.table.setItem(i, 1, QTableWidgetItem(ds['period']))
            self.table.setItem(i, 2, QTableWidgetItem(ds['interval']))
            self.table.setItem(i, 3, QTableWidgetItem(str(ds['bars'])))
            self.table.setItem(i, 4, QTableWidgetItem(ds['start_date'][:10]))
            self.table.setItem(i, 5, QTableWidgetItem(ds['end_date'][:10]))
            self.table.setItem(i, 6, QTableWidgetItem(ds['downloaded']))

        count = len(self._datasets)
        self.lbl_status.setText(f"{count} dataset(s) in cache")

    def _on_download(self):
        """Download new data and save to cache."""
        ticker = self.txt_ticker.text().strip().upper()
        period = self.cmb_period.currentText()
        interval = self.cmb_interval.currentText()

        if not ticker:
            QMessageBox.warning(self, "Error", "Enter a ticker symbol!")
            return

        self.lbl_status.setText(f"Downloading {ticker} ({interval})...")
        self.btn_download.setEnabled(False)
        QApplication.processEvents()

        try:
            df = data_fetcher.fetch_data(
                ticker=ticker, period=period, interval=interval,
            )
            dataset_id = data_cache.save_dataset(ticker, period, interval, df)
            self.lbl_status.setText(
                f"✅ Downloaded {len(df)} bars of {ticker} ({interval}) — saved to cache"
            )
            self._refresh_table()

            # Select the newly downloaded row
            for i, ds in enumerate(self._datasets):
                if ds['id'] == dataset_id:
                    self.table.selectRow(i)
                    break

        except Exception as e:
            self.lbl_status.setText(f"❌ Download failed: {e}")
        finally:
            self.btn_download.setEnabled(True)

    def _on_load(self):
        """Load the selected dataset and emit signal."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._datasets):
            QMessageBox.warning(self, "Error", "Select a dataset first!")
            return

        ds = self._datasets[row]
        self.lbl_status.setText(f"Loading {ds['ticker']}...")
        QApplication.processEvents()

        df = data_cache.load_dataset(ds['id'])
        if df is None or df.empty:
            QMessageBox.warning(self, "Error", "Dataset is empty or corrupted!")
            return

        self.dataset_selected.emit(ds['id'], ds['ticker'], df)
        self.lbl_status.setText(f"✅ Loaded {ds['ticker']} — {len(df)} bars")
        self.accept()  # Close the dialog

    def _on_double_click(self, index):
        """Double-click to load a dataset."""
        self._on_load()

    def _on_delete(self):
        """Delete the selected dataset."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._datasets):
            QMessageBox.warning(self, "Error", "Select a dataset first!")
            return

        ds = self._datasets[row]
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete cached data for {ds['ticker']} ({ds['interval']}, {ds['period']})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            data_cache.delete_dataset(ds['id'])
            self._refresh_table()
            self.lbl_status.setText(f"🗑 Deleted {ds['ticker']}")

    def _on_search(self):
        """Search for tickers using Yahoo Finance."""
        query = self.txt_search.text().strip()
        if not query:
            return

        self.lbl_search_hint.setText("Searching...")
        self.btn_search.setEnabled(False)
        QApplication.processEvents()

        try:
            from yfinance.search import Search
            results = Search(query, max_results=10)
            quotes = results.quotes if results.quotes else []

            self.search_table.setRowCount(len(quotes))
            for i, q in enumerate(quotes):
                symbol = q.get('symbol', '')
                name = q.get('shortname', q.get('longname', ''))
                qtype = q.get('quoteType', '')
                exchange = q.get('exchDisp', q.get('exchange', ''))

                self.search_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.search_table.setItem(i, 1, QTableWidgetItem(name))
                self.search_table.setItem(i, 2, QTableWidgetItem(qtype))
                self.search_table.setItem(i, 3, QTableWidgetItem(exchange))

            self.lbl_search_hint.setText(
                f"Found {len(quotes)} result(s) — double-click to use"
            )
        except Exception as e:
            self.lbl_search_hint.setText(f"Search failed: {e}")
        finally:
            self.btn_search.setEnabled(True)

    def _on_search_select(self, index):
        """Double-click search result → fill the ticker field."""
        row = index.row()
        symbol_item = self.search_table.item(row, 0)
        if symbol_item:
            self.txt_ticker.setText(symbol_item.text())
            name_item = self.search_table.item(row, 1)
            name = name_item.text() if name_item else ''
            self.lbl_status.setText(f"Selected: {symbol_item.text()} — {name}")
