"""
Вставка текста в активное окно.
Буфер обмена + keyboard.send("ctrl+v") — как в старой версии.
"""

import time
import logging
import pyperclip
import keyboard
from app.config import get_config

log = logging.getLogger("voice")


def insert_text(text: str):
    if not text:
        return

    cfg = get_config()
    if cfg.get("insert_space", False):
        text = " " + text

    delay = cfg.get("post_delay_ms", 150) / 1000.0
    time.sleep(delay)

    try:
        old = pyperclip.paste()
    except Exception:
        old = None

    pyperclip.copy(text)
    time.sleep(0.05)
    keyboard.send("ctrl+v")
    time.sleep(0.1)

    if cfg.get("auto_enter", False):
        time.sleep(0.05)
        keyboard.send("enter")

    if old is not None:
        time.sleep(0.1)
        try:
            pyperclip.copy(old)
        except Exception:
            pass

    log.info(f"[INSERT] {text[:50]}")
