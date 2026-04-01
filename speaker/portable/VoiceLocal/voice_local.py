"""
VOICE LOCAL - Голосовой ввод с локальным Whisper (CPU)
Логика записи 1:1 из рабочего voice_claude.py

Горячая клавиша = Push-to-Talk (toggle)
- Нажал → запись
- Нажал ещё раз → Whisper → вставка туда где курсор
"""

import os
import sys
import io
import json
import logging
import tkinter as tk
from tkinter import scrolledtext, ttk

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    BEEP_DIR = sys._MEIPASS
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BEEP_DIR = APP_DIR

CONFIG_FILE = os.path.join(APP_DIR, "voice_config.json")
LOG_FILE = os.path.join(APP_DIR, "voice.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
    encoding="utf-8"
)
log = logging.getLogger("voice")

if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
else:
    sys.stdout = open(LOG_FILE, "a", encoding="utf-8")
    sys.stderr = sys.stdout

cuda_local = os.path.join(APP_DIR, "cuda")
if os.path.isdir(cuda_local):
    os.environ['PATH'] = cuda_local + ";" + os.environ['PATH']
else:
    for cuda_path in [
        os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "cudnn", "bin"),
        os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "cublas", "bin"),
    ]:
        if os.path.isdir(cuda_path):
            os.environ['PATH'] = cuda_path + ";" + os.environ['PATH']

import keyboard
import threading
import time
import pyaudio
import numpy as np
import pyperclip

