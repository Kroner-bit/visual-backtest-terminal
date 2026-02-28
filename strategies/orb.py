"""
Opening Range Breakout (ORB) Strategy
---------------------------------------
Classic intraday breakout strategy with proper session handling.

Rules:
  1. At the start of each trading day, define the "opening range"
     as the high and low of the first N bars (default: 6).
  2. After the opening range is established, wait for a breakout.
  3. BUY when price closes above the opening range high.
  4. SELL (short) when price closes below the opening range low.
  5. Stop-loss at the opposite side of the opening range.
  6. Take-profit at a configurable risk:reward ratio.
  7. Only ONE trade per day.

Best used on intraday timeframes (5m, 15m, 30m).

Parameters:
  - opening_bars: Number of bars to define the opening range (default: 6)
  - rr_ratio:     Risk-to-reward ratio for take-profit (default: 2.0)
  - use_sl:       Whether to use stop-loss (default: True)
  - use_tp:       Whether to use take-profit (default: True)
"""

from backtesting import Strategy
import pandas as pd
import numpy as np


class OpeningRangeBreakout(Strategy):
    # === Strategy Parameters ===
    opening_bars = 6       # First N bars define the opening range
    rr_ratio = 2.0         # Risk:Reward ratio for TP
    use_sl = True          # Use stop-loss
    use_tp = True          # Use take-profit

    def init(self):
        # Pre-compute OR High/Low indicators for chart overlay
        # These will show the range ONLY during the first N bars of each day
        self.or_high = self.I(
            self._calc_or_lines, self.data.High, self.data.Low,
            self.data.Close, self.data.index, True,
            name='OR High', color='#00E676'
        )
        self.or_low = self.I(
            self._calc_or_lines, self.data.High, self.data.Low,
            self.data.Close, self.data.index, False,
            name='OR Low', color='#FF5252'
        )

        # Internal state (reset each day)
        self._current_day = None
        self._day_bar_count = 0
        self._range_high = None
        self._range_low = None
        self._traded_today = False

    @staticmethod
    def _calc_or_lines(high, low, close, index, is_high):
        """
        Calculate opening range lines — only visible during
        the first N bars of each trading day, NaN elsewhere.
        """
        n = 6  # Must match opening_bars default
        result = np.full(len(high), np.nan)
        day_count = 0
        current_day = None
        day_high = -np.inf
        day_low = np.inf

        for i in range(len(high)):
            try:
                bar_day = pd.Timestamp(index[i]).date()
            except Exception:
                bar_day = i // 78  # fallback: ~78 bars per day on 5m

            if bar_day != current_day:
                # New day
                current_day = bar_day
                day_count = 0
                day_high = -np.inf
                day_low = np.inf

            day_count += 1

            if day_count <= n:
                # Still building the range
                day_high = max(day_high, high[i])
                day_low = min(day_low, low[i])
                result[i] = day_high if is_high else day_low

        return result

    def next(self):
        # Detect current day from the bar timestamp
        try:
            bar_day = pd.Timestamp(self.data.index[-1]).date()
        except Exception:
            bar_day = len(self.data) // 78

        # New day? Close any open position and reset state
        if bar_day != self._current_day:
            if self.position:
                self.position.close()
            self._current_day = bar_day
            self._day_bar_count = 0
            self._range_high = -float('inf')
            self._range_low = float('inf')
            self._traded_today = False
            self._day_start_bar = len(self.data) - 1

        self._day_bar_count += 1
        current_bar = len(self.data) - 1

        # Phase 1: Building the opening range (first N bars)
        if self._day_bar_count <= self.opening_bars:
            self._range_high = max(self._range_high, self.data.High[-1])
            self._range_low = min(self._range_low, self.data.Low[-1])
            
            # If this is exactly the last bar of the opening range, draw the rectangle
            if self._day_bar_count == self.opening_bars and hasattr(self, 'draw'):
                self.draw.rectangle(
                    bar1=self._day_start_bar, 
                    price1=self._range_low,
                    bar2=current_bar, 
                    price2=self._range_high,
                    color='#FFD740',        # Yellow border
                    fill_color='#FFD740',   # Yellow fill
                    width=1.0, 
                    alpha=0.15              # Subtle transparency
                )
                
            return  # Don't trade during range building

        # Phase 2: Trading — only if range is valid and no trade yet today
        if self._traded_today:
            return

        if self._range_high <= self._range_low:
            return

        price = self.data.Close[-1]
        range_size = self._range_high - self._range_low

        # Don't open a new trade if already in position
        if self.position:
            return

        # === LONG: price closes above range high ===
        if price > self._range_high:
            sl = self._range_low if self.use_sl else None
            tp = (price + range_size * self.rr_ratio) if self.use_tp else None
            self.buy(sl=sl, tp=tp)
            self._traded_today = True

        # === SHORT: price closes below range low ===
        elif price < self._range_low:
            sl = self._range_high if self.use_sl else None
            tp = (price - range_size * self.rr_ratio) if self.use_tp else None
            self.sell(sl=sl, tp=tp)
            self._traded_today = True
