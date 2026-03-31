"""
Менеджер настроек — читает/пишет config/settings.json
"""

import json
import os
from pathlib import Path
import sys

# Если запускаем портативно — config рядом с exe/скриптом
if getattr(sys, 'frozen', False):
    _APP_DIR = Path(sys.executable).parent
else:
    _APP_DIR = Path(__file__).parent.parent

CONFIG_PATH = _APP_DIR / "config" / "settings.json"

DEFAULTS = {
    # Запись
    "hotkey": "scroll_lock",    # клавиша push-to-talk
    "ptt_mode": "toggle",       # "toggle" (нажал-нажал) или "hold" (держи-отпусти)
    "ring_buffer_sec": 1.5,     # захват до нажатия (сек)
    "device_index": None,       # None = системный микрофон
    "mute_others": False,       # мутить другие микрофоны при записи

    # Распознавание
    "model": "large-v3-turbo",  # whisper модель
    "language": "ru",           # язык
    "use_cuda": True,           # пробовать GPU (NVIDIA)
    "beam_size": 1,             # 1 = быстро, 5 = точнее

    # Постобработка
    "voice_commands": False,        # "точка", "запятая" → знаки
    "capitalize_sentences": False,  # заглавные буквы
    "auto_punctuation": False,      # Whisper сам расставляет знаки
    "insert_space": False,          # пробел перед вставкой
    "auto_enter": False,            # Enter после вставки
    "strip_punctuation": True,      # убирать точки/запятые (наш дефолт)

    # Перевод
    "translate_enabled": False,   # переводить после транскрипции
    "translate_to": "en",         # целевой язык перевода

    # Прочее
    "post_delay_ms": 150,
    "theme": "dark",
}

# Голосовые команды → символы
VOICE_PUNCT_MAP = {
    "точка с запятой": ";",
    "вопросительный знак": "?",
    "восклицательный знак": "!",
    "открыть скобку": "(",
    "закрыть скобку": ")",
    "кавычки открыть": "«",
    "кавычки закрыть": "»",
    "новый абзац": "\n\n",
    "новая строка": "\n",
    "многоточие": "...",
    "двоеточие": ":",
    "запятая": ",",
    "вопрос": "?",
    "точка": ".",
    "тире": " — ",
    "дефис": "-",
    "пробел": " ",
    "удалить": "__DELETE__",
}

# Фильтр галлюцинаций Whisper
HALLUCINATION_FILTER = [
    "субтитры", "подписывайтесь", "подписаться", "канал", "лайк",
    "продолжение следует", "конец", "the end", "смотрите",
    "не забудьте", "ставьте", "комментарий",
]


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except Exception:
                pass

    def save(self):
        CONFIG_PATH.parent.mkdir(exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def all(self):
        return dict(self._data)

    def reset(self):
        self._data = dict(DEFAULTS)
        self.save()


_config = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
