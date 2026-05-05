from __future__ import annotations

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt


# -- Background / surface ------------------------------------------------
BACKGROUND = QColor('#1a1a2e')
SURFACE = QColor('#16213e')
PANEL = QColor('#0f3460')

# -- Text ----------------------------------------------------------------
TEXT_PRIMARY = QColor('#e0e0e0')
TEXT_SECONDARY = QColor('#8a8a9a')

# -- Accents -------------------------------------------------------------
HIGHLIGHT = QColor('#1a8fff')
HIGHLIGHT_TEXT = QColor('#ffffff')

# -- Passenger dot colors ------------------------------------------------
COLOR_COMMUTER_COACH = QColor('#4CAF50')       # green
COLOR_PROVINCIAL_COACH = QColor('#2196F3')     # blue
COLOR_PROVINCIAL_BIZ = QColor('#FFD700')       # gold

# -- Outcome colors (dot recoloring) -------------------------------------
COLOR_REFUND = QColor('#FF8C00')              # orange
COLOR_LATE = QColor('#FF4444')                # red

# -- Station border colors -----------------------------------------------
COLOR_ENTRANCE = QColor('#888888')             # gray
COLOR_CHECKIN = QColor('#ffffff')              # white
COLOR_SECURITY = QColor('#F44336')             # red
COLOR_REGIONAL_GATE = QColor('#4CAF50')        # green
COLOR_PROVINCIAL_GATE = QColor('#2196F3')      # blue

# -- Station fill --------------------------------------------------------
STATION_FILL = QColor('#2a2a3e')

# -- Scene ---------------------------------------------------------------
SCENE_BG = QColor('#111122')

# -- Matplotlib dark style -----------------------------------------------
MPL_BG = '#1a1a2e'
MPL_AXES_BG = '#16213e'
MPL_TEXT = '#e0e0e0'
MPL_GRID = '#2a2a3e'
MPL_HIST_COLOR = '#1a8fff'
MPL_HIST_EDGE = '#0f3460'


FONT_FAMILY = 'Menlo'
FONT_SMALL = QFont(FONT_FAMILY, 9)
FONT_MEDIUM = QFont(FONT_FAMILY, 11)
FONT_LABEL = QFont(FONT_FAMILY, 8)


def passenger_color(gate_type: str, seat_type: str) -> QColor:
    """Map gate/seat type to dot color: commuter=green, provincial biz=gold, provincial coach=blue."""
    if gate_type == 'commuter':
        return COLOR_COMMUTER_COACH
    if seat_type == 'business':
        return COLOR_PROVINCIAL_BIZ
    return COLOR_PROVINCIAL_COACH


def station_border_color(station_name: str) -> QColor:
    name = station_name.lower()
    if name.endswith(' p') and 'security' in name:
        return COLOR_PROVINCIAL_BIZ
    if name.endswith(' r') and 'security' in name:
        return COLOR_SECURITY
    if 'regional' in name:
        return COLOR_REGIONAL_GATE
    if 'provincial' in name:
        return COLOR_PROVINCIAL_GATE
    if 'counter' in name or 'check' in name:
        return COLOR_CHECKIN
    return COLOR_ENTRANCE


def apply_dark_theme(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, BACKGROUND)
    palette.setColor(QPalette.ColorRole.WindowText, TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Base, SURFACE)
    palette.setColor(QPalette.ColorRole.AlternateBase, PANEL)
    palette.setColor(QPalette.ColorRole.Text, TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Button, SURFACE)
    palette.setColor(QPalette.ColorRole.ButtonText, TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Highlight, HIGHLIGHT)
    palette.setColor(QPalette.ColorRole.HighlightedText, HIGHLIGHT_TEXT)
    palette.setColor(QPalette.ColorRole.ToolTipBase, SURFACE)
    palette.setColor(QPalette.ColorRole.ToolTipText, TEXT_PRIMARY)
    app.setPalette(palette)
    app.setFont(FONT_MEDIUM)

    app.setStyleSheet("""
        QSlider::groove:horizontal {
            height: 6px;
            background: #0f3460;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #1a8fff;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QSlider::sub-page:horizontal {
            background: #1a8fff;
            border-radius: 3px;
        }
        QTabWidget::pane {
            border: 1px solid #0f3460;
        }
        QTabBar::tab {
            background: #16213e;
            color: #e0e0e0;
            padding: 8px 20px;
            border: 1px solid #0f3460;
        }
        QTabBar::tab:selected {
            background: #0f3460;
            color: #ffffff;
        }
        QPushButton {
            background: #0f3460;
            color: #e0e0e0;
            border: 1px solid #1a8fff;
            padding: 6px 14px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background: #1a8fff;
        }
        QPushButton:pressed {
            background: #0d2d50;
        }
        QStatusBar {
            background: #111122;
            color: #8a8a9a;
        }
        QScrollArea {
            border: none;
        }
    """)
