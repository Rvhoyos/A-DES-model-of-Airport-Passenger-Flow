from __future__ import annotations

import math
from bisect import bisect_right
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QGraphicsRectItem, QGraphicsSimpleTextItem, QWidget,
)
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QTransform
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal

from .data_model import SimulationData, PassengerTimeline, PassengerState, FADE_OUT_BUFFER
from .station_stats import StationStatsEngine, StationMetrics, CategoryMetrics, EntranceMetrics
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
from .flight_board import (
    REGIONAL_FIRST, REGIONAL_INTERVAL, PROVINCIAL_FIRST, PROVINCIAL_INTERVAL, DAY,
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
# Station info popup
# -----------------------------------------------------------------------

class StationPopup(QGraphicsRectItem):
    """Info panel showing per-station and category stats when a station is clicked."""

    PADDING = 10
    LINE_HEIGHT = 16
    COL_GAP = 24

    def __init__(self, station: StationMetrics, category: CategoryMetrics,
                 pos: QPointF, parent: Optional[QGraphicsRectItem] = None):
        super().__init__(parent)
        self.setZValue(100)

        left_lines = [
            station.station_name,
            f"Served: {station.passengers_served}",
            f"Avg service: {station.avg_service_time:.0f}s",
            f"Avg wait: {station.avg_wait_time:.0f}s",
            f"Utilization: {station.utilization:.0%}" if station.utilization > 0
            else f"Throughput: {station.throughput:.1f}/hr",
            f"Max wait: {station.max_wait_time:.0f}s",
        ]

        cat_label = category.category.replace('_', ' ').title()
        right_lines = [
            f"All {cat_label}",
            f"Served: {category.total_served}",
            f"Avg service: {category.avg_service_time:.0f}s",
            f"Avg wait: {category.avg_wait_time:.0f}s",
            f"Utilization: {category.combined_utilization:.0%}" if category.combined_utilization > 0
            else f"Avg tput: {category.avg_throughput:.1f}/hr",
            f"Total tput: {category.throughput:.1f}/hr",
            f"Stations: {category.station_count}",
        ]

        # Render left column
        left_items: List[QGraphicsSimpleTextItem] = []
        left_max_w = 0.0
        for i, line in enumerate(left_lines):
            txt = QGraphicsSimpleTextItem(line, self)
            txt.setFont(FONT_SMALL)
            txt.setBrush(QBrush(TEXT_PRIMARY if i == 0 else TEXT_SECONDARY))
            txt.setPos(self.PADDING, self.PADDING + i * self.LINE_HEIGHT)
            left_max_w = max(left_max_w, txt.boundingRect().width())
            left_items.append(txt)

        # Render right column
        right_x = self.PADDING + left_max_w + self.COL_GAP
        right_max_w = 0.0
        for i, line in enumerate(right_lines):
            txt = QGraphicsSimpleTextItem(line, self)
            txt.setFont(FONT_SMALL)
            txt.setBrush(QBrush(TEXT_PRIMARY if i == 0 else TEXT_SECONDARY))
            txt.setPos(right_x, self.PADDING + i * self.LINE_HEIGHT)
            right_max_w = max(right_max_w, txt.boundingRect().width())

        # Size background
        w = right_x + right_max_w + self.PADDING
        h = self.PADDING * 2 + max(len(left_lines), len(right_lines)) * self.LINE_HEIGHT
        self.setRect(0, 0, w, h)

        bg = QColor(PANEL)
        bg.setAlpha(230)
        self.setBrush(QBrush(bg))
        self.setPen(QPen(HIGHLIGHT, 1))

        self.setPos(pos.x() + 12, pos.y() - h - 4)


# -----------------------------------------------------------------------
# Entrance info popup
# -----------------------------------------------------------------------

class EntrancePopup(QGraphicsRectItem):
    """Info panel showing arrival stats when the Entrance is clicked."""

    PADDING = 10
    LINE_HEIGHT = 16

    def __init__(self, metrics: EntranceMetrics, pos: QPointF,
                 parent: Optional[QGraphicsRectItem] = None):
        super().__init__(parent)
        self.setZValue(100)

        total = metrics.total_arrived or 1  # avoid div by zero for percentages
        lines = [
            "Entrance",
            f"Arrived: {metrics.total_arrived}",
            f"Rate: {metrics.arrival_rate:.1f}/hr",
            f"Regional: {metrics.regional_count} ({metrics.regional_count/total:.0%})",
            f"Provincial: {metrics.provincial_count} ({metrics.provincial_count/total:.0%})",
            f"Coach: {metrics.coach_count} | Business: {metrics.business_count}",
            f"Avg bags: {metrics.avg_bags:.1f}",
        ]

        max_width = 0.0
        for i, line in enumerate(lines):
            txt = QGraphicsSimpleTextItem(line, self)
            txt.setFont(FONT_SMALL)
            txt.setBrush(QBrush(TEXT_PRIMARY if i == 0 else TEXT_SECONDARY))
            txt.setPos(self.PADDING, self.PADDING + i * self.LINE_HEIGHT)
            max_width = max(max_width, txt.boundingRect().width())

        w = max_width + self.PADDING * 2
        h = self.PADDING * 2 + len(lines) * self.LINE_HEIGHT
        self.setRect(0, 0, w, h)

        bg = QColor(PANEL)
        bg.setAlpha(230)
        self.setBrush(QBrush(bg))
        self.setPen(QPen(HIGHLIGHT, 1))

        self.setPos(pos.x() + 12, pos.y() - h - 4)


# -----------------------------------------------------------------------
# Scene
# -----------------------------------------------------------------------

class AirportScene(QGraphicsScene):

    passenger_clicked = pyqtSignal(int)
    station_clicked = pyqtSignal(str)

    def __init__(self, data: SimulationData, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data = data
        self._station_engine: Optional[StationStatsEngine] = None
        self._current_time: float = 0.0

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
        # gate_name -> (fill_rect, bar_x, bar_y, bar_w, bar_h) - populated by draw_station_rects
        self._capacity_bars: Dict[str, tuple] = {}
        # gate_name -> QGraphicsSimpleTextItem for departure countdown
        self._departure_timers: Dict[str, QGraphicsSimpleTextItem] = {}

        self._layout_stations()
        self.setSceneRect(self._compute_scene_rect())
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

        # Security: split each station into provincial/regional sub-positions
        self._security_stations = set(cats.get('security', []))
        for i, name in enumerate(cats.get('security', [])):
            side = -1 if i % 2 == 0 else 1
            tier = i // 2
            base_y = CORRIDOR_Y + side * (65 + tier * 85)
            self.station_positions[f'{name} P'] = QPointF(COL_SECURITY - 35, base_y)
            self.station_positions[f'{name} R'] = QPointF(COL_SECURITY + 35, base_y)
            self._queue_dirs[f'{name} P'] = side
            self._queue_dirs[f'{name} R'] = side

        # Gates: regional fan above corridor, provincial fan below
        # #1 of each type is closest to the corridor
        regional = cats.get('regional_gate', [])
        provincial = cats.get('provincial_gate', [])
        self._place_fan(regional, COL_GATES, above=True)
        self._place_fan(provincial, COL_GATES, above=False)

    def _compute_scene_rect(self) -> QRectF:
        """Compute scene rect from station positions so all content is visible."""
        if not self.station_positions:
            return QRectF(0, 0, SCENE_WIDTH, SCENE_HEIGHT)

        xs = [p.x() for p in self.station_positions.values()]
        ys = [p.y() for p in self.station_positions.values()]
        pad = 120
        min_x = min(xs) - pad
        max_x = max(xs) + pad
        min_y = min(ys) - pad
        max_y = max(ys) + pad
        w = max(max_x - min_x, SCENE_WIDTH)
        h = max(max_y - min_y, SCENE_HEIGHT)
        # Center the rect around the computed bounds
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        return QRectF(cx - w / 2, cy - h / 2, w, h)

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

    def _resolve_station(self, station: Optional[str], gate_type: str) -> Optional[str]:
        """Map CSV station name to visual position. Splits security by gate type."""
        if station in self._security_stations:
            return f'{station} P' if gate_type == 'provincial' else f'{station} R'
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

        if item is not None:
            # Check passenger dot (data key 0 = passenger ID)
            pid = item.data(0)
            if pid is not None and pid in self.data.passengers:
                self.dismiss_popup()
                tl = self.data.passengers[pid]
                self._popup = PassengerPopup(tl, item.pos())
                self.addItem(self._popup)
                self.passenger_clicked.emit(pid)
                return

            # Check station rect (data key 1 = station name)
            station_name = item.data(1)
            if station_name is not None and self._station_engine is not None:
                self.dismiss_popup()
                if station_name == 'Entrance':
                    metrics = self._station_engine.compute_entrance(self._current_time)
                    self._popup = EntrancePopup(metrics, event.scenePos())
                else:
                    station_metrics = self._station_engine.compute_station(
                        station_name, self._current_time)
                    category_metrics = self._station_engine.compute_category(
                        station_metrics.category, self._current_time)
                    self._popup = StationPopup(
                        station_metrics, category_metrics, event.scenePos())
                self.addItem(self._popup)
                self.station_clicked.emit(station_name)
                return

        # Clicked empty space: dismiss popup
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

    def _overflow_offset(self, station: str, slot: int) -> QPointF:
        """Position for Nth overflow-queue passenger - opposite side from boarding queue."""
        queue_dir = self._queue_dirs.get(station, 1)
        col = slot % 2
        row = slot // 2
        spacing = DOT_RADIUS * 2.5
        x = (col - 0.5) * spacing
        # Away from corridor (opposite of _queue_offset)
        y = queue_dir * (STATION_H / 2 + 4 + row * spacing)
        return QPointF(x, y)

    # ===================================================================
    # Main update (called every frame)
    # ===================================================================

    def set_station_engine(self, engine: StationStatsEngine) -> None:
        """Set the station stats engine for click-to-inspect popups."""
        self._station_engine = engine

    def update_to_time(self, t: float) -> int:
        """Move all passenger dots to their positions at time t.
        Returns the number of active passengers."""
        self._current_time = t
        active = self.data.get_active_passengers(t)

        # --- Pass 1: collect stationary passengers per station for FIFO ordering ---
        station_pax: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        overflow_pax: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        transit_pax: Dict[int, PassengerState] = {}

        for pid, state in active.items():
            tl = self.data.passengers[pid]
            # Queue events have no duration, so fraction is mid-range - force to overflow
            if state.event == 'Queue':
                at_station = self._resolve_station(state.current_station or 'Entrance', tl.gate_type)
                overflow_pax[at_station].append((pid, state.station_arrival_time))
            elif state.fraction <= 0.01 or state.fraction >= 0.99:
                at_station = state.current_station if state.fraction <= 0.01 else state.next_station
                if at_station is None:
                    at_station = 'Entrance'
                at_station = self._resolve_station(at_station, tl.gate_type)
                station_pax[at_station].append((pid, state.station_arrival_time))
            else:
                transit_pax[pid] = state

        # Sort each group by station_arrival_time (FIFO: earliest = front)
        station_slots: Dict[str, Dict[int, int]] = {}
        for station, pax_list in station_pax.items():
            pax_list.sort(key=lambda x: x[1])
            station_slots[station] = {pid: slot for slot, (pid, _) in enumerate(pax_list)}
        overflow_slots: Dict[str, Dict[int, int]] = {}
        for station, pax_list in overflow_pax.items():
            pax_list.sort(key=lambda x: x[1])
            overflow_slots[station] = {pid: slot for slot, (pid, _) in enumerate(pax_list)}

        # --- Pass 2: position and color all dots ---
        for pid, state in active.items():
            tl = self.data.passengers[pid]
            dot = self._get_or_create_dot(pid, tl)

            if pid in transit_pax:
                ts = transit_pax[pid]
                src = self._resolve_station(ts.current_station, tl.gate_type)
                dst = self._resolve_station(ts.next_station, tl.gate_type)
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
                    for station, slot_map in overflow_slots.items():
                        if pid in slot_map:
                            base = self._station_pos(station)
                            offset = self._overflow_offset(station, slot_map[pid])
                            pos = QPointF(base.x() + offset.x(), base.y() + offset.y())
                            break
                    else:
                        pos = self._station_pos(None)

            # Recolor dot based on outcome event
            if state.event == 'Refund':
                dot.setBrush(QBrush(COLOR_REFUND))
            elif state.event == 'Late':
                dot.setBrush(QBrush(COLOR_LATE))
            elif state.event == 'Queue':
                c = QColor(passenger_color(tl.gate_type, tl.seat_type))
                c.setAlpha(120)
                dot.setBrush(QBrush(c))
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

        # --- Update capacity bars and departure timers ---
        self._update_capacity_bars(t)
        self._update_departure_timers(t)

        return len(active)

    def _update_capacity_bars(self, t: float) -> None:
        """Set each gate's capacity bar fill based on boardings since last departure."""
        gate_bt = self.data.stats.gate_boarding_times
        for gate, (fill, bx, by, bw, bh) in self._capacity_bars.items():
            times = gate_bt.get(gate, [])
            if not times:
                fill.setRect(bx, by + bh, bw, 0)
                continue
            prev_dep = _prev_departure(gate, t)
            count = bisect_right(times, t) - bisect_right(times, prev_dep)
            cap = 40 if 'regional' in gate.lower() else 180
            frac = min(1.0, count / cap) if cap > 0 else 0
            fill_h = frac * bh
            fill.setRect(bx, by + bh - fill_h, bw, fill_h)

    def _update_departure_timers(self, t: float) -> None:
        """Update countdown text next to each gate's capacity bar."""
        for gate, text_item in self._departure_timers.items():
            countdown = _next_departure(gate, t) - t
            if countdown < 60:
                text_item.setText(f"{int(countdown)}s")
                text_item.setBrush(QBrush(QColor('#FF4444')))
            elif countdown < 300:
                text_item.setText(f"{int(countdown // 60)}m")
                text_item.setBrush(QBrush(QColor('#FFD700')))
            elif countdown < 3600:
                text_item.setText(f"{int(countdown // 60)}m")
                text_item.setBrush(QBrush(QColor('#8a8a9a')))
            else:
                h = int(countdown // 3600)
                m = int((countdown % 3600) // 60)
                text_item.setText(f"{h}h{m:02d}")
                text_item.setBrush(QBrush(QColor('#8a8a9a')))


def _schedule_params(station: str) -> tuple:
    """Return (first_departure_offset, interval) for the given gate type."""
    if 'regional' in station.lower():
        return REGIONAL_FIRST, REGIONAL_INTERVAL
    return PROVINCIAL_FIRST, PROVINCIAL_INTERVAL


def _next_departure(station: str, t: float) -> float:
    """Return the next departure time after t for this gate type."""
    first, interval = _schedule_params(station)
    day_start = (int(t) // DAY) * DAY
    day_offset = t - day_start
    if day_offset < first:
        return day_start + first
    n = int((day_offset - first) // interval) + 1
    return day_start + first + n * interval


def _prev_departure(station: str, t: float) -> float:
    """Return the most recent departure time at or before t for this gate type."""
    first, interval = _schedule_params(station)
    day_start = (int(t) // DAY) * DAY
    day_offset = t - day_start
    if day_offset < first:
        prev_day = day_start - DAY
        return prev_day + first + ((DAY - first) // interval) * interval if day_start > 0 else 0
    n = int((day_offset - first) // interval)
    return day_start + first + n * interval


# -----------------------------------------------------------------------
# View
# -----------------------------------------------------------------------

class AirportView(QGraphicsView):
    """QGraphicsView with zoom (scroll wheel) and pan (middle-click or Ctrl+left drag)."""

    ZOOM_FACTOR = 1.15

    def __init__(self, scene: AirportScene, parent: Optional[QWidget] = None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet("border: none; background: transparent;")
        self._zoom_level = 0
        self._panning = False
        self._pan_start = QPointF()

    def wheelEvent(self, event) -> None:
        if event.angleDelta().y() > 0:
            self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)
            self._zoom_level += 1
        else:
            self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)
            self._zoom_level -= 1

    def mousePressEvent(self, event) -> None:
        if (event.button() == Qt.MouseButton.MiddleButton or
                (event.button() == Qt.MouseButton.LeftButton and
                 event.modifiers() & Qt.KeyboardModifier.ControlModifier)):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._zoom_level == 0:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mouseDoubleClickEvent(self, event) -> None:
        """Double-click to reset zoom to fit-all."""
        self._zoom_level = 0
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
