from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QGraphicsRectItem, QGraphicsSimpleTextItem, QWidget,
)
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QTransform
from PyQt6.QtCore import Qt, QPointF, pyqtSignal

from .data_model import SimulationData, PassengerTimeline, PassengerState, FADE_OUT_BUFFER
from .theme import (
    SCENE_BG, COLOR_ENTRANCE, FONT_LABEL, FONT_SMALL,
    PANEL, HIGHLIGHT, TEXT_PRIMARY, TEXT_SECONDARY,
    COLOR_REFUND, COLOR_LATE, passenger_color,
)
from .scene_drawing import (
    draw_zones, draw_corridor, draw_station_rects, draw_legend,
    SCENE_WIDTH, SCENE_HEIGHT, STATION_W, STATION_H, DOT_RADIUS,
    COL_ENTRANCE, COL_CHECKIN, COL_SECURITY, COL_GATES, CORRIDOR_Y,
)

# Fade timing (sim-seconds)
FADE_IN_DURATION = 15.0


# -----------------------------------------------------------------------
# Path interpolation along a polyline
# -----------------------------------------------------------------------

def _path_length(path: List[QPointF]) -> float:
    total = 0.0
    for i in range(len(path) - 1):
        dx = path[i + 1].x() - path[i].x()
        dy = path[i + 1].y() - path[i].y()
        total += math.hypot(dx, dy)
    return total


def interpolate_along_path(path: List[QPointF], frac: float) -> QPointF:
    """Return the point at *frac* (0-1) along a polyline path."""
    if frac <= 0.0 or len(path) < 2:
        return path[0]
    if frac >= 1.0:
        return path[-1]

    total = _path_length(path)
    if total < 0.01:
        return path[0]

    target = frac * total
    accumulated = 0.0
    for i in range(len(path) - 1):
        dx = path[i + 1].x() - path[i].x()
        dy = path[i + 1].y() - path[i].y()
        seg_len = math.hypot(dx, dy)
        if accumulated + seg_len >= target and seg_len > 0:
            seg_frac = (target - accumulated) / seg_len
            return QPointF(
                path[i].x() + seg_frac * dx,
                path[i].y() + seg_frac * dy,
            )
        accumulated += seg_len
    return path[-1]


# -----------------------------------------------------------------------
# Passenger info popup
# -----------------------------------------------------------------------

class PassengerPopup(QGraphicsRectItem):
    """A small info panel that appears when a passenger dot is clicked."""

    PADDING = 8
    LINE_HEIGHT = 16

    def __init__(self, timeline: PassengerTimeline, pos: QPointF,
                 parent: Optional[QGraphicsRectItem] = None):
        super().__init__(parent)
        self.setZValue(100)

        lines = [
            f"Passenger {timeline.passenger_id}",
            f"Type: {timeline.gate_type} / {timeline.seat_type}",
            f"Bags: {timeline.bags}",
        ]

        # Build text items as children of this rect
        text_items: List[QGraphicsSimpleTextItem] = []
        max_width = 0.0
        for i, line in enumerate(lines):
            txt = QGraphicsSimpleTextItem(line, self)
            txt.setFont(FONT_SMALL)
            txt.setBrush(QBrush(TEXT_PRIMARY if i == 0 else TEXT_SECONDARY))
            txt.setPos(self.PADDING, self.PADDING + i * self.LINE_HEIGHT)
            max_width = max(max_width, txt.boundingRect().width())
            text_items.append(txt)

        # Size the background rect to fit the text
        w = max_width + self.PADDING * 2
        h = self.PADDING * 2 + len(lines) * self.LINE_HEIGHT
        self.setRect(0, 0, w, h)

        bg = QColor(PANEL)
        bg.setAlpha(230)
        self.setBrush(QBrush(bg))
        self.setPen(QPen(HIGHLIGHT, 1))

        # Position: offset to the right and above the dot so it doesn't cover it
        self.setPos(pos.x() + 12, pos.y() - h - 4)