# === LOCALIZATION ===
TRANSLATIONS = {
    "ru": {
        "tab_voice": " Голос ",
        "tab_settings": " Настройки ",
        "loading": "Загрузка...",
        "ready": "Готов ●",
        "recording": "● ЗАПИСЬ ●",
        "processing": "Обработка...",
        "recognizing": "Распознаю...",
        "model_loading": "Загрузка модели...",
        "mic_section": "Микрофон",
        "mic_label": "Устройство записи:",
        "mic_refresh": "Обновить список",
        "mic_found": "Найдено {} устройств",
        "mic_changed": "Микрофон → device {}",
        "hk_section": "Горячая клавиша",
        "hotkey_label": "Push-to-Talk:",
        "hotkey_apply": "Применить",
        "hotkey_hint": "Можно вписать свою комбинацию, например: ctrl+shift+m",
        "hotkey_applied": "Применено: {}",
        "hotkey_error": "Ошибка: {}",
        "auto_enter": "Нажимать Enter после ввода",
        "model_section": "Модель Whisper",
        "model_hint": "large-v3-turbo = лучшее качество, medium = быстрее",
        "lang_section": "Язык распознавания",
        "ui_lang_section": "Язык интерфейса",
        "restart_btn": "Перезапустить",
        "ptt_short": "Слишком короткая запись",
        "ptt_nothing": "Ничего не распознано",
        "whisper_ok_cuda": "[OK] Whisper CUDA",
        "whisper_ok_cpu": "[OK] Whisper CPU",
        "whisper_no_cuda": "[!] CUDA недоступна: {}",
        "whisper_cpu_fallback": "[LOAD] Использую CPU...",
    },
    "en": {
        "tab_voice": " Voice ",
        "tab_settings": " Settings ",
        "loading": "Loading...",
        "ready": "Ready ●",
        "recording": "● REC ●",
        "processing": "Processing...",
        "recognizing": "Recognizing...",
        "model_loading": "Loading model...",
        "mic_section": "Microphone",
        "mic_label": "Recording device:",
        "mic_refresh": "Refresh list",
        "mic_found": "Found {} devices",
        "mic_changed": "Mic → device {}",
        "hk_section": "Hotkey",
        "hotkey_label": "Push-to-Talk:",
        "hotkey_apply": "Apply",
        "hotkey_hint": "You can type a custom combo, e.g.: ctrl+shift+m",
        "hotkey_applied": "Applied: {}",
        "hotkey_error": "Error: {}",
        "auto_enter": "Press Enter after input",
        "model_section": "Whisper Model",
        "model_hint": "large-v3-turbo = best quality, medium = faster",
        "lang_section": "Recognition language",
        "ui_lang_section": "Interface language",
        "restart_btn": "Restart",
        "ptt_short": "Recording too short",
        "ptt_nothing": "Nothing recognized",
        "whisper_ok_cuda": "[OK] Whisper CUDA",
        "whisper_ok_cpu": "[OK] Whisper CPU",
        "whisper_no_cuda": "[!] CUDA unavailable: {}",
        "whisper_cpu_fallback": "[LOAD] Falling back to CPU...",
    },
    "de": {
        "tab_voice": " Sprache ",
        "tab_settings": " Einstellungen ",
        "loading": "Laden...",
        "ready": "Bereit ●",
        "recording": "● AUFNAHME ●",
        "processing": "Verarbeitung...",
        "recognizing": "Erkenne...",
        "model_loading": "Modell wird geladen...",
        "mic_section": "Mikrofon",
        "mic_label": "Aufnahmegerät:",
        "mic_refresh": "Liste aktualisieren",
        "mic_found": "{} Geräte gefunden",
        "mic_changed": "Mikrofon → Gerät {}",
        "hk_section": "Tastenkürzel",
        "hotkey_label": "Push-to-Talk:",
        "hotkey_apply": "Anwenden",
        "hotkey_hint": "Eigene Kombination möglich, z.B.: ctrl+shift+m",
        "hotkey_applied": "Angewendet: {}",
        "hotkey_error": "Fehler: {}",
        "auto_enter": "Enter nach Eingabe drücken",
        "model_section": "Whisper Modell",
        "model_hint": "large-v3-turbo = beste Qualität, medium = schneller",
        "lang_section": "Erkennungssprache",
        "ui_lang_section": "Oberflächensprache",
        "restart_btn": "Neustart",
        "ptt_short": "Aufnahme zu kurz",
        "ptt_nothing": "Nichts erkannt",
        "whisper_ok_cuda": "[OK] Whisper CUDA",
        "whisper_ok_cpu": "[OK] Whisper CPU",
        "whisper_no_cuda": "[!] CUDA nicht verfügbar: {}",
        "whisper_cpu_fallback": "[LOAD] Verwende CPU...",
    },
    "fr": {
        "tab_voice": " Voix ",
        "tab_settings": " Paramètres ",
        "loading": "Chargement...",
        "ready": "Prêt ●",
        "recording": "● ENR ●",
        "processing": "Traitement...",
        "recognizing": "Reconnaissance...",
        "model_loading": "Chargement du modèle...",
        "mic_section": "Microphone",
        "mic_label": "Périphérique d'enregistrement:",
        "mic_refresh": "Actualiser la liste",
        "mic_found": "{} appareils trouvés",
        "mic_changed": "Micro → appareil {}",
        "hk_section": "Raccourci clavier",
        "hotkey_label": "Push-to-Talk:",
        "hotkey_apply": "Appliquer",
        "hotkey_hint": "Vous pouvez saisir une combinaison, ex: ctrl+shift+m",
        "hotkey_applied": "Appliqué: {}",
        "hotkey_error": "Erreur: {}",
        "auto_enter": "Appuyer sur Entrée après la saisie",
        "model_section": "Modèle Whisper",
        "model_hint": "large-v3-turbo = meilleure qualité, medium = plus rapide",
        "lang_section": "Langue de reconnaissance",
        "ui_lang_section": "Langue de l'interface",
        "restart_btn": "Redémarrer",
        "ptt_short": "Enregistrement trop court",
        "ptt_nothing": "Rien reconnu",
        "whisper_ok_cuda": "[OK] Whisper CUDA",
        "whisper_ok_cpu": "[OK] Whisper CPU",
        "whisper_no_cuda": "[!] CUDA indisponible: {}",
        "whisper_cpu_fallback": "[LOAD] Utilisation du CPU...",
    },
    "es": {
        "tab_voice": " Voz ",
        "tab_settings": " Ajustes ",
        "loading": "Cargando...",
        "ready": "Listo ●",
        "recording": "● GRABANDO ●",
        "processing": "Procesando...",
        "recognizing": "Reconociendo...",
        "model_loading": "Cargando modelo...",
        "mic_section": "Micrófono",
        "mic_label": "Dispositivo de grabación:",
        "mic_refresh": "Actualizar lista",
        "mic_found": "{} dispositivos encontrados",
        "mic_changed": "Micrófono → dispositivo {}",
        "hk_section": "Tecla de acceso rápido",
        "hotkey_label": "Push-to-Talk:",
        "hotkey_apply": "Aplicar",
        "hotkey_hint": "Puedes escribir una combinación, ej: ctrl+shift+m",
        "hotkey_applied": "Aplicado: {}",
        "hotkey_error": "Error: {}",
        "auto_enter": "Presionar Enter después de la entrada",
        "model_section": "Modelo Whisper",
        "model_hint": "large-v3-turbo = mejor calidad, medium = más rápido",
        "lang_section": "Idioma de reconocimiento",
        "ui_lang_section": "Idioma de la interfaz",
        "restart_btn": "Reiniciar",
        "ptt_short": "Grabación demasiado corta",
        "ptt_nothing": "Nada reconocido",
        "whisper_ok_cuda": "[OK] Whisper CUDA",
        "whisper_ok_cpu": "[OK] Whisper CPU",
        "whisper_no_cuda": "[!] CUDA no disponible: {}",
        "whisper_cpu_fallback": "[LOAD] Usando CPU...",
    },
    "pt": {
        "tab_voice": " Voz ",
        "tab_settings": " Configurações ",
        "loading": "Carregando...",
        "ready": "Pronto ●",
        "recording": "● GRAVANDO ●",
        "processing": "Processando...",
        "recognizing": "Reconhecendo...",
        "model_loading": "Carregando modelo...",
        "mic_section": "Microfone",
        "mic_label": "Dispositivo de gravação:",
        "mic_refresh": "Atualizar lista",
        "mic_found": "{} dispositivos encontrados",
        "mic_changed": "Microfone → dispositivo {}",
        "hk_section": "Atalho de teclado",
        "hotkey_label": "Push-to-Talk:",
        "hotkey_apply": "Aplicar",
        "hotkey_hint": "Você pode digitar uma combinação, ex: ctrl+shift+m",
        "hotkey_applied": "Aplicado: {}",
        "hotkey_error": "Erro: {}",
        "auto_enter": "Pressionar Enter após a entrada",
        "model_section": "Modelo Whisper",
        "model_hint": "large-v3-turbo = melhor qualidade, medium = mais rápido",
        "lang_section": "Idioma de reconhecimento",
        "ui_lang_section": "Idioma da interface",
        "restart_btn": "Reiniciar",
        "ptt_short": "Gravação muito curta",
        "ptt_nothing": "Nada reconhecido",
        "whisper_ok_cuda": "[OK] Whisper CUDA",
        "whisper_ok_cpu": "[OK] Whisper CPU",
        "whisper_no_cuda": "[!] CUDA indisponível: {}",
        "whisper_cpu_fallback": "[LOAD] Usando CPU...",
    },
}

