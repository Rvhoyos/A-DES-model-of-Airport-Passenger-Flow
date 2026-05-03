from __future__ import annotations

import math
from typing import List

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QSlider, QLabel,
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal

from .data_model import DayBoundary
from .theme import FONT_SMALL, FONT_LABEL


def _format_sim_time(t: float) -> str:
    """Convert simulation seconds to 'Day N, HH:MM:SS'."""
    day = int(t // 86400) + 1
    remainder = t % 86400
    h = int(remainder // 3600)
    m = int((remainder % 3600) // 60)
    s = int(remainder % 60)
    return f"Day {day}, {h:02d}:{m:02d}:{s:02d}"


class PlaybackEngine(QObject):
    """Drives simulation time forward at a configurable speed."""

    time_changed = pyqtSignal(float)

    def __init__(self, min_time: float, max_time: float, parent: QObject = None):
        super().__init__(parent)
        self.min_time = min_time
        self.max_time = max_time
        self.current_time = min_time
        self.speed = 500.0      # sim-seconds per real-second
        self.playing = False

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 fps
        self._timer.timeout.connect(self._tick)

    def _tick(self) -> None:
        # 16ms timer interval * speed = sim-seconds per tick
        dt_sim = 0.016 * self.speed
        self.current_time = min(self.current_time + dt_sim, self.max_time)
        self.time_changed.emit(self.current_time)
        if self.current_time >= self.max_time:
            self.pause()

    def play(self) -> None:
        self.playing = True
        self._timer.start()

    def pause(self) -> None:
        self.playing = False
        self._timer.stop()

    def toggle(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def seek_to(self, t: float) -> None:
        self.current_time = max(self.min_time, min(t, self.max_time))
        self.time_changed.emit(self.current_time)

    def set_speed(self, speed: float) -> None:
        self.speed = speed


class PlaybackControls(QWidget):
    """Control bar: play/pause, speed slider, timeline scrubber, time label."""

    def __init__(
        self,
        engine: PlaybackEngine,
        day_boundaries: List[DayBoundary],
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.engine = engine
        self.day_boundaries = day_boundaries
        self._updating_slider = False

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)

        # Play / Pause
        self.btn_play = QPushButton('Play')
        self.btn_play.setFixedWidth(70)
        layout.addWidget(self.btn_play)

        # Speed controls
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(0)
        self.speed_label = QLabel('500x')
        self.speed_label.setFont(FONT_LABEL)
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 400)  # maps to 1x - 10000x logarithmic
        self.speed_slider.setValue(self._speed_to_slider(500.0))
        self.speed_slider.setFixedWidth(120)

        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.speed_slider)
        layout.addLayout(speed_layout)

        # Timeline scrubber
        timeline_layout = QVBoxLayout()
        timeline_layout.setSpacing(0)

        self.time_label = QLabel(_format_sim_time(self.engine.min_time))
        self.time_label.setFont(FONT_SMALL)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(
            int(self.engine.min_time),
            int(self.engine.max_time),
        )
        self.timeline_slider.setValue(int(self.engine.min_time))

        timeline_layout.addWidget(self.time_label)
        timeline_layout.addWidget(self.timeline_slider)
        layout.addLayout(timeline_layout, stretch=1)

        # Active count label
        self.active_label = QLabel('0 active')
        self.active_label.setFont(FONT_LABEL)
        self.active_label.setFixedWidth(80)
        self.active_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.active_label)

    def _connect_signals(self) -> None:
        self.btn_play.clicked.connect(self._on_play_pause)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self.timeline_slider.sliderPressed.connect(self._on_scrub_start)
        self.timeline_slider.sliderReleased.connect(self._on_scrub_end)
        self.timeline_slider.valueChanged.connect(self._on_slider_moved)
        self.engine.time_changed.connect(self._on_time_changed)

    # -- Slot handlers ----------------------------------------------------

    def _on_play_pause(self) -> None:
        self.engine.toggle()
        self.btn_play.setText('Pause' if self.engine.playing else 'Play')

    def _on_speed_changed(self, val: int) -> None:
        speed = self._slider_to_speed(val)
        self.engine.set_speed(speed)
        if speed >= 1000:
            self.speed_label.setText(f'{speed:.0f}x')
        elif speed >= 1:
            self.speed_label.setText(f'{speed:.0f}x')
        else:
            self.speed_label.setText(f'{speed:.1f}x')

    def _on_scrub_start(self) -> None:
        self._was_playing = self.engine.playing
        self.engine.pause()
        self.btn_play.setText('Play')

    def _on_scrub_end(self) -> None:
        if getattr(self, '_was_playing', False):
            self.engine.play()
            self.btn_play.setText('Pause')

    def _on_slider_moved(self, val: int) -> None:
        if not self._updating_slider:
            self.engine.seek_to(float(val))

    def _on_time_changed(self, t: float) -> None:
        self._updating_slider = True
        self.timeline_slider.setValue(int(t))
        self._updating_slider = False
        self.time_label.setText(_format_sim_time(t))

    def set_active_count(self, count: int) -> None:
        self.active_label.setText(f'{count} active')

    # -- Speed <-> slider mapping (logarithmic) ---------------------------

    @staticmethod
    def _speed_to_slider(speed: float) -> int:
        # log scale: 1x -> 0, 10000x -> 400
        return int(100 * math.log10(max(1, speed)))

    @staticmethod
    def _slider_to_speed(val: int) -> float:
        return 10.0 ** (val / 100.0)

    # -- Keyboard shortcuts -----------------------------------------------

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Space:
            self._on_play_pause()
        elif key == Qt.Key.Key_Right:
            self.engine.seek_to(self.engine.current_time + 100 * self.engine.speed / 500)
        elif key == Qt.Key.Key_Left:
            self.engine.seek_to(self.engine.current_time - 100 * self.engine.speed / 500)
        else:
            super().keyPressEvent(event)
