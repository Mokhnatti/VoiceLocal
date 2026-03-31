"""
Контроллер Push-to-Talk.
Поддерживает два режима:
  toggle — нажал = начало, нажал ещё раз = стоп
  hold   — зажал = запись, отпустил = стоп
"""

import os
import sys
import threading
from app.recorder import AudioRecorder
from app.transcriber import TranscriptionEngine
from app.hotkey import HotkeyListener
from app.inserter import insert_text
from app.config import get_config

if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BEEP_START = os.path.join(_APP_DIR, "beep_start.wav")
BEEP_STOP  = os.path.join(_APP_DIR, "beep_stop.wav")


def _play_beep(path: str):
    if not os.path.exists(path):
        return
    try:
        import wave as _wave, pyaudio as _pa
        wf = _wave.open(path, 'rb')
        p = _pa.PyAudio()
        s = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                   channels=wf.getnchannels(), rate=wf.getframerate(), output=True)
        data = wf.readframes(4096)
        while data:
            s.write(data)
            data = wf.readframes(4096)
        s.stop_stream(); s.close(); p.terminate(); wf.close()
    except Exception:
        pass


class PTTController:
    def __init__(
        self,
        on_state_change=None,
        on_text=None,
        on_model_ready=None,
        on_model_loading=None,
        on_error=None,
        on_duration=None,
    ):
        self.on_state_change = on_state_change or (lambda s: None)
        self.on_text = on_text or (lambda t: None)
        self.on_model_ready = on_model_ready or (lambda: None)
        self.on_model_loading = on_model_loading or (lambda: None)
        self.on_error = on_error or (lambda e: None)
        self.on_duration = on_duration or (lambda d: None)

        cfg = get_config()
        self._recorder = AudioRecorder(device_index=cfg.get("device_index"))
        self._engine = TranscriptionEngine(
            on_ready=self._model_ready,
            on_error=lambda e: self.on_error(f"Ошибка загрузки модели: {e}"),
        )
        self._hotkey = HotkeyListener(
            on_press=self._key_pressed,
            on_release=self._key_released,
        )

        self._state = "idle"
        self._processing = False
        self._duration_timer = None

    def start(self):
        self.on_model_loading()
        self._engine.load_async()
        self._recorder.start_background()
        self._hotkey.start()

    def stop(self):
        self._hotkey.stop()
        self._stop_duration_timer()
        self._recorder.stop_background()
        self._set_state("idle")

    def _model_ready(self):
        self._set_state("idle")
        self.on_model_ready()

    def reload_model(self):
        self._set_state("idle")
        self.on_model_loading()
        self._engine.reload()

    def update_hotkey(self):
        self._hotkey.update_key()

    def update_device(self):
        cfg = get_config()
        self._recorder.update_device(cfg.get("device_index"))

    def _key_pressed(self):
        if not self._engine.is_ready:
            self.on_error("Модель ещё загружается...")
            return
        if self._processing:
            return

        cfg = get_config()
        mode = cfg.get("ptt_mode", "toggle")

        if mode == "toggle":
            if self._state == "recording":
                self._stop_recording()
            elif self._state == "idle":
                self._start_recording()
        else:
            if self._state == "idle":
                self._start_recording()

    def _key_released(self):
        cfg = get_config()
        mode = cfg.get("ptt_mode", "toggle")
        if mode == "hold" and self._state == "recording":
            self._stop_recording()

    def _start_recording(self):
        self._recorder.start_recording()
        self._set_state("recording")
        self._start_duration_timer()
        threading.Thread(target=_play_beep, args=(BEEP_START,), daemon=True).start()

    def _stop_recording(self):
        self._stop_duration_timer()
        threading.Thread(target=_play_beep, args=(BEEP_STOP,), daemon=True).start()
        audio = self._recorder.stop_recording()
        self._set_state("processing")

        if audio is None or len(audio) < SAMPLE_RATE * 0.1:
            self._set_state("idle")
            return

        threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()

    def _transcribe(self, audio_np):
        self._processing = True
        try:
            text = self._engine.transcribe(audio_np)
            if text:
                self.on_text(text)
                insert_text(text)
        except Exception as e:
            self.on_error(f"Ошибка транскрипции: {e}")
        finally:
            self._processing = False
            self._set_state("idle")

    def _start_duration_timer(self):
        self._stop_duration_timer()
        t = threading.Thread(target=self._tick_duration, daemon=True)
        self._duration_timer = t
        t.start()

    def _stop_duration_timer(self):
        self._duration_timer = None

    def _tick_duration(self):
        import time
        me = self._duration_timer
        while self._state == "recording" and threading.current_thread() is me:
            self.on_duration(self._recorder.duration_seconds)
            time.sleep(0.1)

    def _set_state(self, state: str):
        self._state = state
        self.on_state_change(state)

    @property
    def state(self) -> str:
        return self._state

    def get_microphone_list(self) -> list[dict]:
        return self._recorder.get_devices()


SAMPLE_RATE = 16000
