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
from PyQt6.QtGui import QWheelEvent
from app.config import get_config
from app.i18n import tr, UI_LANG_OPTIONS


class NoScrollComboBox(QComboBox):
    """Комбобокс без смены выбора колесиком мыши."""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

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

RECOGNITION_LANG_OPTIONS = [
    ("ru", "🇷🇺 Русский"),
    ("en", "🇬🇧 English"),
    ("uk", "🇺🇦 Українська"),
    ("de", "🇩🇪 Deutsch"),
    ("fr", "🇫🇷 Français"),
    ("es", "🇪🇸 Español"),
    ("it", "🇮🇹 Italiano"),
    ("pt", "🇧🇷 Português"),
    ("pl", "🇵🇱 Polski"),
    ("tr", "🇹🇷 Türkçe"),
    ("nl", "🇳🇱 Nederlands"),
    ("ar", "🇸🇦 العربية"),
    ("ja", "🇯🇵 日本語"),
    ("zh", "🇨🇳 中文"),
    ("ko", "🇰🇷 한국어"),
    ("auto", "🌐 Auto"),
]

TRANSLATE_LANG_OPTIONS = [
    ("en", "🇬🇧 English"),
    ("ru", "🇷🇺 Русский"),
    ("zh", "🇨🇳 中文"),
    ("de", "🇩🇪 Deutsch"),
    ("fr", "🇫🇷 Français"),
    ("es", "🇪🇸 Español"),
    ("pt", "🇧🇷 Português"),
    ("it", "🇮🇹 Italiano"),
    ("ja", "🇯🇵 日本語"),
    ("ko", "🇰🇷 한국어"),
    ("uk", "🇺🇦 Українська"),
    ("pl", "🇵🇱 Polski"),
    ("tr", "🇹🇷 Türkçe"),
    ("ar", "🇸🇦 العربية"),
    ("nl", "🇳🇱 Nederlands"),
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
        self.setWindowTitle(tr("settings_title"))
        self.setMinimumWidth(560)
        self.resize(560, 620)
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
        grp_ptt = self._group(tr("grp_ptt"))
        g = QVBoxLayout(grp_ptt)
        self._ptt_combo = NoScrollComboBox()
        cur_mode = self._cfg.get("ptt_mode", "toggle")
        for val, key in [("toggle", "ptt_toggle"), ("hold", "ptt_hold")]:
            self._ptt_combo.addItem(tr(key), val)
            if val == cur_mode:
                self._ptt_combo.setCurrentIndex(self._ptt_combo.count() - 1)
        g.addWidget(self._ptt_combo)
        layout.addWidget(grp_ptt)

        # ── Горячая клавиша ──
        grp_hk = self._group(tr("grp_hotkey"))
        g = QVBoxLayout(grp_hk)
        self._hk_combo = NoScrollComboBox()
        cur_hk = self._cfg.get("hotkey", "scroll_lock")
        for val, label in HOTKEY_OPTIONS:
            self._hk_combo.addItem(label, val)
            if val == cur_hk:
                self._hk_combo.setCurrentIndex(self._hk_combo.count() - 1)
        g.addWidget(self._hk_combo)
        layout.addWidget(grp_hk)

        # ── Модель ──
        grp_model = self._group(tr("grp_model"))
        g = QVBoxLayout(grp_model)
        self._model_combo = NoScrollComboBox()
        cur_model = self._cfg.get("model", "large-v3-turbo")
        model_entries = [
            ("tiny",           "model_tiny"),
            ("base",           "model_base"),
            ("small",          "model_small"),
            ("medium",         "model_medium"),
            ("large-v3-turbo", "model_large_turbo"),
            ("large-v3",       "model_large"),
        ]
        for val, key in model_entries:
            self._model_combo.addItem(tr(key), val)
            if val == cur_model:
                self._model_combo.setCurrentIndex(self._model_combo.count() - 1)
        g.addWidget(QLabel(tr("lbl_model")))
        g.addWidget(self._model_combo)
        g.addSpacing(4)

        self._lang_combo = NoScrollComboBox()
        cur_lang = self._cfg.get("language", "ru")
        for val, label in RECOGNITION_LANG_OPTIONS:
            self._lang_combo.addItem(label, val)
            if val == cur_lang:
                self._lang_combo.setCurrentIndex(self._lang_combo.count() - 1)
        g.addWidget(QLabel(tr("lbl_lang")))
        g.addWidget(self._lang_combo)

        self._chk_cuda = QCheckBox(tr("chk_cuda"))
        self._chk_cuda.setChecked(self._cfg.get("use_cuda", True))
        self._chk_cuda.setToolTip(tr("cuda_tip"))
        g.addWidget(self._chk_cuda)
        note = QLabel(tr("note_model"))
        note.setObjectName("noteLabel")
        g.addWidget(note)
        layout.addWidget(grp_model)

        # ── Микрофон ──
        grp_mic = self._group(tr("grp_mic"))
        g = QVBoxLayout(grp_mic)
        self._mic_combo = NoScrollComboBox()
        self._mic_combo.addItem(tr("mic_default"), None)
        devices = self._controller.get_microphone_list()
        cur_dev = self._cfg.get("device_index")
        for d in devices:
            self._mic_combo.addItem(f"[{d['index']}] {d['name']}", d["index"])
            if d["index"] == cur_dev:
                self._mic_combo.setCurrentIndex(self._mic_combo.count() - 1)
        g.addWidget(self._mic_combo)

        self._chk_mute = QCheckBox(tr("chk_mute"))
        self._chk_mute.setChecked(self._cfg.get("mute_others", False))
        from app.audio_mute import is_available as _mute_available
        if not _mute_available():
            self._chk_mute.setEnabled(False)
            self._chk_mute.setToolTip(tr("mute_tip_unavail"))
        else:
            self._chk_mute.setToolTip(tr("mute_tip"))
        g.addWidget(self._chk_mute)
        layout.addWidget(grp_mic)

        # ── Текст и пунктуация ──
        grp_text = self._group(tr("grp_text"))
        g = QVBoxLayout(grp_text)
        self._chk_strip = QCheckBox(tr("chk_strip"))
        self._chk_strip.setChecked(self._cfg.get("strip_punctuation", True))
        self._chk_voice = QCheckBox(tr("chk_voice"))
        self._chk_voice.setChecked(self._cfg.get("voice_commands", False))
        self._chk_cap = QCheckBox(tr("chk_cap"))
        self._chk_cap.setChecked(self._cfg.get("capitalize_sentences", False))
        self._chk_space = QCheckBox(tr("chk_space"))
        self._chk_space.setChecked(self._cfg.get("insert_space", False))
        self._chk_enter = QCheckBox(tr("chk_enter"))
        self._chk_enter.setChecked(self._cfg.get("auto_enter", False))
        for w in [self._chk_strip, self._chk_voice, self._chk_cap, self._chk_space, self._chk_enter]:
            g.addWidget(w)
        layout.addWidget(grp_text)

        # ── Перевод ──
        grp_tr = self._group(tr("grp_translate"))
        g = QVBoxLayout(grp_tr)
        self._chk_translate = QCheckBox(tr("chk_translate"))
        self._chk_translate.setChecked(self._cfg.get("translate_enabled", False))
        g.addWidget(self._chk_translate)
        self._tr_lang_combo = NoScrollComboBox()
        cur_tr = self._cfg.get("translate_to", "en")
        for val, label in TRANSLATE_LANG_OPTIONS:
            self._tr_lang_combo.addItem(label, val)
            if val == cur_tr:
                self._tr_lang_combo.setCurrentIndex(self._tr_lang_combo.count() - 1)
        g.addWidget(QLabel(tr("lbl_translate_to")))
        g.addWidget(self._tr_lang_combo)
        note_tr = QLabel(tr("note_translate"))
        note_tr.setObjectName("noteLabel")
        note_tr.setWordWrap(True)
        g.addWidget(note_tr)
        layout.addWidget(grp_tr)

        # ── Язык интерфейса ──
        grp_ui = self._group(tr("grp_ui_lang"))
        g = QVBoxLayout(grp_ui)
        self._ui_lang_combo = NoScrollComboBox()
        cur_ui_lang = self._cfg.get("ui_lang", "ru")
        for val, label in UI_LANG_OPTIONS:
            self._ui_lang_combo.addItem(label, val)
            if val == cur_ui_lang:
                self._ui_lang_combo.setCurrentIndex(self._ui_lang_combo.count() - 1)
        g.addWidget(self._ui_lang_combo)
        self._ui_lang_note = QLabel("")
        self._ui_lang_note.setObjectName("noteLabel")
        g.addWidget(self._ui_lang_note)
        layout.addWidget(grp_ui)

        # ── Python ──
        grp_py = self._group(tr("grp_python"))
        g = QVBoxLayout(grp_py)
        mode = _detect_python_mode()
        mode_text = {
            "exe":      tr("py_mode_exe"),
            "portable": tr("py_mode_portable"),
            "system":   tr("py_mode_system"),
        }
        lbl_py = QLabel(f"{tr('py_label')} {mode_text.get(mode, mode)}")
        lbl_py.setObjectName("noteLabel")
        g.addWidget(lbl_py)
        if mode == "system":
            hint = QLabel(tr("py_hint_system"))
            hint.setObjectName("noteLabel")
            hint.setWordWrap(True)
            g.addWidget(hint)
        elif mode == "portable":
            hint = QLabel(tr("py_hint_portable"))
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
        btn_reset = QPushButton(tr("btn_reset"))
        btn_reset.setObjectName("resetBtn")
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_cancel = QPushButton(tr("btn_cancel"))
        btn_cancel.setObjectName("cancelBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton(tr("btn_save"))
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
        old_ui_lang = self._cfg.get("ui_lang", "ru")

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
        self._cfg.set("mute_others", self._chk_mute.isChecked())
        self._cfg.set("translate_enabled", self._chk_translate.isChecked())
        self._cfg.set("translate_to", self._tr_lang_combo.currentData())
        self._cfg.set("ui_lang", self._ui_lang_combo.currentData())

        new_ui_lang = self._ui_lang_combo.currentData()
        if new_ui_lang != old_ui_lang:
            self._ui_lang_note.setText(tr("ui_lang_restart"))

        if self._model_combo.currentData() != old_model or self._chk_cuda.isChecked() != self._cfg.get("use_cuda"):
            self._controller.reload_model()
        if self._hk_combo.currentData() != old_hotkey:
            self._controller.update_hotkey()
        if self._mic_combo.currentData() != old_device:
            self._controller.update_device()

        self.accept()

    def _reset(self):
        if QMessageBox.question(
            self, tr("reset_title"), tr("reset_msg"),
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
