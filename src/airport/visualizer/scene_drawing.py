"""PyQt6 drawing boilerplate for the airport scene.

These functions render the static visual elements (zone panels, corridor,
station rectangles, legend). They are separated from AirportScene to keep
the logic file focused on layout, pathing, and per-frame updates.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsSimpleTextItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPathItem,
)
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath
from PyQt6.QtCore import Qt, QRectF

from .theme import (
    STATION_FILL, TEXT_PRIMARY, TEXT_SECONDARY,
    FONT_LABEL, station_border_color,
)

if TYPE_CHECKING:
    from .airport_scene import AirportScene

# -----------------------------------------------------------------------
# Layout constants (shared with airport_scene.py, defined here to avoid
# circular imports since airport_scene imports drawing functions from us)
# -----------------------------------------------------------------------
SCENE_WIDTH = 1200
SCENE_HEIGHT = 700
STATION_W = 130
STATION_W_SMALL = 60
STATION_H = 40
DOT_RADIUS = 4

COL_ENTRANCE = 90
COL_CHECKIN = 310
COL_SECURITY = 540
COL_GATES = 900

CORRIDOR_Y = SCENE_HEIGHT / 2

ZONE_PAD_X = 40
ZONE_PAD_Y = 30


def draw_zones(scene: AirportScene) -> None:
    """Draw translucent background panels for each airport area."""
    cats = scene.data.station_categories
    has_checkin = bool(cats.get('business_checkin') or cats.get('coach_checkin'))

    zones = []

    zones.append(('ARRIVALS', COL_ENTRANCE, QColor(136, 136, 136, 18)))

    if has_checkin:
        zones.append(('CHECK-IN', COL_CHECKIN, QColor(255, 255, 255, 12)))

    if cats.get('security'):
        zones.append(('SECURITY', COL_SECURITY, QColor(244, 67, 54, 14)))

    if cats.get('regional_gate') or cats.get('provincial_gate'):
        zones.append(('GATES', COL_GATES, QColor(33, 150, 243, 14)))

    for label, cx, color in zones:
        x = cx - STATION_W / 2 - ZONE_PAD_X
        w = STATION_W + ZONE_PAD_X * 2
        y = ZONE_PAD_Y
        h = SCENE_HEIGHT - ZONE_PAD_Y * 2

        rect = QGraphicsRectItem(x, y, w, h)
        rect.setBrush(QBrush(color))
        rect.setPen(QPen(Qt.PenStyle.NoPen))
        rect.setZValue(-2)
        scene.addItem(rect)

        header = QGraphicsSimpleTextItem(label)
        header.setBrush(QBrush(QColor(255, 255, 255, 50)))
        header.setFont(FONT_LABEL)
        br = header.boundingRect()
        header.setPos(cx - br.width() / 2, ZONE_PAD_Y + 4)
        header.setZValue(-1)
        scene.addItem(header)


def draw_corridor(scene: AirportScene) -> None:
    """Draw the main walking corridor as a subtle horizontal strip with branch lines."""
    strip_h = 10
    cats = scene.data.station_categories
    x_start = COL_ENTRANCE
    x_end = COL_GATES
    if not (cats.get('regional_gate') or cats.get('provincial_gate')):
        x_end = COL_SECURITY

    corridor = QGraphicsRectItem(
        x_start - 20, CORRIDOR_Y - strip_h / 2,
        x_end - x_start + 40, strip_h,
    )
    corridor.setBrush(QBrush(QColor(255, 255, 255, 8)))
    corridor.setPen(QPen(Qt.PenStyle.NoPen))
    corridor.setZValue(-1)
    scene.addItem(corridor)

    # Dotted lines from corridor to each station
    pen = QPen(QColor(255, 255, 255, 15), 1.5, Qt.PenStyle.DotLine)
    for name, pos in scene.station_positions.items():
        if name == 'Entrance':
            continue
        if abs(pos.y() - CORRIDOR_Y) > 5:
            line = QGraphicsLineItem(pos.x(), CORRIDOR_Y, pos.x(), pos.y())
            line.setPen(pen)
            line.setZValue(-1)
            scene.addItem(line)


def draw_station_rects(scene: AirportScene) -> None:
    """Draw rounded station rectangles with accent bar and queue area indicator."""
    for name, center in scene.station_positions.items():
        border_col = station_border_color(name)
        is_small = name.endswith(' B') or name.endswith(' C')
        w = STATION_W_SMALL if is_small else STATION_W
        x = center.x() - w / 2
        y = center.y() - STATION_H / 2
        # For click detection: sub-stations map to parent station name (logs use unsuffixed)
        station_tag = name[:-2] if is_small else name

        # Queue area indicator (toward corridor side of station)
        # Entrance has no queue - passengers arrive based on Poisson rate
        q_dir = scene._queue_dirs.get(name, 1)
        if name != 'Entrance':
            q_area_h = 60
            q_area_y = center.y() - STATION_H / 2 - q_area_h if q_dir > 0 \
                else center.y() + STATION_H / 2
            q_rect = QGraphicsRectItem(x + 5, q_area_y, w - 10, q_area_h)
            q_rect.setBrush(QBrush(QColor(255, 255, 255, 5)))
            q_rect.setPen(QPen(QColor(255, 255, 255, 12), 0.5, Qt.PenStyle.DotLine))
            q_rect.setZValue(0)
            q_rect.setData(1, station_tag)
            scene.addItem(q_rect)

        # Main rect (rounded via QPainterPath)
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, STATION_H), 6, 6)
        item = QGraphicsPathItem(path)
        item.setBrush(QBrush(STATION_FILL))
        item.setPen(QPen(QColor(255, 255, 255, 25), 1))
        item.setZValue(1)
        item.setData(1, station_tag)
        scene.addItem(item)

        # Colored accent bar on the left edge
        accent = QGraphicsRectItem(x, y + 4, 4, STATION_H - 8)
        accent.setBrush(QBrush(border_col))
        accent.setPen(QPen(Qt.PenStyle.NoPen))
        accent.setZValue(2)
        accent.setData(1, station_tag)
        scene.addItem(accent)

        # Label (short name for split security sub-stations)
        display_name = 'Business' if name.endswith(' B') else 'Coach' if name.endswith(' C') else name
        label = QGraphicsSimpleTextItem(display_name)
        label.setBrush(QBrush(TEXT_PRIMARY))
        label.setFont(FONT_LABEL)
        br = label.boundingRect()
        label.setPos(center.x() - br.width() / 2 + 3, center.y() - br.height() / 2)
        label.setZValue(3)
        label.setData(1, station_tag)
        scene.addItem(label)

        # Overflow queue zone (opposite side from boarding queue, regional gates only)
        if 'regional' in name.lower():
            o_area_h = 60
            # Opposite side from the boarding queue area
            o_area_y = center.y() + STATION_H / 2 if q_dir > 0 \
                else center.y() - STATION_H / 2 - o_area_h
            o_rect = QGraphicsRectItem(x + 5, o_area_y, w - 10, o_area_h)
            o_rect.setBrush(QBrush(QColor(255, 140, 0, 10)))
            o_rect.setPen(QPen(QColor(255, 140, 0, 40), 0.5, Qt.PenStyle.DotLine))
            o_rect.setZValue(0)
            o_rect.setData(1, station_tag)
            scene.addItem(o_rect)
            o_label = QGraphicsSimpleTextItem('overflow')
            o_label.setBrush(QBrush(QColor(255, 140, 0, 60)))
            o_label.setFont(FONT_LABEL)
            o_br = o_label.boundingRect()
            o_label.setPos(center.x() - o_br.width() / 2 + 3, o_area_y + 2)
            o_label.setZValue(1)
            o_label.setData(1, station_tag)
            scene.addItem(o_label)

        # Capacity bar for gate stations
        if 'gate' in name.lower():
            bar_w, bar_h = 6, STATION_H
            bar_x = x + w + 4
            bar_y = y
            bg = QGraphicsRectItem(bar_x, bar_y, bar_w, bar_h)
            bg.setBrush(QBrush(QColor(255, 255, 255, 15)))
            bg.setPen(QPen(QColor(255, 255, 255, 30), 0.5))
            bg.setZValue(1)
            bg.setData(1, station_tag)
            scene.addItem(bg)
            fill = QGraphicsRectItem(bar_x, bar_y + bar_h, bar_w, 0)
            fill.setBrush(QBrush(border_col))
            fill.setPen(QPen(Qt.PenStyle.NoPen))
            fill.setZValue(2)
            fill.setData(1, station_tag)
            scene.addItem(fill)
            scene._capacity_bars[name] = (fill, bar_x, bar_y, bar_w, bar_h)


def draw_legend(scene: AirportScene) -> None:
    """Draw passenger type color legend at the bottom of the scene."""
    x0 = 20
    y0 = SCENE_HEIGHT - 50
    entries = [
        ('Commuter', QColor('#4CAF50')),
        ('Provincial Coach', QColor('#2196F3')),
        ('Provincial Biz', QColor('#FFD700')),
    ]
    for i, (text, color) in enumerate(entries):
        x = x0 + i * 155
        dot = QGraphicsEllipseItem(x, y0, 8, 8)
        dot.setBrush(QBrush(color))
        dot.setPen(QPen(Qt.PenStyle.NoPen))
        dot.setZValue(20)
        scene.addItem(dot)

        lbl = QGraphicsSimpleTextItem(text)
        lbl.setBrush(QBrush(TEXT_SECONDARY))
        lbl.setFont(FONT_LABEL)
        lbl.setPos(x + 12, y0 - 2)
        lbl.setZValue(20)
        scene.addItem(lbl)