UI_LANG_OPTIONS = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "de": "🇩🇪 Deutsch",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "pt": "🇧🇷 Português",
}

RECOGNITION_LANG_OPTIONS = {
    "ru": "🇷🇺 ru — Русский",
    "en": "🇬🇧 en — English",
    "uk": "🇺🇦 uk — Українська",
    "de": "🇩🇪 de — Deutsch",
    "fr": "🇫🇷 fr — Français",
    "es": "🇪🇸 es — Español",
    "it": "🇮🇹 it — Italiano",
    "pt": "🇧🇷 pt — Português",
    "pl": "🇵🇱 pl — Polski",
    "tr": "🇹🇷 tr — Türkçe",
    "ar": "🇸🇦 ar — العربية",
    "ja": "🇯🇵 ja — 日本語",
    "zh": "🇨🇳 zh — 中文",
    "ko": "🇰🇷 ko — 한국어",
    "nl": "🇳🇱 nl — Nederlands",
}

INITIAL_PROMPTS = {
    "ru": "Привет, как дела, хорошо, спасибо",
    "en": "Hello, how are you, good, thanks",
    "de": "Hallo, wie geht es dir, gut, danke",
    "fr": "Bonjour, comment allez-vous, bien, merci",
    "es": "Hola, cómo estás, bien, gracias",
    "pt": "Olá, como vai, bem, obrigado",
    "uk": "Привіт, як справи, добре, дякую",
    "it": "Ciao, come stai, bene, grazie",
    "pl": "Cześć, jak się masz, dobrze, dziękuję",
    "tr": "Merhaba, nasılsın, iyi, teşekkürler",
    "ar": "مرحبا، كيف حالك، جيد، شكرا",
    "ja": "こんにちは、元気ですか、はい、ありがとう",
    "zh": "你好，你好吗，好，谢谢",
    "ko": "안녕하세요, 잘 지내세요, 네, 감사합니다",
    "nl": "Hallo, hoe gaat het, goed, bedankt",
}

def t(key, *args):
    ui_lang = config.get("ui_lang", "ru")
    lang_dict = TRANSLATIONS.get(ui_lang, TRANSLATIONS["ru"])
    text = lang_dict.get(key, TRANSLATIONS["ru"].get(key, key))
    if args:
        try:
            text = text.format(*args)
        except Exception:
            pass
    return text


# === CONFIG ===
DEFAULT_CONFIG = {
    "mic_device_index": 6,
    "hotkey": "scroll lock",
    "language": "ru",
    "ui_lang": "ru",
    "model_size": "large-v3-turbo",
    "auto_enter": False,
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULT_CONFIG, **saved}
        except:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

config = load_config()

# === GUI ===
gui_root = None
gui_text = None
gui_status = None

def gui_log(msg):
    log.info(msg)
    if gui_text and gui_root:
        try:
            gui_root.after(0, _gui_append, msg)
        except:
            pass

def _gui_append(msg):
    try:
        gui_text.configure(state='normal')
        gui_text.insert(tk.END, msg + "\n")
        gui_text.see(tk.END)
        gui_text.configure(state='disabled')
    except:
        pass

def gui_set_status(text, color="#00ff00"):
    if gui_status and gui_root:
        try:
            gui_root.after(0, lambda: gui_status.configure(text=text, fg=color))
        except:
            pass

