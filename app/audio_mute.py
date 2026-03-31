"""
Мут/размут микрофонов через Windows Audio API (pycaw).
При старте записи — мутить все микрофоны кроме выбранного.
При стопе / выходе — размутить всё.
"""

import logging

log = logging.getLogger("voice")

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    _PYCAW_OK = True
except ImportError:
    _PYCAW_OK = False
    log.warning("[MUTE] pycaw не установлен — функция мута недоступна")


def _get_all_mic_endpoints():
    """Список всех активных микрофонных устройств (pycaw)."""
    if not _PYCAW_OK:
        return []
    try:
        devices = AudioUtilities.GetAllDevices()
        mics = []
        for d in devices:
            if d.state == 1 and d.flow == 1:  # state=Active, flow=Capture
                try:
                    iface = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    vol = iface.QueryInterface(IAudioEndpointVolume)
                    mics.append((d.id, d.FriendlyName, vol))
                except Exception:
                    pass
        return mics
    except Exception as e:
        log.warning(f"[MUTE] Ошибка получения устройств: {e}")
        return []


def _find_selected_device_id(device_index: int | None) -> str | None:
    """Найти Windows device ID по sounddevice индексу."""
    if not _PYCAW_OK:
        return None
    if device_index is None:
        return None
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if 0 <= device_index < len(devices):
            target_name = devices[device_index]["name"]
            for dev_id, friendly_name, _ in _get_all_mic_endpoints():
                if target_name.lower() in friendly_name.lower() or friendly_name.lower() in target_name.lower():
                    return dev_id
    except Exception as e:
        log.warning(f"[MUTE] Ошибка поиска устройства: {e}")
    return None


# Кэш: какие устройства мы замутили (чтобы точно их и размутить)
_muted_ids: list[str] = []


def mute_others(selected_device_index: int | None) -> bool:
    """
    Замутить все микрофоны кроме выбранного.
    Возвращает True если хоть что-то замутили.
    """
    global _muted_ids
    if not _PYCAW_OK:
        return False

    selected_id = _find_selected_device_id(selected_device_index)
    endpoints = _get_all_mic_endpoints()

    _muted_ids = []
    for dev_id, name, vol in endpoints:
        if selected_id and dev_id == selected_id:
            continue
        try:
            already_muted = vol.GetMute()
            if not already_muted:
                vol.SetMute(1, None)
                _muted_ids.append(dev_id)
                log.info(f"[MUTE] Замучено: {name}")
        except Exception as e:
            log.warning(f"[MUTE] Ошибка мута {name}: {e}")

    return len(_muted_ids) > 0


def unmute_all():
    """Размутить все микрофоны которые мы замутили."""
    global _muted_ids
    if not _PYCAW_OK or not _muted_ids:
        return

    endpoints = _get_all_mic_endpoints()
    id_to_vol = {dev_id: vol for dev_id, _, vol in endpoints}

    for dev_id in _muted_ids:
        if dev_id in id_to_vol:
            try:
                id_to_vol[dev_id].SetMute(0, None)
                log.info(f"[MUTE] Размучено: {dev_id}")
            except Exception as e:
                log.warning(f"[MUTE] Ошибка размута {dev_id}: {e}")

    _muted_ids = []


def unmute_all_force():
    """Размутить ВСЕ микрофоны (при перезапуске/выходе — на всякий случай)."""
    if not _PYCAW_OK:
        return
    for dev_id, name, vol in _get_all_mic_endpoints():
        try:
            if vol.GetMute():
                vol.SetMute(0, None)
                log.info(f"[MUTE] Force unmute: {name}")
        except Exception:
            pass
    _muted_ids.clear()


def is_available() -> bool:
    return _PYCAW_OK
