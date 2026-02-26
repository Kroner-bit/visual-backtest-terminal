"""
PDF Report Exporter
--------------------
Generates a PDF report with equity curve chart,
backtest statistics, and full trade list.
"""

import os
from datetime import datetime
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


COLORS = {
    'bg': '#1C1C2E',
    'panel': '#252540',
    'text': '#C8C8D4',
    'equity': '#42A5F5',
    'closed': '#26A69A',
    'floating': '#FF9800',
    'positive': '#00E676',
    'negative': '#FF5252',
    'grid': '#2A2A45',
    'header_bg': '#1A1A2E',
}


def export_pdf(
    filepath: str,
    stats: Dict[str, Any],
    trades: list,
    equity_history: list,
    closed_pnl_history: list,
    floating_pnl_history: list,
    initial_cash: float,
    data: pd.DataFrame = None,
    strategy_name: str = "Strategy",
    ticker: str = "",
):
    """
    Export a full backtest report to PDF.

    Args:
        filepath: Output PDF file path
        stats: Dict of backtest statistics
        trades: List of TradeRecord objects
        equity_history: List of equity values per bar
        closed_pnl_history: List of cumulative closed P/L per bar
        floating_pnl_history: List of floating P/L per bar
        initial_cash: Initial cash amount
        data: OHLCV DataFrame (optional, for date range)
        strategy_name: Name of the strategy
        ticker: Ticker symbol
    """
    with PdfPages(filepath) as pdf:
        # === Page 1: Title + Equity Curve + Key Stats ===
        fig1 = Figure(figsize=(11.69, 8.27), facecolor='white')  # A4 landscape

        # Title area
        ax_title = fig1.add_axes([0.05, 0.88, 0.9, 0.10])
        ax_title.axis('off')

        title_text = f"Backtest Report — {strategy_name}"
        if ticker:
            title_text += f"  ({ticker})"
        ax_title.text(0, 0.7, title_text,
                      fontsize=18, fontweight='bold', color='#1A237E',
                      transform=ax_title.transAxes)

        date_range = ""
        if data is not None and len(data) > 0:
            try:
                start = pd.Timestamp(data.index[0]).strftime('%Y-%m-%d')
                end = pd.Timestamp(data.index[-1]).strftime('%Y-%m-%d')
                date_range = f"{start}  →  {end}  |  {len(data)} bars"
            except Exception:
                date_range = f"{len(data)} bars"

        subtitle = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if date_range:
            subtitle += f"  |  {date_range}"
        ax_title.text(0, 0.1, subtitle,
                      fontsize=10, color='#666',
                      transform=ax_title.transAxes)
        ax_title.text(1.0, 0.7, 'Króner Barnabás Zsolt',
                      fontsize=11, color='#444', fontweight='bold',
                      ha='right', va='center',
                      transform=ax_title.transAxes)

        # Equity curve
        ax_eq = fig1.add_axes([0.08, 0.42, 0.84, 0.42])
        n = len(equity_history)
        if n > 1:
            x = np.arange(n)
            eq = np.array(equity_history)
            cl = initial_cash + np.array(closed_pnl_history)
            fl = np.array(floating_pnl_history)

            ax_eq.plot(x, eq, color='#1565C0', linewidth=1.5, label='Equity', zorder=3)
            ax_eq.plot(x, cl, color='#00897B', linewidth=1.2, label='Closed P/L', zorder=2)
            ax_eq.fill_between(x, initial_cash, cl,
                               where=cl >= initial_cash,
                               color='#00897B', alpha=0.15, zorder=1)
            ax_eq.fill_between(x, initial_cash, cl,
                               where=cl < initial_cash,
                               color='#E53935', alpha=0.15, zorder=1)
            ax_eq.fill_between(x, cl, eq,
                               where=fl >= 0,
                               color='#FF9800', alpha=0.2, label='Floating P/L', zorder=1)
            ax_eq.fill_between(x, cl, eq,
                               where=fl < 0,
                               color='#E53935', alpha=0.2, zorder=1)
            ax_eq.axhline(y=initial_cash, color='#999', linewidth=0.8, linestyle='--')
            ax_eq.set_ylabel('Equity ($)', fontsize=10)
            ax_eq.set_xlabel('Bar', fontsize=9)
            ax_eq.legend(loc='upper left', fontsize=8)
            ax_eq.grid(True, alpha=0.2)
            ax_eq.set_title('Equity Curve', fontsize=12, fontweight='bold', pad=8)

        # Key stats table
        ax_stats = fig1.add_axes([0.08, 0.04, 0.84, 0.32])
        ax_stats.axis('off')

        # Build stats table data
        stat_rows = []
        stat_keys = [
            ('Return [%]', 'Return'),
            ('Buy & Hold Return [%]', 'Buy&Hold'),
            ('Equity Final [$]', 'Final Equity'),
            ('Equity Peak [$]', 'Peak Equity'),
            ('Max. Drawdown [%]', 'Max Drawdown'),
            ('Sharpe Ratio', 'Sharpe'),
            ('Sortino Ratio', 'Sortino'),
            ('# Trades', 'Total Trades'),
            ('Win Rate [%]', 'Win Rate'),
            ('Profit Factor', 'Profit Factor'),
            ('Avg. Trade [%]', 'Avg Trade'),
            ('Best Trade [%]', 'Best Trade'),
            ('Worst Trade [%]', 'Worst Trade'),
            ('SQN', 'SQN'),
            ('Exposure Time [%]', 'Exposure'),
            ('Max. Trade Duration', 'Max Duration'),
        ]

        col1_data = []
        col2_data = []
        for key, label in stat_keys:
            if key in stats:
                val = stats[key]
                if isinstance(val, float):
                    if '$' in key:
                        val_str = f"${val:,.2f}"
                    elif '%' in key:
                        val_str = f"{val:.2f}%"
                    else:
                        val_str = f"{val:.4f}"
                else:
                    val_str = str(val)
                if len(col1_data) < 8:
                    col1_data.append((label, val_str))
                else:
                    col2_data.append((label, val_str))

        # Draw two-column stats
        y_start = 0.95
        for i, (label, val) in enumerate(col1_data):
            y = y_start - i * 0.12
            ax_stats.text(0.02, y, label + ":", fontsize=10, color='#444',
                          transform=ax_stats.transAxes, va='center')
            ax_stats.text(0.22, y, val, fontsize=10, fontweight='bold', color='#1A237E',
                          transform=ax_stats.transAxes, va='center')

        for i, (label, val) in enumerate(col2_data):
            y = y_start - i * 0.12
            ax_stats.text(0.52, y, label + ":", fontsize=10, color='#444',
                          transform=ax_stats.transAxes, va='center')
            ax_stats.text(0.72, y, val, fontsize=10, fontweight='bold', color='#1A237E',
                          transform=ax_stats.transAxes, va='center')

        ax_stats.set_title('Performance Summary', fontsize=12, fontweight='bold',
                           loc='left', pad=4)

        pdf.savefig(fig1)
        plt.close(fig1)

        # === Page 2+: Trade List ===
        if trades:
            _export_trades_pages(pdf, trades)


