"""Traduzione tedesco → italiano / inglese, gratuita.

1. Se è impostata DEEPL_API_KEY (piano DeepL API Free: 500.000 caratteri/mese
   gratis) usa DeepL, che dà la qualità migliore.
2. Altrimenti usa l'endpoint pubblico di Google Translate (nessuna chiave).

Le traduzioni sono salvate in cache, così ogni testo si traduce una volta sola.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

CACHE_FILE = Path(os.environ.get("CACHE_DIR", "/tmp")) / "translations.json"
_lock = threading.Lock()
_cache: dict[str, str] = {}
try:
    _cache = json.loads(CACHE_FILE.read_text())
except Exception:  # noqa: BLE001
    _cache = {}


def _key(text: str, lang: str) -> str:
    return lang + ":" + hashlib.sha1(text.encode()).hexdigest()


def _save() -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(_cache))
    except Exception:  # noqa: BLE001
        pass


def _deepl(texts: list[str], lang: str, key: str) -> list[str]:
    host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
    out: list[str] = []
    for i in range(0, len(texts), 40):
        chunk = texts[i : i + 40]
        r = requests.post(
            f"https://{host}/v2/translate",
            headers={"Authorization": f"DeepL-Auth-Key {key}"},
            data=[("text", t) for t in chunk]
            + [("source_lang", "DE"), ("target_lang", "IT" if lang == "it" else "EN-GB")],
            timeout=30,
        )
        r.raise_for_status()
        out.extend(t["text"] for t in r.json()["translations"])
    return out


def _google_one(text: str, lang: str) -> str:
    # l'endpoint accetta testi fino a ~5000 caratteri: dividiamo per paragrafi
    pieces, buf = [], ""
    for para in text.split("\n"):
        if len(buf) + len(para) > 4000:
            pieces.append(buf)
            buf = ""
        buf += para + "\n"
    pieces.append(buf)
    result = []
    for piece in pieces:
        if not piece.strip():
            result.append(piece)
            continue
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "de", "tl": lang, "dt": "t", "q": piece},
            timeout=20,
        )
        r.raise_for_status()
        result.append("".join(seg[0] for seg in r.json()[0] if seg and seg[0]))
    return "".join(result).strip()


def translate_many(texts: list[str], lang: str) -> list[str]:
    """Traduce una lista di testi; in caso di errore restituisce l'originale."""
    if lang not in ("it", "en"):
        return texts
    todo = sorted({t for t in texts if t and t.strip() and _key(t, lang) not in _cache})
    if todo:
        key = os.environ.get("DEEPL_API_KEY", "").strip()
        translated: list[str] | None = None
        if key:
            try:
                translated = _deepl(todo, lang, key)
            except Exception:  # noqa: BLE001 - si ripiega su Google
                translated = None
        if translated is None:
            def safe(t: str) -> str:
                try:
                    return _google_one(t, lang)
                except Exception:  # noqa: BLE001
                    return ""
            with ThreadPoolExecutor(max_workers=6) as pool:
                translated = list(pool.map(safe, todo))
        with _lock:
            for src, dst in zip(todo, translated):
                if dst:
                    _cache[_key(src, lang)] = dst
            _save()
    return [_cache.get(_key(t, lang), t) if t else t for t in texts]
