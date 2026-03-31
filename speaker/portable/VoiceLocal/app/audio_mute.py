"""
Мут/размут микрофонов через Windows Audio API (pycaw).
"""

import logging
log = logging.getLogger("voice")

try:
    from pycaw.pycaw import AudioUtilities
    _PYCAW_OK = True
except ImportError:
    _PYCAW_OK = False


def _get_capture_endpoints():
    """Активные capture-устройства. Capture = id содержит '{0.0.1.'."""
    if not _PYCAW_OK:
        return []
    result = []
    try:
        all_dev = AudioUtilities.GetAllDevices()
        for d in all_dev:
            if "{0.0.1." not in d.id:
                continue
            state_str = str(d.state)
            if "Active" not in state_str:
                continue
            vol = d.EndpointVolume
            if vol is None:
                continue
            result.append((d.id, d.FriendlyName or d.id[:20], vol))
        log.info(f"[MUTE] Capture active: {len(result)}")
        for dev_id, name, _ in result:
            log.info(f"[MUTE]   {name}")
    except Exception as e:
        log.warning(f"[MUTE] Error: {e}")
    return result


def _find_selected_id(device_index, endpoints):
    """Найти device_id выбранного микрофона по sounddevice индексу."""
    if device_index is None:
        return None
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if not (0 <= device_index < len(devices)):
            return None
        target = devices[device_index]["name"].lower()
        log.info(f"[MUTE] Looking for sd device: '{target}'")
        for dev_id, name, _ in endpoints:
            n = name.lower()
            if target[:25] in n or n[:25] in target:
                log.info(f"[MUTE]   -> match: {name}")
                return dev_id
    except Exception as e:
        log.warning(f"[MUTE] Find error: {e}")
    return None


_muted_ids: list = []


def mute_others(selected_device_index) -> bool:
    global _muted_ids
    if not _PYCAW_OK:
        return False

    endpoints = _get_capture_endpoints()
    selected_id = _find_selected_id(selected_device_index, endpoints)
    log.info(f"[MUTE] Selected ID: {selected_id[:30] if selected_id else None}")

    _muted_ids = []
    for dev_id, name, vol in endpoints:
        if selected_id and dev_id == selected_id:
            log.info(f"[MUTE] Skip (selected): {name}")
            continue
        try:
            if not vol.GetMute():
                vol.SetMute(1, None)
                _muted_ids.append(dev_id)
                log.info(f"[MUTE] Muted: {name}")
        except Exception as e:
            log.warning(f"[MUTE] Mute error {name}: {e}")

    log.info(f"[MUTE] Muted total: {len(_muted_ids)}")
    return True


def unmute_all():
    global _muted_ids
    if not _PYCAW_OK or not _muted_ids:
        return
    endpoints = _get_capture_endpoints()
    id_to_vol = {dev_id: vol for dev_id, _, vol in endpoints}
    for dev_id in list(_muted_ids):
        if dev_id in id_to_vol:
            try:
                id_to_vol[dev_id].SetMute(0, None)
                log.info(f"[MUTE] Unmuted: {dev_id[:30]}")
            except Exception as e:
                log.warning(f"[MUTE] Unmute error: {e}")
    _muted_ids = []


def unmute_all_force():
    if not _PYCAW_OK:
        return
    for dev_id, name, vol in _get_capture_endpoints():
        try:
            if vol.GetMute():
                vol.SetMute(0, None)
                log.info(f"[MUTE] Force unmute: {name}")
        except Exception:
            pass
    _muted_ids.clear()


def is_available() -> bool:
    return _PYCAW_OK
