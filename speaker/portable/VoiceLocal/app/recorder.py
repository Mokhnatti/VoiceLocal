"""
Запись аудио с микрофона.
Ring buffer — постоянно крутится, захватывает N секунд ДО нажатия.
При старте записи кольцевой буфер добавляется в начало.
"""

import threading
import numpy as np
import sounddevice as sd
from collections import deque
from app.config import get_config

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"
CHUNK = 1024


class AudioRecorder:
    def __init__(self, device_index=None):
        self.device_index = device_index
        self._lock = threading.Lock()
        self._stream = None
        self._recording = False
        self._ptt_frames = []
        self._ring = deque()
        self._ring_maxlen = 0
        self._update_ring_size()

    def _update_ring_size(self):
        cfg = get_config()
        sec = cfg.get("ring_buffer_sec", 1.5)
        chunks = int(sec * SAMPLE_RATE / CHUNK)
        self._ring = deque(self._ring, maxlen=max(1, chunks))
        self._ring_maxlen = chunks

    def start_background(self):
        """Запустить постоянный поток ring buffer."""
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                device=self.device_index,
                callback=self._callback,
                blocksize=CHUNK,
            )
            self._stream.start()
        except Exception as e:
            self._stream = None
            raise e

    def stop_background(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, indata, frames, time, status):
        chunk = indata.copy().flatten()
        with self._lock:
            self._ring.append(chunk)
            if self._recording:
                self._ptt_frames.append(chunk)

    def start_recording(self):
        """Начать запись — сохранить ring buffer как преамбулу."""
        self._update_ring_size()
        with self._lock:
            self._ptt_frames = list(self._ring)
            self._recording = True

    def stop_recording(self) -> np.ndarray | None:
        """Остановить запись, вернуть numpy array float32 16kHz."""
        with self._lock:
            self._recording = False
            frames = self._ptt_frames[:]
            self._ptt_frames = []

        if not frames:
            return None
        return np.concatenate(frames)

    @property
    def duration_seconds(self) -> float:
        with self._lock:
            total = sum(len(f) for f in self._ptt_frames)
        return total / SAMPLE_RATE

    def get_devices(self) -> list[dict]:
        devices = []
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                devices.append({"index": i, "name": d["name"]})
        return devices

    def update_device(self, device_index):
        """Поменять микрофон на лету."""
        was_running = self._stream is not None
        self.stop_background()
        self.device_index = device_index
        if was_running:
            self.start_background()
