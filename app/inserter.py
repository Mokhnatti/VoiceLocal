"""
Вставка текста в активное окно.
Буфер обмена + Ctrl+V. Fallback: посимвольный ввод.
"""

import time
import pyperclip
import pyautogui
from app.config import get_config


def insert_text(text: str):
    if not text:
        return

    cfg = get_config()
    if cfg.get("insert_space", False):
        text = " " + text

    delay = cfg.get("post_delay_ms", 150) / 1000.0
    time.sleep(delay)

    try:
        _via_clipboard(text)
    except Exception:
        try:
            _via_typing(text)
        except Exception:
            pass

    if cfg.get("auto_enter", False):
        time.sleep(0.05)
        pyautogui.press("enter")


def _via_clipboard(text: str):
    try:
        old = pyperclip.paste()
    except Exception:
        old = ""

    pyperclip.copy(text)
    time.sleep(0.05)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.1)


def _via_typing(text: str):
    pyautogui.typewrite(text, interval=0.01)
