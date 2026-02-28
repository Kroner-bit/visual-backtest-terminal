"""
Candlestick Chart Widget
-------------------------
Embedded matplotlib chart showing OHLCV candles, trade markers,
indicators, and volume. Designed for dark theme MT5-style look.
"""

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

from gui.objects import ChartObject, HLine, VLine, TrendLine, Rectangle, Text


# MT5-style dark colors
COLORS = {
    'bg': '#1C1C2E',
    'panel': '#252540',
    'grid': '#2A2A45',
    'text': '#C8C8D4',
    'candle_up': '#26A69A',
    'candle_down': '#EF5350',
    'wick_up': '#26A69A',
    'wick_down': '#EF5350',
    'volume_up': '#26A69A55',
    'volume_down': '#EF535055',
    'buy_marker': '#00E676',
    'sell_marker': '#FF5252',
    'close_marker': '#FFD740',
    'equity': '#42A5F5',
    'indicator1': '#FF9800',
    'indicator2': '#E040FB',
    'indicator3': '#00BCD4',
    'indicator4': '#FFEB3B',
    'tp_line': '#00E676',
    'sl_line': '#FF5252',
    'crosshair': '#FFFFFF40',
}

INDICATOR_COLORS = [
    '#FF9800', '#E040FB', '#00BCD4', '#FFEB3B',
    '#8BC34A', '#FF5722', '#9C27B0', '#00ACC1',
]


