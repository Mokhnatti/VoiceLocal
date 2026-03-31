"""
Движок транскрипции на базе faster-whisper.
CUDA если доступна, иначе CPU. Фильтр галлюцинаций.
"""

import threading
import re
import os
import sys
from faster_whisper import WhisperModel
from app.config import get_config, VOICE_PUNCT_MAP, HALLUCINATION_FILTER


def _resolve_model_path(model_name: str) -> str:
    """Если рядом с exe есть папка model/ — использовать её."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local = os.path.join(base, "model")
    if os.path.isdir(local):
        return local
    return model_name


class TranscriptionEngine:
    def __init__(self, on_ready=None, on_error=None):
        self._model: WhisperModel | None = None
        self._loading = False
        self._on_ready = on_ready
        self._on_error = on_error
        self._lock = threading.Lock()

    def load_async(self):
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        self._loading = True
        cfg = get_config()
        model_name = cfg.get("model", "large-v3-turbo")
        model_path = _resolve_model_path(model_name)
        use_cuda = cfg.get("use_cuda", True)

        try:
            if use_cuda:
                try:
                    model = WhisperModel(model_path, device="cuda", compute_type="float16")
                except Exception:
                    model = WhisperModel(model_path, device="cpu", compute_type="int8", cpu_threads=0)
            else:
                model = WhisperModel(model_path, device="cpu", compute_type="int8", cpu_threads=0)

            with self._lock:
                self._model = model
            if self._on_ready:
                self._on_ready()
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
        finally:
            self._loading = False

    @property
    def is_ready(self) -> bool:
        with self._lock:
            return self._model is not None

    @property
    def is_loading(self) -> bool:
        return self._loading

    def transcribe(self, audio_np) -> str:
        with self._lock:
            model = self._model
        if model is None:
            return ""

        cfg = get_config()
        language = cfg.get("language", "ru")
        beam_size = cfg.get("beam_size", 1)

        segments, _ = model.transcribe(
            audio_np,
            language=language,
            beam_size=beam_size,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),
            condition_on_previous_text=False,
            initial_prompt="Привет, как дела, хорошо, спасибо",
        )

        parts = []
        for seg in segments:
            parts.append(seg.text.strip())
        raw = " ".join(parts).strip()

        if not raw:
            return ""

        return self._process(raw, cfg)

    def _process(self, text: str, cfg) -> str:
        if cfg.get("strip_punctuation", True) and not cfg.get("auto_punctuation", False):
            text = text.lower()
            text = re.sub(r"[.,!?:;—–«»]", "", text)
            text = re.sub(r"\s{2,}", " ", text).strip()

        for spam in HALLUCINATION_FILTER:
            if spam in text.lower():
                return ""

        words = text.split()
        cleaned = []
        for i, word in enumerate(words):
            if i < 3 or word != words[i-1] or word != words[i-2]:
                cleaned.append(word)
        text = " ".join(cleaned)

        if cfg.get("voice_commands", False):
            text = self._apply_voice_commands(text)

        if cfg.get("capitalize_sentences", False):
            text = self._capitalize(text)

        return text.strip()

    def _apply_voice_commands(self, text: str) -> str:
        sorted_cmds = sorted(VOICE_PUNCT_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        for command, symbol in sorted_cmds:
            pattern = rf"(?<!\w){re.escape(command)}(?!\w)"
            if symbol == "__DELETE__":
                text = re.sub(r"\w+\s*" + pattern, "", text, flags=re.IGNORECASE)
            else:
                text = re.sub(pattern, symbol, text, flags=re.IGNORECASE)
        text = re.sub(r"\s+([.,;:!?»)])", r"\1", text)
        text = re.sub(r"([«(])\s+", r"\1", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    def _capitalize(self, text: str) -> str:
        if not text:
            return text
        text = text[0].upper() + text[1:]
        text = re.sub(r"([.!?]\s+)([а-яёa-z])", lambda m: m.group(1) + m.group(2).upper(), text)
        return text

    def reload(self):
        with self._lock:
            self._model = None
        self.load_async()
