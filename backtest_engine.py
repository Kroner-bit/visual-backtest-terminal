"""
Backtest Engine with Step-by-Step Replay
-----------------------------------------
Runs a full backtest via backtesting.py, then provides bar-by-bar
replay state for the visual GUI.
"""

import importlib.util
import sys
import traceback
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

from gui.objects import Drawer, ChartObject


@dataclass
class TradeRecord:
    """A single trade record extracted from backtest results."""
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    size: float  # positive = long, negative = short
    pnl: float
    return_pct: float
    entry_time: Any
    exit_time: Any
    tag: str = ""

    @property
    def is_long(self) -> bool:
        return self.size > 0


@dataclass
class BarState:
    """State of the backtest at a given bar."""
    bar_index: int
    timestamp: Any
    open: float
    high: float
    low: float
    close: float
    volume: float
    equity: float
    open_trades: List[Dict]     # Currently open trades at this bar
    trade_events: List[Dict]    # Trades opened or closed at this bar
    indicators: Dict[str, float]  # Indicator values at this bar
    chart_objects: List[ChartObject] # Custom drawn objects until this bar


class BacktestReplay:
    """
    Manages full backtest execution and provides per-bar state for replay.
    """

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.strategy_class: Optional[type] = None
        self.results: Optional[pd.Series] = None
        self.trades: List[TradeRecord] = []
        self.equity_curve: Optional[np.ndarray] = None
        self.indicators: Dict[str, np.ndarray] = {}
        self.drawer: Drawer = Drawer()
        self.total_bars: int = 0
        self.initial_cash: float = 10_000
        self._bt: Optional[Backtest] = None

    def load_strategy_from_code(self, code: str, strategy_name: str = None) -> type:
        """
        Dynamically load a Strategy subclass from source code string.

        Args:
            code: Python source code containing a Strategy subclass.
            strategy_name: Name of the Strategy class to use. If None,
                           auto-detects the first Strategy subclass.

        Returns:
            The Strategy subclass.
        """
        # Create a temporary module
        spec = importlib.util.spec_from_loader("_dynamic_strategy", loader=None)
        module = importlib.util.module_from_spec(spec)

        # Execute the code in the module's namespace
        try:
            exec(code, module.__dict__)
        except Exception as e:
            raise SyntaxError(f"Error in strategy code:\n{traceback.format_exc()}")

        # Find Strategy subclasses
        strategy_classes = []
        for name, obj in module.__dict__.items():
            if (isinstance(obj, type)
                    and issubclass(obj, Strategy)
                    and obj is not Strategy):
                strategy_classes.append((name, obj))

        if not strategy_classes:
            raise ValueError(
                "No Strategy subclass found in the code. "
                "Make sure your class inherits from backtesting.Strategy."
            )

        if strategy_name:
            for name, cls in strategy_classes:
                if name == strategy_name:
                    return cls
            raise ValueError(
                f"Strategy '{strategy_name}' not found. "
                f"Available: {[n for n, _ in strategy_classes]}"
            )

        # Return the first one found
        return strategy_classes[0][1]

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_class: type,
        cash: float = 10_000,
        commission: float = 0.0,
        spread: float = 0.0,
        margin: float = 1.0,
        hedging: bool = False,
        exclusive_orders: bool = True,
    ) -> pd.Series:
        """
        Run the full backtest and extract trade/equity data for replay.

        Returns:
            backtesting.py results Series.
        """
        self.data = data.copy()
        self.strategy_class = strategy_class
        self.initial_cash = cash
        self.total_bars = len(data)
        self.drawer = Drawer()

        # We must monkey-patch the init/next of the strategy to inject drawer
        # and update its current bar index.
        OriginalStrategyClass = strategy_class
        
        class InjectedStrategy(OriginalStrategyClass):
            def __init__(self_strategy, broker, data, params):
                super().__init__(broker, data, params)
                self_strategy.draw = self.drawer

            def init(self_strategy):
                self.drawer.set_current_bar(0)
                super().init()

            def next(self_strategy):
                # Update drawer state to the current bar *before* strategy code executes
                self.drawer.set_current_bar(len(self_strategy.data) - 1)
                super().next()

        # Run the backtest
        self._bt = Backtest(
            data,
            InjectedStrategy,
            cash=cash,
            commission=commission,
            spread=spread,
            margin=margin,
            hedging=hedging,
            exclusive_orders=exclusive_orders,
        )
        self.results = self._bt.run()

        # Extract equity curve
        self._extract_equity_curve()

        # Extract trades
        self._extract_trades()

        # Extract indicator values from the strategy instance
        self._extract_indicators()

        return self.results

    def _extract_equity_curve(self):
        """Extract equity curve from results."""
        try:
            equity_df = self.results._equity_curve
            if equity_df is not None and 'Equity' in equity_df.columns:
                self.equity_curve = equity_df['Equity'].values
            else:
                self.equity_curve = np.full(self.total_bars, self.initial_cash)
        except Exception:
            self.equity_curve = np.full(self.total_bars, self.initial_cash)

    def _extract_trades(self):
        """Extract trade records from backtest results."""
        self.trades = []

        try:
            trades_df = self.results._trades
        except Exception:
            return

        if trades_df is None or not hasattr(trades_df, 'iterrows') or trades_df.empty:
            return

        columns = list(trades_df.columns)

        for _, row in trades_df.iterrows():
            # Get entry/exit bar indices directly (these are always integer indices)
            entry_bar = int(row['EntryBar']) if 'EntryBar' in columns else 0
            exit_bar = int(row['ExitBar']) if 'ExitBar' in columns else self.total_bars - 1

            # Get entry/exit timestamps
            entry_time = row['EntryTime'] if 'EntryTime' in columns else self.data.index[entry_bar]
            exit_time = row['ExitTime'] if 'ExitTime' in columns else self.data.index[min(exit_bar, self.total_bars - 1)]

            # Get prices
            entry_price = float(row['EntryPrice']) if 'EntryPrice' in columns else 0.0
            exit_price = float(row['ExitPrice']) if 'ExitPrice' in columns else 0.0

            # Get size (positive=long, negative=short)
            size = float(row['Size']) if 'Size' in columns else 0.0

            # Get PnL
            pnl = float(row['PnL']) if 'PnL' in columns else 0.0

            # Get return percent
            return_pct = float(row['ReturnPct']) if 'ReturnPct' in columns else 0.0

            # Get tag
            tag = str(row['Tag']) if 'Tag' in columns and row['Tag'] is not None else ""

            self.trades.append(TradeRecord(
                entry_bar=entry_bar,
                exit_bar=exit_bar,
                entry_price=entry_price,
                exit_price=exit_price,
                size=size,
                pnl=pnl,
                return_pct=return_pct,
                entry_time=entry_time,
                exit_time=exit_time,
                tag=tag,
            ))

    def _extract_indicators(self):
        """Extract indicator arrays from the strategy after run."""
        self.indicators = {}
        try:
            # Access the strategy instance through the backtest
            strategy = self.results._strategy
            if strategy is None:
                return

            # Access indicators - they are stored as _indicators list
            for i, indicator in enumerate(strategy._indicators):
                name = getattr(indicator, 'name', f'indicator_{i}')
                # indicator is an _Indicator wrapper - get its array values
                try:
                    values = np.array(indicator, dtype=float)
                    if len(values) == self.total_bars:
                        self.indicators[name] = values
                except Exception:
                    pass
        except Exception:
            pass

    def get_bar_state(self, bar_index: int) -> BarState:
        """
        Get the full state at a given bar index.

        Args:
            bar_index: 0-based bar index

        Returns:
            BarState with all info needed for the GUI at this bar.
        """
        bar_index = max(0, min(bar_index, self.total_bars - 1))

        row = self.data.iloc[bar_index]

        # Find open trades at this bar
        open_trades = []
        trade_events = []
        for t in self.trades:
            # Trade is open at this bar:
            # entered on or before this bar AND exits strictly after this bar
            if t.entry_bar <= bar_index < t.exit_bar:
                current_price = float(row['Close'])
                if t.is_long:
                    floating_pnl = (current_price - t.entry_price) * abs(t.size)
                else:
                    floating_pnl = (t.entry_price - current_price) * abs(t.size)

                open_trades.append({
                    'entry_bar': t.entry_bar,
                    'entry_time': t.entry_time,
                    'entry_price': t.entry_price,
                    'size': t.size,
                    'is_long': t.is_long,
                    'current_price': current_price,
                    'floating_pnl': floating_pnl,
                    'tag': t.tag,
                })

            # Trade opened at this bar
            if t.entry_bar == bar_index:
                trade_events.append({
                    'type': 'OPEN',
                    'is_long': t.is_long,
                    'price': t.entry_price,
                    'size': t.size,
                    'tag': t.tag,
                })

            # Trade closed at this bar
            if t.exit_bar == bar_index:
                trade_events.append({
                    'type': 'CLOSE',
                    'is_long': t.is_long,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'size': t.size,
                    'pnl': t.pnl,
                    'tag': t.tag,
                })

        # Get equity
        if self.equity_curve is not None and bar_index < len(self.equity_curve):
            equity = float(self.equity_curve[bar_index])
        else:
            equity = self.initial_cash

        # Get indicator values
        indicator_vals = {}
        for name, arr in self.indicators.items():
            if bar_index < len(arr):
                val = arr[bar_index]
                try:
                    if not np.isnan(val):
                        indicator_vals[name] = float(val)
                except (TypeError, ValueError):
                    pass

        volume = float(row.get('Volume', 0)) if 'Volume' in row.index else 0.0

        # Get chart objects created up to this bar
        chart_objects = self.drawer.get_objects_until(bar_index)

        return BarState(
            bar_index=bar_index,
            timestamp=self.data.index[bar_index],
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=volume,
            equity=equity,
            open_trades=open_trades,
            trade_events=trade_events,
            indicators=indicator_vals,
            chart_objects=chart_objects,
        )

    def get_closed_trades_until(self, bar_index: int) -> List[TradeRecord]:
        """Get all trades that have been closed by the given bar."""
        return [t for t in self.trades if t.exit_bar <= bar_index]

    def get_stats_dict(self) -> Dict[str, Any]:
        """Return the backtesting results as a clean dictionary."""
        if self.results is None:
            return {}

        stats = {}
        keys_of_interest = [
            'Start', 'End', 'Duration',
            'Exposure Time [%]',
            'Equity Final [$]', 'Equity Peak [$]',
            'Return [%]', 'Buy & Hold Return [%]',
            'Return (Ann.) [%]', 'Volatility (Ann.) [%]',
            'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio',
            'Max. Drawdown [%]', 'Avg. Drawdown [%]',
            'Max. Drawdown Duration', 'Avg. Drawdown Duration',
            '# Trades', 'Win Rate [%]',
            'Best Trade [%]', 'Worst Trade [%]',
            'Avg. Trade [%]', 'Max. Trade Duration',
            'Avg. Trade Duration', 'Profit Factor',
            'Expectancy [%]', 'SQN',
        ]

        for key in keys_of_interest:
            try:
                val = self.results[key]
                if isinstance(val, (np.floating, np.integer)):
                    val = round(float(val), 4)
                stats[key] = val
            except (KeyError, IndexError):
                pass

        return stats