# === НАСТРОЙКИ (из оригинала) ===
SAMPLE_RATE = 16000
PADDING_SEC = 0.3
CLIPBOARD_RESTORE = True

BEEP_START_FILE = os.path.join(BEEP_DIR, "beep_start.wav")
BEEP_STOP_FILE = os.path.join(BEEP_DIR, "beep_stop.wav")

HALLUCINATION_FILTER = [
    "субтитры", "подписывайтесь", "подписаться", "канал", "лайк",
    "продолжение следует", "конец", "the end", "смотрите",
    "не забудьте", "ставьте", "комментарий",
    "subscribe", "like and subscribe", "don't forget to",
]

# === СОСТОЯНИЕ (из оригинала) ===
whisper_model = None
ptt_recording = False
ptt_frames = []
last_ptt_toggle = 0
stop_all = threading.Event()
current_hotkey_hook = None

# === КОЛЬЦЕВОЙ БУФЕР (из оригинала — 1:1) ===
from collections import deque
RING_BUFFER_SEC = 1.5
RING_CHUNKS = int(RING_BUFFER_SEC * SAMPLE_RATE / 1024)
ring_buffer = deque(maxlen=RING_CHUNKS)
ring_stream = None
ring_running = False
mic_rate = SAMPLE_RATE

def ring_buffer_loop():
    global ring_stream, ring_running, mic_rate
    p = pyaudio.PyAudio()
    mic_idx = config.get("mic_device_index", 6)

    mic_rate = SAMPLE_RATE
    try:
        ring_stream = p.open(
            format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE,
            input=True, input_device_index=mic_idx, frames_per_buffer=1024
        )
        gui_log(f"[RING] mic={mic_idx}, {SAMPLE_RATE}Hz")
    except:
        try:
            info = p.get_device_info_by_index(mic_idx)
            mic_rate = int(info["defaultSampleRate"])
            ring_stream = p.open(
                format=pyaudio.paInt16, channels=1, rate=mic_rate,
                input=True, input_device_index=mic_idx, frames_per_buffer=1024
            )
            gui_log(f"[RING] mic={mic_idx}, {mic_rate}Hz (resample)")
        except Exception as e:
            gui_log(f"[RING] mic error idx={mic_idx}: {e}")
            p.terminate()
            return

    ring_running = True
    gui_log(f"[RING] buffer {RING_BUFFER_SEC}s active")
    while not stop_all.is_set():
        try:
            data = ring_stream.read(1024, exception_on_overflow=False)
            if mic_rate != SAMPLE_RATE:
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                n_out = int(len(samples) * SAMPLE_RATE / mic_rate)
                resampled = np.interp(
                    np.linspace(0, len(samples), n_out, endpoint=False),
                    np.arange(len(samples)),
                    samples
                ).astype(np.int16)
                data = resampled.tobytes()
            ring_buffer.append(data)
            if ptt_recording:
                ptt_frames.append(data)
        except:
            break

    ring_running = False
    ring_stream.stop_stream()
    ring_stream.close()
    ring_stream = None
    p.terminate()


# === WHISPER LOCAL ===
def load_whisper():
    global whisper_model
    if whisper_model is not None:
        return

    model_name = config.get("model_size", "large-v3-turbo")
    local_model = os.path.join(APP_DIR, "model")
    if os.path.isdir(local_model):
        model_path = local_model
        gui_log(f"[LOAD] Loading Whisper from model/...")
    else:
        model_path = model_name
        gui_log(f"[LOAD] Loading Whisper {model_name}...")
    gui_set_status(t("model_loading"), "#ffaa00")

    from faster_whisper import WhisperModel
    try:
        whisper_model = WhisperModel(model_path, device="cuda", compute_type="float16")
        gui_log(t("whisper_ok_cuda"))
    except Exception as e:
        gui_log(t("whisper_no_cuda", e))
        gui_log(t("whisper_cpu_fallback"))
        whisper_model = WhisperModel(model_path, device="cpu", compute_type="int8")
        gui_log(t("whisper_ok_cpu"))

    hk = config.get("hotkey", "scroll lock")
    gui_set_status(f"{t('ready')} {hk.title()}", "#00ff00")


def transcribe(audio_np):
    global whisper_model
    if audio_np is None or len(audio_np) < 1000:
        return ""
    if whisper_model is None:
        load_whisper()

    lang = config.get("language", "ru")
    initial_prompt = INITIAL_PROMPTS.get(lang, "")
    segments, _ = whisper_model.transcribe(
        audio_np,
        language=lang,
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=initial_prompt
    )
    text = " ".join([s.text for s in segments]).strip().lower()
    text = text.replace(",", "").replace(".", "").replace("!", "").replace("?", "")
    text = text.replace(":", "").replace(";", "").replace("—", "").replace("–", "")
    text = text.replace("«", "").replace("»", "")

    for spam in HALLUCINATION_FILTER:
        if spam in text:
            return ""
    return text


