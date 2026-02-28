from backtesting import Strategy
from backtesting.lib import crossover
from backtesting.test import SMA
import pandas as pd

def EMA(arr, n):
    """
    Pandas based Exponential Moving Average
    """
    return pd.Series(arr).ewm(span=n, adjust=False).mean()

class MT5DrawingDemo(Strategy):
    """
    A demo strategy showing off the new MT5-Style Drawing API.
    It buys on EMA crossover and draws various objects on the chart.
    """
    fast = 10
    slow = 21

    def init(self):
        # Register indicators
        self.ema_fast = self.I(EMA, self.data.Close, self.fast)
        self.ema_slow = self.I(EMA, self.data.Close, self.slow)
        
        # We will keep track of our last trade to draw a box around it
        self.last_buy_bar = -1
        self.last_buy_price = 0.0

    def next(self):
        current_bar = len(self.data) - 1
        current_close = self.data.Close[-1]
        
        # Detect Crossover up
        if crossover(self.ema_fast, self.ema_slow):
            # Close existing shorts if any (though we only go long here)
            if self.position.is_short:
                self.position.close()
                
            self.buy()
            self.last_buy_bar = current_bar
            self.last_buy_price = current_close
            
            # --- DRAWING API DEMO ---
            
            # 1. Draw a bold vertical line at the entry bar
            self.draw.vline(bar=current_bar, color='#00E676', style='-', width=1.5, alpha=0.8)
            
            # 2. Draw a text label above the high of the entry candle
            highest = self.data.High[-1]
            self.draw.text(bar=current_bar, price=highest * 1.002, 
                           text="BUY", color='white', bold=True, 
                           bgcolor='#1B5E20', valign='bottom')
            
            # 3. Draw a horizontal reference line for the entry price
            self.draw.hline(price=current_close, color='#00E676', style=':', width=1.0, alpha=0.5)

        # Detect Crossover down (Exit)
        elif crossover(self.ema_slow, self.ema_fast):
            if self.position.is_long:
                self.position.close()
                
                # --- DRAWING API DEMO ---
                
                # 1. Draw a red vertical line at the exit
                self.draw.vline(bar=current_bar, color='#FF5252', style=':', width=1.5, alpha=0.8)
                
                # 2. Draw a trendline connecting the entry and exit prices
                if self.last_buy_bar != -1:
                    # Green line if profitable, red if loss
                    pnl_color = '#00E676' if current_close > self.last_buy_price else '#FF5252'
                    
                    self.draw.trendline(
                        bar1=self.last_buy_bar, price1=self.last_buy_price,
                        bar2=current_bar, price2=current_close,
                        color=pnl_color, style='-', width=2.0, alpha=0.8
                    )
                    
                    # 3. Draw a semi-transparent box around the entire trade duration
                    highest_in_trade = max(self.data.High[self.last_buy_bar:current_bar+1])
                    lowest_in_trade = min(self.data.Low[self.last_buy_bar:current_bar+1])
                    
                    self.draw.rectangle(
                        bar1=self.last_buy_bar, price1=lowest_in_trade,
                        bar2=current_bar, price2=highest_in_trade,
                        color=pnl_color, fill_color=pnl_color, width=1.0, alpha=0.1
                    )
                    
                    self.last_buy_bar = -1