# -----------------------------------------------------------------------
# Scene
# -----------------------------------------------------------------------

class AirportScene(QGraphicsScene):

    passenger_clicked = pyqtSignal(int)

    def __init__(self, data: SimulationData, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data = data

        self.setSceneRect(0, 0, SCENE_WIDTH, SCENE_HEIGHT)
        self.setBackgroundBrush(QBrush(SCENE_BG))

        # station_name -> QPointF center position
        self.station_positions: Dict[str, QPointF] = {}
        # station_name -> which side of corridor: -1 = above, +1 = below
        self._queue_dirs: Dict[str, int] = {}
        # (station_a, station_b) -> list of QPointF waypoints
        self._path_cache: Dict[Tuple[Optional[str], Optional[str]], List[QPointF]] = {}
        # passenger_id -> QGraphicsEllipseItem
        self._dots: Dict[int, QGraphicsEllipseItem] = {}
        self._visible_pids: set = set()
        self._popup: Optional[PassengerPopup] = None

        self._layout_stations()
        draw_zones(self)
        draw_corridor(self)
        draw_station_rects(self)
        draw_legend(self)

    # ===================================================================
    # Station layout
    # ===================================================================

    def _layout_stations(self) -> None:
        cats = self.data.station_categories
        has_checkin = bool(cats.get('business_checkin') or cats.get('coach_checkin'))

        # Entrance: on the corridor
        self.station_positions['Entrance'] = QPointF(COL_ENTRANCE, CORRIDOR_Y)
        self._queue_dirs['Entrance'] = 1  # queue extends down

        # Check-in: alternate above/below corridor, #1 nearest
        if has_checkin:
            checkin = cats.get('business_checkin', []) + cats.get('coach_checkin', [])
            self._place_alternating(checkin, COL_CHECKIN)

        # Security: split each station into business/coach sub-positions
        self._security_stations = set(cats.get('security', []))
        for i, name in enumerate(cats.get('security', [])):
            side = -1 if i % 2 == 0 else 1
            tier = i // 2
            base_y = CORRIDOR_Y + side * (65 + tier * 85)
            self.station_positions[f'{name} B'] = QPointF(COL_SECURITY - 35, base_y)
            self.station_positions[f'{name} C'] = QPointF(COL_SECURITY + 35, base_y)
            self._queue_dirs[f'{name} B'] = side
            self._queue_dirs[f'{name} C'] = side

        # Gates: regional fan above corridor, provincial fan below
        # #1 of each type is closest to the corridor
        regional = cats.get('regional_gate', [])
        provincial = cats.get('provincial_gate', [])
        self._place_fan(regional, COL_GATES, above=True)
        self._place_fan(provincial, COL_GATES, above=False)

    def _place_alternating(self, names: list, x: float) -> None:
        """Place stations alternating above/below the corridor.
        Station 1 is closest to the corridor, higher numbers fan outward."""
        base_gap = 65
        spacing = 85
        for i, name in enumerate(names):
            side = -1 if i % 2 == 0 else 1   # even idx above, odd below
            tier = i // 2                      # how many pairs deep
            y = CORRIDOR_Y + side * (base_gap + tier * spacing)
            self.station_positions[name] = QPointF(x, y)
            self._queue_dirs[name] = side      # station side: queue grows toward corridor

    def _place_fan(self, names: list, x: float, above: bool) -> None:
        """Place stations fanning out from the corridor on one side.
        Station 1 is closest to the corridor."""
        if not names:
            return
        direction = -1 if above else 1
        base_gap = 65
        spacing = 85
        for i, name in enumerate(names):
            y = CORRIDOR_Y + direction * (base_gap + i * spacing)
            self.station_positions[name] = QPointF(x, y)
            self._queue_dirs[name] = direction  # station side: queue grows toward corridor

    def _resolve_station(self, station: Optional[str], seat_type: str) -> Optional[str]:
        """Map CSV station name to visual position. Splits security by seat type."""
        if station in self._security_stations:
            return f'{station} B' if seat_type == 'business' else f'{station} C'
        return station

    # ===================================================================
    # Corridor pathing
    # ===================================================================

    def _build_path(self, station_a: Optional[str], station_b: Optional[str]) -> List[QPointF]:
        """Build a corridor-routed polyline path between two stations."""
        key = (station_a, station_b)
        if key in self._path_cache:
            return self._path_cache[key]

        pos_a = self._station_pos(station_a)
        pos_b = self._station_pos(station_b)

        # Same station or very close: direct
        if abs(pos_a.x() - pos_b.x()) < 5 and abs(pos_a.y() - pos_b.y()) < 5:
            path = [pos_a, pos_b]
        # Same column: go direct vertically
        elif abs(pos_a.x() - pos_b.x()) < 50:
            path = [pos_a, pos_b]
        else:
            # Route through corridor: A -> corridor -> corridor -> B
            path = [pos_a]
            if abs(pos_a.y() - CORRIDOR_Y) > 5:
                path.append(QPointF(pos_a.x(), CORRIDOR_Y))
            path.append(QPointF(pos_b.x(), CORRIDOR_Y))
            if abs(pos_b.y() - CORRIDOR_Y) > 5:
                path.append(pos_b)

        self._path_cache[key] = path
        return path

    def _station_pos(self, station: Optional[str]) -> QPointF:
        if station is None:
            return self.station_positions.get('Entrance', QPointF(COL_ENTRANCE, CORRIDOR_Y))
        return self.station_positions.get(station, QPointF(COL_ENTRANCE, CORRIDOR_Y))

    # ===================================================================
    # Passenger dots
    # ===================================================================

    def _get_or_create_dot(self, pid: int, timeline: PassengerTimeline) -> QGraphicsEllipseItem:
        if pid in self._dots:
            return self._dots[pid]

        color = passenger_color(timeline.gate_type, timeline.seat_type)
        r = DOT_RADIUS + timeline.bags * 1.0
        dot = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        dot.setBrush(QBrush(color))
        dot.setPen(QPen(Qt.PenStyle.NoPen))
        dot.setZValue(10)
        dot.setVisible(False)
        dot.setToolTip(
            f"Passenger {pid}\n"
            f"Type: {timeline.gate_type}/{timeline.seat_type}\n"
            f"Bags: {timeline.bags}"
        )
        dot.setData(0, pid)
        self.addItem(dot)
        self._dots[pid] = dot
        return dot

    def _compute_opacity(self, timeline: PassengerTimeline, t: float) -> float:
        """Fade-in at arrival, fade-out after final event."""
        # Fade in
        if t < timeline.arrival_time + FADE_IN_DURATION:
            elapsed = t - timeline.arrival_time
            return max(0.0, min(1.0, elapsed / FADE_IN_DURATION))
        # Fade out
        dep = timeline.visual_departure_time
        if t > dep:
            elapsed = t - dep
            return max(0.0, 1.0 - elapsed / FADE_OUT_BUFFER)
        return 1.0

    # ===================================================================
    # Click-to-inspect
    # ===================================================================

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.scenePos(), QTransform())

        # Check if the clicked item is a passenger dot
        if item is not None:
            pid = item.data(0)
            if pid is not None and pid in self.data.passengers:
                self.dismiss_popup()
                tl = self.data.passengers[pid]
                self._popup = PassengerPopup(tl, item.pos())
                self.addItem(self._popup)
                self.passenger_clicked.emit(pid)
                return

        # Clicked empty space or non-dot item: dismiss popup
        self.dismiss_popup()
        super().mousePressEvent(event)

    def dismiss_popup(self) -> None:
        if self._popup is not None:
            self.removeItem(self._popup)
            self._popup = None

    # ===================================================================
    # Queue formation
    # ===================================================================

    def _queue_offset(self, station: str, slot: int) -> QPointF:
        """Position for the Nth passenger in a station's queue.

        Layout: two columns extending from the station toward the corridor.
        Slot 0 (front/FIFO head) is right at the station rect edge.
        Higher slots extend toward the corridor (where new arrivals come from).

        For a station ABOVE the corridor (queue_dir = -1):
          slot 0 is just below the station (toward corridor)
          slot N is further below (closer to corridor)

        For a station BELOW the corridor (queue_dir = +1):
          slot 0 is just above the station (toward corridor)
          slot N is further above (closer to corridor)
        """
        queue_dir = self._queue_dirs.get(station, 1)

        # Two columns so queues don't get absurdly long
        col = slot % 2
        row = slot // 2

        spacing = DOT_RADIUS * 2.5
        x = (col - 0.5) * spacing  # two columns centered on station

        # toward_corridor is the direction from station toward CORRIDOR_Y
        toward_corridor = -queue_dir  # if station is above (dir=-1), toward corridor is +y
        y = toward_corridor * (STATION_H / 2 + 4 + row * spacing)

        return QPointF(x, y)

    # ===================================================================
    # Main update (called every frame)
    # ===================================================================

    def update_to_time(self, t: float) -> int:
        """Move all passenger dots to their positions at time t.
        Returns the number of active passengers."""
        active = self.data.get_active_passengers(t)

        # --- Pass 1: collect stationary passengers per station for FIFO ordering ---
        station_pax: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        transit_pax: Dict[int, PassengerState] = {}

        for pid, state in active.items():
            tl = self.data.passengers[pid]
            if state.fraction <= 0.01 or state.fraction >= 0.99:
                at_station = state.current_station if state.fraction <= 0.01 else state.next_station
                if at_station is None:
                    at_station = 'Entrance'
                at_station = self._resolve_station(at_station, tl.seat_type)
                station_pax[at_station].append((pid, state.station_arrival_time))
            else:
                transit_pax[pid] = state

        # Sort each station's passengers by station_arrival_time (FIFO: earliest = front)
        station_slots: Dict[str, Dict[int, int]] = {}
        for station, pax_list in station_pax.items():
            pax_list.sort(key=lambda x: x[1])
            station_slots[station] = {pid: slot for slot, (pid, _) in enumerate(pax_list)}

        # --- Pass 2: position and color all dots ---
        for pid, state in active.items():
            tl = self.data.passengers[pid]
            dot = self._get_or_create_dot(pid, tl)

            if pid in transit_pax:
                ts = transit_pax[pid]
                src = self._resolve_station(ts.current_station, tl.seat_type)
                dst = self._resolve_station(ts.next_station, tl.seat_type)
                path = self._build_path(src, dst)
                pos = interpolate_along_path(path, ts.fraction)
            else:
                for station, slot_map in station_slots.items():
                    if pid in slot_map:
                        base = self._station_pos(station)
                        offset = self._queue_offset(station, slot_map[pid])
                        pos = QPointF(base.x() + offset.x(), base.y() + offset.y())
                        break
                else:
                    pos = self._station_pos(None)

            # Recolor dot based on outcome event
            if state.event == 'Refund':
                dot.setBrush(QBrush(COLOR_REFUND))
            elif state.event == 'Late':
                dot.setBrush(QBrush(COLOR_LATE))
            else:
                dot.setBrush(QBrush(passenger_color(tl.gate_type, tl.seat_type)))

            opacity = self._compute_opacity(tl, t)
            dot.setPos(pos)
            dot.setOpacity(opacity)
            dot.setVisible(opacity > 0.01)
            self._visible_pids.add(pid)

        # Hide passengers no longer active
        gone = self._visible_pids - set(active.keys())
        for pid in gone:
            if pid in self._dots:
                self._dots[pid].setVisible(False)
        self._visible_pids -= gone

        return len(active)


# -----------------------------------------------------------------------
# View
# -----------------------------------------------------------------------

class AirportView(QGraphicsView):
    """QGraphicsView wrapper with antialiasing and zoom-to-fit."""

    def __init__(self, scene: AirportScene, parent: Optional[QWidget] = None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("border: none; background: transparent;")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
