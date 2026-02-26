"""
Strategy Optimizer Dialog
--------------------------
Separate window for optimizing strategy parameters.
Detects parameters from strategy code, runs all combinations
using backtesting.py optimize(), displays results chart,
and allows exporting results and applying best parameters.
"""

import re
import ast
import traceback
from itertools import product
from functools import reduce
from operator import mul

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QApplication, QGroupBox, QAbstractItemView,
    QComboBox, QCheckBox, QDoubleSpinBox, QFileDialog,
    QSplitter, QWidget, QProgressBar,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

from backtesting import Backtest, Strategy


def detect_parameters(code: str) -> list:
    """
    Parse strategy code to find optimizable class-level numeric parameters.
    Returns list of dicts: {name, value, type}.
    """
    params = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                name = target.id
                                if name.startswith('_'):
                                    continue
                                val = item.value
                                if isinstance(val, ast.Constant) and isinstance(val.value, (int, float)):
                                    params.append({
                                        'name': name,
                                        'value': val.value,
                                        'type': type(val.value).__name__,
                                    })
    except Exception:
        pass
    return params


def apply_parameters_to_code(code: str, params: dict) -> str:
    """
    Replace parameter values in strategy code.
    params: {name: new_value}
    """
    for name, value in params.items():
        # Match: name = value (possibly with spaces)
        pattern = rf'(\b{re.escape(name)}\s*=\s*)[^\n#]+'
        if isinstance(value, float):
            replacement = rf'\g<1>{value}'
        else:
            replacement = rf'\g<1>{value}'
        code = re.sub(pattern, replacement, code, count=1)
    return code


