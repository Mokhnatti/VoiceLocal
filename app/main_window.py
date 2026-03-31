"""
Главное окно VoiceLocal.
Тёмный минималистичный дизайн, пульсирующий индикатор.
"""

import math
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QBrush

from app.controller import PTTController
from app.config import get_config

DARK_BG  = "#0f0f12"
SURFACE  = "#1a1a22"
SURFACE2 = "#22222e"
ACCENT   = "#7c6af7"
ACCENT2  = "#a594f9"
TEXT     = "#e8e6f0"
TEXT_DIM = "#888899"
BORDER   = "#2a2a38"
RED      = "#e05555"
GREEN    = "#4caf7d"


class RecordIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._state = "idle"
        self._phase = 0.0
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(40)

    def set_state(self, state: str):
        self._state = state

    def _tick(self):
        self._phase = (self._phase + 0.08) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._state
        phase = self._phase
        if s == "recording":
            pulse = 0.5 + 0.5 * math.sin(phase)
            color = QColor(int(180 + 75 * pulse), int(30 * (1 - pulse)), 30)
            r = 7 + 2 * pulse
        elif s == "processing":
            color = QColor(220, 180, 0)
            r = 7
        elif s == "loading":
            pulse = 0.5 + 0.5 * math.sin(phase * 1.5)
            color = QColor(80, 140, 220)
            r = 7
        else:
            color = QColor(80, 80, 90)
            r = 6
        cx, cy = self.width() / 2, self.height() / 2
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))


