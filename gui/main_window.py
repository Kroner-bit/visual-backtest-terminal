"""
Main Window
-------------
Central QMainWindow that integrates all GUI components:
chart, strategy editor, controls, trades panel, results panel.
Manages backtest execution and visual playback.
"""

import traceback
import os
from datetime import datetime
import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMessageBox, QApplication, QStatusBar,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor

from gui.chart_widget import ChartWidget
from gui.strategy_editor import StrategyEditor
from gui.controls_widget import ControlsWidget
from gui.trades_panel import TradesPanel
from gui.results_panel import ResultsPanel
from gui.equity_curve import EquityCurveWidget
from gui.pdf_export import export_pdf
from backtest_engine import BacktestReplay
import data_fetcher


class MainWindow(QMainWindow):
    """
    Main application window for the visual backtester.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visual Backtest Terminal")
        self.setMinimumSize(1280, 800)
        self.resize(1500, 900)

        # State
        self.replay = BacktestReplay()
        self.ohlcv_data = None
        self.current_bar = 0
        self.is_playing = False
        self.play_speed = 5  # multiplier (0 = max)
        self.all_trade_markers = []  # accumulated trade markers
        self._ticker = ""             # current ticker for report

        # Playback timer
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self._advance_bar)

        # Build UI
        self._setup_ui()
        self._connect_signals()

        # Status bar
        self.statusBar()  # styled by global stylesheet
        self.statusBar().showMessage("Ready — Download data and run a backtest to begin")

    def _setup_ui(self):
        """Create and arrange all widgets."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # === Top area: Editor | Chart | Trades ===
        top_splitter = QSplitter(Qt.Horizontal)

        # Left: Strategy Editor
        self.strategy_editor = StrategyEditor()
        top_splitter.addWidget(self.strategy_editor)

        # Center: Chart
        self.chart_widget = ChartWidget()
        top_splitter.addWidget(self.chart_widget)

        # Right: Trades + Results
        right_splitter = QSplitter(Qt.Vertical)
        self.trades_panel = TradesPanel()
        self.results_panel = ResultsPanel()
        right_splitter.addWidget(self.trades_panel)
        right_splitter.addWidget(self.results_panel)
        right_splitter.setSizes([400, 300])
        top_splitter.addWidget(right_splitter)

        # Set splitter proportions
        top_splitter.setSizes([350, 700, 350])

        main_layout.addWidget(top_splitter, stretch=1)

        # === Equity Curve (collapsible) ===
        self.equity_curve_widget = EquityCurveWidget()
        main_layout.addWidget(self.equity_curve_widget)

        # === Bottom: Controls ===
        self.controls = ControlsWidget()
        main_layout.addWidget(self.controls)

    def _connect_signals(self):
        """Wire up all signals/slots."""
        # Data manager
        self.controls.open_data_manager.connect(self._on_open_data_manager)

        # Strategy editor run
        self.strategy_editor.run_backtest_requested.connect(self._on_run_backtest)
        self.strategy_editor.optimize_requested.connect(self._on_optimize)
        self.strategy_editor.walkforward_requested.connect(self._on_walkforward)

        # Playback controls
        self.controls.play_toggled.connect(self._on_play_toggle)
        self.controls.step_forward.connect(self._on_step_forward)
        self.controls.step_backward.connect(self._on_step_backward)
        self.controls.go_to_start.connect(self._on_go_to_start)
        self.controls.go_to_end.connect(self._on_go_to_end)
        self.controls.speed_changed.connect(self._on_speed_changed)
        self.controls.export_requested.connect(self._on_export_pdf)

    # ── Optimizer ─────────────────────────────────────────────────

    def _on_optimize(self, code: str):
        """Open the Strategy Optimizer dialog."""
        if self.ohlcv_data is None or self.ohlcv_data.empty:
            self.strategy_editor.show_error(
                "Load data first via Data Manager before optimizing!"
            )
            return

        from gui.optimizer_dialog import OptimizerDialog
        cash = self.controls.get_cash()
        dlg = OptimizerDialog(code, self.ohlcv_data, cash=cash, parent=self)
        dlg.optimized_code.connect(self._on_optimized_code)
        dlg.exec_()

    def _on_optimized_code(self, new_code: str):
        """Apply optimized parameters back to strategy editor."""
        self.strategy_editor.set_code(new_code)
        self.strategy_editor.show_message(
            "✅ Optimized parameters applied to strategy code!", success=True
        )

    # ── Walk-Forward ──────────────────────────────────────────────

    def _on_walkforward(self, code: str):
        """Open the Walk-Forward Analysis dialog."""
        if self.ohlcv_data is None or self.ohlcv_data.empty:
            self.strategy_editor.show_error(
                "Load data first via Data Manager before walk-forward!"
            )
            return

        from gui.walkforward_dialog import WalkForwardDialog
        cash = self.controls.get_cash()
        dlg = WalkForwardDialog(code, self.ohlcv_data, cash=cash, parent=self)
        dlg.result_ready.connect(self._on_walkforward_result)
        dlg.exec_()

    def _on_walkforward_result(self, test_data, stats_dict, modified_code):
        """Handle walk-forward result: load test data for replay."""
        self.ohlcv_data = test_data
        self.strategy_editor.set_code(modified_code)

        # Show data on chart
        bars = len(test_data)
        self.chart_widget.set_data(test_data)
        self.chart_widget.update_chart(bars - 1)

        # Reset playback
        self.current_bar = 0
        self.all_trade_markers = []
        self.controls.update_bar_info(0, bars)
        self.controls.enable_export(False)
        self.controls.lbl_data_info.setText(
            f'<span style="color:#42A5F5;font-weight:bold;">WF Window</span>'
            f' — {bars} bars'
        )

        self.strategy_editor.show_message(
            f"✅ Walk-Forward window loaded ({bars} bars) — Run Backtest for replay!",
            success=True
        )
        self.statusBar().showMessage(
            f"Walk-Forward window loaded — {bars} bars. "
            f"Click ▶ Run Backtest to start replay."
        )

    # ── Data Manager ──────────────────────────────────────────────

    def _on_open_data_manager(self):
        """Open the Data Manager dialog."""
        from gui.data_manager import DataManagerDialog
        dlg = DataManagerDialog(self)
        dlg.dataset_selected.connect(self._on_dataset_loaded)
        dlg.exec_()

    def _on_dataset_loaded(self, dataset_id: int, ticker: str, df):
        """Handle dataset selected from Data Manager."""
        self.ohlcv_data = df
        bars = len(df)

        self.statusBar().showMessage(
            f"✅ Loaded {bars} bars of {ticker} from cache"
        )

        # Show the data on chart
        self.chart_widget.set_data(self.ohlcv_data)
        self.chart_widget.update_chart(bars - 1)

        # Reset playback
        self.current_bar = 0
        self.all_trade_markers = []
        self._ticker = ticker
        self.controls.update_bar_info(0, bars)
        self.controls.enable_export(False)
        self.controls.lbl_data_info.setText(
            f'<span style="color:#42A5F5;font-weight:bold;">{ticker}</span>'
            f' — {bars} bars'
        )

        self.strategy_editor.show_message(
            f"Data loaded: {ticker} — {bars} bars", success=True
        )

    # ── Backtest Execution ─────────────────────────────────────────

    def _on_run_backtest(self, code: str):
        """Run the backtest with the given strategy code."""
        if self.ohlcv_data is None or self.ohlcv_data.empty:
            self.strategy_editor.show_error(
                "No data loaded! Download data first."
            )
            return

        self.statusBar().showMessage("Running backtest...")
        self.results_panel.show_running()
        QApplication.processEvents()

        try:
            # Load strategy from code
            strategy_class = self.replay.load_strategy_from_code(code)

            # Run backtest
            cash = self.controls.get_cash()
            results = self.replay.run_backtest(
                data=self.ohlcv_data,
                strategy_class=strategy_class,
                cash=cash,
            )

            # Set chart data with indicators
            self.chart_widget.set_data(self.ohlcv_data, self.replay.indicators)

            # Build all trade markers for the full backtest
            self._build_all_markers()

            # Reset to start for playback
            self.current_bar = 0
            self.all_trade_markers = self._build_all_markers()

            # Reset equity curve
            self.equity_curve_widget.reset(cash)

            # Update results panel
            stats = self.replay.get_stats_dict()
            self.results_panel.update_results(stats)

            # Show initial state
            self._update_display()

            n_trades = len(self.replay.trades)
            self.statusBar().showMessage(
                f"✅ Backtest complete — {n_trades} trades. "
                f"Use playback controls to replay."
            )
            self.strategy_editor.show_message(
                f"Backtest OK — {n_trades} trades found. Press ▶ to replay.",
                success=True
            )

        except Exception as e:
            self.statusBar().showMessage("❌ Backtest failed")
            self.strategy_editor.show_error(
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
            )

    def _build_all_markers(self) -> list:
        """Build trade markers for all trades."""
        markers = []
        for t in self.replay.trades:
            # Entry marker
            markers.append({
                'bar': t.entry_bar,
                'price': t.entry_price,
                'type': 'OPEN',
                'is_long': t.is_long,
            })
            # Exit marker
            markers.append({
                'bar': t.exit_bar,
                'price': t.exit_price,
                'type': 'CLOSE',
                'is_long': t.is_long,
            })
        return markers

    # ── Playback Controls ──────────────────────────────────────────

    def _on_play_toggle(self, is_playing: bool):
        """Start or stop playback."""
        self.is_playing = is_playing

        if self.replay.total_bars == 0:
            self.controls.stop_playback()
            self.strategy_editor.show_error("Run a backtest first before playback.")
            return

        if is_playing:
            interval = self._speed_to_interval()
            self.play_timer.start(interval)
            self.statusBar().showMessage("▶ Playing...")
        else:
            self.play_timer.stop()
            self.statusBar().showMessage(
                f"⏸ Paused at bar {self.current_bar}/{self.replay.total_bars}"
            )

    def _on_step_forward(self):
        """Advance one bar."""
        if self.replay.total_bars == 0:
            return
        self.current_bar = min(self.current_bar + 1, self.replay.total_bars - 1)
        self._update_display()

    def _on_step_backward(self):
        """Go back one bar."""
        if self.replay.total_bars == 0:
            return
        self.current_bar = max(0, self.current_bar - 1)
        self._update_display()

    def _on_go_to_start(self):
        """Go to the first bar."""
        self.current_bar = 0
        self._update_display()

    def _on_go_to_end(self):
        """Go to the last bar."""
        if self.replay.total_bars == 0:
            return
        self.current_bar = self.replay.total_bars - 1
        self._update_display()
        # Stop playback
        self.is_playing = False
        self.play_timer.stop()
        self.controls.stop_playback()
        self.controls.enable_export(True)
        self.statusBar().showMessage(
            f"✅ Jumped to end — Export to PDF available"
        )

    def _on_speed_changed(self, speed: int):
        """Update playback speed."""
        self.play_speed = speed
        if self.is_playing:
            interval = self._speed_to_interval()
            self.play_timer.setInterval(interval)

    def _speed_to_interval(self) -> int:
        """Convert speed multiplier to timer interval in ms."""
        if self.play_speed == 0:  # max speed
            return 1
        # Base interval 500ms, divided by speed
        return max(1, int(500 / self.play_speed))

    def _advance_bar(self):
        """Timer callback: advance one bar during playback."""
        if self.current_bar >= self.replay.total_bars - 1:
            # Reached end
            self.is_playing = False
            self.play_timer.stop()
            self.controls.stop_playback()
            self.controls.enable_export(True)
            self.statusBar().showMessage("✅ Playback complete — Export to PDF available")
            return

        self.current_bar += 1
        self._update_display()

    # ── Display Update ─────────────────────────────────────────────

    def _update_display(self):
        """Update all panels for the current bar."""
        if self.replay.total_bars == 0:
            return

        bar_state = self.replay.get_bar_state(self.current_bar)

        # Filter trade markers visible up to current bar
        visible_markers = [
            m for m in self.all_trade_markers
            if m['bar'] <= self.current_bar
        ]

        # Update chart
        self.chart_widget.update_chart(
            bar_index=self.current_bar,
            trade_markers=visible_markers,
            open_trades=bar_state.open_trades,
            indicators=self.replay.indicators,
            chart_objects=bar_state.chart_objects,
        )

        # Update trades panel
        self.trades_panel.update_open_trades(bar_state.open_trades)
        closed = self.replay.get_closed_trades_until(self.current_bar)
        self.trades_panel.update_closed_trades(closed)

        # Update bar counter with timestamp
        try:
            ts = str(bar_state.timestamp)
            # Format nicely for display
            import pandas as pd
            ts_parsed = pd.Timestamp(ts)
            if ts_parsed.hour == 0 and ts_parsed.minute == 0:
                timestamp_str = ts_parsed.strftime('%Y-%m-%d')
            else:
                timestamp_str = ts_parsed.strftime('%Y-%m-%d  %H:%M')
        except Exception:
            timestamp_str = str(bar_state.timestamp)

        self.controls.update_bar_info(
            self.current_bar + 1, self.replay.total_bars, timestamp_str
        )

        # Update account info
        floating_pnl = sum(t.get('floating_pnl', 0) for t in bar_state.open_trades)
        equity = bar_state.equity
        # Approximate balance (equity minus floating)
        balance = equity - floating_pnl

        self.controls.update_account_info(
            balance=balance,
            equity=equity,
            floating_pnl=floating_pnl,
            open_count=len(bar_state.open_trades),
            closed_count=len(closed),
        )

        # Update equity curve
        closed_pnl = sum(t.pnl for t in closed)
        self.equity_curve_widget.update_curve(
            bar_index=self.current_bar,
            equity=equity,
            closed_pnl=closed_pnl,
            floating_pnl=floating_pnl,
        )

    # ── PDF Export ────────────────────────────────────────────────────────

    def _on_export_pdf(self):
        """Export backtest report to PDF."""
        if self.replay.total_bars == 0:
            return

        default_name = f"backtest_{self._ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Report as PDF", default_name,
            "PDF Files (*.pdf);;All Files (*)"
        )
        if not filepath:
            return

        self.statusBar().showMessage("📄 Exporting PDF report...")
        QApplication.processEvents()

        try:
            # Gather equity curve data from the widget
            eq_widget = self.equity_curve_widget
            equity_hist = eq_widget._equity_history[:]
            closed_hist = eq_widget._closed_pnl_history[:]
            float_hist = eq_widget._floating_pnl_history[:]

            # If equity history is incomplete, fill it by replaying
            if len(equity_hist) < self.replay.total_bars:
                for i in range(len(equity_hist), self.replay.total_bars):
                    bs = self.replay.get_bar_state(i)
                    cl = self.replay.get_closed_trades_until(i)
                    fp = sum(t.get('floating_pnl', 0) for t in bs.open_trades)
                    cp = sum(t.pnl for t in cl)
                    equity_hist.append(bs.equity)
                    closed_hist.append(cp)
                    float_hist.append(fp)

            # Get strategy name
            strat_name = "Strategy"
            if self.replay.strategy_class:
                strat_name = self.replay.strategy_class.__name__

            export_pdf(
                filepath=filepath,
                stats=self.replay.get_stats_dict(),
                trades=self.replay.trades,
                equity_history=equity_hist,
                closed_pnl_history=closed_hist,
                floating_pnl_history=float_hist,
                initial_cash=self.replay.initial_cash,
                data=self.replay.data,
                strategy_name=strat_name,
                ticker=self._ticker,
            )

            self.statusBar().showMessage(f"✅ PDF exported: {filepath}")
            self.strategy_editor.show_message(
                f"PDF report saved: {os.path.basename(filepath)}", success=True
            )
        except Exception as e:
            self.statusBar().showMessage("❌ PDF export failed")
            self.strategy_editor.show_error(f"Export error: {e}")
