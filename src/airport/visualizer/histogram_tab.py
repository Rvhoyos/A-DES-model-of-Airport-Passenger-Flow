from __future__ import annotations

from typing import Optional

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt

from .data_model import SimulationData
from .theme import MPL_BG, MPL_AXES_BG, MPL_TEXT, MPL_GRID, MPL_HIST_COLOR, MPL_HIST_EDGE


def _style_ax(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_facecolor(MPL_AXES_BG)
    ax.set_title(title, color=MPL_TEXT, fontsize=11, pad=10)
    ax.set_xlabel(xlabel, color=MPL_TEXT, fontsize=9)
    ax.set_ylabel(ylabel, color=MPL_TEXT, fontsize=9)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    ax.grid(True, color=MPL_GRID, alpha=0.3)
    for spine in ax.spines.values():
        spine.set_color(MPL_GRID)


def _make_canvas(fig: Figure) -> FigureCanvasQTAgg:
    fig.patch.set_facecolor(MPL_BG)
    fig.tight_layout(pad=2.0)
    canvas = FigureCanvasQTAgg(fig)
    canvas.setMinimumHeight(300)
    return canvas


class HistogramTab(QScrollArea):
    """Scrollable panel of matplotlib histograms embedded in PyQt6."""

    def __init__(self, data: SimulationData, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data = data
        self.df = data.df

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.layout_ = QVBoxLayout(container)
        self.layout_.setSpacing(16)
        self.layout_.setContentsMargins(20, 20, 20, 20)

        self._build_charts()
        self.setWidget(container)

    def _build_charts(self) -> None:
        df = self.df
        day_starts = [86400 * i for i in range(8)]  # day boundary markers

        # 1. All events time distribution
        fig1 = Figure(figsize=(10, 3.5), dpi=100)
        ax1 = fig1.add_subplot(111)
        ax1.hist(df['Time'].dropna(), bins=80, color=MPL_HIST_COLOR, edgecolor=MPL_HIST_EDGE, alpha=0.85)
        for ds in day_starts:
            if df['Time'].min() <= ds <= df['Time'].max():
                ax1.axvline(ds, color='#F44336', linestyle='--', alpha=0.4, linewidth=0.8)
        _style_ax(ax1, 'Event Distribution Over Simulation Time', 'Time (seconds)', 'Event Count')
        self.layout_.addWidget(_make_canvas(fig1))

        # 2. Check-in counter events
        df_checkin = df[df['Details'].astype(str).str.contains('service time', case=False, na=False)]
        fig2 = Figure(figsize=(10, 3.5), dpi=100)
        ax2 = fig2.add_subplot(111)
        if len(df_checkin) > 0:
            ax2.hist(df_checkin['Time'].dropna(), bins=50, color='#ffffff', edgecolor=MPL_HIST_EDGE, alpha=0.85)
        else:
            ax2.text(0.5, 0.5, 'No check-in events in data\n(check-in currently skipped in sim)',
                     ha='center', va='center', transform=ax2.transAxes, color=MPL_TEXT, fontsize=10)
        _style_ax(ax2, 'Check-in Counter Event Distribution', 'Time (seconds)', 'Event Count')
        self.layout_.addWidget(_make_canvas(fig2))

        # 3. Security screening time distribution
        df_sec = df[df['Event'] == 'Security Screening']
        fig3 = Figure(figsize=(10, 3.5), dpi=100)
        ax3 = fig3.add_subplot(111)
        if len(df_sec) > 0:
            ax3.hist(df_sec['Time'].dropna(), bins=60, color='#F44336', edgecolor=MPL_HIST_EDGE, alpha=0.85)
        _style_ax(ax3, 'Security Screening Events Over Time', 'Time (seconds)', 'Event Count')
        self.layout_.addWidget(_make_canvas(fig3))

        # 4. Boarding events distribution
        df_board = df[df['Event'] == 'Boarding']
        fig4 = Figure(figsize=(10, 3.5), dpi=100)
        ax4 = fig4.add_subplot(111)
        if len(df_board) > 0:
            ax4.hist(df_board['Time'].dropna(), bins=60, color='#4CAF50', edgecolor=MPL_HIST_EDGE, alpha=0.85)
        _style_ax(ax4, 'Boarding Events Over Time', 'Time (seconds)', 'Event Count')
        self.layout_.addWidget(_make_canvas(fig4))

        # 5. Security screening duration (exponential distribution)
        durations = df_sec['Duration'].dropna()
        fig5 = Figure(figsize=(10, 3.5), dpi=100)
        ax5 = fig5.add_subplot(111)
        if len(durations) > 0:
            ax5.hist(durations, bins=50, color='#FF9800', edgecolor=MPL_HIST_EDGE, alpha=0.85, density=True)
            # Overlay theoretical exponential pdf
            x = np.linspace(0, durations.max(), 200)
            mean_dur = durations.mean()
            if mean_dur > 0:
                lam = 1.0 / mean_dur
                ax5.plot(x, lam * np.exp(-lam * x), color='#ffffff', linewidth=1.5,
                         label=f'Exp(lambda={lam:.4f}), mean={mean_dur:.1f}s')
                ax5.legend(facecolor=MPL_AXES_BG, edgecolor=MPL_GRID, labelcolor=MPL_TEXT, fontsize=8)
        _style_ax(ax5, 'Security Screening Duration Distribution', 'Duration (seconds)', 'Density')
        self.layout_.addWidget(_make_canvas(fig5))

        # 6. Per-station event count
        station_counts = df['Station'].dropna().value_counts()
        # Filter out flight departures
        station_counts = station_counts[~station_counts.index.str.contains('Flight', case=False)]
        fig6 = Figure(figsize=(10, 3.5), dpi=100)
        ax6 = fig6.add_subplot(111)
        if len(station_counts) > 0:
            colors = [self._station_chart_color(s) for s in station_counts.index]
            ax6.barh(station_counts.index, station_counts.values, color=colors, edgecolor=MPL_HIST_EDGE)
            ax6.invert_yaxis()
        _style_ax(ax6, 'Events per Station', 'Event Count', '')
        self.layout_.addWidget(_make_canvas(fig6))

        # 7. Passenger type breakdown
        df_arrivals = df[df['Event'] == 'Arrival']
        fig7 = Figure(figsize=(10, 3.5), dpi=100)
        ax7 = fig7.add_subplot(111)
        if len(df_arrivals) > 0:
            type_labels = df_arrivals.apply(
                lambda r: f"{r['Gate Type']}/{r['Seat Type']}", axis=1
            )
            counts = type_labels.value_counts()
            pie_colors = [self._type_chart_color(lbl) for lbl in counts.index]
            wedges, texts, autotexts = ax7.pie(
                counts.values, labels=counts.index, colors=pie_colors,
                autopct='%1.1f%%', startangle=90,
                textprops={'color': MPL_TEXT, 'fontsize': 9}
            )
            for at in autotexts:
                at.set_color('#ffffff')
                at.set_fontsize(8)
        _style_ax(ax7, 'Passenger Type Breakdown', '', '')
        ax7.set_ylabel('')
        ax7.set_xlabel('')
        self.layout_.addWidget(_make_canvas(fig7))

    @staticmethod
    def _station_chart_color(station: str) -> str:
        s = station.lower()
        if 'security' in s:
            return '#F44336'
        if 'regional' in s:
            return '#4CAF50'
        if 'provincial' in s:
            return '#2196F3'
        if 'counter' in s or 'check' in s:
            return '#ffffff'
        return '#888888'

    @staticmethod
    def _type_chart_color(label: str) -> str:
        label = label.lower()
        if 'commuter' in label:
            return '#4CAF50'
        if 'business' in label:
            return '#FFD700'
        if 'provincial' in label:
            return '#2196F3'
        return '#888888'
