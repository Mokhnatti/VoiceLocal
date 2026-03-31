"""
Глобальный хоткей — работает даже когда окно не в фокусе.
Использует pynput. Поддерживает Toggle и Hold режимы.
"""

import threading
from pynput import keyboard
from pynput.keyboard import Key, KeyCode
from app.config import get_config

KEY_MAP = {
    "home": Key.home,
    "end": Key.end,
    "insert": Key.insert,
    "caps_lock": Key.caps_lock,
    "scroll_lock": Key.scroll_lock,
    "pause": Key.pause,
    "num_lock": Key.num_lock,
    "print_screen": Key.print_screen,
    "f13": Key.f13,
    "f14": Key.f14,
    "f15": Key.f15,
    "f16": Key.f16,
}


def parse_hotkey(hotkey_str: str):
    s = hotkey_str.strip().lower().replace(" ", "_")
    if s in KEY_MAP:
        return KEY_MAP[s]
    if len(s) == 1:
        return KeyCode.from_char(s)
    return Key.scroll_lock


class HotkeyListener:
    def __init__(self, on_press=None, on_release=None):
        self.on_press_cb = on_press
        self.on_release_cb = on_release
        self._listener = None
        self._pressed = False
        self._lock = threading.Lock()
        self._target_key = None

    def start(self):
        self._reload_key()
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _reload_key(self):
        cfg = get_config()
        self._target_key = parse_hotkey(cfg.get("hotkey", "scroll_lock"))

    def update_key(self):
        self._reload_key()
        with self._lock:
            self._pressed = False

    def _keys_match(self, key) -> bool:
        target = self._target_key
        if target is None:
            return False
        try:
            if isinstance(target, Key):
                return key == target
            if isinstance(target, KeyCode):
                if isinstance(key, KeyCode):
                    return key.char == target.char
        except Exception:
            pass
        return False

    def _on_press(self, key):
        if self._keys_match(key):
            with self._lock:
                if not self._pressed:
                    self._pressed = True
                    if self.on_press_cb:
                        threading.Thread(target=self.on_press_cb, daemon=True).start()

    def _on_release(self, key):
        if self._keys_match(key):
            with self._lock:
                if self._pressed:
                    self._pressed = False
                    if self.on_release_cb:
                        threading.Thread(target=self.on_release_cb, daemon=True).start()