# === ЗВУКИ (из оригинала) ===
def play_beep(beep_file):
    if not os.path.exists(beep_file):
        return
    try:
        import wave as _wave
        wf = _wave.open(beep_file, 'rb')
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        data = wf.readframes(4096)
        while data:
            stream.write(data)
            data = wf.readframes(4096)
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf.close()
    except:
        pass


# === ВСТАВКА ТЕКСТА ===
def paste_text(text):
    old_clipboard = None
    if CLIPBOARD_RESTORE:
        try:
            old_clipboard = pyperclip.paste()
        except:
            old_clipboard = None

    pyperclip.copy(text)
    time.sleep(0.1)
    keyboard.send("ctrl+v")
    time.sleep(0.15)

    if config.get("auto_enter", False):
        time.sleep(0.1)
        keyboard.send("enter")

    if CLIPBOARD_RESTORE and old_clipboard is not None:
        time.sleep(0.2)
        try:
            pyperclip.copy(old_clipboard)
        except:
            pass


# === PTT (из оригинала — 1:1) ===
def ptt_process():
    global ptt_frames

    if not ptt_frames or len(ptt_frames) < 10:
        gui_log(f"[PTT] {t('ptt_short')}")
        hk = config.get("hotkey", "scroll lock")
        gui_set_status(f"{t('ready')} {hk.title()}", "#00ff00")
        return

    duration = len(ptt_frames) * 1024 / SAMPLE_RATE
    gui_log(f"[PTT] {duration:.1f}s recorded")
    gui_set_status(t("recognizing"), "#ffaa00")

    audio_data = b''.join(ptt_frames)
    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

    padding_samples = int(PADDING_SEC * SAMPLE_RATE)
    audio_np = np.concatenate([
        np.zeros(padding_samples, dtype=np.float32),
        audio_np,
        np.zeros(padding_samples, dtype=np.float32)
    ])

    text = transcribe(audio_np)

    hk = config.get("hotkey", "scroll lock")
    if not text:
        gui_log(f"[PTT] {t('ptt_nothing')}")
        gui_set_status(f"{t('ready')} {hk.title()}", "#00ff00")
        return

    words = text.split()
    cleaned = []
    for i, word in enumerate(words):
        if i < 3 or word != words[i-1] or word != words[i-2]:
            cleaned.append(word)
    text = " ".join(cleaned)

    if not text:
        gui_set_status(f"{t('ready')} {hk.title()}", "#00ff00")
        return

    gui_log(f">>> {text}")
    gui_set_status(f"{t('ready')} {hk.title()}", "#00ff00")

    paste_text(text)


def ptt_toggle():
    global ptt_recording, last_ptt_toggle, ptt_frames

    if time.time() - last_ptt_toggle < 0.3:
        return
    last_ptt_toggle = time.time()

    try:
        if not ptt_recording:
            ptt_frames = list(ring_buffer)
            ptt_recording = True
            threading.Thread(target=play_beep, args=(BEEP_START_FILE,), daemon=True).start()
            gui_log("[REC] ●●●")
            gui_set_status(t("recording"), "#ff0000")
        else:
            ptt_recording = False
            threading.Thread(target=play_beep, args=(BEEP_STOP_FILE,), daemon=True).start()
            gui_log("[STOP]")
            gui_set_status(t("processing"), "#ffaa00")
            threading.Thread(target=ptt_process, daemon=True).start()
    except Exception as e:
        gui_log(f"[PTT] error: {e}")
        ptt_recording = False
        hk = config.get("hotkey", "scroll lock")
        gui_set_status(f"{t('ready')} {hk.title()}", "#00ff00")


def register_hotkey():
    global current_hotkey_hook
    hk = config.get("hotkey", "scroll lock")
    if current_hotkey_hook is not None:
        try:
            keyboard.remove_hotkey(current_hotkey_hook)
        except:
            pass
    current_hotkey_hook = keyboard.add_hotkey(hk, ptt_toggle, suppress=True)
    gui_log(f"[HOTKEY] {hk.title()}")


# === СПИСОК МИКРОФОНОВ ===
def get_microphone_list():
    p = pyaudio.PyAudio()
    mics = []
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0 and info.get("hostApi", 99) == 0:
                name = info.get("name", f"Device {i}")
                mics.append((i, name))
        except:
            continue
    p.terminate()
    return mics


# === SINGLE INSTANCE ===
def check_single_instance():
    if not getattr(sys, 'frozen', False):
        return
    import subprocess
    exe_name = os.path.basename(sys.executable)
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV"],
        capture_output=True, text=True
    )
    if result.stdout.count(exe_name) > 1:
        log.info("[!] Already running — exit")
        sys.exit(0)


