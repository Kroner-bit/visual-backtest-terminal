"""
Chart Objects API
-----------------
Definitions for custom visual objects that strategies can draw on the chart.
"""

from dataclasses import dataclass
from typing import Optional, Union, Tuple

class ChartObject:
    """Base class for all chart objects."""
    layer: int = 10  # zorder in matplotlib

@dataclass
class HLine(ChartObject):
    """Horizontal line at a specific price level."""
    price: float
    color: str = '#FFFFFF'
    style: str = '--'  # '-', '--', '-.', ':'
    width: float = 1.0
    alpha: float = 0.5

@dataclass
class VLine(ChartObject):
    """Vertical line at a specific bar index."""
    bar: int
    color: str = '#FFFFFF'
    style: str = '--'
    width: float = 1.0
    alpha: float = 0.5

@dataclass
class TrendLine(ChartObject):
    """A line connecting two points (bar1, price1) to (bar2, price2)."""
    bar1: int
    price1: float
    bar2: int
    price2: float
    color: str = '#FFFFFF'
    style: str = '-'
    width: float = 1.0
    alpha: float = 1.0
    extend_right: bool = False  # If true, extends line to infinity
    
@dataclass
class Rectangle(ChartObject):
    """A box defined by two points."""
    bar1: int
    price1: float
    bar2: int
    price2: float
    color: str = '#FFFFFF'
    fill_color: Optional[str] = None
    width: float = 1.0
    alpha: float = 0.2

@dataclass
class Text(ChartObject):
    """Text annotation at a specific coordinate."""
    bar: int
    price: float
    text: str
    color: str = '#FFFFFF'
    size: int = 9
    bgcolor: Optional[str] = None
    halign: str = 'center'  # 'left', 'center', 'right'
    valign: str = 'center'  # 'top', 'center', 'bottom', 'baseline'
    bold: bool = False


class Drawer:
    """
    API injected into backtesting.Strategy as `self.draw`.
    Strategies use these methods to create chart objects.
    """
    def __init__(self):
        self.objects = []  # List of tuples: (created_bar_index, ChartObject)
        self._current_bar = 0

    def set_current_bar(self, bar_index: int):
        self._current_bar = bar_index

    def get_objects_until(self, bar_index: int) -> list:
        """Get all objects created up to the given bar index."""
        return [obj for b, obj in self.objects if b <= bar_index]

    def hline(self, price: float, color: str = '#FFFFFF', style: str = '--', 
              width: float = 1.0, alpha: float = 0.5) -> HLine:
        """Draw a horizontal line across the entire chart."""
        obj = HLine(price=price, color=color, style=style, width=width, alpha=alpha)
        self.objects.append((self._current_bar, obj))
        return obj

    def vline(self, bar: int, color: str = '#FFFFFF', style: str = '--', 
              width: float = 1.0, alpha: float = 0.5) -> VLine:
        """Draw a vertical line at a specific bar index."""
        obj = VLine(bar=bar, color=color, style=style, width=width, alpha=alpha)
        self.objects.append((self._current_bar, obj))
        return obj

    def trendline(self, bar1: int, price1: float, bar2: int, price2: float, 
                  color: str = '#FFFFFF', style: str = '-', width: float = 1.0, 
                  alpha: float = 1.0, extend_right: bool = False) -> TrendLine:
        """Draw a line segment connecting two coordinates."""
        obj = TrendLine(bar1=bar1, price1=price1, bar2=bar2, price2=price2,
                        color=color, style=style, width=width, alpha=alpha, 
                        extend_right=extend_right)
        self.objects.append((self._current_bar, obj))
        return obj

    def rectangle(self, bar1: int, price1: float, bar2: int, price2: float, 
                  color: str = '#FFFFFF', fill_color: Optional[str] = None, 
                  width: float = 1.0, alpha: float = 0.2) -> Rectangle:
        """Draw a rectangle between two coordinate points."""
        obj = Rectangle(bar1=bar1, price1=price1, bar2=bar2, price2=price2,
                        color=color, fill_color=fill_color, width=width, alpha=alpha)
        self.objects.append((self._current_bar, obj))
        return obj

    def text(self, bar: int, price: float, text: str, color: str = '#FFFFFF', 
             size: int = 9, bgcolor: Optional[str] = None, halign: str = 'center', 
             valign: str = 'center', bold: bool = False) -> Text:
        """Draw text on the chart."""
        obj = Text(bar=bar, price=price, text=text, color=color, size=size, 
                   bgcolor=bgcolor, halign=halign, valign=valign, bold=bold)
        self.objects.append((self._current_bar, obj))
        return obj