class MainWindow(QMainWindow):
    sig_state         = pyqtSignal(str)
    sig_text          = pyqtSignal(str)
    sig_error         = pyqtSignal(str)
    sig_model_ready   = pyqtSignal()
    sig_model_loading = pyqtSignal()
    sig_duration      = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self._cfg = get_config()
        self._tray = None
        self._drag_pos = QPoint()
        self._setup_window()
        self._build_ui()
        self._apply_stylesheet()
        self._connect_signals()
        self._start_controller()

    def _setup_window(self):
        self.setWindowTitle("VoiceLocal")
        self.setMinimumSize(420, 240)
        self.resize(480, 280)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        tb = QWidget()
        tb.setObjectName("titleBar")
        tb.setFixedHeight(44)
        tb_layout = QHBoxLayout(tb)
        tb_layout.setContentsMargins(20, 0, 8, 0)
        tb_layout.setSpacing(0)

        lbl = QLabel("VoiceLocal")
        lbl.setObjectName("title")
        tb_layout.addWidget(lbl)
        tb_layout.addSpacing(10)

        sub = QLabel("Speech → Text")
        sub.setObjectName("subtitle")
        tb_layout.addWidget(sub)
        tb_layout.addStretch()

        for txt, name, tip, slot in [
            ("⚙", "titleBarBtn", "Настройки", self._open_settings),
            ("✕", "closeBtn", "Скрыть в трей", self.hide),
        ]:
            btn = QPushButton(txt)
            btn.setObjectName(name)
            btn.setToolTip(tip)
            btn.setFixedSize(32, 32)
            btn.clicked.connect(slot)
            tb_layout.addWidget(btn)

        tb.mousePressEvent = self._tb_press
        tb.mouseMoveEvent = self._tb_move
        root.addWidget(tb)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        # Content
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(20)

        status_row = QHBoxLayout()
        self._indicator = RecordIndicator()
        status_row.addWidget(self._indicator)
        status_row.addSpacing(10)
        self._lbl_status = QLabel("Загрузка модели...")
        self._lbl_status.setObjectName("statusLabel")
        status_row.addWidget(self._lbl_status)
        status_row.addStretch()
        self._lbl_duration = QLabel("")
        self._lbl_duration.setObjectName("durationLabel")
        status_row.addWidget(self._lbl_duration)
        cl.addLayout(status_row)

        self._lbl_hotkey = QLabel(self._hotkey_hint())
        self._lbl_hotkey.setObjectName("hotkeyHint")
        self._lbl_hotkey.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self._lbl_hotkey)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("separator")
        cl.addWidget(sep2)

        lbl_last = QLabel("ПОСЛЕДНИЙ РЕЗУЛЬТАТ")
        lbl_last.setObjectName("sectionTitle")
        cl.addWidget(lbl_last)

        self._lbl_last = QLabel("—")
        self._lbl_last.setObjectName("lastText")
        self._lbl_last.setWordWrap(True)
        self._lbl_last.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cl.addWidget(self._lbl_last)

        cl.addStretch()

        self._lbl_error = QLabel("")
        self._lbl_error.setObjectName("errorLabel")
        self._lbl_error.setWordWrap(True)
        self._lbl_error.hide()
        cl.addWidget(self._lbl_error)

        root.addWidget(content)

    def _hotkey_hint(self) -> str:
        hk = self._cfg.get("hotkey", "scroll_lock").replace("_", " ").upper()
        mode = self._cfg.get("ptt_mode", "toggle")
        if mode == "hold":
            return f"Зажмите  [{hk}]  чтобы говорить"
        return f"Нажмите  [{hk}]  для записи, ещё раз — стоп"

    def _connect_signals(self):
        self.sig_state.connect(self._on_state)
        self.sig_text.connect(self._on_text)
        self.sig_error.connect(self._on_error)
        self.sig_model_ready.connect(self._on_model_ready)
        self.sig_model_loading.connect(self._on_model_loading)
        self.sig_duration.connect(self._on_duration)

    def _start_controller(self):
        self._controller = PTTController(
            on_state_change=lambda s: self.sig_state.emit(s),
            on_text=lambda t: self.sig_text.emit(t),
            on_error=lambda e: self.sig_error.emit(e),
            on_model_ready=lambda: self.sig_model_ready.emit(),
            on_model_loading=lambda: self.sig_model_loading.emit(),
            on_duration=lambda d: self.sig_duration.emit(d),
        )
        self._controller.start()

    def _on_state(self, state: str):
        self._indicator.set_state(state)
        if self._tray:
            self._tray.set_state(state)
        if state == "recording":
            self._lbl_status.setText("● Запись...")
            self._lbl_status.setStyleSheet(f"color: {RED};")
            self._lbl_error.hide()
        elif state == "processing":
            self._lbl_status.setText("◌ Распознавание...")
            self._lbl_status.setStyleSheet("color: #ddbb44;")
            self._lbl_duration.setText("")
        elif state == "idle":
            self._lbl_status.setText("Готов")
            self._lbl_status.setStyleSheet(f"color: {TEXT_DIM};")
            self._lbl_duration.setText("")

    def _on_text(self, text: str):
        self._lbl_last.setText(text)

    def _on_error(self, msg: str):
        self._lbl_error.setText(f"⚠ {msg}")
        self._lbl_error.show()
        QTimer.singleShot(6000, self._lbl_error.hide)

    def _on_model_ready(self):
        self._indicator.set_state("idle")
        self._lbl_status.setText("Готов")
        self._lbl_status.setStyleSheet(f"color: {GREEN};")
        self._lbl_hotkey.setText(self._hotkey_hint())
        QTimer.singleShot(2000, lambda: self._lbl_status.setStyleSheet(f"color: {TEXT_DIM};"))

    def _on_model_loading(self):
        self._indicator.set_state("loading")
        model = self._cfg.get("model", "large-v3-turbo")
        self._lbl_status.setText(f"Загрузка модели {model}...")
        self._lbl_status.setStyleSheet("color: #5588dd;")

    def _on_duration(self, sec: float):
        self._lbl_duration.setText(f"{sec:.1f}s")

    def _open_settings(self):
        from app.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._controller, self)
        if dlg.exec():
            self._lbl_hotkey.setText(self._hotkey_hint())

    def _tb_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _tb_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def quit_app(self):
        self._controller.stop()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def _apply_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {DARK_BG}; color: {TEXT};
                font-family: 'Segoe UI', sans-serif; font-size: 13px;
            }}
            QLabel#title {{
                font-size: 15px; font-weight: 700; color: {ACCENT2}; letter-spacing: 0.5px;
            }}
            QLabel#subtitle {{
                font-size: 11px; color: {TEXT_DIM}; letter-spacing: 1px;
            }}
            QFrame#separator {{ border: none; border-top: 1px solid {BORDER}; }}
            QLabel#statusLabel {{ font-size: 14px; font-weight: 600; color: {TEXT_DIM}; }}
            QLabel#durationLabel {{ font-size: 13px; color: {RED}; font-weight: 600; }}
            QLabel#hotkeyHint {{
                font-size: 12px; color: {TEXT_DIM};
                padding: 8px; border: 1px dashed {BORDER}; border-radius: 6px;
            }}
            QLabel#sectionTitle {{
                font-size: 10px; font-weight: 600; color: {TEXT_DIM}; letter-spacing: 1px;
            }}
            QLabel#lastText {{ font-size: 14px; color: {TEXT}; padding: 2px 0; }}
            QLabel#errorLabel {{
                background-color: rgba(224,85,85,0.12); color: {RED};
                border: 1px solid rgba(224,85,85,0.35); border-radius: 6px;
                padding: 8px 12px; font-size: 12px;
            }}
            QWidget#titleBar {{ background-color: {DARK_BG}; }}
            QPushButton#titleBarBtn {{
                background-color: transparent; color: {TEXT_DIM};
                border: none; border-radius: 6px; font-size: 14px;
            }}
            QPushButton#titleBarBtn:hover {{ background-color: {SURFACE2}; color: {TEXT}; }}
            QPushButton#closeBtn {{
                background-color: transparent; color: {TEXT_DIM};
                border: none; border-radius: 6px; font-size: 11px;
            }}
            QPushButton#closeBtn:hover {{ background-color: rgba(224,85,85,0.18); color: {RED}; }}
        """)
