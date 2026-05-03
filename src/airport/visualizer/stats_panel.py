from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import List, Tuple

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .data_model import StatsTimeSeries
from .theme import SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SMALL


@dataclass
class StatsSnapshot:
    workers: int
    arrived: int
    boarded: int
    refunded: int
    late: int
    queued: int
    flights_departed: int
    revenue: float
    refund_cost: float
    op_cost: float
    worker_cost: float
    profit: float


class StatsEngine:
    """Computes real-time stats at any playback time using bisect on sorted event lists."""

    def __init__(self, stats: StatsTimeSeries):
        self._stats = stats
        # Pre-extract time keys for bisect (avoids rebuilding each frame)
        self._arrival_times = stats.arrival_times
        self._boarding_times = [t for t, _ in stats.boarding_events]
        self._boarding_costs = [c for _, c in stats.boarding_events]
        self._refund_times = [t for t, _ in stats.refund_events]
        self._refund_costs = [c for _, c in stats.refund_events]
        self._late_times = stats.late_times
        self._queue_times = stats.queue_times
        self._dequeue_times = stats.dequeue_times
        self._departure_times = [t for t, _ in stats.departure_events]
        self._departure_costs = [c for _, c in stats.departure_events]

    HOURLY_RATE = 20

    def compute(self, t: float) -> StatsSnapshot:
        arrived = bisect_right(self._arrival_times, t)

        board_idx = bisect_right(self._boarding_times, t)
        revenue = sum(self._boarding_costs[:board_idx])

        refund_idx = bisect_right(self._refund_times, t)
        refund_cost = sum(self._refund_costs[:refund_idx])

        late = bisect_right(self._late_times, t)
        queued = bisect_right(self._queue_times, t) - bisect_right(self._dequeue_times, t)

        dep_idx = bisect_right(self._departure_times, t)
        op_cost = sum(self._departure_costs[:dep_idx])

        worker_cost = self._stats.worker_count * self.HOURLY_RATE * (t / 3600)

        return StatsSnapshot(
            workers=self._stats.worker_count,
            arrived=arrived,
            boarded=board_idx,
            refunded=refund_idx,
            late=late,
            queued=max(0, queued),
            flights_departed=dep_idx,
            revenue=revenue,
            refund_cost=refund_cost,
            op_cost=op_cost,
            worker_cost=worker_cost,
            profit=revenue - refund_cost - op_cost - worker_cost,
        )


def _fmt_dollar(value: float) -> str:
    return f"${value:,.0f}"


class StatsPanel(QWidget):
    """Two-row real-time stats bar for the playback tab."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {SURFACE.name()}; padding: 4px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(2)

        # Row 1: passenger stats
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        self._lbl_workers = self._make_stat(row1, "Workers")
        self._lbl_arrived = self._make_stat(row1, "Arrived")
        self._lbl_boarded = self._make_stat(row1, "Boarded")
        self._lbl_refunded = self._make_stat(row1, "Refunded")
        self._lbl_late = self._make_stat(row1, "Late")
        self._lbl_queued = self._make_stat(row1, "Queued")
        row1.addStretch()
        layout.addLayout(row1)

        # Row 2: financial stats
        row2 = QHBoxLayout()
        row2.setSpacing(20)
        self._lbl_flights = self._make_stat(row2, "Flights")
        self._lbl_revenue = self._make_stat(row2, "Revenue")
        self._lbl_op_cost = self._make_stat(row2, "Op. Cost")
        self._lbl_worker_cost = self._make_stat(row2, "Workers")
        self._lbl_refund_cost = self._make_stat(row2, "Refunds")
        self._lbl_profit = self._make_stat(row2, "Profit")
        row2.addStretch()
        layout.addLayout(row2)

    def _make_stat(self, layout: QHBoxLayout, label: str) -> QLabel:
        """Create a 'Label: Value' pair and add to the layout. Returns the value label."""
        lbl = QLabel(f"{label}:")
        lbl.setFont(FONT_SMALL)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        layout.addWidget(lbl)

        val = QLabel("0")
        val.setFont(FONT_SMALL)
        val.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
        layout.addWidget(val)
        return val

    def update_stats(self, snap: StatsSnapshot) -> None:
        self._lbl_workers.setText(str(snap.workers))
        self._lbl_arrived.setText(str(snap.arrived))
        self._lbl_boarded.setText(str(snap.boarded))
        self._lbl_refunded.setText(str(snap.refunded))
        self._lbl_late.setText(str(snap.late))
        self._lbl_queued.setText(str(snap.queued))
        self._lbl_flights.setText(str(snap.flights_departed))
        self._lbl_revenue.setText(_fmt_dollar(snap.revenue))
        self._lbl_op_cost.setText(_fmt_dollar(snap.op_cost))
        self._lbl_worker_cost.setText(_fmt_dollar(snap.worker_cost))
        self._lbl_refund_cost.setText(_fmt_dollar(snap.refund_cost))
        self._lbl_profit.setText(_fmt_dollar(snap.profit))
