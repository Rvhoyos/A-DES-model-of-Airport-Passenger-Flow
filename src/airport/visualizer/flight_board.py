"""Flight departures board: schedule engine and display panel.

FlightSchedule computes upcoming departures from deterministic rules.
FlightBoardPanel renders them as a compact countdown bar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame

from .theme import (
    SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SMALL,
    COLOR_REGIONAL_GATE, COLOR_PROVINCIAL_GATE, COLOR_LATE,
)

# Schedule constants (seconds)
REGIONAL_FIRST = 1800       # 00:30
REGIONAL_INTERVAL = 3600    # hourly
PROVINCIAL_FIRST = 0        # 00:00
PROVINCIAL_INTERVAL = 21600 # every 6 hours
DAY = 86400


# -----------------------------------------------------------------------
# Engine
# -----------------------------------------------------------------------

@dataclass
class UpcomingFlight:
    departure_time: float
    countdown: float        # seconds until departure (negative = just departed)
    time_of_day: str        # "HH:MM"


@dataclass
class FlightBoardSnapshot:
    regional: List[UpcomingFlight] = field(default_factory=list)
    provincial: List[UpcomingFlight] = field(default_factory=list)


class FlightSchedule:
    """Pure computation: next N departures per gate type at any playback time."""

    def __init__(self, count: int = 2):
        self._count = count

    def compute(self, t: float) -> FlightBoardSnapshot:
        return FlightBoardSnapshot(
            regional=self._next_departures(t, REGIONAL_FIRST, REGIONAL_INTERVAL),
            provincial=self._next_departures(t, PROVINCIAL_FIRST, PROVINCIAL_INTERVAL),
        )

    def _next_departures(self, t: float, first: int, interval: int) -> List[UpcomingFlight]:
        day_start = (int(t) // DAY) * DAY
        day_offset = t - day_start

        if day_offset < first:
            next_dep = day_start + first
        else:
            slots_passed = int((day_offset - first) // interval) + 1
            next_dep = day_start + first + slots_passed * interval

        results = []
        for i in range(self._count):
            dep = next_dep + i * interval
            countdown = dep - t
            hh = int((dep % DAY) // 3600)
            mm = int((dep % 3600) // 60)
            results.append(UpcomingFlight(
                departure_time=dep,
                countdown=countdown,
                time_of_day=f"{hh:02d}:{mm:02d}",
            ))
        return results


# -----------------------------------------------------------------------
# Display
# -----------------------------------------------------------------------

def _fmt_countdown(seconds: float) -> str:
    if seconds < 0:
        return "NOW"
    s = int(seconds)
    if s >= 3600:
        return f"{s // 3600}h {(s % 3600) // 60}m"
    if s >= 60:
        return f"{s // 60}m {s % 60}s"
    return f"{s}s"


class FlightBoardPanel(QWidget):
    """Compact departures bar showing upcoming flights with countdowns."""

    def __init__(self, schedule: FlightSchedule, parent: QWidget = None):
        super().__init__(parent)
        self._schedule = schedule
        self.setStyleSheet(f"background: {SURFACE.name()}; padding: 2px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Header
        header = QLabel("DEPARTURES")
        header.setFont(FONT_SMALL)
        header.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        layout.addWidget(header)

        self._add_separator(layout)

        # Regional section
        self._regional_dot = self._make_dot(COLOR_REGIONAL_GATE.name())
        layout.addWidget(self._regional_dot)
        reg_label = QLabel("Regional")
        reg_label.setFont(FONT_SMALL)
        reg_label.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        layout.addWidget(reg_label)
        self._regional_labels: List[QLabel] = []
        for _ in range(2):
            lbl = QLabel("")
            lbl.setFont(FONT_SMALL)
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
            layout.addWidget(lbl)
            self._regional_labels.append(lbl)

        self._add_separator(layout)

        # Provincial section
        self._provincial_dot = self._make_dot(COLOR_PROVINCIAL_GATE.name())
        layout.addWidget(self._provincial_dot)
        prov_label = QLabel("Provincial")
        prov_label.setFont(FONT_SMALL)
        prov_label.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        layout.addWidget(prov_label)
        self._provincial_labels: List[QLabel] = []
        for _ in range(2):
            lbl = QLabel("")
            lbl.setFont(FONT_SMALL)
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
            layout.addWidget(lbl)
            self._provincial_labels.append(lbl)

        layout.addStretch()

    def update_flights(self, t: float) -> None:
        snap = self._schedule.compute(t)
        self._update_section(self._regional_labels, snap.regional)
        self._update_section(self._provincial_labels, snap.provincial)

    def _update_section(self, labels: List[QLabel], flights: List[UpcomingFlight]) -> None:
        for i, lbl in enumerate(labels):
            if i < len(flights):
                f = flights[i]
                countdown = _fmt_countdown(f.countdown)
                lbl.setText(f"{f.time_of_day} ({countdown})")
                if f.countdown < 60:
                    lbl.setStyleSheet(f"color: {COLOR_LATE.name()};")
                elif f.countdown < 300:
                    lbl.setStyleSheet(f"color: #FFD700;")
                else:
                    lbl.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
            else:
                lbl.setText("")

    @staticmethod
    def _make_dot(color: str) -> QLabel:
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background: {color}; border-radius: 4px; padding: 0px;"
        )
        return dot

    @staticmethod
    def _add_separator(layout: QHBoxLayout) -> None:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #0f3460;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)
