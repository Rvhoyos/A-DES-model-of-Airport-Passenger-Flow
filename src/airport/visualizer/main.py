from __future__ import annotations

import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QStatusBar,
)
from .theme import apply_dark_theme
from .data_model import SimulationData
from .airport_scene import AirportScene, AirportView
from .playback_controls import PlaybackEngine, PlaybackControls
from .histogram_tab import HistogramTab
from .stats_panel import StatsEngine, StatsPanel
from .station_stats import StationStatsEngine
from .flight_board import FlightSchedule, FlightBoardPanel


class MainWindow(QMainWindow):

    def __init__(self, data: SimulationData):
        super().__init__()
        self.data = data

        self.setWindowTitle('Smiths Falls Airport DES - Simulation Playback')
        self.resize(1400, 900)

        # -- Playback engine --
        self.engine = PlaybackEngine(data.min_time, data.max_time, self)

        # -- Tab widget --
        tabs = QTabWidget()

        # Tab 1: Playback
        playback_widget = QWidget()
        playback_layout = QVBoxLayout(playback_widget)
        playback_layout.setContentsMargins(0, 0, 0, 0)
        playback_layout.setSpacing(0)

        self.scene = AirportScene(data)
        self.view = AirportView(self.scene)
        self.station_stats_engine = StationStatsEngine(data)
        self.scene.set_station_engine(self.station_stats_engine)
        self.stats_engine = StatsEngine(data.stats)
        self.stats_panel = StatsPanel()
        self.flight_schedule = FlightSchedule()
        self.flight_board = FlightBoardPanel(self.flight_schedule)
        self.controls = PlaybackControls(self.engine, data.day_boundaries)

        playback_layout.addWidget(self.view, stretch=1)
        playback_layout.addWidget(self.flight_board)
        playback_layout.addWidget(self.stats_panel)
        playback_layout.addWidget(self.controls)
        tabs.addTab(playback_widget, 'Playback')

        # Tab 2: Analytics
        self.histograms = HistogramTab(data)
        tabs.addTab(self.histograms, 'Analytics')

        self.setCentralWidget(tabs)

        # -- Status bar --
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(
            f'{len(data.passengers)} passengers | '
            f'{len(data.day_boundaries)} sim-days | '
            f'Time: {data.min_time:.0f}s - {data.max_time:.0f}s'
        )

        # -- Wire signals --
        self.engine.time_changed.connect(self._on_time)
        self.scene.passenger_clicked.connect(self._on_passenger_clicked)
        self.scene.station_clicked.connect(self._on_station_clicked)

        # Initial render at start time
        self._on_time(data.min_time)

    def _on_time(self, t: float) -> None:
        active = self.scene.update_to_time(t)
        self.controls.set_active_count(active)
        self.stats_panel.update_stats(self.stats_engine.compute(t))
        self.flight_board.update_flights(t)
        # Dismiss popup when playback is running (user hit play)
        if self.engine.playing:
            self.scene.dismiss_popup()

    def _on_passenger_clicked(self, pid: int) -> None:
        self.engine.pause()
        self.controls.btn_play.setText('Play')

    def _on_station_clicked(self, name: str) -> None:
        self.engine.pause()
        self.controls.btn_play.setText('Play')

    def keyPressEvent(self, event) -> None:
        # Forward keyboard events to controls for play/pause/seek
        self.controls.keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)

    data = SimulationData.from_directory()
    window = MainWindow(data)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
