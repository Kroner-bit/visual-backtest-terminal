"""
Playback Controls Widget
--------------------------
Controls for downloading data, running backtest, and
playing back visually with speed control.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QSlider, QProgressBar,
    QSpinBox, QDateEdit, QGroupBox, QSizePolicy, QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QTimer
from PyQt5.QtGui import QFont


class ControlsWidget(QWidget):
    """
    Data download settings + playback controls (play/pause/speed).
    """

    # Signals
    open_data_manager = pyqtSignal()      # open data manager dialog
    play_toggled = pyqtSignal(bool)       # is_playing
    step_forward = pyqtSignal()
    step_backward = pyqtSignal()
    go_to_start = pyqtSignal()
    go_to_end = pyqtSignal()
    speed_changed = pyqtSignal(int)       # speed multiplier
    bar_position_changed = pyqtSignal(int) # manual bar position
    export_requested = pyqtSignal()        # export PDF

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(3)

        # === Row 1: Data Manager + Cash ===
        data_layout = QHBoxLayout()
        data_layout.setSpacing(8)

        self.btn_data_manager = QPushButton("Data Manager")
        self.btn_data_manager.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 5px 16px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)

        self.lbl_data_info = QLabel("No data loaded")
        self.lbl_data_info.setStyleSheet("color: #6B6B80; font-size: 11px; padding: 0 12px;")

        lbl_cash = QLabel("Cash:")
        lbl_cash.setStyleSheet("color: #6B6B80; font-size: 11px;")
        self.spn_cash = QSpinBox()
        self.spn_cash.setRange(100, 10_000_000)
        self.spn_cash.setValue(10_000)
        self.spn_cash.setSingleStep(1000)
        self.spn_cash.setPrefix("$")
        self.spn_cash.setMaximumWidth(110)
        # styled by global stylesheet

        data_layout.addWidget(self.btn_data_manager)
        data_layout.addWidget(self.lbl_data_info, stretch=1)
        data_layout.addWidget(lbl_cash)
        data_layout.addWidget(self.spn_cash)
        main_layout.addLayout(data_layout)

        # === Row 2: Playback controls ===
        play_layout = QHBoxLayout()
        play_layout.setSpacing(3)

        self.btn_start = QPushButton("⏮")
        self.btn_step_back = QPushButton("⏪")
        self.btn_play = QPushButton("▶")
        self.btn_step_fwd = QPushButton("⏩")
        self.btn_end = QPushButton("⏭")

        transport_css = """
            QPushButton {{
                background-color: {bg};
                color: #E0E0EC;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
                min-width: 34px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """

        for btn in [self.btn_start, self.btn_step_back, self.btn_step_fwd, self.btn_end]:
            btn.setStyleSheet(transport_css.format(bg='#1E1F32', hover='#282A40'))

        self.btn_play.setStyleSheet(transport_css.format(bg='#16A34A', hover='#15803D'))

        play_layout.addWidget(self.btn_start)
        play_layout.addWidget(self.btn_step_back)
        play_layout.addWidget(self.btn_play)
        play_layout.addWidget(self.btn_step_fwd)
        play_layout.addWidget(self.btn_end)

        # Speed
        play_layout.addSpacing(10)
        lbl_speed = QLabel("Speed:")
        lbl_speed.setStyleSheet("color: #6B6B80; font-size: 10px;")
        play_layout.addWidget(lbl_speed)

        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(0, 5)
        self.slider_speed.setValue(2)
        self.slider_speed.setMaximumWidth(100)
        # styled by global stylesheet
        play_layout.addWidget(self.slider_speed)

        self.lbl_speed_val = QLabel("5x")
        self.lbl_speed_val.setStyleSheet("color: #2563EB; font-size: 10px; font-weight: 700; min-width: 30px;")
        play_layout.addWidget(self.lbl_speed_val)

        # Progress
        play_layout.addSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(14)
        # styled by global stylesheet
        play_layout.addWidget(self.progress_bar, stretch=1)

        self.lbl_bar_count = QLabel("Bar 0 / 0")
        self.lbl_bar_count.setStyleSheet("color: #8E8EA0; font-size: 10px; min-width: 80px;")
        play_layout.addWidget(self.lbl_bar_count)

        # Timestamp
        play_layout.addSpacing(6)
        self.lbl_timestamp = QLabel("--")
        self.lbl_timestamp.setStyleSheet(
            "color: #D97706; font-size: 11px; font-weight: 700; min-width: 150px;"
        )
        play_layout.addWidget(self.lbl_timestamp)

        # Export PDF
        play_layout.addSpacing(6)
        self.btn_export = QPushButton("Export PDF")
        self.btn_export.setEnabled(False)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #6D28D9;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #7C3AED; }
            QPushButton:disabled {
                background-color: #1E1F32;
                color: #3B3D56;
            }
        """)
        play_layout.addWidget(self.btn_export)
        main_layout.addLayout(play_layout)

        # === Row 3: Account info strip ===
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)

        self.lbl_balance = self._create_info_label("Balance:", "$10,000.00")
        self.lbl_equity = self._create_info_label("Equity:", "$10,000.00")
        self.lbl_floating_pnl = self._create_info_label("Floating P/L:", "$0.00")
        self.lbl_open_trades = self._create_info_label("Open Trades:", "0")
        self.lbl_closed_trades = self._create_info_label("Closed Trades:", "0")

        info_layout.addWidget(self.lbl_balance)
        info_layout.addWidget(self.lbl_equity)
        info_layout.addWidget(self.lbl_floating_pnl)
        info_layout.addWidget(self.lbl_open_trades)
        info_layout.addWidget(self.lbl_closed_trades)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        # Speed map
        self._speed_map = {0: 1, 1: 2, 2: 5, 3: 10, 4: 50, 5: 0}  # 0 = max speed
        self._is_playing = False

        # Connections
        self.btn_data_manager.clicked.connect(self.open_data_manager.emit)
        self.btn_play.clicked.connect(self._on_play_toggle)
        self.btn_start.clicked.connect(self.go_to_start.emit)
        self.btn_end.clicked.connect(self.go_to_end.emit)
        self.btn_step_fwd.clicked.connect(self.step_forward.emit)
        self.btn_step_back.clicked.connect(self.step_backward.emit)
        self.slider_speed.valueChanged.connect(self._on_speed_changed)
        self.btn_export.clicked.connect(self.export_requested.emit)

        self._on_speed_changed(self.slider_speed.value())

    def _create_info_label(self, title: str, value: str) -> QLabel:
        lbl = QLabel(f'<span style="color:#6B6B80;">{title}</span> '
                     f'<span style="color:#E0E0EC;font-weight:bold;">{value}</span>')
        lbl.setStyleSheet("font-size: 10px;")
        return lbl


    def _on_play_toggle(self):
        self._is_playing = not self._is_playing
        if self._is_playing:
            self.btn_play.setText("⏸")
            self.btn_play.setStyleSheet("""
                QPushButton {
                    background-color: #E65100;
                    color: #FFFFFF;
                    border: 1px solid #F57C00;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 14px;
                    min-width: 36px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
        else:
            self.btn_play.setText("▶")
            self.btn_play.setStyleSheet("""
                QPushButton {
                    background-color: #1B5E20;
                    color: #FFFFFF;
                    border: 1px solid #2E7D32;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 14px;
                    min-width: 36px;
                }
                QPushButton:hover {
                    background-color: #2E7D32;
                }
            """)
        self.play_toggled.emit(self._is_playing)

    def _on_speed_changed(self, val):
        speed = self._speed_map.get(val, 5)
        label = "MAX" if speed == 0 else f"{speed}x"
        self.lbl_speed_val.setText(label)
        self.speed_changed.emit(speed)

    def update_bar_info(self, current_bar: int, total_bars: int, timestamp: str = ""):
        """Update bar counter, progress bar, and timestamp."""
        self.lbl_bar_count.setText(f"Bar {current_bar} / {total_bars}")
        if total_bars > 0:
            self.progress_bar.setMaximum(total_bars)
            self.progress_bar.setValue(current_bar)
        if timestamp:
            self.lbl_timestamp.setText(f"🕐 {timestamp}")
        else:
            self.lbl_timestamp.setText("🕐 --")

    def update_account_info(self, balance: float, equity: float,
                            floating_pnl: float, open_count: int,
                            closed_count: int):
        """Update account info strip."""
        pnl_color = '#00E676' if floating_pnl >= 0 else '#FF5252'

        self.lbl_balance.setText(
            f'<span style="color:#888;">Balance:</span> '
            f'<span style="color:#FFF;font-weight:bold;">${balance:,.2f}</span>'
        )
        self.lbl_equity.setText(
            f'<span style="color:#888;">Equity:</span> '
            f'<span style="color:#42A5F5;font-weight:bold;">${equity:,.2f}</span>'
        )
        self.lbl_floating_pnl.setText(
            f'<span style="color:#888;">Floating P/L:</span> '
            f'<span style="color:{pnl_color};font-weight:bold;">${floating_pnl:,.2f}</span>'
        )
        self.lbl_open_trades.setText(
            f'<span style="color:#888;">Open:</span> '
            f'<span style="color:#FFF;font-weight:bold;">{open_count}</span>'
        )
        self.lbl_closed_trades.setText(
            f'<span style="color:#888;">Closed:</span> '
            f'<span style="color:#FFF;font-weight:bold;">{closed_count}</span>'
        )

    def stop_playback(self):
        """Stop playback and reset button."""
        self._is_playing = False
        self.btn_play.setText("▶")
        self.btn_play.setStyleSheet("""
            QPushButton {
                background-color: #1B5E20;
                color: #FFFFFF;
                border: 1px solid #2E7D32;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 14px;
                min-width: 36px;
            }
            QPushButton:hover {
                background-color: #2E7D32;
            }
        """)

    def get_cash(self) -> int:
        """Return initial cash value."""
        return self.spn_cash.value()

    def enable_export(self, enabled: bool):
        """Enable or disable the PDF export button."""
        self.btn_export.setEnabled(enabled)
