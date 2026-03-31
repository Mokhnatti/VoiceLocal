"""
Диалог настроек VoiceLocal.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QFrame, QMessageBox, QGroupBox, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
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

HOTKEY_OPTIONS = [
    ("scroll_lock", "Scroll Lock"),
    ("pause", "Pause"),
    ("home", "Home"),
    ("end", "End"),
    ("insert", "Insert"),
    ("caps_lock", "Caps Lock"),
    ("num_lock", "Num Lock"),
    ("f13", "F13"), ("f14", "F14"), ("f15", "F15"), ("f16", "F16"),
]

MODEL_OPTIONS = [
    ("tiny",            "tiny — очень быстро, качество ниже"),
    ("base",            "base — быстро"),
    ("small",           "small — баланс"),
    ("medium",          "medium — хорошее качество"),
    ("large-v3-turbo",  "large-v3-turbo — лучшее качество ★"),
    ("large-v3",        "large-v3 — максимум, медленнее"),
]

LANG_OPTIONS = [
    ("ru", "Русский"),
    ("en", "English"),
    ("uk", "Українська"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("auto", "Авто-определение"),
]

PTT_MODES = [
    ("toggle", "Toggle — нажал = старт, нажал ещё раз = стоп"),
    ("hold",   "Hold — держи = запись, отпустил = стоп"),
]


def _detect_python_mode() -> str:
    if getattr(sys, 'frozen', False):
        return "exe"
    base = Path(__file__).parent.parent
    portable_py = base / "python" / "python.exe"
    if portable_py.exists():
        return "portable"
    return "system"


class SettingsDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._cfg = get_config()
        self.setWindowTitle("Настройки — VoiceLocal")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build_ui()
        self._apply_stylesheet()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 8)
        layout.setSpacing(12)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # ── PTT режим ──
        grp_ptt = self._group("Режим Push-to-Talk")
        g = QVBoxLayout(grp_ptt)
        self._ptt_combo = QComboBox()
        cur_mode = self._cfg.get("ptt_mode", "toggle")
        for val, label in PTT_MODES:
            self._ptt_combo.addItem(label, val)
            if val == cur_mode:
                self._ptt_combo.setCurrentIndex(self._ptt_combo.count() - 1)
        g.addWidget(self._ptt_combo)
        layout.addWidget(grp_ptt)

        # ── Горячая клавиша ──
        grp_hk = self._group("Клавиша")
        g = QVBoxLayout(grp_hk)
        self._hk_combo = QComboBox()
        cur_hk = self._cfg.get("hotkey", "scroll_lock")
        for val, label in HOTKEY_OPTIONS:
            self._hk_combo.addItem(label, val)
            if val == cur_hk:
                self._hk_combo.setCurrentIndex(self._hk_combo.count() - 1)
        g.addWidget(self._hk_combo)
        layout.addWidget(grp_hk)

        # ── Модель ──
        grp_model = self._group("Модель Whisper")
        g = QVBoxLayout(grp_model)
        self._model_combo = QComboBox()
        cur_model = self._cfg.get("model", "large-v3-turbo")
        for val, label in MODEL_OPTIONS:
            self._model_combo.addItem(label, val)
            if val == cur_model:
                self._model_combo.setCurrentIndex(self._model_combo.count() - 1)
        g.addWidget(QLabel("Модель:"))
        g.addWidget(self._model_combo)
        g.addSpacing(4)
        self._lang_combo = QComboBox()
        cur_lang = self._cfg.get("language", "ru")
        for val, label in LANG_OPTIONS:
            self._lang_combo.addItem(label, val)
            if val == cur_lang:
                self._lang_combo.setCurrentIndex(self._lang_combo.count() - 1)
        g.addWidget(QLabel("Язык:"))
        g.addWidget(self._lang_combo)
        self._chk_cuda = QCheckBox("Использовать GPU (NVIDIA CUDA)")
        self._chk_cuda.setChecked(self._cfg.get("use_cuda", True))
        self._chk_cuda.setToolTip("Если CUDA недоступна — автоматически переключится на CPU")
        g.addWidget(self._chk_cuda)
        note = QLabel("⚠ Смена модели перезагружает движок (~10–30 сек)")
        note.setObjectName("noteLabel")
        g.addWidget(note)
        layout.addWidget(grp_model)

        # ── Микрофон ──
        grp_mic = self._group("Микрофон")
        g = QVBoxLayout(grp_mic)
        self._mic_combo = QComboBox()
        self._mic_combo.addItem("По умолчанию (системный)", None)
        devices = self._controller.get_microphone_list()
        cur_dev = self._cfg.get("device_index")
        for d in devices:
            self._mic_combo.addItem(f"[{d['index']}] {d['name']}", d["index"])
            if d["index"] == cur_dev:
                self._mic_combo.setCurrentIndex(self._mic_combo.count() - 1)
        g.addWidget(self._mic_combo)
        layout.addWidget(grp_mic)

        # ── Текст и пунктуация ──
        grp_text = self._group("Текст")
        g = QVBoxLayout(grp_text)
        self._chk_strip = QCheckBox("Убирать знаки препинания (режим 1C / чат)")
        self._chk_strip.setChecked(self._cfg.get("strip_punctuation", True))
        self._chk_voice = QCheckBox('Голосовые команды ("точка", "запятая", "новая строка"...)')
        self._chk_voice.setChecked(self._cfg.get("voice_commands", False))
        self._chk_cap = QCheckBox("Заглавные буквы в начале предложений")
        self._chk_cap.setChecked(self._cfg.get("capitalize_sentences", False))
        self._chk_space = QCheckBox("Добавлять пробел перед вставкой")
        self._chk_space.setChecked(self._cfg.get("insert_space", False))
        self._chk_enter = QCheckBox("Нажимать Enter после вставки")
        self._chk_enter.setChecked(self._cfg.get("auto_enter", False))
        for w in [self._chk_strip, self._chk_voice, self._chk_cap, self._chk_space, self._chk_enter]:
            g.addWidget(w)
        layout.addWidget(grp_text)

        # ── Python ──
        grp_py = self._group("Python")
        g = QVBoxLayout(grp_py)
        mode = _detect_python_mode()
        mode_text = {"exe": "EXE (скомпилировано)", "portable": "Портативный (из папки python/)", "system": "Системный"}
        lbl_py = QLabel(f"Режим: {mode_text.get(mode, mode)}")
        lbl_py.setObjectName("noteLabel")
        g.addWidget(lbl_py)
        if mode == "system":
            hint = QLabel("Для переноса на другой ПК без установки Python — скачай портативную версию с GitHub.")
            hint.setObjectName("noteLabel")
            hint.setWordWrap(True)
            g.addWidget(hint)
        elif mode == "portable":
            hint = QLabel("Портативный Python — можно скопировать папку целиком на любой ПК.")
            hint.setObjectName("noteLabel")
            hint.setWordWrap(True)
            g.addWidget(hint)
        layout.addWidget(grp_py)

        # ── Кнопки ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("btnSep")
        outer.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(24, 12, 24, 16)
        btn_reset = QPushButton("Сброс")
        btn_reset.setObjectName("resetBtn")
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("cancelBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton("Сохранить")
        btn_ok.setObjectName("okBtn")
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_ok)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_row)
        outer.addWidget(btn_widget)

    def _group(self, title: str) -> QGroupBox:
        return QGroupBox(title)

    def _save(self):
        old_model = self._cfg.get("model")
        old_hotkey = self._cfg.get("hotkey")
        old_device = self._cfg.get("device_index")

        self._cfg.set("ptt_mode", self._ptt_combo.currentData())
        self._cfg.set("hotkey", self._hk_combo.currentData())
        self._cfg.set("model", self._model_combo.currentData())
        self._cfg.set("language", self._lang_combo.currentData())
        self._cfg.set("use_cuda", self._chk_cuda.isChecked())
        self._cfg.set("device_index", self._mic_combo.currentData())
        self._cfg.set("strip_punctuation", self._chk_strip.isChecked())
        self._cfg.set("voice_commands", self._chk_voice.isChecked())
        self._cfg.set("capitalize_sentences", self._chk_cap.isChecked())
        self._cfg.set("insert_space", self._chk_space.isChecked())
        self._cfg.set("auto_enter", self._chk_enter.isChecked())

        if self._model_combo.currentData() != old_model or self._chk_cuda.isChecked() != self._cfg.get("use_cuda"):
            self._controller.reload_model()
        if self._hk_combo.currentData() != old_hotkey:
            self._controller.update_hotkey()
        if self._mic_combo.currentData() != old_device:
            self._controller.update_device()

        self.accept()

    def _reset(self):
        if QMessageBox.question(
            self, "Сброс", "Сбросить все настройки?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self._cfg.reset()
            self.reject()

    def _apply_stylesheet(self):
        self.setStyleSheet(f"""
            QDialog, QWidget {{
                background-color: {DARK_BG}; color: {TEXT};
                font-family: 'Segoe UI', sans-serif; font-size: 13px;
            }}
            QScrollArea {{ background-color: {DARK_BG}; border: none; }}
            QGroupBox {{
                background-color: {SURFACE}; border: 1px solid {BORDER};
                border-radius: 10px; margin-top: 8px; padding: 12px;
                font-weight: 600; color: {ACCENT2};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}
            QComboBox {{
                background-color: {SURFACE2}; color: {TEXT};
                border: 1px solid {BORDER}; border-radius: 6px;
                padding: 6px 10px; min-height: 28px;
            }}
            QComboBox:hover {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{
                background-color: {SURFACE2}; color: {TEXT};
                border: 1px solid {BORDER}; selection-background-color: {ACCENT};
            }}
            QComboBox::drop-down {{ border: none; padding-right: 8px; }}
            QCheckBox {{ spacing: 8px; color: {TEXT}; padding: 3px 0; }}
            QCheckBox::indicator {{
                width: 16px; height: 16px; border-radius: 4px;
                border: 1px solid {BORDER}; background: {SURFACE2};
            }}
            QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT}; }}
            QLabel#noteLabel {{ color: {TEXT_DIM}; font-size: 11px; padding-top: 4px; }}
            QFrame#btnSep {{ border: none; border-top: 1px solid {BORDER}; }}
            QPushButton#okBtn {{
                background-color: {ACCENT}; color: white; border: none;
                border-radius: 8px; padding: 8px 20px; font-weight: 600;
            }}
            QPushButton#okBtn:hover {{ background-color: {ACCENT2}; }}
            QPushButton#cancelBtn {{
                background-color: {SURFACE2}; color: {TEXT};
                border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 16px;
            }}
            QPushButton#cancelBtn:hover {{ border-color: {ACCENT}; }}
            QPushButton#resetBtn {{
                background-color: transparent; color: {RED};
                border: 1px solid rgba(224,85,85,0.4); border-radius: 8px;
                padding: 8px 12px; font-size: 12px;
            }}
            QPushButton#resetBtn:hover {{ background-color: rgba(224,85,85,0.1); }}
        """)
