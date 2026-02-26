"""
Walk-Forward Analysis Dialog (v2)
----------------------------------
Rolling window walk-forward optimisation with:
  - Manual window (row) count
  - Contiguous test periods (no gaps)
  - Parameter selection with min / max / step
  - Combined dynamic-parameter backtest for replay
"""

import traceback
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QGroupBox, QMessageBox,
    QApplication, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QProgressBar,
    QComboBox, QWidget, QFileDialog, QCheckBox,
    QDoubleSpinBox, QSplitter,
)
from PyQt5.QtCore import Qt, pyqtSignal

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle as MplRect, Patch
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

from backtesting import Backtest, Strategy
from gui.optimizer_dialog import detect_parameters


class WalkForwardDialog(QDialog):
    """Walk-Forward Analysis with contiguous OOS windows and dynamic params."""

    # (combined_oos_df, param_schedule, strategy_code)
    result_ready = pyqtSignal(object, object, str)

    def __init__(self, strategy_code: str, data: pd.DataFrame,
                 cash: float = 10_000, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 Walk-Forward Analysis")
        self.setMinimumSize(1050, 750)
        self.resize(1150, 820)
        self.setStyleSheet("QDialog{background:#1C1C2E;color:#C8C8D4;}")

        self._code = strategy_code
        self._data = data
        self._cash = cash
        self._N = len(data)
        self._params = detect_parameters(strategy_code)
        self._windows = []          # (train_s, train_e, test_s, test_e)
        self._window_results = []   # per-window dicts
        self._param_schedule = []   # [(test_start_idx, test_end_idx, {param: val})]

        ml = QVBoxLayout(self)
        ml.setSpacing(6)
        ml.setContentsMargins(10, 10, 10, 10)

        # ── Top: row count + add-row ───────────────────────────────
        top_grp = QGroupBox("⚙ Window Layout")
        top_grp.setStyleSheet(self._group_css("#42A5F5"))
        tl = QVBoxLayout(top_grp)

        # Row count control
        row_ctrl = QHBoxLayout()
        row_ctrl.setSpacing(8)
        ss = "color:#888;font-size:11px;"
        is_ = ("QSpinBox{background:#1A1A2E;color:#FFF;"
               "border:1px solid #3A3A5A;border-radius:3px;"
               "padding:4px;font-size:12px;}")

        row_ctrl.addWidget(self._lbl("Windows (rows):", ss))
        self.spn_rows = QSpinBox()
        self.spn_rows.setRange(1, 30)
        self.spn_rows.setValue(5)
        self.spn_rows.setStyleSheet(is_)
        self.spn_rows.valueChanged.connect(self._on_rows_changed)
        row_ctrl.addWidget(self.spn_rows)

        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet("color:#FFD740;font-size:12px;font-weight:bold;")
        row_ctrl.addStretch()
        row_ctrl.addWidget(self.lbl_info)
        tl.addLayout(row_ctrl)

        # Per-row window table
        self.win_table = QTableWidget()
        self.win_table.setColumnCount(5)
        self.win_table.setHorizontalHeaderLabels([
            "#", "Train (bars)", "Test (bars)", "Train Period", "Test Period"
        ])
        self.win_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.win_table.verticalHeader().setVisible(False)
        self.win_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.win_table.setMaximumHeight(180)
        self.win_table.setStyleSheet(self._table_css("#42A5F5"))
        tl.addWidget(self.win_table)
        ml.addWidget(top_grp)

        self._row_widgets = []  # [{train_spn, test_spn}]

        # ── Parameter selection ───────────────────────────────────
        param_grp = QGroupBox("📊 Parameters to Optimise")
        param_grp.setStyleSheet(self._group_css("#FF9800"))
        pl = QVBoxLayout(param_grp)

        self.param_table = QTableWidget()
        self.param_table.setColumnCount(6)
        self.param_table.setHorizontalHeaderLabels(
            ["✓", "Parameter", "Default", "Min", "Max", "Step"])
        self.param_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.param_table.verticalHeader().setVisible(False)
        self.param_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.param_table.setMaximumHeight(140)
        self.param_table.setStyleSheet(self._table_css("#FF9800"))
        self._populate_params()
        pl.addWidget(self.param_table)
        ml.addWidget(param_grp)

        # ── Visual preview ────────────────────────────────────────
        self.fig = Figure(figsize=(10, 2.8), facecolor='#1C1C2E', dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(150)
        self.canvas.setMaximumHeight(220)
        ml.addWidget(self.canvas)

        # ── Progress ──────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(14)
        self.progress.setStyleSheet(
            "QProgressBar{background:#1A1A2E;border:1px solid #3A3A5A;"
            "border-radius:4px;text-align:center;color:#C8C8D4;font-size:10px;}"
            "QProgressBar::chunk{background:#1B5E20;border-radius:3px;}")
        ml.addWidget(self.progress)

        # ── Results table ─────────────────────────────────────────
        self.results_table = QTableWidget()
        self.results_table.setStyleSheet(self._table_css("#42A5F5"))
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        ml.addWidget(self.results_table, stretch=1)

        # ── Buttons ───────────────────────────────────────────────
        bl = QHBoxLayout()

        self.btn_run = self._btn("🚀 Run Walk-Forward", "#1B5E20", "#2E7D32")
        self.btn_run.clicked.connect(self._run)
        bl.addWidget(self.btn_run)

        self.btn_load = self._btn("📊 Load Combined to Replay", "#1565C0", "#1976D2")
        self.btn_load.setEnabled(False)
        self.btn_load.clicked.connect(self._load_combined)
        bl.addWidget(self.btn_load)

        self.btn_pdf = self._btn("📄 Export PDF", "#4A148C", "#6A1B9A")
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.clicked.connect(self._export_pdf)
        bl.addWidget(self.btn_pdf)

        bl.addStretch()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#888;font-size:11px;")
        bl.addWidget(self.lbl_status)
        ml.addLayout(bl)

        self._on_rows_changed(self.spn_rows.value())

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _group_css(c):
        return (f"QGroupBox{{color:{c};font-size:13px;font-weight:bold;"
                "border:1px solid #2A2A45;border-radius:6px;"
                "margin-top:8px;padding-top:14px;}"
                "QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px;}")

    @staticmethod
    def _table_css(c):
        return ("QTableWidget{background:#1A1A2E;color:#C8C8D4;"
                "border:1px solid #2A2A45;border-radius:4px;"
                "gridline-color:#2A2A45;font-size:11px;}"
                "QTableWidget::item:selected{background:#1565C0;color:#FFF;}"
                f"QHeaderView::section{{background:#252540;color:{c};"
                "font-weight:bold;font-size:10px;padding:3px;"
                "border:1px solid #2A2A45;}")

    @staticmethod
    def _lbl(text, style):
        l = QLabel(text)
        l.setStyleSheet(style)
        return l

    @staticmethod
    def _btn(text, bg, hover):
        b = QPushButton(text)
        b.setStyleSheet(
            f"QPushButton{{background:{bg};color:#FFF;border:1px solid {hover};"
            f"border-radius:4px;padding:7px 18px;font-size:12px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{hover};}}"
            "QPushButton:disabled{background:#2A2A45;color:#555;}")
        return b

    # ── Parameter table ────────────────────────────────────────────

    def _populate_params(self):
        self.param_table.setRowCount(len(self._params))
        self._pw = []  # param widgets

        for i, p in enumerate(self._params):
            chk = QCheckBox()
            chk.setChecked(True)
            w = QWidget()
            lo = QHBoxLayout(w)
            lo.addWidget(chk)
            lo.setAlignment(Qt.AlignCenter)
            lo.setContentsMargins(0, 0, 0, 0)
            self.param_table.setCellWidget(i, 0, w)

            self.param_table.setItem(i, 1, QTableWidgetItem(p['name']))
            self.param_table.setItem(i, 2, QTableWidgetItem(str(p['value'])))

            dec = 2 if p['type'] == 'float' else 0
            sty = "background:#1A1A2E;color:#FFF;border:1px solid #3A3A5A;"

            mn = QDoubleSpinBox(); mn.setRange(-1e9, 1e9); mn.setDecimals(dec)
            mn.setValue(max(1, p['value'] * 0.5) if p['value'] > 0 else p['value'] - 5)
            mn.setStyleSheet(sty)
            self.param_table.setCellWidget(i, 3, mn)

            mx = QDoubleSpinBox(); mx.setRange(-1e9, 1e9); mx.setDecimals(dec)
            mx.setValue(p['value'] * 2 if p['value'] > 0 else p['value'] + 10)
            mx.setStyleSheet(sty)
            self.param_table.setCellWidget(i, 4, mx)

            st = QDoubleSpinBox(); st.setRange(0.01, 1e6); st.setDecimals(dec)
            st.setValue(max(1, p['value'] * 0.25) if p['value'] > 0 else 1)
            st.setStyleSheet(sty)
            self.param_table.setCellWidget(i, 5, st)

            self._pw.append({'chk': chk, 'mn': mn, 'mx': mx, 'st': st,
                             'name': p['name'], 'type': p['type'],
                             'default': p['value']})

    def _opt_ranges(self):
        """Build optimisation keyword ranges from the table."""
        rng = {}
        for w in self._pw:
            if not w['chk'].isChecked():
                continue
            lo, hi, step = w['mn'].value(), w['mx'].value(), w['st'].value()
            if step <= 0 or lo > hi:
                continue
            if w['type'] == 'int':
                rng[w['name']] = range(int(lo), int(hi) + 1, int(step))
            else:
                vals, v = [], lo
                while v <= hi + 1e-9:
                    vals.append(round(v, 4)); v += step
                rng[w['name']] = vals
        return rng

    # ── Window layout ──────────────────────────────────────────────

    def _on_rows_changed(self, nrows):
        """Rebuild the window layout table when row count changes."""
        # Compute sensible defaults
        default_test = max(5, self._N // (nrows + 1))
        default_train = max(10, self._N - nrows * default_test)

        self.win_table.setRowCount(nrows)

        spn_style = ("background:#1A1A2E;color:#FFF;"
                     "border:1px solid #3A3A5A;border-radius:3px;padding:2px;")

        old_widgets = self._row_widgets
        self._row_widgets = []

        for i in range(nrows):
            # Row number
            self.win_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

            # Re-use existing values if available
            if i < len(old_widgets):
                old_tr = int(old_widgets[i]['train'].value())
                old_te = int(old_widgets[i]['test'].value())
            else:
                old_tr = default_train
                old_te = default_test

            # Train spinbox
            spn_tr = QSpinBox()
            spn_tr.setRange(5, self._N)
            spn_tr.setValue(old_tr)
            spn_tr.setStyleSheet(spn_style)
            spn_tr.valueChanged.connect(self._rebuild_from_table)
            self.win_table.setCellWidget(i, 1, spn_tr)

            # Test spinbox
            spn_te = QSpinBox()
            spn_te.setRange(1, self._N)
            spn_te.setValue(old_te)
            spn_te.setStyleSheet(spn_style)
            spn_te.valueChanged.connect(self._rebuild_from_table)
            self.win_table.setCellWidget(i, 2, spn_te)

            self._row_widgets.append({'train': spn_tr, 'test': spn_te})

        self._rebuild_from_table()

    def _rebuild_from_table(self, *_):
        """Recalculate windows from per-row spinners. Tests are contiguous."""
        if not self._row_widgets:
            return

        nrows = len(self._row_widgets)
        test_sizes = [int(w['test'].value()) for w in self._row_widgets]
        train_sizes = [int(w['train'].value()) for w in self._row_widgets]

        # Tests are contiguous: first test starts after first training
        # test_start[0] = train_sizes[0]
        # test_start[i] = test_end[i-1]
        windows = []
        test_cursor = train_sizes[0]  # first test starts after first train

        total_test = sum(test_sizes)
        fits = (test_cursor + total_test) <= self._N

        for i in range(nrows):
            test_s = test_cursor
            test_e = min(test_s + test_sizes[i], self._N)
            train_e = test_s
            train_s = max(0, train_e - train_sizes[i])
            windows.append((train_s, train_e, test_s, test_e))
            test_cursor = test_e

            # Update date labels in table
            try:
                t_start = pd.Timestamp(self._data.index[train_s]).strftime('%Y-%m-%d')
                t_end = pd.Timestamp(self._data.index[min(train_e, self._N) - 1]).strftime('%Y-%m-%d')
                self.win_table.setItem(i, 3, QTableWidgetItem(f"{t_start} → {t_end}"))
            except Exception:
                self.win_table.setItem(i, 3, QTableWidgetItem(f"Bar {train_s}–{train_e}"))
            try:
                v_start = pd.Timestamp(self._data.index[min(test_s, self._N - 1)]).strftime('%Y-%m-%d')
                v_end = pd.Timestamp(self._data.index[min(test_e, self._N) - 1]).strftime('%Y-%m-%d')
                self.win_table.setItem(i, 4, QTableWidgetItem(f"{v_start} → {v_end}"))
            except Exception:
                self.win_table.setItem(i, 4, QTableWidgetItem(f"Bar {test_s}–{test_e}"))

        self._windows = windows

        used = test_cursor
        remaining = self._N - used
        warn = "" if fits else "  ⚠ exceeds data!"
        self.lbl_info.setText(
            f"{nrows} windows  |  Total test: {total_test} bars  |  "
            f"Used: {used}/{self._N}{warn}")

        self._draw_preview()

    def _draw_preview(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor('#1C1C2E')

        if not self._windows:
            ax.text(0.5, 0.5, "Adjust settings to create windows",
                    ha='center', va='center', color='#FF5252',
                    fontsize=12, transform=ax.transAxes)
            self.canvas.draw_idle()
            return

        n = len(self._windows)
        rh, gap = 0.8, 0.25

        for i, (ts, te, vs, ve) in enumerate(self._windows):
            y = (n - 1 - i) * (rh + gap)

            # Color based on result if available
            ret = None
            if i < len(self._window_results):
                ret = self._window_results[i].get('return', None)

            ax.add_patch(MplRect((ts, y), te - ts, rh,
                                  facecolor='#FF7043', edgecolor='#FF5722',
                                  alpha=0.85, lw=1.2, zorder=2))
            test_col = ('#4CAF50' if ret and ret >= 0 else
                        '#F44336' if ret is not None else '#FFD54F')
            ax.add_patch(MplRect((vs, y), ve - vs, rh,
                                  facecolor=test_col, edgecolor='#FFF',
                                  alpha=0.85, lw=1.2, zorder=2))

            ax.text((ts + te) / 2, y + rh / 2, "Train", fontsize=7,
                    ha='center', va='center', color='#FFF',
                    fontweight='bold', zorder=3)
            label = f"{ret:+.1f}%" if ret is not None else "Test"
            ax.text((vs + ve) / 2, y + rh / 2, label, fontsize=7,
                    ha='center', va='center',
                    color='#FFF' if ret is not None else '#333',
                    fontweight='bold', zorder=3)

        ax.set_xlim(-2, self._N + 2)
        ax.set_ylim(-gap, n * (rh + gap))

        ntk = min(10, self._N)
        tpos = np.linspace(0, self._N - 1, ntk, dtype=int)
        tlbl = []
        for p in tpos:
            try:
                tlbl.append(pd.Timestamp(self._data.index[p]).strftime('%Y-%m-%d'))
            except Exception:
                tlbl.append(str(p))
        ax.set_xticks(tpos)
        ax.set_xticklabels(tlbl, fontsize=7, rotation=30, ha='right')
        ax.set_yticks([])
        ax.tick_params(colors='#C8C8D4')
        ax.legend(handles=[
            Patch(facecolor='#FF7043', label='Training (IS)'),
            Patch(facecolor='#FFD54F', label='Test (OOS)'),
        ], loc='upper right', fontsize=8,
            facecolor='#252540', edgecolor='#3A3A5A', labelcolor='#C8C8D4')
        ax.set_title('Walk-Forward Windows', color='#42A5F5',
                     fontsize=11, fontweight='bold')
        for sp in ax.spines.values():
            sp.set_color('#2A2A45')
        self.fig.tight_layout(pad=0.8)
        self.canvas.draw_idle()

    # ── Run ────────────────────────────────────────────────────────

    def _run(self):
        if not self._windows:
            QMessageBox.warning(self, "Error", "No valid windows!")
            return

        opt_ranges = self._opt_ranges()
        if not opt_ranges:
            QMessageBox.warning(self, "Error",
                                "Select and configure at least one parameter!")
            return

        self.btn_run.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(self._windows))
        self._window_results = []
        self._param_schedule = []

        maximize = "Return [%]"

        try:
            from backtest_engine import BacktestReplay
            replay = BacktestReplay()
            strat_cls = replay.load_strategy_from_code(self._code)

            for i, (ts, te, vs, ve) in enumerate(self._windows):
                self.progress.setValue(i)
                self.lbl_status.setText(f"Window {i+1}/{len(self._windows)}")
                QApplication.processEvents()

                train_df = self._data.iloc[ts:te].copy()
                test_df = self._data.iloc[vs:ve].copy()

                wr = {'window': i + 1,
                      'train_s': ts, 'train_e': te,
                      'test_s': vs, 'test_e': ve}

                try:
                    wr['train_period'] = (
                        f"{pd.Timestamp(train_df.index[0]).strftime('%m/%d')}"
                        f"–{pd.Timestamp(train_df.index[-1]).strftime('%m/%d')}")
                    wr['test_period'] = (
                        f"{pd.Timestamp(test_df.index[0]).strftime('%m/%d')}"
                        f"–{pd.Timestamp(test_df.index[-1]).strftime('%m/%d')}")
                except Exception:
                    wr['train_period'] = f"{ts}–{te}"
                    wr['test_period'] = f"{vs}–{ve}"

                # 1. Optimise on training
                best = {p['name']: p['value'] for p in self._params}
                try:
                    bt_tr = Backtest(train_df, strat_cls,
                                    cash=self._cash, exclusive_orders=True)
                    opt_st = bt_tr.optimize(**opt_ranges, maximize=maximize)
                    for k in opt_ranges:
                        best[k] = getattr(opt_st._strategy, k)
                except Exception:
                    pass
                wr['best_params'] = dict(best)

                # 2. Test with optimised params
                try:
                    bt_te = Backtest(test_df, strat_cls,
                                    cash=self._cash, exclusive_orders=True)
                    st = bt_te.run(**best)
                    wr['return'] = st.get('Return [%]', 0)
                    wr['max_dd'] = st.get('Max. Drawdown [%]', 0)
                    wr['win_rate'] = st.get('Win Rate [%]', 0)
                    wr['trades'] = st.get('# Trades', 0)
                    wr['sharpe'] = st.get('Sharpe Ratio', 0)
                except Exception as e:
                    wr['return'] = 0; wr['max_dd'] = 0
                    wr['win_rate'] = 0; wr['trades'] = 0; wr['sharpe'] = 0
                    wr['error'] = str(e)

                self._window_results.append(wr)
                self._param_schedule.append((vs, ve, dict(best)))

            self.progress.setValue(len(self._windows))
            self._show_results()
            self._draw_preview()  # redraw with colours
            self.btn_load.setEnabled(True)
            self.btn_pdf.setEnabled(True)

            tot = sum(w.get('return', 0) for w in self._window_results)
            avg = tot / len(self._window_results)
            self.lbl_status.setText(
                f"✅ Done!  Avg Return: {avg:.2f}%  |  "
                f"Total Return: {tot:.2f}%")

        except Exception as e:
            self.lbl_status.setText(f"❌ {e}")
            QMessageBox.critical(self, "Error",
                                  f"{e}\n\n{traceback.format_exc()}")
        finally:
            self.btn_run.setEnabled(True)
            self.progress.setVisible(False)

    def _show_results(self):
        cols = ["#", "Train", "Test", "Best Params",
                "Trades", "Return%", "MaxDD%", "WinRate%", "Sharpe"]
        self.results_table.setColumnCount(len(cols))
        self.results_table.setHorizontalHeaderLabels(cols)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setRowCount(len(self._window_results))

        for i, w in enumerate(self._window_results):
            self.results_table.setItem(i, 0, QTableWidgetItem(str(w['window'])))
            self.results_table.setItem(i, 1, QTableWidgetItem(w.get('train_period', '')))
            self.results_table.setItem(i, 2, QTableWidgetItem(w.get('test_period', '')))

            bp = w.get('best_params', {})
            bp_str = ", ".join(f"{k}={v}" for k, v in bp.items()
                               if k in self._opt_ranges())
            self.results_table.setItem(i, 3, QTableWidgetItem(bp_str))

            self.results_table.setItem(i, 4, QTableWidgetItem(str(w.get('trades', 0))))

            ret = w.get('return', 0)
            ri = QTableWidgetItem(f"{ret:+.2f}%")
            ri.setForeground(Qt.green if ret >= 0 else Qt.red)
            self.results_table.setItem(i, 5, ri)

            dd = w.get('max_dd', 0)
            di = QTableWidgetItem(f"{dd:.2f}%")
            di.setForeground(Qt.red)
            self.results_table.setItem(i, 6, di)

            self.results_table.setItem(i, 7, QTableWidgetItem(
                f"{w.get('win_rate', 0):.1f}%"))
            self.results_table.setItem(i, 8, QTableWidgetItem(
                f"{w.get('sharpe', 0):.2f}"))

    # ── Load combined ──────────────────────────────────────────────

    def _load_combined(self):
        """Build combined OOS dataset with dynamic param schedule and send
        to main window."""
        if not self._param_schedule:
            return

        # Concatenate all OOS data
        oos_frames = []
        for vs, ve, _ in self._param_schedule:
            oos_frames.append(self._data.iloc[vs:ve])
        combined = pd.concat(oos_frames)
        combined = combined[~combined.index.duplicated(keep='first')]

        # Build a strategy wrapper with dynamic params
        schedule = list(self._param_schedule)  # copy
        code = self._generate_dynamic_strategy(schedule)

        self.result_ready.emit(combined, schedule, code)
        self.lbl_status.setText("✅ Combined OOS loaded — close to replay!")

    def _generate_dynamic_strategy(self, schedule):
        """Generate strategy code that switches parameters at window boundaries."""
        # Get base strategy code
        base = self._code

        # Build param schedule as a Python literal
        sched_entries = []
        for vs, ve, params in schedule:
            ts_start = repr(str(self._data.index[vs]))
            ts_end = repr(str(self._data.index[min(ve, self._N) - 1]))
            pdict = repr(params)
            sched_entries.append(f"    ({ts_start}, {ts_end}, {pdict}),")

        sched_str = "[\n" + "\n".join(sched_entries) + "\n]"

        # Find the strategy class name
        import re
        m = re.search(r'class\s+(\w+)\s*\(\s*Strategy\s*\)', base)
        cls_name = m.group(1) if m else "MyStrategy"

        # Generate wrapper code
        wrapper = f'''{base}

# ── Walk-Forward Dynamic Parameter Wrapper ──

_WF_SCHEDULE = {sched_str}

class WF_{cls_name}({cls_name}):
    """Walk-Forward wrapper: switches parameters per OOS window."""

    def next(self):
        current_ts = str(self.data.index[-1])
        for ts_start, ts_end, params in _WF_SCHEDULE:
            if ts_start <= current_ts <= ts_end:
                for k, v in params.items():
                    setattr(self, k, v)
                break
        super().next()
'''
        return wrapper

    # ── PDF export ─────────────────────────────────────────────────

    def _export_pdf(self):
        if not self._window_results:
            return
        fp, _ = QFileDialog.getSaveFileName(
            self, "Export Walk-Forward Report",
            "walkforward_report.pdf", "PDF (*.pdf)")
        if not fp:
            return
        try:
            with PdfPages(fp) as pdf:
                self.fig.savefig(pdf, format='pdf', facecolor='white',
                                 bbox_inches='tight')
                fig2 = Figure(figsize=(11.69, 8.27), facecolor='white')
                ax = fig2.add_axes([0.05, 0.1, 0.9, 0.82])
                ax.axis('off')
                ax.text(0, 1.02, 'Walk-Forward Analysis Report',
                        fontsize=16, fontweight='bold', color='#1A237E',
                        transform=ax.transAxes)
                ax.text(1.0, 1.02, 'Króner Barnabás Zsolt',
                        fontsize=11, color='#444', fontweight='bold',
                        ha='right', transform=ax.transAxes)
                y = 0.94
                hdr = f"{'#':>3}  {'Train':<18} {'Test':<18} {'Best Params':<30} {'Ret%':>7} {'DD%':>7} {'WR%':>7}"
                ax.text(0, y, hdr, fontsize=8, fontweight='bold',
                        color='#1A237E', fontfamily='monospace',
                        transform=ax.transAxes)
                y -= 0.04
                for w in self._window_results:
                    bp = w.get('best_params', {})
                    bp_s = ",".join(f"{k}={v}" for k, v in bp.items()
                                    if k in self._opt_ranges())[:28]
                    ret = w.get('return', 0)
                    color = '#1B5E20' if ret >= 0 else '#B71C1C'
                    line = (f"{w['window']:>3}  "
                            f"{w.get('train_period',''):<18} "
                            f"{w.get('test_period',''):<18} "
                            f"{bp_s:<30} "
                            f"{ret:>+7.2f} "
                            f"{w.get('max_dd',0):>7.2f} "
                            f"{w.get('win_rate',0):>7.1f}")
                    ax.text(0, y, line, fontsize=7, color=color,
                            fontfamily='monospace', transform=ax.transAxes)
                    y -= 0.025
                tot = sum(w.get('return', 0) for w in self._window_results)
                avg = tot / len(self._window_results)
                y -= 0.02
                ax.text(0, y,
                        f"Total OOS Return: {tot:.2f}%  |  "
                        f"Avg: {avg:.2f}%  |  Windows: {len(self._window_results)}",
                        fontsize=10, fontweight='bold', color='#1A237E',
                        transform=ax.transAxes)
                pdf.savefig(fig2)
                plt.close(fig2)
            self.lbl_status.setText(f"✅ PDF: {fp}")
        except Exception as e:
            self.lbl_status.setText(f"❌ {e}")
