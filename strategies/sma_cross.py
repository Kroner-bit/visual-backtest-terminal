"""
SMA Crossover Strategy
-----------------------
A simple moving average crossover strategy.
Buy when the fast SMA crosses above the slow SMA.
Sell when the fast SMA crosses below the slow SMA.
"""

from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd


def SMA(values, n):
    """Simple Moving Average."""
    return pd.Series(values).rolling(n).mean()


class SmaCross(Strategy):
    # Strategy parameters (editable)
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