# === HOTKEY OPTIONS ===
HOTKEY_OPTIONS = [
    "scroll lock", "pause", "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
    "ctrl+shift+r", "ctrl+shift+v", "ctrl+alt+r", "ctrl+alt+v",
    "alt+f9", "ctrl+f9",
]

MODEL_OPTIONS = ["large-v3-turbo", "medium", "small", "base", "tiny"]


# === GUI ===
def create_gui():
    global gui_root, gui_text, gui_status

    gui_root = tk.Tk()
    gui_root.title("Voice Local")
    gui_root.configure(bg="#1e1e1e")
    gui_root.attributes("-topmost", True)
    gui_root.resizable(True, True)

    screen_w = gui_root.winfo_screenwidth()
    screen_h = gui_root.winfo_screenheight()
    win_w, win_h = 440, 380
    x = screen_w - win_w - 10
    y = screen_h - win_h - 60
    gui_root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    gui_root.attributes("-alpha", 0.92)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TNotebook", background="#1e1e1e", borderwidth=0)
    style.configure("Dark.TNotebook.Tab", background="#333", foreground="#ccc",
                     padding=[10, 4], font=("Consolas", 9))
    style.map("Dark.TNotebook.Tab",
              background=[("selected", "#1e1e1e")],
              foreground=[("selected", "#fff")])
    style.configure("Dark.TFrame", background="#1e1e1e")

    notebook = ttk.Notebook(gui_root, style="Dark.TNotebook")
    notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    # === TAB 1: Voice ===
    main_tab = ttk.Frame(notebook, style="Dark.TFrame")
    notebook.add(main_tab, text=t("tab_voice"))

    top_frame = tk.Frame(main_tab, bg="#1e1e1e")
    top_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

    gui_status = tk.Label(
        top_frame, text=t("loading"), font=("Consolas", 11, "bold"),
        fg="#ffaa00", bg="#1e1e1e", anchor="w"
    )
    gui_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

    btn_frame = tk.Frame(top_frame, bg="#1e1e1e")
    btn_frame.pack(side=tk.RIGHT)

    def do_restart():
        gui_log("[RESTART]")
        import subprocess as _sp
        _sp.Popen([sys.executable] + sys.argv)
        gui_root.destroy()
        os._exit(0)

    def do_clear():
        gui_text.configure(state='normal')
        gui_text.delete(1.0, tk.END)
        gui_text.configure(state='disabled')

    def do_quit():
        gui_root.destroy()
        os._exit(0)

    for txt, cmd, bg in [("🗑", do_clear, "#333"), ("↻", do_restart, "#333"), ("✕", do_quit, "#550000")]:
        tk.Button(
            btn_frame, text=txt, command=cmd,
            font=("Consolas", 10), bg=bg, fg="#fff",
            relief="flat", width=3, cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)

    gui_text = scrolledtext.ScrolledText(
        main_tab, wrap=tk.WORD, font=("Consolas", 9),
        bg="#0d0d0d", fg="#cccccc", insertbackground="#fff",
        relief="flat", state='disabled', height=10
    )
    gui_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # === TAB 2: Settings ===
    settings_tab = ttk.Frame(notebook, style="Dark.TFrame")
    notebook.add(settings_tab, text=t("tab_settings"))

    settings_canvas = tk.Canvas(settings_tab, bg="#1e1e1e", highlightthickness=0)
    settings_inner = tk.Frame(settings_canvas, bg="#1e1e1e")
    settings_canvas.pack(fill=tk.BOTH, expand=True)
    settings_canvas.create_window((0, 0), window=settings_inner, anchor="nw")
    settings_inner.bind("<Configure>", lambda e: settings_canvas.configure(scrollregion=settings_canvas.bbox("all")))

    def _on_mousewheel(event):
        settings_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    settings_canvas.bind("<MouseWheel>", _on_mousewheel)
    settings_inner.bind("<MouseWheel>", _on_mousewheel)

    # --- Микрофон ---
    mic_frame = tk.LabelFrame(
        settings_inner, text=t("mic_section"), font=("Consolas", 9, "bold"),
        bg="#1e1e1e", fg="#aaa", padx=10, pady=8
    )
    mic_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

    mics = get_microphone_list()
    mic_names = [f"[{idx}] {name}" for idx, name in mics]
    mic_indices = [idx for idx, name in mics]

    current_mic_idx = config.get("mic_device_index", 6)
    current_mic_display = 0
    for i, idx in enumerate(mic_indices):
        if idx == current_mic_idx:
            current_mic_display = i
            break

    mic_var = tk.StringVar(value=mic_names[current_mic_display] if mic_names else "")

    tk.Label(mic_frame, text=t("mic_label"), bg="#1e1e1e", fg="#ccc",
             font=("Consolas", 9)).pack(anchor="w")

    mic_combo = ttk.Combobox(
        mic_frame, textvariable=mic_var, values=mic_names,
        state="readonly", font=("Consolas", 9), width=45
    )
    mic_combo.pack(fill=tk.X, pady=(4, 0))

    mic_bottom = tk.Frame(mic_frame, bg="#1e1e1e")
    mic_bottom.pack(fill=tk.X, pady=(6, 0))

    mic_status_label = tk.Label(mic_bottom, text="", bg="#1e1e1e", fg="#00ff00", font=("Consolas", 8))
    mic_status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, anchor="w")

    mic_restart_btn = tk.Button(
        mic_bottom, text=t("restart_btn"), command=lambda: do_restart(),
        font=("Consolas", 9, "bold"), bg="#664400", fg="#fff", relief="flat", cursor="hand2"
    )

    def on_mic_change(event=None):
        sel = mic_combo.current()
        if 0 <= sel < len(mic_indices):
            new_idx = mic_indices[sel]
            config["mic_device_index"] = new_idx
            save_config(config)
            mic_status_label.configure(text=t("mic_changed", new_idx), fg="#ffaa00")
            mic_restart_btn.pack(side=tk.RIGHT, padx=(6, 0))
            gui_log(f"[CONFIG] mic → {new_idx}")

    mic_combo.bind("<<ComboboxSelected>>", on_mic_change)

    def do_refresh_mics():
        nonlocal mics, mic_names, mic_indices
        mics = get_microphone_list()
        mic_names = [f"[{idx}] {name}" for idx, name in mics]
        mic_indices = [idx for idx, name in mics]
        mic_combo['values'] = mic_names
        mic_status_label.configure(text=t("mic_found", len(mics)), fg="#00ff00")

    tk.Button(
        mic_frame, text=t("mic_refresh"), command=do_refresh_mics,
        font=("Consolas", 8), bg="#333", fg="#fff", relief="flat", cursor="hand2"
    ).pack(anchor="w", pady=(4, 0))

    # --- Горячая клавиша ---
    hk_frame = tk.LabelFrame(
        settings_inner, text=t("hk_section"), font=("Consolas", 9, "bold"),
        bg="#1e1e1e", fg="#aaa", padx=10, pady=8
    )
    hk_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

    current_hk = config.get("hotkey", "scroll lock")
    hk_var = tk.StringVar(value=current_hk)

    tk.Label(hk_frame, text=t("hotkey_label"), bg="#1e1e1e", fg="#ccc",
             font=("Consolas", 9)).pack(anchor="w")

    hk_combo = ttk.Combobox(
        hk_frame, textvariable=hk_var, values=HOTKEY_OPTIONS,
        font=("Consolas", 9), width=25
    )
    hk_combo.pack(fill=tk.X, pady=(4, 0))

    hk_status_label = tk.Label(hk_frame, text="", bg="#1e1e1e", fg="#00ff00", font=("Consolas", 8))
    hk_status_label.pack(anchor="w", pady=(4, 0))

    def on_hk_apply():
        new_hk = hk_var.get().strip()
        if not new_hk:
            return
        config["hotkey"] = new_hk
        save_config(config)
        try:
            register_hotkey()
            hk_status_label.configure(text=t("hotkey_applied", new_hk), fg="#00ff00")
            gui_set_status(f"{t('ready')} {new_hk.title()}", "#00ff00")
        except Exception as e:
            hk_status_label.configure(text=t("hotkey_error", e), fg="#ff4444")

    tk.Button(
        hk_frame, text=t("hotkey_apply"), command=on_hk_apply,
        font=("Consolas", 8), bg="#333", fg="#fff", relief="flat", cursor="hand2"
    ).pack(anchor="w", pady=(4, 0))

    tk.Label(
        settings_inner, text=t("hotkey_hint"),
        bg="#1e1e1e", fg="#666", font=("Consolas", 8)
    ).pack(anchor="w", padx=14, pady=(2, 5))

    # --- Auto Enter ---
    enter_var = tk.BooleanVar(value=config.get("auto_enter", False))

    def on_enter_toggle():
        config["auto_enter"] = enter_var.get()
        save_config(config)

    tk.Checkbutton(
        settings_inner, text=t("auto_enter"),
        variable=enter_var, command=on_enter_toggle,
        font=("Consolas", 9), bg="#1e1e1e", fg="#ddd",
        selectcolor="#333", activebackground="#1e1e1e", activeforeground="#ddd",
        cursor="hand2"
    ).pack(anchor="w", padx=10, pady=(5, 5))

    # --- Модель ---
    model_frame = tk.LabelFrame(
        settings_inner, text=t("model_section"), font=("Consolas", 9, "bold"),
        bg="#1e1e1e", fg="#aaa", padx=10, pady=8
    )
    model_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

    tk.Label(model_frame, text=t("model_hint"),
             bg="#1e1e1e", fg="#888", font=("Consolas", 8)).pack(anchor="w")

    model_var = tk.StringVar(value=config.get("model_size", "large-v3-turbo"))
    model_combo = ttk.Combobox(
        model_frame, textvariable=model_var, values=MODEL_OPTIONS,
        font=("Consolas", 9), width=20, state="readonly"
    )
    model_combo.pack(anchor="w", pady=(4, 0))

    model_restart_btn = tk.Button(
        model_frame, text=t("restart_btn"), command=lambda: do_restart(),
        font=("Consolas", 9, "bold"), bg="#664400", fg="#fff", relief="flat", cursor="hand2"
    )

    def on_model_change(event=None):
        config["model_size"] = model_var.get()
        save_config(config)
        gui_log(f"[CONFIG] model → {model_var.get()}")
        model_restart_btn.pack(anchor="w", pady=(4, 0))

    model_combo.bind("<<ComboboxSelected>>", on_model_change)

    # --- Язык распознавания ---
    lang_frame = tk.LabelFrame(
        settings_inner, text=t("lang_section"), font=("Consolas", 9, "bold"),
        bg="#1e1e1e", fg="#aaa", padx=10, pady=8
    )
    lang_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

    rec_lang_codes = list(RECOGNITION_LANG_OPTIONS.keys())
    rec_lang_labels = list(RECOGNITION_LANG_OPTIONS.values())
    current_lang = config.get("language", "ru")
    current_lang_idx = rec_lang_codes.index(current_lang) if current_lang in rec_lang_codes else 0

    lang_var = tk.StringVar(value=rec_lang_labels[current_lang_idx])
    lang_combo = ttk.Combobox(
        lang_frame, textvariable=lang_var, values=rec_lang_labels,
        font=("Consolas", 9), width=28, state="readonly"
    )
    lang_combo.pack(anchor="w", pady=(4, 0))

    def on_lang_change(event=None):
        idx = lang_combo.current()
        if 0 <= idx < len(rec_lang_codes):
            config["language"] = rec_lang_codes[idx]
            save_config(config)
            gui_log(f"[CONFIG] lang → {rec_lang_codes[idx]}")

    lang_combo.bind("<<ComboboxSelected>>", on_lang_change)

    # --- Язык интерфейса ---
    ui_lang_frame = tk.LabelFrame(
        settings_inner, text=t("ui_lang_section"), font=("Consolas", 9, "bold"),
        bg="#1e1e1e", fg="#aaa", padx=10, pady=8
    )
    ui_lang_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

    ui_lang_codes = list(UI_LANG_OPTIONS.keys())
    ui_lang_labels = list(UI_LANG_OPTIONS.values())
    current_ui_lang = config.get("ui_lang", "ru")
    current_ui_idx = ui_lang_codes.index(current_ui_lang) if current_ui_lang in ui_lang_codes else 0

    ui_lang_var = tk.StringVar(value=ui_lang_labels[current_ui_idx])
    ui_lang_combo = ttk.Combobox(
        ui_lang_frame, textvariable=ui_lang_var, values=ui_lang_labels,
        font=("Consolas", 9), width=20, state="readonly"
    )
    ui_lang_combo.pack(anchor="w", pady=(4, 0))

    ui_lang_restart_btn = tk.Button(
        ui_lang_frame, text=t("restart_btn"), command=lambda: do_restart(),
        font=("Consolas", 9, "bold"), bg="#664400", fg="#fff", relief="flat", cursor="hand2"
    )

    def on_ui_lang_change(event=None):
        idx = ui_lang_combo.current()
        if 0 <= idx < len(ui_lang_codes):
            config["ui_lang"] = ui_lang_codes[idx]
            save_config(config)
            gui_log(f"[CONFIG] ui_lang → {ui_lang_codes[idx]}")
            ui_lang_restart_btn.pack(anchor="w", pady=(4, 0))

    ui_lang_combo.bind("<<ComboboxSelected>>", on_ui_lang_change)

    gui_root.protocol("WM_DELETE_WINDOW", lambda: gui_root.iconify())
    return gui_root


# === MAIN ===
def main():
    check_single_instance()
    root = create_gui()

    hk = config.get("hotkey", "scroll lock")
    gui_log("Voice Local")
    gui_log(f"{hk.title()} = Push-to-Talk")

    def init_worker():
        load_whisper()
        threading.Thread(target=ring_buffer_loop, daemon=True).start()
        time.sleep(0.5)
        register_hotkey()
        gui_log("Ready!")

    threading.Thread(target=init_worker, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_all.set()
    except Exception as e:
        log.error(f"Fatal: {e}")
        import traceback
        log.error(traceback.format_exc())