class OptimizerDialog(QDialog):
    """
    Strategy parameter optimization dialog.
    """

    # Signal: optimized code to apply
    optimized_code = pyqtSignal(str)

    def __init__(self, strategy_code: str, data: pd.DataFrame,
                 cash: float = 10_000, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Strategy Optimizer")
        self.setMinimumSize(950, 700)
        self.resize(1050, 750)
        self.setStyleSheet("""
            QDialog {
                background-color: #1C1C2E;
                color: #C8C8D4;
            }
        """)

        self._code = strategy_code
        self._data = data
        self._cash = cash
        self._params = detect_parameters(strategy_code)
        self._results_df = None  # DataFrame of optimization results
        self._best_params = {}

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # === Parameter Table ===
        param_group = QGroupBox("📊 Strategy Parameters")
        param_group.setStyleSheet("""
            QGroupBox {
                color: #42A5F5; font-size: 13px; font-weight: bold;
                border: 1px solid #2A2A45; border-radius: 6px;
                margin-top: 8px; padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px; padding: 0 6px;
            }
        """)
        param_layout = QVBoxLayout(param_group)

        self.param_table = QTableWidget()
        self.param_table.setColumnCount(6)
        self.param_table.setHorizontalHeaderLabels([
            "✓", "Parameter", "Default", "Min", "Max", "Step"
        ])
        self.param_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.param_table.verticalHeader().setVisible(False)
        self.param_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.param_table.setMaximumHeight(180)
        self.param_table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A2E; color: #C8C8D4;
                border: 1px solid #2A2A45; border-radius: 4px;
                gridline-color: #2A2A45; font-size: 11px;
            }
            QHeaderView::section {
                background-color: #252540; color: #42A5F5;
                font-weight: bold; font-size: 11px;
                padding: 4px; border: 1px solid #2A2A45;
            }
        """)
        self._populate_params()
        param_layout.addWidget(self.param_table)

        # Info row
        info_row = QHBoxLayout()
        self.lbl_combinations = QLabel("Combinations: 0")
        self.lbl_combinations.setStyleSheet(
            "color: #FFD740; font-size: 12px; font-weight: bold;"
        )
        info_row.addWidget(self.lbl_combinations)
        info_row.addStretch()

        # Maximize selector
        lbl_max = QLabel("Maximize:")
        lbl_max.setStyleSheet("color: #888; font-size: 11px;")
        self.cmb_maximize = QComboBox()
        self.cmb_maximize.addItems([
            "Return [%]", "Equity Final [$]", "Sharpe Ratio",
            "Sortino Ratio", "Profit Factor", "SQN", "Win Rate [%]",
        ])
        self.cmb_maximize.setStyleSheet("""
            QComboBox {
                background-color: #1A1A2E; color: #FFF;
                border: 1px solid #3A3A5A; border-radius: 3px;
                padding: 4px 8px; font-size: 11px;
            }
        """)
        info_row.addWidget(lbl_max)
        info_row.addWidget(self.cmb_maximize)

        # Run button
        self.btn_run = QPushButton("🚀 Run Optimization")
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #1B5E20; color: #FFF;
                border: 1px solid #2E7D32; border-radius: 4px;
                padding: 6px 20px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2E7D32; }
        """)
        self.btn_run.clicked.connect(self._run_optimization)
        info_row.addWidget(self.btn_run)

        param_layout.addLayout(info_row)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(14)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #1A1A2E; border: 1px solid #3A3A5A;
                border-radius: 4px; text-align: center;
                color: #C8C8D4; font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #1B5E20; border-radius: 3px;
            }
        """)
        param_layout.addWidget(self.progress)

        main_layout.addWidget(param_group)

        # === Results: Chart + Table ===
        results_splitter = QSplitter(Qt.Horizontal)

        # Chart
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        self.fig = Figure(figsize=(6, 3.5), facecolor='#1C1C2E', dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color: #1C1C2E;")
        chart_layout.addWidget(self.canvas)
        results_splitter.addWidget(chart_container)

        # Results table
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)

        lbl_results = QLabel("📋 Results (click row to select)")
        lbl_results.setStyleSheet("color: #42A5F5; font-size: 12px; font-weight: bold;")
        results_layout.addWidget(lbl_results)

        self.results_table = QTableWidget()
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A2E; color: #C8C8D4;
                border: 1px solid #2A2A45; border-radius: 4px;
                gridline-color: #2A2A45; font-size: 11px;
            }
            QTableWidget::item:selected {
                background-color: #1B5E20; color: #FFF;
            }
            QHeaderView::section {
                background-color: #252540; color: #42A5F5;
                font-weight: bold; font-size: 10px;
                padding: 3px; border: 1px solid #2A2A45;
            }
        """)
        results_layout.addWidget(self.results_table)
        results_splitter.addWidget(results_container)

        results_splitter.setSizes([500, 500])
        main_layout.addWidget(results_splitter, stretch=1)

        # === Bottom buttons ===
        btn_layout = QHBoxLayout()

        self.btn_apply = QPushButton("✅ Apply Selected Parameters")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #1565C0; color: #FFF;
                border: 1px solid #1976D2; border-radius: 4px;
                padding: 7px 20px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled {
                background-color: #2A2A45; color: #555;
            }
        """)
        self.btn_apply.clicked.connect(self._apply_selected)

        self.btn_export = QPushButton("📄 Export PDF")
        self.btn_export.setEnabled(False)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #4A148C; color: #FFF;
                border: 1px solid #6A1B9A; border-radius: 4px;
                padding: 7px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #6A1B9A; }
            QPushButton:disabled {
                background-color: #2A2A45; color: #555;
            }
        """)
        self.btn_export.clicked.connect(self._export_pdf)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #888; font-size: 11px;")

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addStretch()
        btn_layout.addWidget(self.lbl_status)

        main_layout.addLayout(btn_layout)

        # Initial combo count
        self._update_combinations()

    def _populate_params(self):
        """Fill parameter table from detected parameters."""
        self.param_table.setRowCount(len(self._params))
        self._param_widgets = []

        for i, p in enumerate(self._params):
            # Checkbox
            chk = QCheckBox()
            chk.setChecked(True)
            chk.stateChanged.connect(self._update_combinations)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.param_table.setCellWidget(i, 0, chk_widget)

            # Name
            self.param_table.setItem(i, 1, QTableWidgetItem(p['name']))

            # Default value
            self.param_table.setItem(i, 2, QTableWidgetItem(str(p['value'])))

            # Min
            spn_min = QDoubleSpinBox()
            spn_min.setRange(-1e9, 1e9)
            spn_min.setDecimals(2 if p['type'] == 'float' else 0)
            spn_min.setValue(max(1, p['value'] * 0.5) if p['value'] > 0 else p['value'] - 5)
            spn_min.setStyleSheet("background:#1A1A2E;color:#FFF;border:1px solid #3A3A5A;")
            spn_min.valueChanged.connect(self._update_combinations)
            self.param_table.setCellWidget(i, 3, spn_min)

            # Max
            spn_max = QDoubleSpinBox()
            spn_max.setRange(-1e9, 1e9)
            spn_max.setDecimals(2 if p['type'] == 'float' else 0)
            spn_max.setValue(p['value'] * 2 if p['value'] > 0 else p['value'] + 10)
            spn_max.setStyleSheet("background:#1A1A2E;color:#FFF;border:1px solid #3A3A5A;")
            spn_max.valueChanged.connect(self._update_combinations)
            self.param_table.setCellWidget(i, 4, spn_max)

            # Step
            spn_step = QDoubleSpinBox()
            spn_step.setRange(0.01, 1e6)
            spn_step.setDecimals(2 if p['type'] == 'float' else 0)
            default_step = max(1, p['value'] * 0.25) if p['value'] > 0 else 1
            spn_step.setValue(default_step)
            spn_step.setStyleSheet("background:#1A1A2E;color:#FFF;border:1px solid #3A3A5A;")
            spn_step.valueChanged.connect(self._update_combinations)
            self.param_table.setCellWidget(i, 5, spn_step)

            self._param_widgets.append({
                'checkbox': chk,
                'min': spn_min,
                'max': spn_max,
                'step': spn_step,
                'name': p['name'],
                'type': p['type'],
                'default': p['value'],
            })

    def _get_param_ranges(self) -> dict:
        """Get selected parameter ranges as kwargs for optimize()."""
        ranges = {}
        for w in self._param_widgets:
            if not w['checkbox'].isChecked():
                continue
            mn = w['min'].value()
            mx = w['max'].value()
            st = w['step'].value()
            if st <= 0 or mn > mx:
                continue
            if w['type'] == 'int':
                values = list(range(int(mn), int(mx) + 1, int(st)))
            else:
                values = []
                v = mn
                while v <= mx + 1e-9:
                    values.append(round(v, 4))
                    v += st
            if values:
                ranges[w['name']] = values
        return ranges

    def _update_combinations(self, *_):
        """Update the combination count label."""
        ranges = self._get_param_ranges()
        if not ranges:
            self.lbl_combinations.setText("Combinations: 0 — select parameters")
            return
        count = reduce(mul, (len(v) for v in ranges.values()), 1)
        detail = " × ".join(f"{k}({len(v)})" for k, v in ranges.items())
        self.lbl_combinations.setText(f"Combinations: {count}  [{detail}]")

    def _run_optimization(self):
        """Run the optimization."""
        ranges = self._get_param_ranges()
        if not ranges:
            QMessageBox.warning(self, "Error", "Select at least one parameter to optimize!")
            return

        self.btn_run.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.lbl_status.setText("Running optimization...")
        QApplication.processEvents()

        try:
            # Load strategy
            from backtest_engine import BacktestReplay
            replay = BacktestReplay()
            strategy_class = replay.load_strategy_from_code(self._code)

            # Setup backtest
            bt = Backtest(
                self._data, strategy_class,
                cash=self._cash, exclusive_orders=True,
            )

            maximize = self.cmb_maximize.currentText()

            # Run optimization
            stats, heatmap = bt.optimize(
                **ranges,
                maximize=maximize,
                return_heatmap=True,
            )

            self.progress.setValue(100)

            # Process results
            self._process_results(stats, heatmap, ranges, maximize)

            self.btn_apply.setEnabled(True)
            self.btn_export.setEnabled(True)

            # Store best params
            self._best_params = {}
            for name in ranges:
                self._best_params[name] = getattr(stats._strategy, name)

            self.lbl_status.setText(
                f"✅ Done! Best: {self._best_params} → "
                f"{maximize}: {stats[maximize]:.2f}"
            )

        except Exception as e:
            self.lbl_status.setText(f"❌ Error: {e}")
            QMessageBox.critical(self, "Optimization Error",
                                  f"{e}\n\n{traceback.format_exc()}")
        finally:
            self.btn_run.setEnabled(True)
            self.progress.setVisible(False)

    def _process_results(self, best_stats, heatmap, ranges, maximize):
        """Process and display optimization results."""
        # Convert heatmap to a usable DataFrame
        hm = heatmap.dropna()
        if hasattr(hm.index, 'names') and len(hm.index.names) > 1:
            df = hm.reset_index()
        else:
            df = pd.DataFrame({
                list(ranges.keys())[0]: hm.index,
                maximize: hm.values,
            })

        # Ensure maximize column name
        if maximize not in df.columns:
            df.columns = list(df.columns[:-1]) + [maximize]

        df = df.sort_values(maximize, ascending=False).reset_index(drop=True)
        self._results_df = df

        # Fill results table
        param_names = [n for n in ranges.keys()]
        columns = param_names + [maximize]
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setRowCount(len(df))

        for i in range(len(df)):
            for j, col in enumerate(columns):
                val = df.iloc[i][col] if col in df.columns else ""
                if isinstance(val, float):
                    text = f"{val:.4f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                if j == len(columns) - 1:  # Result column
                    try:
                        fval = float(val)
                        if fval > 0:
                            item.setForeground(Qt.green)
                        elif fval < 0:
                            item.setForeground(Qt.red)
                    except (ValueError, TypeError):
                        pass
                self.results_table.setItem(i, j, item)

        # Select best row
        self.results_table.selectRow(0)

        # Draw chart
        self._draw_chart(df, param_names, maximize)

    def _draw_chart(self, df, param_names, maximize):
        """Draw the optimization results chart."""
        self.fig.clear()

        if len(param_names) == 1:
            # Simple line/bar chart
            ax = self.fig.add_subplot(111)
            ax.set_facecolor('#1C1C2E')

            x = df[param_names[0]].values
            y = df[maximize].values

            colors = ['#00E676' if v >= 0 else '#FF5252' for v in y]
            ax.bar(range(len(x)), y, color=colors, alpha=0.8, width=0.7)
            ax.set_xticks(range(len(x)))
            ax.set_xticklabels([str(v) for v in x], fontsize=7, rotation=45)
            ax.set_xlabel(param_names[0], color='#C8C8D4', fontsize=9)
            ax.set_ylabel(maximize, color='#C8C8D4', fontsize=9)
            ax.axhline(y=0, color='#FFFFFF30', linewidth=0.8)

        elif len(param_names) == 2:
            # Heatmap
            ax = self.fig.add_subplot(111)
            ax.set_facecolor('#1C1C2E')

            try:
                pivot = df.pivot_table(
                    index=param_names[0], columns=param_names[1],
                    values=maximize
                )
                im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto')
                ax.set_xticks(range(len(pivot.columns)))
                ax.set_xticklabels([str(v) for v in pivot.columns], fontsize=7)
                ax.set_yticks(range(len(pivot.index)))
                ax.set_yticklabels([str(v) for v in pivot.index], fontsize=7)
                ax.set_xlabel(param_names[1], color='#C8C8D4', fontsize=9)
                ax.set_ylabel(param_names[0], color='#C8C8D4', fontsize=9)
                self.fig.colorbar(im, ax=ax, shrink=0.8, label=maximize)
            except Exception:
                # Fallback to scatter
                ax.scatter(range(len(df)), df[maximize].values,
                           c=df[maximize].values, cmap='RdYlGn', s=30)
                ax.set_ylabel(maximize, color='#C8C8D4', fontsize=9)
        else:
            # More than 2 params: sorted bar chart
            ax = self.fig.add_subplot(111)
            ax.set_facecolor('#1C1C2E')
            y = df[maximize].values
            colors = ['#00E676' if v >= 0 else '#FF5252' for v in y]
            ax.bar(range(len(y)), y, color=colors, alpha=0.8, width=0.8)
            ax.set_xlabel('Combination #', color='#C8C8D4', fontsize=9)
            ax.set_ylabel(maximize, color='#C8C8D4', fontsize=9)
            ax.axhline(y=0, color='#FFFFFF30', linewidth=0.8)

        ax.tick_params(colors='#C8C8D4', labelsize=7)
        ax.set_title(f'Optimization: {maximize}', color='#42A5F5',
                     fontsize=11, fontweight='bold')
        for spine in ax.spines.values():
            spine.set_color('#2A2A45')

        self.fig.tight_layout(pad=1.0)
        self.canvas.draw_idle()

    def _apply_selected(self):
        """Apply selected row's parameters back to strategy code."""
        row = self.results_table.currentRow()
        if row < 0 or self._results_df is None:
            return

        params = {}
        param_names = [w['name'] for w in self._param_widgets if w['checkbox'].isChecked()]
        for name in param_names:
            if name in self._results_df.columns:
                val = self._results_df.iloc[row][name]
                # Keep type
                orig = next((w for w in self._param_widgets if w['name'] == name), None)
                if orig and orig['type'] == 'int':
                    val = int(val)
                else:
                    val = float(val)
                params[name] = val

        new_code = apply_parameters_to_code(self._code, params)
        self.optimized_code.emit(new_code)
        self.lbl_status.setText(f"✅ Applied: {params}")

    def _export_pdf(self):
        """Export optimization results to PDF."""
        if self._results_df is None:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Optimization Report",
            "optimization_report.pdf",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if not filepath:
            return

        try:
            maximize = self.cmb_maximize.currentText()
            df = self._results_df
            param_names = [w['name'] for w in self._param_widgets if w['checkbox'].isChecked()]

            with PdfPages(filepath) as pdf:
                # Page 1: Chart + Summary
                fig1 = Figure(figsize=(11.69, 8.27), facecolor='white')

                ax_title = fig1.add_axes([0.05, 0.90, 0.9, 0.08])
                ax_title.axis('off')
                ax_title.text(0, 0.5, 'Strategy Optimization Report',
                              fontsize=18, fontweight='bold', color='#1A237E',
                              transform=ax_title.transAxes)
                ax_title.text(1.0, 0.5, 'Króner Barnabás Zsolt',
                              fontsize=11, color='#444', fontweight='bold',
                              ha='right', transform=ax_title.transAxes)

                # Chart
                ax = fig1.add_axes([0.08, 0.45, 0.84, 0.40])
                y = df[maximize].values
                colors_bar = ['#1B5E20' if v >= 0 else '#B71C1C' for v in y]
                ax.bar(range(len(y)), y, color=colors_bar, alpha=0.8)
                ax.set_xlabel('Combination #', fontsize=10)
                ax.set_ylabel(maximize, fontsize=10)
                ax.set_title(f'Optimization Results: {maximize}', fontsize=13,
                             fontweight='bold')
                ax.axhline(y=0, color='#999', linewidth=0.5)
                ax.grid(True, alpha=0.2)

                # Best result info
                ax_info = fig1.add_axes([0.08, 0.05, 0.84, 0.33])
                ax_info.axis('off')
                ax_info.set_title('Top 10 Results', fontsize=12, fontweight='bold',
                                  loc='left')

                top = df.head(10)
                cols = param_names + [maximize]
                header = "   ".join(f"{c:>12s}" for c in cols)
                ax_info.text(0, 0.95, header, fontsize=9, fontweight='bold',
                             color='#1A237E', fontfamily='monospace',
                             transform=ax_info.transAxes)
                for i in range(len(top)):
                    row_str = "   ".join(
                        f"{top.iloc[i][c]:>12.4f}" if isinstance(top.iloc[i][c], float)
                        else f"{str(top.iloc[i][c]):>12s}"
                        for c in cols
                    )
                    color = '#1B5E20' if top.iloc[i][maximize] >= 0 else '#B71C1C'
                    ax_info.text(0, 0.85 - i * 0.09, row_str,
                                fontsize=8, color=color, fontfamily='monospace',
                                transform=ax_info.transAxes)

                pdf.savefig(fig1)
                plt.close(fig1)

            self.lbl_status.setText(f"✅ PDF exported: {filepath}")
        except Exception as e:
            self.lbl_status.setText(f"❌ Export failed: {e}")
