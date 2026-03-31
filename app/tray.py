"""
Иконка в системном трее.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt


def _make_icon(color: str) -> QIcon:
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, size - 8, size - 8)
    p.setBrush(QBrush(QColor("white")))
    p.drawRoundedRect(22, 12, 20, 28, 10, 10)
    p.drawRect(30, 42, 4, 8)
    p.drawRect(22, 49, 20, 4)
    p.end()
    return QIcon(pix)


_ICONS = {}

def _get_icon(state: str) -> QIcon:
    colors = {"recording": "#e05555", "processing": "#d4a017", "loading": "#5588dd"}
    color = colors.get(state, "#7c6af7")
    if color not in _ICONS:
        _ICONS[color] = _make_icon(color)
    return _ICONS[color]


class TrayIcon(QSystemTrayIcon):
    def __init__(self, window, app):
        super().__init__()
        self._window = window
        self._app = app
        self.setIcon(_get_icon("idle"))
        self.setToolTip("VoiceLocal — Speech to Text")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def set_state(self, state: str):
        self.setIcon(_get_icon(state))
        tips = {
            "recording": "VoiceLocal — Запись...",
            "processing": "VoiceLocal — Распознавание...",
        }
        self.setToolTip(tips.get(state, "VoiceLocal — Speech to Text"))

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a22; color: #e8e6f0;
                border: 1px solid #2a2a38; border-radius: 8px;
                padding: 4px; font-family: 'Segoe UI', sans-serif; font-size: 13px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #7c6af7; color: white; }
            QMenu::separator { height: 1px; background: #2a2a38; margin: 4px 8px; }
        """)
        menu.addAction("📋 Открыть окно").triggered.connect(self._show_window)
        menu.addSeparator()
        menu.addAction("⚙ Настройки").triggered.connect(self._open_settings)
        menu.addSeparator()
        menu.addAction("✕ Выйти").triggered.connect(self._window.quit_app)
        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _open_settings(self):
        self._show_window()
        self._window._open_settings()