def _export_trades_pages(pdf, trades):
    """Generate trade list pages."""
    rows_per_page = 35
    total_pages = (len(trades) + rows_per_page - 1) // rows_per_page

    headers = ['#', 'Entry Time', 'Exit Time', 'Type', 'Size',
               'Entry $', 'Exit $', 'P/L ($)', 'Return %']
    col_widths = [0.04, 0.14, 0.14, 0.06, 0.08, 0.10, 0.10, 0.12, 0.10]

    for page in range(total_pages):
        fig = Figure(figsize=(11.69, 8.27), facecolor='white')
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.88])
        ax.axis('off')

        # Page title
        ax.text(0, 1.02, f'Trade List (Page {page + 1}/{total_pages})',
                fontsize=13, fontweight='bold', color='#1A237E',
                transform=ax.transAxes)
        ax.text(1.0, 1.02, 'Króner Barnabás Zsolt',
                fontsize=11, color='#444', fontweight='bold',
                ha='right', transform=ax.transAxes)

        # Header row
        x_pos = 0
        y = 0.97
        for j, (header, w) in enumerate(zip(headers, col_widths)):
            ax.text(x_pos + w / 2, y, header, fontsize=8, fontweight='bold',
                    color='#444', ha='center', va='center',
                    transform=ax.transAxes,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8EAF6',
                              edgecolor='#C5CAE9'))
            x_pos += w

        # Draw line under header
        ax.plot([0, 0.88], [y - 0.015, y - 0.015], color='#C5CAE9',
                linewidth=0.8, transform=ax.transAxes, clip_on=False)

        # Data rows
        start_idx = page * rows_per_page
        end_idx = min(start_idx + rows_per_page, len(trades))
        row_height = 0.025

        for i, t in enumerate(trades[start_idx:end_idx]):
            row_y = y - 0.035 - (i * row_height)

            entry_time = str(t.entry_time)[:16]
            exit_time = str(t.exit_time)[:16]
            type_str = "LONG" if t.is_long else "SHORT"
            pnl_color = '#1B5E20' if t.pnl >= 0 else '#B71C1C'

            row_data = [
                str(start_idx + i + 1),
                entry_time,
                exit_time,
                type_str,
                f"{abs(t.size):.1f}",
                f"{t.entry_price:.2f}",
                f"{t.exit_price:.2f}",
                f"${t.pnl:+,.2f}",
                f"{t.return_pct * 100:.2f}%",
            ]

            x_pos = 0
            for j, (cell, w) in enumerate(zip(row_data, col_widths)):
                color = '#333'
                weight = 'normal'
                if j == 3:  # Type
                    color = '#1B5E20' if t.is_long else '#B71C1C'
                    weight = 'bold'
                elif j == 7:  # P/L
                    color = pnl_color
                    weight = 'bold'
                elif j == 8:  # Return
                    color = pnl_color

                ax.text(x_pos + w / 2, row_y, cell,
                        fontsize=7, color=color, fontweight=weight,
                        ha='center', va='center',
                        transform=ax.transAxes)
                x_pos += w

            # Subtle row separator
            if i % 2 == 0:
                ax.fill_between(
                    [0, 0.88],
                    [row_y - row_height / 2] * 2,
                    [row_y + row_height / 2] * 2,
                    facecolor='#F5F5F5', transform=ax.transAxes,
                    zorder=0, clip_on=False
                )

        # Summary at bottom
        total_pnl = sum(t.pnl for t in trades)
        winners = sum(1 for t in trades if t.pnl > 0)
        losers = sum(1 for t in trades if t.pnl <= 0)
        summary_y = y - 0.035 - ((end_idx - start_idx) * row_height) - 0.03

        if page == total_pages - 1:
            pnl_color = '#1B5E20' if total_pnl >= 0 else '#B71C1C'
            ax.text(0, summary_y,
                    f"Total: {len(trades)} trades  |  Winners: {winners}  |  "
                    f"Losers: {losers}  |  Net P/L: ${total_pnl:+,.2f}",
                    fontsize=9, fontweight='bold', color=pnl_color,
                    transform=ax.transAxes)

        pdf.savefig(fig)
        plt.close(fig)