class ChartWidget(QWidget):
    """
    Candlestick chart with trade markers, indicators, and volume.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Data
        self.ohlcv_data: pd.DataFrame = None
        self.visible_bars: int = 0
        self.trade_markers = []    # List of dicts {bar, price, type, is_long}
        self.indicator_data = {}   # name -> array
        self.open_trade_lines = [] # Currently open trade horizontal lines
        self.chart_objects = []    # Custom objects drawn by strategy

        # Chart setup
        self.fig = Figure(facecolor=COLORS['bg'], dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet(f"background-color: {COLORS['bg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        # Create subplots
        self._setup_axes()

        # Visible window
        self.window_size = 80   # Number of bars visible at once
        self.scroll_offset = 0  # Scroll position

    def _setup_axes(self):
        """Create the price and volume axes."""
        self.fig.clear()

        # Price chart (main)
        self.ax_price = self.fig.add_axes([0.06, 0.28, 0.88, 0.68])
        # Volume chart (bottom)
        self.ax_volume = self.fig.add_axes([0.06, 0.06, 0.88, 0.18])

        for ax in [self.ax_price, self.ax_volume]:
            ax.set_facecolor(COLORS['bg'])
            ax.tick_params(colors=COLORS['text'], labelsize=8)
            ax.grid(True, color=COLORS['grid'], alpha=0.3, linewidth=0.5)
            for spine in ax.spines.values():
                spine.set_color(COLORS['grid'])
                spine.set_linewidth(0.5)

        self.ax_price.tick_params(labelbottom=False)

    def set_data(self, data: pd.DataFrame, indicators: dict = None):
        """Set the full OHLCV data and indicator arrays."""
        self.ohlcv_data = data
        self.indicator_data = indicators or {}
        self.trade_markers = []
        self.open_trade_lines = []
        self.chart_objects = []

    def update_chart(self, bar_index: int, trade_markers: list = None,
                     open_trades: list = None, indicators: dict = None,
                     chart_objects: list = None):
        """
        Redraw the chart up to bar_index.

        Args:
            bar_index: Show candles 0..bar_index
            trade_markers: List of {bar, price, type ('OPEN'/'CLOSE'), is_long}
            open_trades: List of {entry_bar, entry_price, is_long, current_price}
            indicators: Dict of indicator name -> array
            chart_objects: List of custom drawn objects
        """
        if self.ohlcv_data is None or self.ohlcv_data.empty:
            return

        self.visible_bars = min(bar_index + 1, len(self.ohlcv_data))

        if trade_markers is not None:
            self.trade_markers = trade_markers
        if indicators is not None:
            self.indicator_data = indicators
        if chart_objects is not None:
            self.chart_objects = chart_objects

        # Determine visible window
        start = max(0, self.visible_bars - self.window_size)
        end = self.visible_bars
        visible_data = self.ohlcv_data.iloc[start:end]

        if visible_data.empty:
            return

        # Clear axes
        self.ax_price.clear()
        self.ax_volume.clear()

        # Re-apply style
        for ax in [self.ax_price, self.ax_volume]:
            ax.set_facecolor(COLORS['bg'])
            ax.tick_params(colors=COLORS['text'], labelsize=8)
            ax.grid(True, color=COLORS['grid'], alpha=0.3, linewidth=0.5)
            for spine in ax.spines.values():
                spine.set_color(COLORS['grid'])
                spine.set_linewidth(0.5)

        self.ax_price.tick_params(labelbottom=False)

        # Plot candles
        x_indices = np.arange(len(visible_data))
        opens = visible_data['Open'].values
        highs = visible_data['High'].values
        lows = visible_data['Low'].values
        closes = visible_data['Close'].values

        up = closes >= opens
        down = ~up

        body_width = 0.6
        wick_width = 0.15

        # Up candles
        if np.any(up):
            self.ax_price.bar(x_indices[up], closes[up] - opens[up],
                              bottom=opens[up], width=body_width,
                              color=COLORS['candle_up'], edgecolor=COLORS['candle_up'],
                              linewidth=0.5, zorder=3)
            self.ax_price.vlines(x_indices[up], lows[up], highs[up],
                                 colors=COLORS['wick_up'], linewidth=wick_width,
                                 zorder=2)

        # Down candles
        if np.any(down):
            self.ax_price.bar(x_indices[down], opens[down] - closes[down],
                              bottom=closes[down], width=body_width,
                              color=COLORS['candle_down'], edgecolor=COLORS['candle_down'],
                              linewidth=0.5, zorder=3)
            self.ax_price.vlines(x_indices[down], lows[down], highs[down],
                                 colors=COLORS['wick_down'], linewidth=wick_width,
                                 zorder=2)

        # Draw volume bars
        if 'Volume' in visible_data.columns:
            volumes = visible_data['Volume'].values
            vol_colors = [COLORS['volume_up'] if u else COLORS['volume_down'] for u in up]
            self.ax_volume.bar(x_indices, volumes, width=body_width,
                               color=vol_colors, zorder=3)
            self.ax_volume.set_ylabel('Volume', color=COLORS['text'], fontsize=8)

        # Draw indicators
        for idx, (name, arr) in enumerate(self.indicator_data.items()):
            if arr is not None and len(arr) > 0:
                vis_arr = arr[start:end]
                color = INDICATOR_COLORS[idx % len(INDICATOR_COLORS)]
                # Filter NaN
                valid = ~np.isnan(vis_arr)
                if np.any(valid):
                    self.ax_price.plot(x_indices[valid], vis_arr[valid],
                                      color=color, linewidth=1.2, alpha=0.9,
                                      label=name, zorder=4)

        # Draw trade markers
        for marker in self.trade_markers:
            bar = marker.get('bar', 0)
            price = marker.get('price', 0)
            mtype = marker.get('type', 'OPEN')
            is_long = marker.get('is_long', True)

            # Convert to visible x position
            x_pos = bar - start
            if x_pos < 0 or x_pos >= len(x_indices):
                continue

            if mtype == 'OPEN':
                if is_long:
                    self.ax_price.annotate('▲', xy=(x_pos, price),
                                           fontsize=12, color=COLORS['buy_marker'],
                                           ha='center', va='top', zorder=10,
                                           fontweight='bold')
                else:
                    self.ax_price.annotate('▼', xy=(x_pos, price),
                                           fontsize=12, color=COLORS['sell_marker'],
                                           ha='center', va='bottom', zorder=10,
                                           fontweight='bold')
            elif mtype == 'CLOSE':
                self.ax_price.annotate('✕', xy=(x_pos, price),
                                       fontsize=10, color=COLORS['close_marker'],
                                       ha='center', va='center', zorder=10,
                                       fontweight='bold')

        # Draw open trade entry lines
        if open_trades:
            for ot in open_trades:
                entry_price = ot.get('entry_price', 0)
                is_long = ot.get('is_long', True)
                color = COLORS['buy_marker'] if is_long else COLORS['sell_marker']
                self.ax_price.axhline(y=entry_price, color=color, linewidth=0.8,
                                      linestyle='--', alpha=0.6, zorder=5)

        # Draw custom chart objects
        for obj in self.chart_objects:
            z = obj.layer
            if isinstance(obj, HLine):
                self.ax_price.axhline(y=obj.price, color=obj.color, linestyle=obj.style,
                                      linewidth=obj.width, alpha=obj.alpha, zorder=z)
            elif isinstance(obj, VLine):
                x_pos = obj.bar - start
                if 0 <= x_pos <= len(x_indices):
                    self.ax_price.axvline(x=x_pos, color=obj.color, linestyle=obj.style,
                                          linewidth=obj.width, alpha=obj.alpha, zorder=z)
            elif isinstance(obj, TrendLine):
                x1 = obj.bar1 - start
                x2 = obj.bar2 - start
                # Even if points are outside window, matplotlib handles clipping
                if obj.extend_right and x1 != x2:
                    # Calculate slope and extend to right edge
                    slope = (obj.price2 - obj.price1) / (x2 - x1)
                    x2_ext = max(x2, len(x_indices) + 10)
                    y2_ext = obj.price1 + slope * (x2_ext - x1)
                    self.ax_price.plot([x1, x2_ext], [obj.price1, y2_ext],
                                       color=obj.color, linestyle=obj.style,
                                       linewidth=obj.width, alpha=obj.alpha, zorder=z)
                else:
                    self.ax_price.plot([x1, x2], [obj.price1, obj.price2],
                                       color=obj.color, linestyle=obj.style,
                                       linewidth=obj.width, alpha=obj.alpha, zorder=z)
            elif isinstance(obj, Rectangle):
                x1 = obj.bar1 - start
                x2 = obj.bar2 - start
                width = x2 - x1
                height = obj.price2 - obj.price1
                
                rect = patches.Rectangle((x1, obj.price1), width, height,
                                         linewidth=obj.width, edgecolor=obj.color,
                                         facecolor=obj.fill_color or 'none',
                                         alpha=obj.alpha, zorder=z)
                self.ax_price.add_patch(rect)
            elif isinstance(obj, Text):
                x_pos = obj.bar - start
                if 0 <= x_pos <= len(x_indices):
                    bbox_args = None
                    if obj.bgcolor:
                        bbox_args = dict(boxstyle='round,pad=0.2', facecolor=obj.bgcolor,
                                         edgecolor='none', alpha=0.7)
                    weight = 'bold' if obj.bold else 'normal'
                    self.ax_price.text(x_pos, obj.price, obj.text,
                                       color=obj.color, fontsize=obj.size,
                                       ha=obj.halign, va=obj.valign,
                                       weight=weight, bbox=bbox_args, zorder=z)

        # X-axis labels (dates)
        date_labels = []
        for ts in visible_data.index:
            try:
                date_labels.append(pd.Timestamp(ts).strftime('%m/%d'))
            except Exception:
                date_labels.append(str(ts))

        # Show fewer x-ticks
        tick_step = max(1, len(x_indices) // 10)
        tick_positions = x_indices[::tick_step]
        tick_labels = [date_labels[i] for i in range(0, len(date_labels), tick_step)]

        self.ax_volume.set_xticks(tick_positions)
        self.ax_volume.set_xticklabels(tick_labels, rotation=45, fontsize=7,
                                        color=COLORS['text'])

        # Y-axis formatting
        self.ax_price.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))

        # Price label
        self.ax_price.set_ylabel('Price', color=COLORS['text'], fontsize=9)

        # Legend
        if self.indicator_data:
            self.ax_price.legend(loc='upper left', fontsize=7,
                                 facecolor=COLORS['panel'], edgecolor=COLORS['grid'],
                                 labelcolor=COLORS['text'])

        # Current price line
        if self.visible_bars > 0:
            current_close = closes[-1]
            self.ax_price.axhline(y=current_close, color='#FFFFFF',
                                  linewidth=0.5, linestyle=':', alpha=0.4, zorder=1)
            # Price label on right
            self.ax_price.annotate(f'{current_close:.2f}',
                                   xy=(1.01, current_close),
                                   xycoords=('axes fraction', 'data'),
                                   fontsize=7, color='#FFFFFF',
                                   va='center', ha='left',
                                   bbox=dict(boxstyle='round,pad=0.2',
                                             facecolor=COLORS['panel'],
                                             edgecolor=COLORS['grid']),
                                   zorder=11)

        self.fig.tight_layout(pad=0.5)
        self.canvas.draw_idle()

    def set_window_size(self, size: int):
        """Set the number of visible bars."""
        self.window_size = max(20, min(size, 500))

    def zoom_in(self):
        """Zoom in (fewer bars visible)."""
        self.window_size = max(20, self.window_size - 10)

    def zoom_out(self):
        """Zoom out (more bars visible)."""
        self.window_size = min(500, self.window_size + 10)
