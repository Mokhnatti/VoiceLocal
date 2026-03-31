"""
Перевод текста через бесплатный Google Translate (без API ключа).
"""

import urllib.request
import urllib.parse
import json
import logging

log = logging.getLogger("voice")


def translate(text: str, target_lang: str, source_lang: str = "auto") -> str:
    if not text:
        return text
    try:
        params = urllib.parse.urlencode({
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text,
        })
        url = f"https://translate.googleapis.com/translate_a/single?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = [item[0] for item in data[0] if item[0]]
        result = "".join(parts).strip()
        log.info(f"[TRANSLATE] {text[:30]} → {result[:30]}")
        return result
    except Exception as e:
        log.warning(f"[TRANSLATE] Error: {e}")
        return text
