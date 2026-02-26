"""
Equity Curve Widget
--------------------
Collapsible chart showing equity curve with separate lines
for total equity and floating P/L.
"""

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


COLORS = {
    'bg': '#1C1C2E',
    'grid': '#2A2A45',
    'text': '#C8C8D4',
    'equity': '#42A5F5',
    'closed_equity': '#26A69A',
    'floating_pnl': '#FF9800',
    'zero_line': '#FFFFFF30',
    'positive': '#00E676',
    'negative': '#FF5252',
}


class EquityCurveWidget(QWidget):
    """
    Collapsible equity curve chart with separate lines for
    closed-trade equity and floating P/L.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._is_collapsed = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar (always visible)
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #252540;
                border: 1px solid #2A2A45;
                border-radius: 4px 4px 0 0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        self.btn_toggle = QPushButton("▼")
        self.btn_toggle.setFixedSize(24, 24)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #42A5F5;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #90CAF9;
            }
        """)
        self.btn_toggle.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.btn_toggle)

        title = QLabel("📈 Equity Curve")
        title.setStyleSheet("""
            QLabel {
                color: #E0E0E0;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title)

        # Legend items
        header_layout.addStretch()
        self._add_legend_item(header_layout, "● Equity", COLORS['equity'])
        self._add_legend_item(header_layout, "● Closed P/L", COLORS['closed_equity'])
        self._add_legend_item(header_layout, "● Floating P/L", COLORS['floating_pnl'])

        main_layout.addWidget(header)

        # Chart area (collapsible)
        self.chart_container = QFrame()
        self.chart_container.setStyleSheet(f"background-color: {COLORS['bg']};")
        chart_layout = QVBoxLayout(self.chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        self.fig = Figure(facecolor=COLORS['bg'], dpi=100)
        self.fig.set_size_inches(10, 2.5)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet(f"background-color: {COLORS['bg']};")
        self.canvas.setMinimumHeight(140)
        self.canvas.setMaximumHeight(180)
        chart_layout.addWidget(self.canvas)

        main_layout.addWidget(self.chart_container)

        # Internal data storage
        self._equity_history = []       # total equity per bar
        self._closed_pnl_history = []   # cumulative closed P/L per bar
        self._floating_pnl_history = [] # floating P/L per bar
        self._initial_cash = 10_000

        self._setup_axes()

    def _add_legend_item(self, layout, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        layout.addWidget(lbl)

    def _setup_axes(self):
        """Create the chart axes."""
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(COLORS['bg'])
        self.ax.tick_params(colors=COLORS['text'], labelsize=7)
        self.ax.grid(True, color=COLORS['grid'], alpha=0.3, linewidth=0.5)
        for spine in self.ax.spines.values():
            spine.set_color(COLORS['grid'])
            spine.set_linewidth(0.5)

    def _toggle_collapse(self):
        """Toggle chart visibility."""
        self._is_collapsed = not self._is_collapsed
        self.chart_container.setVisible(not self._is_collapsed)
        self.btn_toggle.setText("▶" if self._is_collapsed else "▼")

    def reset(self, initial_cash: float = 10_000):
        """Reset data for a new backtest."""
        self._initial_cash = initial_cash
        self._equity_history = []
        self._closed_pnl_history = []
        self._floating_pnl_history = []

    def update_curve(self, bar_index: int, equity: float,
                     closed_pnl: float, floating_pnl: float):
        """
        Update equity curve data for the current bar.

        Args:
            bar_index: Current bar index
            equity: Total equity (balance + floating)
            closed_pnl: Cumulative closed-trade P/L
            floating_pnl: Current floating P/L
        """
        # Extend lists if needed
        while len(self._equity_history) <= bar_index:
            self._equity_history.append(self._initial_cash)
            self._closed_pnl_history.append(0.0)
            self._floating_pnl_history.append(0.0)

        self._equity_history[bar_index] = equity
        self._closed_pnl_history[bar_index] = closed_pnl
        self._floating_pnl_history[bar_index] = floating_pnl

        # Only redraw if visible
        if self._is_collapsed:
            return

        self._redraw(bar_index)

    def _redraw(self, up_to_bar: int):
        """Redraw the equity curve chart."""
        self.ax.clear()
        self.ax.set_facecolor(COLORS['bg'])
        self.ax.tick_params(colors=COLORS['text'], labelsize=7)
        self.ax.grid(True, color=COLORS['grid'], alpha=0.3, linewidth=0.5)
        for spine in self.ax.spines.values():
            spine.set_color(COLORS['grid'])
            spine.set_linewidth(0.5)

        n = min(up_to_bar + 1, len(self._equity_history))
        if n < 2:
            self.canvas.draw_idle()
            return

        x = np.arange(n)
        equity = np.array(self._equity_history[:n])
        closed = np.array(self._closed_pnl_history[:n])
        floating = np.array(self._floating_pnl_history[:n])

        # Plot equity line
        self.ax.plot(x, equity, color=COLORS['equity'],
                     linewidth=1.5, alpha=0.9, zorder=3)

        # Plot closed P/L as area relative to initial cash
        closed_equity = self._initial_cash + closed
        self.ax.plot(x, closed_equity, color=COLORS['closed_equity'],
                     linewidth=1.2, alpha=0.8, zorder=2)
        self.ax.fill_between(x, self._initial_cash, closed_equity,
                             where=closed_equity >= self._initial_cash,
                             color=COLORS['closed_equity'], alpha=0.15, zorder=1)
        self.ax.fill_between(x, self._initial_cash, closed_equity,
                             where=closed_equity < self._initial_cash,
                             color=COLORS['negative'], alpha=0.15, zorder=1)

        # Plot floating P/L as filled area at the bottom
        # Shift floating to a secondary visual: show as deviation from equity
        self.ax.fill_between(x, closed_equity, equity,
                             where=floating >= 0,
                             color=COLORS['floating_pnl'], alpha=0.25, zorder=1)
        self.ax.fill_between(x, closed_equity, equity,
                             where=floating < 0,
                             color=COLORS['negative'], alpha=0.25, zorder=1)

        # Zero line (initial cash)
        self.ax.axhline(y=self._initial_cash, color=COLORS['zero_line'],
                        linewidth=0.8, linestyle='--', zorder=0)

        # Current equity annotation
        curr_equity = equity[-1]
        pnl_total = curr_equity - self._initial_cash
        pnl_color = COLORS['positive'] if pnl_total >= 0 else COLORS['negative']
        self.ax.annotate(
            f'${curr_equity:,.0f} ({pnl_total:+,.0f})',
            xy=(1.0, curr_equity),
            xycoords=('axes fraction', 'data'),
            fontsize=8, color=pnl_color, fontweight='bold',
            va='center', ha='left',
            bbox=dict(boxstyle='round,pad=0.2',
                      facecolor=COLORS['bg'], edgecolor=COLORS['grid']),
            zorder=10
        )

        self.ax.set_ylabel('Equity ($)', color=COLORS['text'], fontsize=8)
        self.fig.tight_layout(pad=0.5)
        self.canvas.draw_idle()
